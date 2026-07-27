(() => {
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
			frappe.show_alert({
				message: __("Reporte archivado sin eliminar su trazabilidad."),
				indicator: "green",
			});
			$(document).trigger("nexora:data-changed");
		} catch (error) {
			console.error("NEXORA saved report archive failed", error);
			frappe.msgprint({
				title: __("No fue posible archivar"),
				message: __("Revise que el reporte le pertenezca y que conserve acceso al proyecto."),
				indicator: "red",
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
