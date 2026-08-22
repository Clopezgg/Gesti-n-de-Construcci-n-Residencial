// `showError` no devuelve valor: encadenarlo con `||` ejecutaba siempre el respaldo y
// mostraba dos diálogos. La rama explícita usa el respaldo solo si el bundle no cargó.
function nexoraShowError(error, { title, message }) {
	if (typeof window.nexora?.ui?.showError === "function") {
		window.nexora.ui.showError(error, { title, fallback: message });
		return;
	}
	frappe.msgprint({ title, message, indicator: "red" });
}
// prettier-ignore
frappe.pages["nexora-dashboard"].on_page_load = function (wrapper) {
	const page = frappe.ui.make_app_page({ parent: wrapper, title: __("NEXORA"), single_column: true });
	const body = $(page.body);
	let requestSerial = 0;
	let activeContext = null;
	let synchronizingProject = false;
	const projectControl = page.add_field({
		fieldname: "project",
		label: __("Proyecto"),
		fieldtype: "Link",
		options: "Project",
		change: () => void projectChanged(),
	});
	const operationLabels = {
		Inflow: __("Fondo"),
		Outflow: __("Gasto"),
		"Internal Transfer": __("Transferencia interna"),
		"Real Return": __("Devolución real"),
		"Commitment Reserve": __("Reserva de compromiso"),
		"Commitment Execution": __("Ejecución de compromiso"),
		"Commitment Release": __("Liberación de compromiso"),
	};
	const presentationLabels = { Cancellation: __("Anulado"), Income: __("Fondo"), Expense: __("Gasto") };
	const statusLabels = {
		Draft: __("Borrador"),
		Executed: __("Registrado definitivamente"),
		Active: __("Activo"),
		Exhausted: __("Agotado"),
		Cancelled: __("Anulado"),
		Approved: __("Aprobado"),
		Rejected: __("Rechazado"),
		"Compensated Partial": __("Corregido parcialmente"),
		"Compensated Total": __("Corregido totalmente"),
		Suspended: __("Suspendido"),
		"In Liquidation": __("En liquidación"),
	};
	const ledgerStatusLabels = { Posted: __("Registrado definitivamente") };
	const channelLabels = { Remittance: __("Remesas"), Cash: __("Efectivo"), Deposit: __("Depósitos"), Transfer: __("Transferencias"), Other: __("Otros") };
	const channelTypeLabels = { Remittance: __("Remesa"), Cash: __("Efectivo"), Deposit: __("Depósito"), Transfer: __("Transferencia"), Other: __("Otro") };
	// NXR-UX-0013: colores tomados del Design System, no de Bootstrap/Frappe con
	// respaldo hexadecimal propio. El gasto usa `--nxr-money-out` (tinta neutra, no
	// rojo) siguiendo la decisión ya escrita en `nexora_design_system.css`: pintar de
	// rojo cada gasto legítimo entrena al usuario a ignorar el rojo, y entonces deja de
	// servir para avisar de lo que sí está mal. Antes esta línea contradecía esa regla.
	const toneColors = { income: "var(--nxr-money-in)", expense: "var(--nxr-money-out)", balance: "var(--nxr-accent)", voided: "var(--nxr-money-void)", warning: "var(--nxr-warning)" };
	const complianceStateLabels = { Vencido: __("Vencido"), "Por vencer": __("Por vencer"), Vigente: __("Vigente") };
	const complianceStateTones = { Vencido: "expense", "Por vencer": "warning", Vigente: "balance" };

	body.html(`
		<main class="nxr-product-shell nxr-dashboard-shell nxr-executive" data-state="loading" aria-busy="true">
			<header class="nxr-panel-header">
				<h1>${__("Panel principal")}</h1>
				<p>${__("Resumen ejecutivo del sistema")}</p>
			</header>
			<section class="nxr-kpi-row" aria-label="${__("Indicadores clave")}"></section>
			<section class="nxr-central-grid">
				<article class="nxr-ds-card nxr-central-budget">
					<header><strong>${__("Ejecución presupuestaria")}</strong></header>
					<div class="nxr-budget-donut-wrap"></div>
				</article>
				<article class="nxr-ds-card nxr-central-cashflow">
					<header><strong>${__("Flujo de fondos")}</strong><span>${__("Últimos 6 meses")}</span></header>
					<div class="nxr-cashflow-chart"></div>
				</article>
				<article class="nxr-ds-card nxr-central-notifications">
					<header><strong>${__("Notificaciones")}</strong></header>
					<ul class="nxr-central-notifications-list"></ul>
				</article>
			</section>
			<section class="nxr-operational-grid">
				<article class="nxr-ds-card nxr-operational-recent">
					<header><strong>${__("Últimas operaciones")}</strong></header>
					<div class="nxr-ds-table-wrap"><table class="nxr-ds-table nxr-operational-recent-table">
						<thead><tr><th>${__("Documento")}</th><th>${__("Fecha")}</th><th>${__("Descripción")}</th><th data-numeric="true">${__(
							"Monto"
						)}</th><th>${__("Estado")}</th></tr></thead>
						<tbody></tbody>
					</table></div>
				</article>
				<article class="nxr-ds-card nxr-operational-projects">
					<header><strong>${__("Proyectos activos")}</strong></header>
					<div class="nxr-ds-table-wrap"><table class="nxr-ds-table nxr-operational-projects-table">
						<thead><tr><th>${__("Proyecto")}</th><th data-numeric="true">${__("% avance")}</th><th data-numeric="true">${__(
							"Presupuesto"
						)}</th><th data-numeric="true">${__("Ejecutado")}</th></tr></thead>
						<tbody></tbody>
					</table></div>
				</article>
			</section>
			<section class="nxr-ds-card nxr-quick-actions">
				<header><strong>${__("Acciones rápidas")}</strong></header>
				<div class="nxr-quick-actions-grid">
					<button type="button" class="nxr-ds-btn nxr-ds-btn--secondary" data-action="income">${__("Nueva operación")}</button>
					<button type="button" class="nxr-ds-btn nxr-ds-btn--secondary" data-quick-route="nexora-purchase-requests">${__(
						"Nueva solicitud de compra"
					)}</button>
					<button type="button" class="nxr-ds-btn nxr-ds-btn--secondary" data-quick-route="nexora-project">${__(
						"Nuevo proyecto"
					)}</button>
					<button type="button" class="nxr-ds-btn nxr-ds-btn--secondary" data-action="expense">${__("Registrar gasto")}</button>
					<button type="button" class="nxr-ds-btn nxr-ds-btn--secondary" data-quick-route="nexora-evidence">${__(
						"Cargar evidencia"
					)}</button>
					<button type="button" class="nxr-ds-btn nxr-ds-btn--secondary" data-quick-route="nexora-reports">${__(
						"Generar reporte"
					)}</button>
				</div>
			</section>
			<section class="nxr-ds-card nxr-sap-card" hidden>
				<header><strong>${__("Integración SAP")}</strong><span data-sap-status-badge></span></header>
				<div class="nxr-sap-card-body"></div>
			</section>
			<section class="nxr-dashboard-welcome nxr-executive-hero">
				<div><p class="nxr-eyebrow">NX00 · ${__("RESUMEN EJECUTIVO")}</p><h2 class="nxr-project-name">${__("NEXORA")}</h2><p>${__("Gestión Integral de Fondos, Proyectos y Operaciones")}</p><small class="nxr-dashboard-context">${__("Preparando información canónica…")}</small><div class="nxr-dashboard-active-context"><span class="nxr-dashboard-period"></span><span class="nxr-dashboard-user"></span></div></div>
				<div class="nxr-dashboard-primary-actions"><span class="nxr-schedule-pill">${__("Actualizando")}</span><button class="nxr-ds-btn nxr-ds-btn--primary nxr-ds-btn--sm" data-action="income">${__("Registrar fondos")}</button><button class="nxr-ds-btn nxr-ds-btn--secondary nxr-ds-btn--sm" data-action="expense">${__("Registrar gasto")}</button><button class="nxr-ds-btn nxr-ds-btn--secondary nxr-ds-btn--sm" data-project-360>${__("Ver proyecto 360°")}</button></div>
			</section>
			<section class="nxr-agenda" aria-labelledby="nxr-agenda-title">
				<header><h3 id="nxr-agenda-title">${__("Qué requiere su atención hoy")}</h3><span class="nxr-agenda-count" aria-live="polite"></span></header>
				<ol class="nxr-agenda-list"></ol>
			</section>
			<section class="nxr-alert-rows nxr-executive-alerts"></section>
			<section class="nxr-executive-metrics"></section>
			<section class="nxr-executive-grid nxr-executive-primary">
				<article class="nxr-ds-card nxr-executive-card"><header><div><strong>${__("Avance de la obra")}</strong><span>${__("Comparación física y financiera")}</span></div><button class="nxr-ds-btn nxr-ds-btn--secondary nxr-ds-btn--sm" data-route="nexora-reports" data-report="PR03">${__("Detalle")}</button></header><div class="nxr-progress-summary"></div></article>
				<article class="nxr-ds-card nxr-executive-card"><header><div><strong>${__("Gastos por categoría")}</strong><span>${__("Ejecución del período activo")}</span></div><button class="nxr-ds-btn nxr-ds-btn--secondary nxr-ds-btn--sm" data-route="nexora-reports" data-report="FI02">${__("Ver gastos")}</button></header><div class="nxr-expense-bars nxr-bars"></div></article>
				<article class="nxr-ds-card nxr-executive-card"><header><div><strong>${__("Fondos por canal")}</strong><span>${__("Remesas, depósitos y transferencias")}</span></div><button class="nxr-ds-btn nxr-ds-btn--secondary nxr-ds-btn--sm" data-route="nexora-reports" data-report="FI01">${__("Ver fondos")}</button></header><div class="nxr-income-bars nxr-bars"></div></article>
			</section>
			<section class="nxr-executive-grid nxr-executive-secondary">
				<article class="nxr-ds-card nxr-executive-card nxr-compact"><header><div><strong>${__("Pendiente de pagar")}</strong><span>${__("Vencido o próximo")}</span></div><button class="nxr-ds-btn nxr-ds-btn--secondary nxr-ds-btn--sm" data-route="nexora-reports" data-report="FI03">${__("Revisar pendientes")}</button></header><div class="nxr-payables-list"></div></article>
				<article class="nxr-ds-card nxr-executive-card nxr-compact"><header><div><strong>${__("Fondos y remesas")}</strong><span>${__("Saldo independiente por fondo")}</span></div><button class="nxr-ds-btn nxr-ds-btn--secondary nxr-ds-btn--sm" data-route="nexora-reports" data-report="FI01">${__("Estado de cuenta")}</button></header><div class="nxr-balance-row nxr-funds-list"></div></article>
				<article class="nxr-ds-card nxr-executive-card nxr-compact"><header><div><strong>${__("Inventario crítico")}</strong><span>${__("Saldos agotados o negativos")}</span></div><button class="nxr-ds-btn nxr-ds-btn--secondary nxr-ds-btn--sm" data-route="nexora-reports" data-report="MM03">${__("Revisar inventario")}</button></header><div class="nxr-inventory-list"></div></article>
			</section>
			<section class="nxr-executive-grid nxr-executive-secondary">
				<article class="nxr-ds-card nxr-executive-card nxr-compact"><header><div><strong>${__("Actividad reciente")}</strong><span>${__("Historial financiero cronológico")}</span></div><button class="nxr-ds-btn nxr-ds-btn--secondary nxr-ds-btn--sm" data-route="nexora-finance" data-nexora-operational-ledger="1">${__("Ver actividad")}</button></header><div class="nxr-activity-list"></div></article>
				<article class="nxr-ds-card nxr-executive-card nxr-compact"><header><div><strong>${__("Comprobantes y fotografías")}</strong><span>${__("Expediente cronológico")}</span></div><button class="nxr-ds-btn nxr-ds-btn--secondary nxr-ds-btn--sm" data-route="nexora-evidence">${__("Ver comprobantes")}</button></header><div class="nxr-evidence-gallery"></div></article>
				<article class="nxr-ds-card nxr-executive-card nxr-compact"><header><div><strong>${__("Tareas frecuentes")}</strong><span>${__("Acciones según su contexto activo")}</span></div></header><div class="nxr-quick-links"><button data-route="nexora-purchase-requests">${__("Crear solicitud de compra")}</button><button data-route="nexora-suppliers">${__("Revisar proveedores")}</button><button data-route="nexora-search">${__("Buscar documento")}</button><button data-route="nexora-closing">${__("Revisar cierre")}</button></div></article>
			</section>
			<section class="nxr-executive-grid nxr-executive-secondary">
				<article class="nxr-ds-card nxr-executive-card nxr-compact"><header><div><strong>${__("Actividad del equipo")}</strong><span>${__("Decisiones recientes de otros usuarios")}</span></div></header><div class="nxr-team-activity-list"></div></article>
				<article class="nxr-ds-card nxr-executive-card nxr-compact"><header><div><strong>${__("Cumplimiento y vencimientos")}</strong><span>${__("Entidades con documentación por vencer")}</span></div><button class="nxr-ds-btn nxr-ds-btn--secondary nxr-ds-btn--sm" data-route="nexora-entities">${__("Ver entidades")}</button></header><div class="nxr-compliance-list"></div></article>
				<article class="nxr-ds-card nxr-executive-card nxr-compact"><header><div><strong>${__("Accesos recientes")}</strong><span>${__("Retome un trabajo interrumpido")}</span></div></header><div class="nxr-recent-routes-list"></div></article>
			</section>
			<section class="nxr-ds-card nxr-executive-card nxr-contract-panel"><header><div><strong>${__("Estado contractual")}</strong><span>${__("Valor, ejecutado, pagado y saldo")}</span></div><button class="nxr-ds-btn nxr-ds-btn--secondary nxr-ds-btn--sm" data-route="nexora-reports" data-report="CO01">${__("Ver contratos")}</button></header><div class="nxr-contract-rows nxr-contract-table"></div></section>
			<section class="nxr-ds-card nxr-executive-card"><header><div><strong>${__("Últimos movimientos")}</strong><span>${__("Trazabilidad financiera")}</span></div></header><div class="nxr-ds-table-wrap"><table class="nxr-ds-table nxr-dashboard-recent-rows"><thead><tr><th>${__("Documento")}</th><th>${__("Fecha")}</th><th>${__("Tipo")}</th><th>${__("Estado")}</th><th data-numeric="true">${__("Importe")}</th></tr></thead><tbody></tbody></table></div></section>
		</main>
	`);

	page.add_button(__("Actualizar datos"), () => load(true), "primary");
	body.on("click", "[data-action]", function () {
		const action = $(this).data("action");
		frappe.route_options = { ...routeContext(), nexora_action: action };
		frappe.set_route("nexora-finance");
	});
	body.on("change", "[data-nexora-dashboard-period]", function () {
		void changeDashboardPeriod($(this).val());
	});
	body.on("click", "[data-route]:not([data-action])", function () {
		frappe.route_options = { ...routeContext(), nexora_report: $(this).data("report") || null };
		frappe.set_route($(this).data("route"));
	});
	// Panel «Acciones rápidas» (reconstrucción visual definitiva): mismo
	// mecanismo real que `[data-route]`, atributo propio para no competir con su
	// exigencia de `nexora_report`.
	body.on("click", "[data-quick-route]", function () {
		frappe.route_options = routeContext();
		frappe.set_route($(this).data("quick-route"));
	});
	body.on("click", "[data-sap-configure]", function () {
		frappe.set_route("nexora-sap");
	});
	// NXR-UX-0010: acceso contextual al contexto 360° del proyecto activo — no un
	// destino nuevo en la navegación principal, solo alcanzable desde donde el
	// proyecto ya está seleccionado (atributo propio, no `[data-action]`, para no
	// caer en el manejador que siempre enruta a "nexora-finance").
	body.on("click", "[data-project-360]", function () {
		frappe.route_options = { project: routeContext().project };
		frappe.set_route("nexora-project");
	});
	$(document).on("nexora:data-changed.nexora-dashboard", () => load(false));
	const contextListener = (event) => void applyContext(event.detail || {}, true);
	document.addEventListener("nexora:context-changed", contextListener);
	$(wrapper).on("remove", () => {
		$(document).off("nexora:data-changed.nexora-dashboard");
		document.removeEventListener("nexora:context-changed", contextListener);
	});

	const launchOptions = frappe.route_options || {};
	frappe.route_options = null;
	void initialize(launchOptions);

	async function initialize(options) {
		try {
			const context = await window.nexora.context?.load?.({ silent: true });
			activeContext = context || fallbackContext(options.project);
			if (options.project && options.project !== activeContext.project) {
				activeContext = (await window.nexora.context?.update?.({ project: options.project }, { skipConfirmation: true })) || { ...activeContext, project: options.project };
			}
		} catch (error) {
			console.warn("NEXORA dashboard context fallback", error);
			activeContext = fallbackContext(options.project);
		}
		await applyContext(activeContext, true);
		void loadSapCard();
	}

	function fallbackContext(project = null) {
		return {
			project: project || null,
			project_label: project || __("Todos los proyectos"),
			period: "",
			from_date: null,
			to_date: null,
			user_label: frappe.session.user,
			role_label: __("Usuario NEXORA"),
			can_view_all_projects: !requiresProjectSelectionFromRoles(),
			can_view_financial_details: true,
			requires_project_selection: requiresProjectSelectionFromRoles() && !project,
		};
	}

	async function applyContext(context, reload) {
		activeContext = { ...fallbackContext(), ...(context || {}) };
		const desiredProject = activeContext.project || "";
		if ((projectControl.get_value() || "") !== desiredProject) {
			synchronizingProject = true;
			try {
				await projectControl.set_value(desiredProject);
			} finally {
				synchronizingProject = false;
			}
		}
		renderIdentity();
		if (!reload) return;
		if (requiresProjectSelection()) renderProjectPrompt();
		else await load(false);
	}

	async function projectChanged() {
		if (synchronizingProject) return;
		const project = projectControl.get_value() || null;
		if (!window.nexora.context?.update) {
			activeContext = { ...fallbackContext(project), ...(activeContext || {}), project };
			if (requiresProjectSelection()) renderProjectPrompt();
			else await load(false);
			return;
		}
		const updated = await window.nexora.context.update({ project });
		if (!updated) {
			await applyContext(activeContext, false);
			return;
		}
		await applyContext(updated, true);
	}

	function routeContext() {
		return {
			project: projectControl.get_value() || activeContext?.project || null,
			from_date: activeContext?.from_date || null,
			to_date: activeContext?.to_date || null,
			nexora_period: activeContext?.period || null,
		};
	}

	function snapshotPayload() {
		return {
			project: projectControl.get_value() || activeContext?.project || null,
			from_date: activeContext?.from_date || null,
			to_date: activeContext?.to_date || null,
		};
	}

	function requiresProjectSelectionFromRoles() {
		return frappe.user.has_role("NEXORA Project Viewer") && ![
			"System Manager",
			"NEXORA Administrator",
			"NEXORA Finance Manager",
			"NEXORA Finance Operator",
			"NEXORA Auditor",
		].some((role) => frappe.user.has_role(role));
	}

	function requiresProjectSelection() {
		return Boolean(activeContext?.requires_project_selection || (requiresProjectSelectionFromRoles() && !projectControl.get_value()));
	}

	function requestExecutiveSnapshot(payload, freeze) {
		return new Promise((resolve, reject) => {
			let settled = false;
			const finish = (callback, value) => {
				if (settled) return;
				settled = true;
				window.clearTimeout(deadline);
				callback(value);
			};
			const deadline = window.setTimeout(
				() =>
					finish(
						reject,
						new Error(
							__(
								"El resumen ejecutivo excedió 120 segundos. Revise la conexión y vuelva a intentar.",
							),
						),
				),
				120000,
			);
			try {
				frappe.call({
					method: "nexora.dashboard.executive.get_executive_snapshot",
					type: "POST",
					args: { payload },
					freeze,
					freeze_message: __("Actualizando resumen ejecutivo…"),
					callback: (response) => finish(resolve, response?.message || {}),
					error: (error) =>
						finish(
							reject,
							error instanceof Error
								? error
								: new Error(__("El servidor no pudo entregar el resumen ejecutivo.")),
						),
				});
			} catch (error) {
				finish(reject, error);
			}
		});
	}

	async function changeDashboardPeriod(period) {
		if (!period || period === activeContext?.period) return;
		if (!window.nexora.context?.update) return;
		const updated = await window.nexora.context.update({ period });
		if (!updated) {
			renderIdentity();
			return;
		}
		await applyContext(updated, true);
	}

	function renderIdentity(period = null) {
		const activePeriod = periodKey(period) || activeContext?.period || monthKey(new Date());
		body.find(".nxr-dashboard-period").html(`${__("Período")}: ${periodSelect(activePeriod)}`);
		body.find(".nxr-dashboard-user").text(`${activeContext?.user_label || frappe.session.user} · ${activeContext?.role_label || __("Usuario NEXORA")}`);
	}

	function periodKey(period = null) {
		if (period?.from_date) return String(period.from_date).slice(0, 7);
		return null;
	}

	function periodSelect(activePeriod) {
		const options = relativePeriods(activePeriod)
			.map((period) => `<option value="${escape(period)}"${period === activePeriod ? " selected" : ""}>${escape(periodLabel(period))}</option>`)
			.join("");
		return `<select class="nxr-ds-select" data-nexora-dashboard-period aria-label="${__("Período")}">${options}</select>`;
	}

	function relativePeriods(activePeriod) {
		const [year, month] = String(activePeriod).split("-").map((part) => Number(part));
		if (!year || !month) return [activePeriod].filter(Boolean);
		return [-1, 0, 1, 2].map((offset) => monthKey(new Date(year, month - 1 + offset, 1)));
	}

	function monthKey(value) {
		return `${value.getFullYear()}-${String(value.getMonth() + 1).padStart(2, "0")}`;
	}

	function periodLabel(period) {
		const [year, month] = String(period).split("-").map((part) => Number(part));
		if (!year || !month) return period;
		const dateValue = new Date(year, month - 1, 1);
		const monthLabel = new Intl.DateTimeFormat("es", { month: "long" }).format(dateValue);
		const label = `${monthLabel} ${year}`;
		return label.charAt(0).toUpperCase() + label.slice(1);
	}

	function renderProjectPrompt() {
		body.find(".nxr-dashboard-shell").attr({ "data-state": "ready", "aria-busy": "false" });
		body.find(".nxr-project-name").text(__("Seleccione un proyecto"));
		body.find(".nxr-dashboard-context").text(__("Su perfil requiere un proyecto autorizado para mostrar información financiera."));
		body.find(".nxr-executive-alerts").html(alertCard("info", __("Proyecto requerido"), __("Use el selector de contexto para continuar.")));
		renderIdentity();
		renderMetrics([]);
	}

	async function load(freeze) {
		if (requiresProjectSelection()) {
			renderProjectPrompt();
			return;
		}
		const serial = ++requestSerial;
		body.find(".nxr-dashboard-shell").attr({ "data-state": "loading", "aria-busy": "true" });
		try {
			const snapshot = await requestExecutiveSnapshot(snapshotPayload(), Boolean(freeze));
			if (serial !== requestSerial) return;
			render(snapshot);
		} catch (error) {
			if (serial !== requestSerial) return;
			console.error("NEXORA dashboard failed", error);
			body.find(".nxr-dashboard-shell").attr({ "data-state": "error", "aria-busy": "false" });
			nexoraShowError(error, { title: __("Resumen no disponible"), message: __("Revise la conexión, el proyecto o sus permisos y vuelva a intentar.") });
		}
	}

	function render(data) {
		const finance = data.finance || {};
		const budgets = data.budgets || {};
		const pendingAccounts = data.pending_accounts || {};
		const progress = data.progress || {};
		const analytics = data.analytics || {};
		const executive = data.executive || {};
		const sourceTotals = analytics.source_totals || {};
		body.find(".nxr-project-name").text(data.context?.project_label || activeContext?.project_label || __("Todos los proyectos"));
		body.find(".nxr-dashboard-context").text(`${finance.source_count || 0} ${__("fondos")} · ${analytics.contract_count || 0} ${__("contratos")} · ${pendingAccounts.count || 0} ${__("pendientes de pago")}`);
		body.find(".nxr-schedule-pill").text(Number(executive.projected_available_hnl || 0) < 0 ? __("Atención financiera") : __("Información actualizada"));
		renderIdentity(data.period || null);
		renderAgenda(data);
		renderAlerts(sourceTotals);
		const metrics = [
			{ label: __("Saldo disponible"), value: finance.total_available_hnl ?? executive.cash_available_hnl, tone: "balance" },
			{ label: __("Comprometido"), value: executive.committed_hnl ?? finance.total_reserved_hnl, tone: "balance" },
			{ label: __("Pendiente de pagar"), value: executive.pending_obligations_hnl ?? pendingAccounts.total_hnl, tone: "expense" },
			{ label: __("Fondos netos"), value: executive.net_received_hnl ?? executive.received_hnl, tone: "income" },
			{ label: __("Gastos ejecutados"), value: executive.spent_hnl, tone: "expense" },
			{ label: __("Presupuesto disponible"), value: executive.budget_available_hnl ?? budgets.total_available_hnl, tone: "balance" },
		];
		renderMetrics(activeContext?.can_view_financial_details === false ? [] : metrics);
		renderKpiRow(data);
		renderBudgetDonut(budgets);
		renderCashflowChart(data.cash_flow_monthly || []);
		renderCentralNotifications(data);
		renderOperationalRecent(data.recent_operations || []);
		renderActiveProjects(data.projects?.rows || []);
		renderProgress(progress.physical_percent, executive.financial_percent, progress.operational || {});
		renderBars(".nxr-expense-bars", analytics.expenses_by_category || [], (row) => row.label, "expense");
		renderBars(".nxr-income-bars", analytics.income_by_channel || [], (row) => channelLabels[row.label] || row.label, "income");
		renderPayables(pendingAccounts.items || []);
		renderFunds(analytics.rows || []);
		renderInventory(analytics.critical_inventory || []);
		renderActivity(data.recent_operations || []);
		renderEvidence(data.evidence?.items || []);
		renderContracts(analytics.contracts || data.contracts?.items || []);
		renderTeamActivity(data.team_activity?.items || []);
		renderCompliance(data.compliance_alerts?.items || []);
		renderRecentRoutes();
		renderRecent(data.recent_operations || []);
		body.find(".nxr-dashboard-shell").attr({ "data-state": "ready", "aria-busy": "false" });
	}

	/**
	 * «¿Qué debo hacer hoy?» era la única pregunta del panel que nadie respondía. Los
	 * datos estaban —vencimientos, comprobantes, conciliaciones, alertas—, pero repartidos
	 * entre nueve tarjetas que el usuario tenía que recorrer y ordenar mentalmente.
	 *
	 * Aquí no se pide nada nuevo al servidor: se reúne lo que ya venía y se ordena por lo
	 * que cuesta no atenderlo. Un vencimiento de pago pesa más que un comprobante sin
	 * revisar, y ambos pesan más que una nota informativa.
	 */
	function renderAgenda(data) {
		const analytics = data.analytics || {};
		const pending = data.pending_accounts || {};
		const items = [];

		for (const row of (pending.items || []).slice(0, 3)) {
			const due = row.due_date ? new Date(row.due_date) : null;
			const overdue = due && due < new Date(frappe.datetime.get_today());
			items.push({
				weight: overdue ? 0 : 1,
				level: overdue ? "critical" : "warning",
				title: overdue ? __("Pago vencido") : __("Pago próximo"),
				detail: `${row.title || row.document_number || ""} · ${money(row.amount_hnl)}`,
				action: __("Revisar"),
				route: "nexora-reports",
				report: "FI03",
			});
		}

		const unreconciled = Number(analytics.unreconciled_count || 0);
		if (unreconciled) {
			items.push({
				weight: 2,
				level: "warning",
				title: __("Fondos sin conciliar"),
				detail: __("{0} registro(s) de fondos esperan su respaldo documental.", [unreconciled]),
				action: __("Conciliar"),
				route: "nexora-evidence",
			});
		}

		for (const alert of (data.alerts || []).slice(0, 3)) {
			if (alert.level === "success") continue;
			items.push({
				weight: alert.level === "danger" || alert.level === "critical" ? 0 : 3,
				level: alert.level === "danger" ? "critical" : alert.level || "info",
				title: alert.title,
				detail: alert.message,
				action: __("Ver"),
				route: "nexora-search",
			});
		}

		items.sort((left, right) => left.weight - right.weight);
		const visible = items.slice(0, 5);
		const count = body.find(".nxr-agenda-count");
		count.text(
			visible.length
				? __("{0} de {1}", [visible.length, items.length])
				: __("Nada pendiente")
		);
		body.find(".nxr-agenda-list").html(
			visible.length
				? visible
						.map(
							(item) => `<li class="nxr-agenda-item" data-level="${escape(item.level)}">
					<span class="nxr-agenda-mark" aria-hidden="true"></span>
					<span class="nxr-agenda-text"><strong>${escape(item.title)}</strong><small>${escape(item.detail || "")}</small></span>
					<button type="button" class="nxr-agenda-action" data-route="${escape(item.route)}"${
								item.report ? ` data-report="${escape(item.report)}"` : ""
							}>${escape(item.action)}</button>
				</li>`
						)
						.join("")
				: `<li class="nxr-agenda-item" data-level="clear">
					<span class="nxr-agenda-mark" aria-hidden="true"></span>
					<span class="nxr-agenda-text"><strong>${__("Todo al día")}</strong><small>${__(
						"No hay vencimientos, conciliaciones ni alertas abiertas."
					)}</small></span>
				</li>`
		);
	}

	// NXR-UX-0015: hasta aquí llegaban también los pagos vencidos y la conciliación
	// pendiente, repetidos con otra forma justo debajo de `renderAgenda` — misma
	// pregunta ("¿qué requiere atención hoy?") respondida dos veces seguidas. Esa parte
	// se retiró: `renderAgenda` ya la resuelve, ordenada por urgencia y con acción
	// directa. Lo que queda aquí es un aviso distinto — de auditoría, no de urgencia —
	// que la agenda no cubre: que el período incluye movimientos corregidos o
	// reversados, cuyo respaldo sigue existiendo en el historial.
	function renderAlerts(sourceTotals) {
		const rows = [];
		if (Number(sourceTotals.reversed_hnl || 0) > 0) {
			rows.push({
				level: "info",
				title: __("Movimientos corregidos"),
				message: __("El período incluye anulaciones o reversos preservados en el historial financiero."),
			});
		}
		body.find(".nxr-executive-alerts").html(rows.map((row) => alertCard(row.level, row.title, row.message)).join(""));
	}

	function alertCard(level, title, message) { return `<article class="nxr-executive-alert" data-level="${escape(level)}"><i></i><span><strong>${escape(title)}</strong><small>${escape(message)}</small></span></article>`; }
	function renderMetrics(rows) { body.find(".nxr-executive-metrics").html(rows.length ? rows.map((row) => { const tone = row.tone === "income" && Number(row.value || 0) < 0 ? "voided" : row.tone; return `<article class="nxr-executive-metric nxr-ds-card" data-tone="${escape(tone || "neutral")}"><span>${escape(row.label)}</span><strong${toneStyle(tone)}>${money(row.value)}</strong></article>`; }).join("") : `<article class="nxr-executive-metric nxr-ds-card"><span>${__("Información financiera")}</span><strong>${requiresProjectSelection() ? __("Seleccione un proyecto") : __("No disponible para este perfil")}</strong></article>`); }
	// RECONSTRUCCIÓN VISUAL DEFINITIVA — fila de 5 KPI ejecutivos exigida por el
	// mandato, con variación real contra `previous_period` (misma ventana de
	// días, inmediatamente anterior, calculada en `snapshot_query.py`). Nunca
	// una cifra inventada: sin período anterior real, se dice explícitamente en
	// vez de mostrar un "+0%" que sugeriría un dato que no existe.
	function kpiFigure(row) {
		if (row.kind === "percent") return `${Number(row.value || 0).toFixed(1)}%`;
		if (row.kind === "count") return number(row.value || 0);
		return money(row.value);
	}

	function kpiVariation(row) {
		const current = Number(row.value || 0);
		const prior = Number(row.previous || 0);
		if (row.kind === "count") {
			const delta = current - prior;
			return { text: `${delta > 0 ? "+" : ""}${delta}`, positive: delta >= 0 };
		}
		if (row.kind === "percent") {
			const delta = current - prior;
			return { text: `${delta > 0 ? "+" : ""}${delta.toFixed(1)} pp`, positive: delta >= 0 };
		}
		if (!prior) return { text: __("Sin período anterior"), positive: null };
		const percent = ((current - prior) / Math.abs(prior)) * 100;
		return { text: `${percent > 0 ? "+" : ""}${percent.toFixed(1)}%`, positive: percent >= 0 };
	}

	function kpiCardHtml(row) {
		const variation = kpiVariation(row);
		const variationClass =
			variation.positive === null ? "is-neutral" : variation.positive ? "is-positive" : "is-negative";
		return `<article class="nxr-kpi-card nxr-ds-card" data-tone="${escape(row.tone)}">
			<span class="nxr-kpi-label">${escape(row.label)}</span>
			<strong class="nxr-kpi-value"${toneStyle(row.tone)}>${kpiFigure(row)}</strong>
			<span class="nxr-kpi-variation ${variationClass}">${escape(variation.text)}</span>
		</article>`;
	}

	function renderKpiRow(data) {
		const executive = data.executive || {};
		const previous = data.previous_period || {};
		if (activeContext?.can_view_financial_details === false) {
			body.find(".nxr-kpi-row").html(empty(__("No disponible para este perfil.")));
			return;
		}
		const rows = [
			{
				label: __("Saldo disponible"),
				value: executive.cash_available_hnl,
				previous: previous.cash_available_hnl,
				tone: "balance",
				kind: "money",
			},
			{
				label: __("Comprometido"),
				value: executive.committed_hnl,
				previous: previous.committed_hnl,
				tone: "balance",
				kind: "money",
			},
			{
				label: __("Pendiente de pagar"),
				value: executive.pending_obligations_hnl,
				previous: previous.pending_obligations_hnl,
				tone: "expense",
				kind: "money",
			},
			{
				label: __("Proyectos activos"),
				value: executive.active_projects_count,
				previous: previous.active_projects_count,
				tone: "balance",
				kind: "count",
			},
			{
				label: __("% Ejecución promedio"),
				value: executive.average_execution_percent,
				previous: previous.average_execution_percent,
				tone: "balance",
				kind: "percent",
			},
		];
		body.find(".nxr-kpi-row").html(rows.map(kpiCardHtml).join(""));
	}

	// COLUMNA 1 del bloque central: donut CSS real (conic-gradient), sin ninguna
	// librería de gráficos nueva — mismos tres colores semánticos que el resto
	// del panel ya usa (`toneColors`).
	function renderBudgetDonut(budgets) {
		const total = Number(budgets.total_approved_hnl || 0);
		const executed = Number(budgets.total_executed_hnl || 0);
		const committed = Number(budgets.total_committed_hnl || 0);
		const available = Number(budgets.total_available_hnl || 0);
		const container = body.find(".nxr-budget-donut-wrap");
		if (!total && !executed && !committed && !available) {
			container.html(empty(__("Sin presupuesto registrado para este período.")));
			return;
		}
		const base = total > 0 ? total : executed + committed + available || 1;
		const executedPct = Math.max((executed / base) * 100, 0);
		const committedPct = Math.max((committed / base) * 100, 0);
		const gradient = `conic-gradient(var(--nxr-money-out) 0% ${executedPct}%, var(--nxr-warning) ${executedPct}% ${
			executedPct + committedPct
		}%, var(--nxr-money-in) ${executedPct + committedPct}% 100%)`;
		container.html(`
			<div class="nxr-budget-donut" style="background:${gradient}">
				<span>${money(total)}</span><small>${__("Presupuesto total")}</small>
			</div>
			<ul class="nxr-budget-legend">
				<li data-tone="expense"><i></i>${__("Ejecutado")}<b>${money(executed)}</b></li>
				<li data-tone="warning"><i></i>${__("Comprometido")}<b>${money(committed)}</b></li>
				<li data-tone="income"><i></i>${__("Disponible")}<b>${money(available)}</b></li>
			</ul>
		`);
	}

	// COLUMNA 2: serie temporal real de `cash_flow_monthly` (6 meses, calculada
	// en `cashflow_query.py` reutilizando `source_query.source_totals`) — SVG
	// propio, sin ninguna librería de gráficos nueva.
	function monthShortLabel(month) {
		const [year, monthNumber] = String(month)
			.split("-")
			.map((part) => Number(part));
		if (!year || !monthNumber) return month;
		return new Intl.DateTimeFormat("es", { month: "short" })
			.format(new Date(year, monthNumber - 1, 1))
			.replace(".", "");
	}

	function renderCashflowChart(rows) {
		const container = body.find(".nxr-cashflow-chart");
		if (!rows.length) {
			container.html(empty(__("Sin datos para mostrar.")));
			return;
		}
		const width = 320;
		const height = 140;
		const paddingX = 10;
		const paddingY = 18;
		const values = rows.flatMap((row) => [row.income_hnl, row.expense_hnl, row.balance_hnl]).map(Number);
		const maxValue = Math.max(...values, 1);
		const minValue = Math.min(...values, 0);
		const range = maxValue - minValue || 1;
		const stepX = (width - paddingX * 2) / Math.max(rows.length - 1, 1);
		const scaleY = (value) => height - paddingY - ((value - minValue) / range) * (height - paddingY * 2);
		const balancePoints = rows
			.map((row, index) => `${paddingX + index * stepX},${scaleY(row.balance_hnl)}`)
			.join(" ");
		const barWidth = Math.min(stepX * 0.26, 12);
		const zeroY = scaleY(0);
		const bars = rows
			.map((row, index) => {
				const x = paddingX + index * stepX;
				const incomeY = scaleY(Math.max(row.income_hnl, 0));
				const expenseY = scaleY(Math.max(row.expense_hnl, 0));
				return `<rect x="${x - barWidth - 1}" y="${incomeY}" width="${barWidth}" height="${Math.max(
					zeroY - incomeY,
					0
				)}" fill="var(--nxr-money-in)" opacity="0.6"></rect><rect x="${x + 1}" y="${expenseY}" width="${barWidth}" height="${Math.max(
					zeroY - expenseY,
					0
				)}" fill="var(--nxr-money-out)" opacity="0.6"></rect>`;
			})
			.join("");
		const labels = rows
			.map(
				(row, index) =>
					`<text x="${paddingX + index * stepX}" y="${height - 2}" text-anchor="middle" class="nxr-cashflow-label">${escape(
						monthShortLabel(row.month)
					)}</text>`
			)
			.join("");
		container.html(`
			<svg viewBox="0 0 ${width} ${height}" role="img" aria-label="${__("Flujo de fondos de los últimos 6 meses")}">
				${bars}
				<polyline points="${balancePoints}" fill="none" stroke="var(--nxr-accent)" stroke-width="2"></polyline>
				${labels}
			</svg>
			<div class="nxr-cashflow-legend">
				<span data-tone="income"><i></i>${__("Ingresos")}</span>
				<span data-tone="expense"><i></i>${__("Egresos")}</span>
				<span data-tone="balance"><i></i>${__("Saldo")}</span>
			</div>
		`);
	}

	// COLUMNA 3: reutiliza arreglos que `render()` ya recibe del mismo
	// `get_executive_snapshot` — nunca una segunda llamada al servidor ni un
	// evento inventado. Cada fila navega al documento real correspondiente.
	function renderCentralNotifications(data) {
		const items = [];
		for (const row of (data.pending_accounts?.items || []).slice(0, 3)) {
			const due = row.due_date ? new Date(row.due_date) : null;
			const overdue = due && due < new Date(frappe.datetime.get_today());
			items.push({
				title: overdue ? __("Pago vencido") : __("Pago pendiente de aprobación"),
				detail: `${row.title || row.document_number || ""} · ${money(row.amount_hnl)}`,
				href: frappe.utils.get_form_link("NXR Operation", row.name),
			});
		}
		for (const row of (data.compliance_alerts?.items || []).slice(0, 2)) {
			items.push({
				title: __("Cumplimiento por vencer"),
				detail: `${row.entity_name || row.entity || ""} · ${date(row.valid_until)}`,
				href: frappe.utils.get_form_link("NXR Entity Compliance", row.name),
			});
		}
		for (const row of (data.recent_operations || [])) {
			if (items.length >= 6) break;
			if (row.operation_type !== "Inflow" && row.operation_type !== "Outflow") continue;
			items.push({
				title: row.operation_type === "Inflow" ? __("Fondo registrado") : __("Gasto registrado"),
				detail: `${row.document_number || row.name} · ${money(row.amount_hnl)}`,
				href: frappe.utils.get_form_link("NXR Operation", row.name),
			});
		}
		const visible = items.slice(0, 6);
		body.find(".nxr-central-notifications-list").html(
			visible.length
				? visible
						.map(
							(item) =>
								`<li><a href="${item.href}"><strong>${escape(item.title)}</strong><small>${escape(
									item.detail
								)}</small></a></li>`
						)
						.join("")
				: `<li class="nxr-executive-empty">${escape(__("Sin notificaciones nuevas."))}</li>`
		);
	}

	// BLOQUE OPERATIVO, izquierda: mismas filas que ya llegan en
	// `data.recent_operations`, con la columna "Descripción" que la tabla
	// original (`.nxr-dashboard-recent-rows`, más abajo) no tenía.
	function renderOperationalRecent(rows) {
		body.find(".nxr-operational-recent-table tbody").html(
			rows.length
				? rows
						.slice(0, 8)
						.map((row) => {
							const tone = operationTone(row);
							return `<tr data-tone="${escape(tone)}">
						<td><a href="${frappe.utils.get_form_link("NXR Operation", row.name)}">${escape(
								row.document_number || row.name
							)}</a></td>
						<td>${date(row.operation_date)}</td>
						<td>${escape(operationTypeLabel(row))}</td>
						<td data-numeric="true"${toneStyle(tone)}>${money(row.amount_hnl)}</td>
						<td>${escape(operationStatusLabel(row))}</td>
					</tr>`;
						})
						.join("")
				: `<tr><td colspan="5">${empty(__("No hay operaciones recientes."))}</td></tr>`
		);
	}

	// BLOQUE OPERATIVO, derecha: `data.projects.rows` viene de
	// `project_query.active_projects_summary()` — reutiliza `budget_snapshot_as_of`
	// (mismo cálculo ya auditado de "Presupuesto disponible") y `NXR Progress
	// Record` (misma fuente que "Avance de la obra"), nunca una cifra inventada.
	function renderActiveProjects(rows) {
		body.find(".nxr-operational-projects-table tbody").html(
			rows.length
				? rows
						.map(
							(row) => `<tr>
						<td><a href="${frappe.utils.get_form_link("Project", row.project)}">${escape(
								row.project_label
							)}</a></td>
						<td data-numeric="true">${Number(row.physical_percent || 0).toFixed(1)}%</td>
						<td data-numeric="true">${money(row.budget_hnl)}</td>
						<td data-numeric="true">${money(row.executed_hnl)}</td>
					</tr>`
						)
						.join("")
				: `<tr><td colspan="4">${empty(__("No hay proyectos activos."))}</td></tr>`
		);
	}

	// INTEGRACIÓN SAP: `view_sap_connection` (permissions.py) es más estrecho que
	// `view_reports` (lo que ya exige el resto del panel) — Operador financiero y
	// Consulta de proyecto pueden ver el panel pero no esta tarjeta. Se comprueba
	// aquí en el cliente solo para decidir si se pide el dato (nunca para
	// autorizar nada: el servidor ya rechaza `get_sap_summary` igual si alguien
	// se salta este chequeo), evitando un `PermissionError` real contra un botón
	// que ese rol nunca debió ver.
	const SAP_VIEW_ROLES = ["System Manager", "NEXORA Administrator", "NEXORA Finance Manager", "NEXORA Auditor"];

	function canViewSap() {
		return SAP_VIEW_ROLES.some((role) => frappe.user.has_role(role));
	}

	function loadSapCard() {
		if (!canViewSap()) return Promise.resolve();
		return new Promise((resolve) => {
			frappe.call({
				method: "nexora.integrations.sap.get_sap_summary",
				type: "GET",
				callback: (response) => {
					renderSapCard(response?.message || {});
					resolve();
				},
				error: (error) => {
					console.warn("NEXORA dashboard SAP summary failed", error);
					resolve();
				},
			});
		});
	}

	function renderSapCard(summary) {
		const card = body.find(".nxr-sap-card");
		card.removeAttr("hidden");
		const connection = summary.active_connection;
		const connected = Boolean(connection);
		card
			.find("[data-sap-status-badge]")
			.html(
				`<span class="nxr-ds-badge nxr-ds-badge--${connected ? "success" : "neutral"}">${
					connected ? __("Conectado") : __("No conectado")
				}</span>`
			);
		if (!connected) {
			card.find(".nxr-sap-card-body").html(`
				<p class="nxr-executive-empty">${escape(__("No conectado."))}</p>
				<button type="button" class="nxr-ds-btn nxr-ds-btn--secondary nxr-ds-btn--sm" data-sap-configure>${__(
					"Configurar conexión"
				)}</button>
			`);
			return;
		}
		card.find(".nxr-sap-card-body").html(`
			<dl class="nxr-sap-facts">
				<div><dt>${__("Sistema")}</dt><dd>SAP S/4HANA</dd></div>
				<div><dt>${__("Cliente")}</dt><dd>${escape(connection.connection_name)}</dd></div>
				<div><dt>${__("Última sincronización")}</dt><dd>${
			summary.last_document_event_at ? date(summary.last_document_event_at) : __("Sin sincronizaciones todavía")
		}</dd></div>
				<div><dt>${__("Registros enviados")}</dt><dd>${number(summary.documents_submitted || 0)}</dd></div>
				<div><dt>${__("Registros recibidos")}</dt><dd>${number(summary.documents_received || 0)}</dd></div>
			</dl>
			<button type="button" class="nxr-ds-btn nxr-ds-btn--secondary nxr-ds-btn--sm" data-sap-configure>${__(
				"Ver sincronizaciones"
			)}</button>
		`);
	}

	function renderProgress(physicalValue, financialValue, operational) { const physical = Number(physicalValue || 0); const financial = Number(financialValue || 0); body.find(".nxr-progress-summary").html(`<div class="nxr-progress-pair"><div><span>${__("Avance físico")}</span><strong>${physical.toFixed(1)}%</strong><div class="nxr-progress-track"><i style="width:${clamp(physical)}%"></i></div></div><div><span>${__("Avance financiero")}</span><strong>${financial.toFixed(1)}%</strong><div class="nxr-progress-track is-financial"><i style="width:${clamp(financial)}%"></i></div></div></div><div class="nxr-progress-counts"><span><small>${__("Contratos activos")}</small><strong>${operational.active_contracts || 0}</strong></span><span><small>${__("Solicitudes")}</small><strong>${operational.pending_requests || 0}</strong></span><span><small>${__("Calidad")}</small><strong>${operational.open_quality_issues || 0}</strong></span></div>`); }
	function renderBars(selector, rows, rowLabel, tone) { const visible = rows.slice(0, 5); const maximum = Math.max(...visible.map((row) => Math.abs(Number(row.amount_hnl || 0))), 1); body.find(selector).html(visible.length ? visible.map((row) => { const rowTone = Number(row.amount_hnl || 0) < 0 ? "voided" : tone; return `<div class="nxr-bar-row" data-tone="${escape(rowTone)}"><span title="${escape(rowLabel(row))}">${escape(rowLabel(row))}</span><b><i style="width:${Math.max((Math.abs(Number(row.amount_hnl || 0)) / maximum) * 100, 2)}%;background:${toneColor(rowTone)}"></i></b><strong${toneStyle(rowTone)}>${money(row.amount_hnl)}</strong></div>`; }).join("") : empty(__("Sin datos para mostrar."))); }
	function renderPayables(rows) { body.find(".nxr-payables-list").html(rows.length ? rows.slice(0, 4).map((row) => `<a class="nxr-executive-row" data-tone="expense" href="${frappe.utils.get_form_link(row.doctype, row.name)}"><span><strong>${escape(row.title || row.document_number)}</strong><small>${escape(row.beneficiary || date(row.due_date))}</small></span><b${toneStyle("expense")}>${money(row.amount_hnl)}</b></a>`).join("") : empty(__("No hay cuentas vencidas."))); }
	function renderFunds(rows) { body.find(".nxr-funds-list").html(rows.length ? rows.slice(0, 4).map((row) => `<a class="nxr-executive-row" data-tone="balance" href="${frappe.utils.get_form_link("NXR Fund Source", row.name)}"><span><strong>${escape(row.origin_or_sender || row.source_name)}</strong><small>${escape(channelLabels[row.channel] || row.channel)} · ${date(row.source_date)}</small></span><b${toneStyle("balance")}>${money(row.current_available_hnl)}</b></a>`).join("") : empty(__("No hay fondos registrados."))); }
	function renderInventory(rows) { body.find(".nxr-inventory-list").html(rows.length ? rows.map((row) => `<div class="nxr-executive-row"><span><strong>${escape(row.item)}</strong><small>${escape(row.warehouse)}</small></span><b>${number(row.balance_qty)}</b></div>`).join("") : empty(__("No hay saldos críticos."))); }
	function renderActivity(rows) { body.find(".nxr-activity-list").html(rows.length ? rows.slice(0, 4).map((row) => { const tone = operationTone(row); return `<a class="nxr-executive-row" data-tone="${escape(tone)}" data-kind="${escape(row.presentation_kind || row.operation_type)}" href="${frappe.utils.get_form_link("NXR Operation", row.name)}"><span><strong>${escape(row.document_number || row.name)}</strong><small>${date(row.operation_date)} · ${ledgerValue(operationTypeLabel(row), row, "type")}</small></span><b${toneStyle(tone)}>${row.presentation_struck ? `<s>${money(row.amount_hnl)}</s>` : money(row.amount_hnl)}</b></a>`; }).join("") : empty(__("No hay actividad reciente."))); }
	function renderEvidence(rows) { body.find(".nxr-evidence-gallery").html(rows.length ? rows.slice(0, 6).map((row) => `<a class="nxr-evidence-tile" href="${escape(row.file_url)}" target="_blank" rel="noopener"><img src="${escape(row.file_url)}" alt="${escape(row.file_name || row.evidence_kind || __("Comprobante"))}" loading="eager"><span>${escape(window.nexora.ui?.label?.("evidenceKind", row.evidence_kind) || row.evidence_kind || row.file_name)}</span></a>`).join("") : empty(__("No hay comprobantes recientes."))); }
	function renderContracts(rows) { const target = body.find(".nxr-contract-rows"); if (!rows.length) { target.html(empty(__("No hay contratos registrados."))); return; } target.html(`<div class="nxr-ds-table-wrap"><table class="nxr-ds-table"><thead><tr><th>${__("Contrato")}</th><th>${__("Contratista")}</th><th>${__("Estado")}</th><th>${__("Inicio")}</th><th>${__("Fin")}</th><th data-numeric="true">${__("Valor")}</th><th data-numeric="true">${__("Pagado")}</th><th data-numeric="true">${__("Saldo")}</th></tr></thead><tbody>${rows.map((row) => `<tr><td><a href="${frappe.utils.get_form_link("NXR Contract", row.name)}">${escape(row.document_number || row.name)}</a></td><td>${escape(row.contractor_label || row.contractor)}</td><td>${escape(window.nexora.ui?.label?.("status", row.status) || statusLabels[row.status] || row.status)}</td><td>${date(row.start_date)}</td><td>${date(row.current_end_date)}</td><td data-numeric="true">${money(row.contract_value_hnl ?? row.current_amount)}</td><td data-numeric="true">${money(row.paid_hnl ?? row.paid_amount)}</td><td data-numeric="true">${money(row.balance_hnl ?? row.pending_amount)}</td></tr>`).join("")}</tbody></table></div>`); }
	function renderTeamActivity(rows) { body.find(".nxr-team-activity-list").html(rows.length ? rows.map((row) => `<a class="nxr-executive-row" href="${frappe.utils.get_form_link("NXR Operation", row.name)}"><span><strong>${escape(row.actor_label || row.actor || __("Alguien"))}</strong><small>${escape(window.nexora.ui?.label?.("status", row.status) || statusLabels[row.status] || row.status)} · ${escape(row.document_number || row.name)}</small></span><b>${date(row.modified)}</b></a>`).join("") : empty(__("Sin decisiones recientes de otros usuarios."))); }
	function renderCompliance(rows) { body.find(".nxr-compliance-list").html(rows.length ? rows.map((row) => { const tone = complianceStateTones[row.compliance_state] || "balance"; return `<a class="nxr-executive-row" data-tone="${escape(tone)}" href="${frappe.utils.get_form_link("NXR Entity Compliance", row.name)}"><span><strong>${escape(row.entity_name || row.entity)}</strong><small>${escape(window.nexora.ui?.label?.("complianceType", row.compliance_type) || row.compliance_type)} · ${date(row.valid_until)}</small></span><b${toneStyle(tone)}>${escape(complianceStateLabels[row.compliance_state] || row.compliance_state)}</b></a>`; }).join("") : empty(__("Sin vencimientos de cumplimiento en los próximos 30 días."))); }
	function renderRecentRoutes() { const rows = window.nexora.recentRoutes?.list?.() || []; body.find(".nxr-recent-routes-list").html(rows.length ? `<div class="nxr-quick-links">${rows.map((row) => `<button data-route="${escape(row.route)}">${escape(row.label)}</button>`).join("")}</div>` : empty(__("Todavía no visitó otras pantallas en esta sesión."))); }
	function renderRecent(rows) { body.find(".nxr-dashboard-recent-rows tbody").html(rows.slice(0, 6).map((row) => { const tone = operationTone(row); return `<tr data-operation="${escape(row.name)}" data-kind="${escape(row.presentation_kind || row.operation_type)}" data-tone="${escape(tone)}"><td><a href="${frappe.utils.get_form_link("NXR Operation", row.name)}">${escape(row.document_number || row.name)}</a></td><td>${date(row.operation_date)}</td><td>${ledgerValue(operationTypeLabel(row), row, "type")}</td><td>${escape(operationStatusLabel(row))}</td><td data-numeric="true">${ledgerValue(money(row.amount_hnl), row, "amount")}</td></tr>`; }).join("")); }
	function operationTypeLabel(row) { const kind = row.presentation_kind || row.operation_type; const base = presentationLabels[kind] || operationLabels[row.operation_type] || row.operation_type; return kind === "Income" && row.source_channel ? `${base} · ${channelTypeLabels[row.source_channel] || row.source_channel}` : base; }
	function operationStatusLabel(row) { return window.nexora.ui?.label?.("status", row.presentation_status || row.status) || ledgerStatusLabels[row.presentation_status] || statusLabels[row.status] || row.status; }
	function operationTone(row) { return toneColors[row.presentation_tone] ? row.presentation_tone : "neutral"; }
	function ledgerValue(value, row, kind) { const content = escape(value); const decorated = row.presentation_struck ? `<s>${content}</s>` : content; return `<span class="nxr-ledger-${kind}" data-tone="${escape(operationTone(row))}"${toneStyle(operationTone(row))}>${decorated}</span>`; }
	function toneColor(tone) { return toneColors[tone] || "var(--nxr-accent)"; }
	function toneStyle(tone) { return toneColors[tone] ? ` style="color:${toneColors[tone]}"` : ""; }
	function money(value) { return window.nexora.ui?.formatMoney?.(value) || new Intl.NumberFormat("es-HN", { style: "currency", currency: "HNL", minimumFractionDigits: 2 }).format(Number(value || 0)); }
	function number(value) { return new Intl.NumberFormat("es-HN", { maximumFractionDigits: 6 }).format(Number(value || 0)); }
	function date(value) { return window.nexora.ui.formatDate(value); }
	function clamp(value) { return Math.max(0, Math.min(Number(value || 0), 100)); }
	function escape(value) { return window.nexora.ui.escapeHtml(value); }
	function empty(message) { return `<p class="nxr-executive-empty">${escape(message)}</p>`; }
};
