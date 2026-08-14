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
			Submitted: __("Enviado a revisión"),
			Corrected: __("Corregido"),
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
		complianceType: Object.freeze({
			Identity: __("Identidad"),
			Tax: __("Fiscal"),
			Contractual: __("Contractual"),
			Banking: __("Bancario"),
			Supplier: __("Proveedor"),
			Labor: __("Laboral"),
			Insurance: __("Seguro"),
			Other: __("Otro"),
		}),
		// Hallazgo real de auditoría visual (recorrido real, pantalla «Buscador
		// universal» → «Vista consolidada»): `NXR Operation Effect.dimension`/
		// `.effect_type` viajaban sin traducir — el valor interno en inglés
		// (`financial/db.py`) se pintaba tal cual en la única pantalla que muestra
		// el efecto financiero fila por fila. Conjunto completo tomado de los
		// literales reales de `financial/db.py`, `operational_commands.py` y
		// `corrections.py` — no inventado.
		dimension: Object.freeze({
			Funds: __("Fondos"),
			Reserved: __("Reservado"),
			Cost: __("Costo"),
			Budget: __("Presupuesto"),
			Savings: __("Ahorro"),
			Investment: __("Inversión"),
		}),
		effectType: Object.freeze({
			Executed: __("Ejecutado"),
			Reserved: __("Reservado"),
			Released: __("Liberado"),
			"Internal Transfer": __("Traslado interno"),
			"Real Return": __("Devolución real"),
			"Analytic Adjustment": __("Ajuste analítico"),
			Reclassification: __("Reclasificación"),
			Received: __("Recibido"),
			Reversed: __("Anulado"),
			"Cost Recognized": __("Costo reconocido"),
			"Budget Reserved": __("Presupuesto reservado"),
			"Budget Executed": __("Presupuesto ejecutado"),
			"Savings Applied": __("Ahorro aplicado"),
			"Investment Applied": __("Inversión aplicada"),
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

	// Cada página redefinía estas tres funciones de forma idéntica (mismo cuerpo,
	// palabra por palabra, en once archivos). Viven aquí una sola vez; las páginas
	// mantienen su función local como una llamada de una línea, así ningún punto de
	// uso existente cambia.
	function escapeHtml(value) {
		return frappe.utils.escape_html(String(value ?? ""));
	}

	function formatDate(value) {
		return value ? frappe.datetime.str_to_user(String(value).slice(0, 10)) : __("Sin fecha");
	}

	function generateId() {
		return (
			globalThis.crypto?.randomUUID?.() || `nxr-${Date.now()}-${Math.random().toString(16).slice(2)}`
		);
	}

	function showSuccess({ title = __("Operación completada"), message, documentNumber = "" }) {
		frappe.show_alert({
			message: documentNumber ? `${message} · ${documentNumber}` : message || title,
			indicator: "green",
		});
	}

	function showError(error, { title = __("No fue posible completar la acción"), fallback } = {}) {
		const rawMessage =
			String(error?.message || "").trim() ||
			fallback ||
			__("No se registró ningún cambio. Revise los datos e intente nuevamente.");
		const safeMessage = escapeHtml(rawMessage);
		frappe.msgprint({ title, message: safeMessage, indicator: "red" });
	}

	window.nexora.ui = Object.freeze({
		vocabulary,
		label,
		selectOptions,
		term,
		formatMoney,
		escapeHtml,
		formatDate,
		generateId,
		showSuccess,
		showError,
	});

	const contextState = {
		current: null,
		loadPromise: null,
		projectControl: null,
		writeSerial: 0,
		projectSlot: null,
		surface: null,
		suppressProjectChange: false,
		dirtySources: new Map(),
	};
	const writeRoutes = new Set([
		"nexora-operations",
		"nexora-finance",
		"nexora-evidence",
		"nexora-contracts",
		"nexora-suppliers",
		"nexora-purchase-requests",
	]);

	function routeName() {
		return String((frappe.get_route?.() || [])[0] || "").toLowerCase();
	}

	function cloneContext() {
		return contextState.current ? { ...contextState.current } : null;
	}

	function normalizeContext(value = {}) {
		return {
			project: value.project || null,
			project_label: value.project_label || __("Todos los proyectos"),
			period: value.period || "",
			from_date: value.from_date || null,
			to_date: value.to_date || null,
			user: value.user || frappe.session?.user || "",
			user_label: value.user_label || frappe.session?.user || "",
			roles: Array.isArray(value.roles) ? value.roles : [],
			role_label: value.role_label || __("Usuario NEXORA"),
			can_view_all_projects: Boolean(value.can_view_all_projects),
			can_view_financial_details: value.can_view_financial_details !== false,
			requires_project_selection: Boolean(value.requires_project_selection),
		};
	}

	function publishContext() {
		const detail = cloneContext();
		if (!detail) return;
		document.dispatchEvent(new CustomEvent("nexora:context-changed", { detail }));
		$(document).trigger("nexora:context-changed", [detail]);
	}

	function hasUnsavedChanges() {
		if (window.cur_frm?.is_dirty?.()) return true;
		return [...contextState.dirtySources.values()].some((checker) =>
			typeof checker === "function" ? Boolean(checker()) : Boolean(checker)
		);
	}

	function confirmDiscard() {
		if (!hasUnsavedChanges()) return Promise.resolve(true);
		return new Promise((resolve) => {
			frappe.confirm(
				__(
					"Hay información sin guardar. Cambiar el proyecto o período descartará esos datos. ¿Continuar?"
				),
				() => resolve(true),
				() => resolve(false)
			);
		});
	}

	function setContextBusy(busy) {
		contextState.surface?.setAttribute("aria-busy", busy ? "true" : "false");
		contextState.projectControl?.$input?.prop("disabled", Boolean(busy));
		const periodInput = contextState.surface?.querySelector("[data-nexora-context-period]");
		if (periodInput) periodInput.disabled = Boolean(busy);
	}

	async function loadContext({ force = false, silent = false } = {}) {
		if (contextState.current && !force) return cloneContext();
		if (contextState.loadPromise && !force) return contextState.loadPromise;
		contextState.loadPromise = (async () => {
			try {
				const response = await frappe.call({
					method: "nexora.boot.get_active_context",
					type: "GET",
				});
				contextState.current = normalizeContext(response.message || {});
				renderContextSurface();
				publishContext();
				return cloneContext();
			} catch (error) {
				console.error("NEXORA context load failed", error);
				if (!silent) {
					showError(error, {
						title: __("No fue posible cargar el contexto"),
						fallback: __("Puede continuar en la página actual y volver a intentarlo."),
					});
				}
				throw error;
			} finally {
				contextState.loadPromise = null;
			}
		})();
		return contextState.loadPromise;
	}

	async function updateContext(next = {}, { skipConfirmation = false } = {}) {
		const current = contextState.current || (await loadContext({ silent: true }));
		const candidate = {
			project: Object.prototype.hasOwnProperty.call(next, "project")
				? next.project || null
				: current.project,
			period: Object.prototype.hasOwnProperty.call(next, "period") ? next.period || "" : current.period,
		};
		if (candidate.project === current.project && candidate.period === current.period) {
			return cloneContext();
		}
		if (!skipConfirmation && !(await confirmDiscard())) {
			renderContextSurface();
			return null;
		}
		setContextBusy(true);
		try {
			const response = await frappe.call({
				method: "nexora.boot.set_active_context",
				type: "POST",
				args: { payload: candidate },
				freeze: true,
				freeze_message: __("Actualizando proyecto y período…"),
			});
			contextState.current = normalizeContext(response.message || {});
			contextState.dirtySources.clear();
			renderContextSurface();
			publishContext();
			return cloneContext();
		} catch (error) {
			console.error("NEXORA context update failed", error);
			showError(error, {
				title: __("No fue posible cambiar el contexto"),
				fallback: __("Se conservó el proyecto y período anteriores."),
			});
			renderContextSurface();
			return null;
		} finally {
			setContextBusy(false);
		}
	}

	function registerDirtySource(name, checker = true) {
		contextState.dirtySources.set(String(name), checker);
		return () => contextState.dirtySources.delete(String(name));
	}

	function markDirty(name = routeName()) {
		contextState.dirtySources.set(String(name), true);
	}

	function clearDirty(name = null) {
		if (name) contextState.dirtySources.delete(String(name));
		else contextState.dirtySources.clear();
	}

	/**
	 * Proyecto activo del usuario, cargándolo si aún no está en memoria.
	 * Permite que cualquier pantalla arranque en el mismo proyecto que la anterior
	 * en lugar de obligar a elegirlo otra vez.
	 */
	async function activeProject() {
		if (contextState.current) return contextState.current.project || null;
		try {
			const context = await loadContext({ silent: true });
			return context?.project || null;
		} catch (error) {
			console.warn("NEXORA active project unavailable", error);
			return null;
		}
	}

	/**
	 * Publica el proyecto elegido dentro de una pantalla como contexto activo, de
	 * modo que la barra global y el resto de módulos no queden contradiciéndolo.
	 * No pide confirmación: el usuario ya está actuando sobre esa pantalla.
	 */
	async function setActiveProject(project) {
		const current = contextState.current?.project || null;
		const next = project || null;
		if (current === next) return cloneContext();
		// Dos cambios rapidos generan dos escrituras concurrentes: sin este contador la
		// respuesta antigua puede pisar el contexto y devolver el selector al proyecto
		// anterior. Solo la ultima intencion aplica y publica su resultado.
		const serial = ++contextState.writeSerial;
		const result = await updateContext({ project: next }, { skipConfirmation: true });
		return serial === contextState.writeSerial ? result : cloneContext();
	}

	/**
	 * Suscribe una pantalla a los cambios de contexto y devuelve la función para
	 * darse de baja cuando el wrapper se destruye.
	 */
	function onContextChange(handler) {
		if (typeof handler !== "function") return () => {};
		// Los suscriptores son asíncronos y hacen await de llamadas que pueden fallar.
		// Un rechazo sin capturar aborta la sincronización y solo deja un
		// "unhandledrejection" en consola, con la pantalla a medio actualizar.
		const listener = (event) => {
			try {
				Promise.resolve(handler(event.detail || cloneContext())).catch((error) =>
					console.error("NEXORA context-change handler failed", error)
				);
			} catch (error) {
				console.error("NEXORA context-change handler failed", error);
			}
		};
		document.addEventListener("nexora:context-changed", listener);
		return () => document.removeEventListener("nexora:context-changed", listener);
	}

	window.nexora.context = Object.freeze({
		get: cloneContext,
		load: loadContext,
		update: updateContext,
		activeProject,
		setActiveProject,
		onContextChange,
		registerDirtySource,
		markDirty,
		clearDirty,
		hasUnsavedChanges,
	});

	function setProjectControlValue(value) {
		if (!contextState.projectControl) return;
		const current = contextState.projectControl.get_value() || "";
		const next = value || "";
		if (current === next) return;
		contextState.suppressProjectChange = true;
		Promise.resolve(contextState.projectControl.set_value(next)).finally(() => {
			contextState.suppressProjectChange = false;
		});
	}

	function contextRouteOptions() {
		const context = contextState.current || {};
		return {
			project: context.project || null,
			from_date: context.from_date || null,
			to_date: context.to_date || null,
			nexora_period: context.period || null,
		};
	}

	function bindNavigationContext(shell) {
		if (shell.dataset.contextNavigationBound === "1") return;
		shell.dataset.contextNavigationBound = "1";
		shell.addEventListener(
			"click",
			(event) => {
				if (!event.target.closest(".nxr-product-nav a")) return;
				frappe.route_options = { ...(frappe.route_options || {}), ...contextRouteOptions() };
			},
			true
		);
	}

	function ensureContextSurface() {
		const shell = document.querySelector(".nxr-product-navigation");
		if (!shell) return null;
		bindNavigationContext(shell);
		let surface = shell.querySelector(".nxr-global-context");
		if (!surface) {
			surface = document.createElement("section");
			surface.className = "nxr-global-context";
			surface.setAttribute("aria-label", __("Contexto activo de NEXORA"));
			surface.innerHTML = `
				<div class="nxr-context-project" data-nexora-context-project></div>
				<label class="nxr-context-period">
					<span>${__("Período activo")}</span>
					<input class="form-control" type="month" data-nexora-context-period aria-label="${__("Período activo")}">
				</label>
				<div class="nxr-context-identity">
					<span data-nexora-context-user>${__("Cargando usuario…")}</span>
					<small data-nexora-context-role></small>
				</div>
				<div class="nxr-context-state" role="status" aria-live="polite" data-nexora-context-state></div>`;
			const nav = shell.querySelector(".nxr-product-nav");
			shell.insertBefore(surface, nav || null);
		}
		contextState.surface = surface;
		const projectSlot = surface.querySelector("[data-nexora-context-project]");
		if (projectSlot && contextState.projectSlot !== projectSlot) {
			contextState.projectSlot = projectSlot;
			projectSlot.innerHTML = "";
			contextState.projectControl = frappe.ui.form.make_control({
				parent: $(projectSlot),
				df: {
					fieldname: "nexora_active_project",
					label: __("Proyecto activo"),
					fieldtype: "Link",
					options: "Project",
					change: () => {
						if (contextState.suppressProjectChange) return;
						void updateContext({ project: contextState.projectControl.get_value() || null });
					},
				},
				render_input: true,
			});
		}
		const periodInput = surface.querySelector("[data-nexora-context-period]");
		if (periodInput && periodInput.dataset.bound !== "1") {
			periodInput.dataset.bound = "1";
			periodInput.addEventListener("change", () => {
				void updateContext({ period: periodInput.value });
			});
		}
		return surface;
	}

	function renderContextSurface() {
		const surface = ensureContextSurface();
		if (!surface) return;
		const context = contextState.current;
		if (!context) {
			setText(surface.querySelector("[data-nexora-context-state]"), __("Cargando contexto…"));
			return;
		}
		setProjectControlValue(context.project);
		const periodInput = surface.querySelector("[data-nexora-context-period]");
		if (periodInput && periodInput.value !== context.period) periodInput.value = context.period;
		setText(surface.querySelector("[data-nexora-context-user]"), context.user_label);
		setText(surface.querySelector("[data-nexora-context-role]"), context.role_label);
		setText(
			surface.querySelector("[data-nexora-context-state]"),
			context.requires_project_selection
				? __("Seleccione un proyecto autorizado")
				: `${context.project_label} · ${context.period}`
		);
	}

	function setText(node, value) {
		if (!node) return;
		const text = String(value ?? "");
		if (node.textContent === text) return;
		node.textContent = text;
	}

	document.addEventListener(
		"change",
		(event) => {
			if (event.target.closest?.(".nxr-global-context")) return;
			const route = routeName();
			if (writeRoutes.has(route) && event.target.closest?.(`[id="page-${route}"]`)) {
				markDirty(`page:${route}`);
			}
		},
		true
	);
	document.addEventListener("nexora:dirty-state", (event) => {
		const name = String(event.detail?.name || routeName());
		if (event.detail?.dirty) registerDirtySource(name, true);
		else clearDirty(name);
	});
	document.addEventListener("nexora:data-changed", () => clearDirty());

	const clickNamespace = "click.nexora-report-actions";
	let observer = null;
	let observerFrame = null;

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
		if (observerFrame !== null) window.cancelAnimationFrame(observerFrame);
		observerFrame = null;
		observer = new MutationObserver(scheduleEnhancements);
		observer.observe(document.body, { childList: true, subtree: true });
		scheduleEnhancements();
		void loadContext({ silent: true });
	}

	function scheduleEnhancements() {
		if (observerFrame !== null) return;
		observerFrame = window.requestAnimationFrame(() => {
			observerFrame = null;
			enhanceSavedReports();
			renderContextSurface();
		});
	}

	$(bind);
	if (frappe.router?.on) {
		frappe.router.on("change", () => {
			clearDirty();
			window.setTimeout(() => {
				enhanceSavedReports();
				renderContextSurface();
			}, 0);
		});
	}
})();
