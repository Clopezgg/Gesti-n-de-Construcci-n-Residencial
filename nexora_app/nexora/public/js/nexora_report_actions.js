frappe.provide("nexora");

(() => {
	const vocabulary = Object.freeze({
		fund: __("Fondo"),
		funds: __("Fondos"),
		financialAccount: __("Cuenta guardada"),
		movement: __("Movimiento"),
		movementType: __("Tipo de movimiento"),
		post: __("Registrar definitivamente"),
		referenceDocument: __("Documento que se corrige"),
		allocation: __("Distribución del pago"),
		evidence: __("Comprobante"),
		ledger: __("Historial financiero"),
	});
	const dictionaries = Object.freeze({
		status: Object.freeze({
			Draft: __("Borrador"),
			"In Review": __("Pendiente de revisión"),
			Pending: __("Pendiente"),
			Approved: __("Aprobado"),
			Active: __("Activo"),
			Suspended: __("Suspendido"),
			Completed: __("Completado"),
			"In Liquidation": __("En liquidación"),
			Liquidated: __("Liquidado"),
			"Early Terminated": __("Finalizado anticipadamente"),
			"Cancelled Before Active": __("Cancelado antes de activar"),
			Cancelled: __("Anulado"),
			Executed: __("Registrado definitivamente"),
			Posted: __("Registrado definitivamente"),
			Validated: __("Validado"),
			Rejected: __("Rechazado"),
			Expired: __("Vencido"),
			Inactive: __("Inactivo"),
			Exhausted: __("Agotado"),
			"Compensated Partial": __("Corregido parcialmente"),
			"Compensated Total": __("Corregido totalmente"),
			"Exception Approved": __("Excepción aprobada"),
		}),
		channel: Object.freeze({
			Remittance: __("Remesa"),
			Cash: __("Efectivo"),
			Deposit: __("Depósito bancario"),
			Transfer: __("Transferencia"),
			Other: __("Otro"),
			WhatsApp: __("WhatsApp"),
			"Bank Receipt": __("Comprobante bancario"),
			"Cash Receipt": __("Recibo de efectivo"),
			Email: __("Correo electrónico"),
		}),
		paymentMethod: Object.freeze({
			Cash: __("Efectivo"),
			Deposit: __("Depósito"),
			Transfer: __("Transferencia"),
			Other: __("Otro"),
		}),
		evidenceKind: Object.freeze({
			"Payment Proof": __("Comprobante de pago"),
			"External Authorization": __("Autorización externa"),
			"Real Return": __("Devolución real"),
			"Document Substitution": __("Sustitución de documento"),
			Other: __("Otro"),
		}),
		supplierClassification: Object.freeze({
			Goods: __("Bienes"),
			Services: __("Servicios"),
			Mixed: __("Bienes y servicios"),
			Consultant: __("Consultoría"),
			Logistics: __("Logística"),
			Other: __("Otro"),
		}),
		contractModality: Object.freeze({
			"Lump Sum": __("Suma alzada"),
			"Unit Price": __("Precios unitarios"),
			"Time and Materials": __("Tiempo y materiales"),
			"Labor Only": __("Solo mano de obra"),
			Mixed: __("Mixto"),
			Other: __("Otro"),
		}),
	});

	function label(group, value, fallback = "") {
		const key = String(value ?? "");
		return dictionaries[group]?.[key] || fallback || key;
	}

	function selectOptions(group, { blank = false } = {}) {
		const options = Object.entries(dictionaries[group] || {}).map(([value, text]) => ({
			label: text,
			value,
		}));
		return blank ? [{ label: "", value: "" }, ...options] : options;
	}

	function term(value) {
		const terms = {
			"Fuente de fondos": vocabulary.fund,
			Fuente: vocabulary.fund,
			Fuentes: vocabulary.funds,
			Evidencia: vocabulary.evidence,
			Operación: vocabulary.movement,
		};
		return terms[String(value ?? "")] || String(value ?? "");
	}

	function formatMoney(value, currency = "HNL") {
		return new Intl.NumberFormat("es-HN", {
			style: "currency",
			currency: currency || "HNL",
			minimumFractionDigits: 2,
		}).format(Number(value || 0));
	}

	function showSuccess({ title = __("Operación completada"), message, documentNumber = "" }) {
		frappe.show_alert({
			message: documentNumber ? `${message} · ${documentNumber}` : message || title,
			indicator: "green",
		});
	}

	function showError(error, { title = __("No fue posible completar la acción"), fallback } = {}) {
		const message =
			String(error?.message || "").trim() ||
			fallback ||
			__("No se registró ningún cambio. Revise los datos e intente nuevamente.");
		frappe.msgprint({ title, message, indicator: "red" });
	}

	window.nexora.ui = Object.freeze({
		vocabulary,
		label,
		selectOptions,
		term,
		formatMoney,
		showSuccess,
		showError,
	});

	const clickNamespace = "click.nexora-report-actions";
	let observer = null;

	function isReportsRoute() {
		const route = frappe.get_route ? frappe.get_route() : [];
		return route[0] === "nexora-reports";
	}

	function enhanceSavedReports() {
		if (!isReportsRoute()) return;
		document.querySelectorAll(".nxr-saved-report[data-saved]").forEach((openButton) => {
			if (openButton.parentElement?.classList.contains("nxr-saved-report-row")) return;
			const reportName = openButton.dataset.saved;
			if (!reportName || !openButton.parentNode) return;
			const row = document.createElement("div");
			row.className = "nxr-saved-report-row";
			row.style.display = "grid";
			row.style.gridTemplateColumns = "minmax(0, 1fr) auto";
			row.style.gap = "8px";
			row.style.alignItems = "stretch";
			openButton.parentNode.insertBefore(row, openButton);
			row.appendChild(openButton);
			const archiveButton = document.createElement("button");
			archiveButton.type = "button";
			archiveButton.className = "btn btn-default btn-sm nxr-archive-saved-report";
			archiveButton.dataset.archiveSaved = reportName;
			archiveButton.textContent = __("Archivar");
			archiveButton.title = __("Archivar sin eliminar el historial ni la auditoría");
			row.appendChild(archiveButton);
		});
	}

	async function archiveSavedReport(reportName) {
		try {
			await frappe.call({
				method: "nexora.reports.actions.archive_saved_report",
				type: "POST",
				args: {
					payload: {
						saved_report: reportName,
						idempotency_key: `archive-saved-report-${reportName}`,
					},
				},
				freeze: true,
				freeze_message: __("Archivando reporte…"),
			});
			showSuccess({ message: __("Reporte archivado sin eliminar su trazabilidad.") });
			$(document).trigger("nexora:data-changed");
		} catch (error) {
			console.error("NEXORA saved report archive failed", error);
			showError(error, {
				title: __("No fue posible archivar"),
				fallback: __("Revise que el reporte le pertenezca y que conserve acceso al proyecto."),
			});
		}
	}

	function bind() {
		$(document)
			.off(clickNamespace, "[data-archive-saved]")
			.on(clickNamespace, "[data-archive-saved]", function (event) {
				event.preventDefault();
				event.stopPropagation();
				const reportName = String(this.dataset.archiveSaved || "");
				if (!reportName) return;
				frappe.confirm(
					__(
						"El reporte dejará de mostrarse, pero conservará su número, filtros y auditoría. ¿Continuar?"
					),
					() => archiveSavedReport(reportName)
				);
			});
		if (observer) observer.disconnect();
		observer = new MutationObserver(enhanceSavedReports);
		observer.observe(document.body, { childList: true, subtree: true });
		enhanceSavedReports();
	}

	$(bind);
	if (frappe.router?.on) frappe.router.on("change", () => window.setTimeout(enhanceSavedReports, 0));
})();
