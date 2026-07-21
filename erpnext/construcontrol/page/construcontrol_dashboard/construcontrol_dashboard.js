frappe.pages["construcontrol-dashboard"].on_page_load = function (wrapper) {
	"use strict";

	const page = frappe.ui.make_app_page({ parent: wrapper, title: "ConstruControl", single_column: true });
	const body = $(wrapper).find(".layout-main-section");
	let activeProject = null;
	let syncingProjectField = false;
	let dashboardRequest = 0;
	let currentSummary = {};

	page.add_field({
		fieldname: "project",
		label: "Proyecto",
		fieldtype: "Link",
		options: "Project",
		change() {
			const selectedProject = this.get_value() || null;
			if (syncingProjectField || selectedProject === activeProject) return;
			activeProject = selectedProject;
			loadDashboard();
		},
	});
	page.set_primary_action("Registrar movimiento", () => openQuickCreate(), "add");
	page.add_inner_button("Centro de proyecto", () => frappe.set_route("construcontrol-project-center"));
	page.add_inner_button("Reportes", () => frappe.set_route("construcontrol-reporting-center"));

	body.html(`
    <main class="cc-executive-dashboard" aria-busy="false">
      <section id="cc-executive-hero" class="cc-executive-hero">
        <div><small>CC00 · RESUMEN EJECUTIVO</small><h2>Gestión residencial integral</h2><p>Actualizando el estado de la obra...</p></div>
        <div class="cc-hero-status"><span id="cc-dashboard-refresh-state" class="cc-refresh-state" hidden>Actualizando</span><span id="cc-schedule-status" class="cc-schedule-status">Cargando</span></div>
      </section>
      <section id="cc-alerts" class="cc-alert-strip" aria-label="Alertas principales"></section>
      <section id="cc-financial-metrics" class="cc-executive-metrics"></section>
      <section class="cc-executive-grid cc-executive-grid-primary">
        <article class="cc-executive-card"><div class="cc-card-header"><div><strong>Avance de la obra</strong><span>Comparación física y financiera</span></div><button class="btn btn-xs btn-default" data-page="project">Detalle</button></div><div id="cc-progress-summary"></div></article>
        <article class="cc-executive-card"><div class="cc-card-header"><div><strong>Gastos por categoría</strong><span>Distribución de la ejecución</span></div><button class="btn btn-xs btn-default" data-list="CC Expense Control">Ver gastos</button></div><div id="cc-expense-chart" class="cc-bar-chart"></div></article>
        <article class="cc-executive-card"><div class="cc-card-header"><div><strong>Ingresos por canal</strong><span>Remesas, depósitos y transferencias</span></div><button class="btn btn-xs btn-default" data-list="CC Funding Source">Ver ingresos</button></div><div id="cc-income-chart" class="cc-bar-chart"></div></article>
      </section>
      <section class="cc-executive-grid cc-executive-grid-secondary">
        <article class="cc-executive-card cc-compact-card"><div class="cc-card-header"><div><strong>Cuentas por pagar</strong><span>Vencidas o próximas</span></div><button class="btn btn-xs btn-default" data-list="CC Payable Control">Ver más</button></div><div id="cc-payables" class="cc-dashboard-list"></div></article>
        <article class="cc-executive-card cc-compact-card"><div class="cc-card-header"><div><strong>Inventario crítico</strong><span>Materiales que requieren atención</span></div><button class="btn btn-xs btn-default" data-list="CC Material Ledger">Ver más</button></div><div id="cc-low-stock" class="cc-dashboard-list"></div></article>
        <article class="cc-executive-card cc-compact-card"><div class="cc-card-header"><div><strong>Actividad reciente</strong><span>Últimas acciones relevantes</span></div><button class="btn btn-xs btn-default" data-list="CC Audit Log">Ver más</button></div><div id="cc-recent-activity" class="cc-dashboard-list"></div></article>
      </section>
    </main>
  `);

	const escape = (value) => frappe.utils.escape_html(String(value ?? ""));
	const money = (value) => format_currency(value || 0, "HNL");

	function renderMetrics(summary) {
		const f = summary.financial || {};
		const metrics = [
			["Ingresos recibidos", money(f.received_hnl)],
			["Gastos registrados", money(f.expense_total_hnl)],
			["Pagado", money(f.paid_hnl)],
			["Caja disponible", money(f.cash_available_hnl), f.cash_available_hnl < 0],
			["Comprometido", money(f.committed_hnl)],
			["Presupuesto disponible", money(f.available_budget_hnl), f.available_budget_hnl < 0],
		];
		body.find("#cc-financial-metrics").html(
			metrics
				.map(
					(row) =>
						`<div class="cc-executive-metric ${row[2] ? "is-negative" : ""}"><span>${escape(
							row[0]
						)}</span><strong>${row[1]}</strong></div>`
				)
				.join("")
		);
	}

	function renderProgress(summary) {
		const p = summary.progress || {};
		const physical = Math.min(Math.max(Number(p.physical_percent) || 0, 0), 100);
		const financial = Math.min(Math.max(Number(p.financial_percent) || 0, 0), 100);
		body.find("#cc-progress-summary").html(
			`<div class="cc-progress-pair"><div class="cc-progress-block"><span class="text-muted">Avance físico</span><strong>${physical}%</strong><div class="cc-progress-line"><i style="width:${physical}%"></i></div></div><div class="cc-progress-block"><span class="text-muted">Avance financiero</span><strong>${financial}%</strong><div class="cc-progress-line financial"><i style="width:${financial}%"></i></div></div></div><div class="cc-progress-details"><div><span>Fases</span><strong>${
				p.phase_count || 0
			}</strong></div><div><span>Atrasadas</span><strong>${
				p.delayed_phase_count || 0
			}</strong></div><div><span>En riesgo</span><strong>${
				p.at_risk_phase_count || 0
			}</strong></div></div>`
		);
	}

	function renderBars(selector, rows) {
		const visible = (rows || []).slice(0, 5);
		const max = Math.max(...visible.map((row) => Number(row.amount_hnl) || 0), 1);
		body.find(selector).html(
			visible.length
				? visible
						.map(
							(row) =>
								`<div class="cc-bar-row"><span class="cc-bar-label" title="${escape(
									row.label
								)}">${escape(
									row.label
								)}</span><span class="cc-bar-track"><i style="width:${Math.max(
									((Number(row.amount_hnl) || 0) / max) * 100,
									2
								)}%"></i></span><span class="cc-bar-value">${money(
									row.amount_hnl
								)}</span></div>`
						)
						.join("")
				: `<span class="cc-empty-state">Sin datos para mostrar.</span>`
		);
	}

	function renderList(selector, rows, renderer, empty) {
		const visible = (rows || []).slice(0, 3);
		body.find(selector).html(
			visible.length
				? visible.map(renderer).join("")
				: `<span class="cc-empty-state">${escape(empty)}</span>`
		);
	}

	function renderAlerts(alerts) {
		const visible = (alerts || []).slice(0, 4);
		body.find("#cc-alerts").html(
			visible
				.map(
					(alert, index) =>
						`<button type="button" class="cc-dashboard-alert ${escape(
							alert.level
						)}" data-alert-index="${index}"><span class="cc-alert-dot" aria-hidden="true"></span><span><strong>${escape(
							alert.title
						)}</strong><small>${escape(alert.message)}</small></span></button>`
				)
				.join("")
		);
	}

	function syncProjectSelector(summaryProject) {
		const projectField = page.fields_dict.project;
		const normalizedProject = summaryProject || null;
		if (!projectField || (projectField.get_value() || null) === normalizedProject) return;
		syncingProjectField = true;
		let update;
		try {
			update = projectField.set_value(normalizedProject);
		} catch (_error) {
			syncingProjectField = false;
			return;
		}
		Promise.resolve(update).then(
			() =>
				window.setTimeout(() => {
					syncingProjectField = false;
				}, 0),
			() => {
				syncingProjectField = false;
			}
		);
	}

	function render(summary) {
		currentSummary = summary || {};
		activeProject = summary.project || null;
		syncProjectSelector(activeProject);
		body.find("#cc-executive-hero h2").text(summary.project_name || "Gestión residencial integral");
		body.find("#cc-executive-hero p").text(
			`${summary.progress?.phase_count || 0} fases · ${
				summary.counts?.contract_count || 0
			} contratos · ${summary.counts?.expense_count || 0} gastos`
		);
		body.find("#cc-schedule-status")
			.attr("class", `cc-schedule-status ${escape(summary.progress?.schedule_status || "")}`)
			.text(summary.progress?.schedule_status_label || "En tiempo");
		renderAlerts(summary.alerts || []);
		renderMetrics(summary);
		renderProgress(summary);
		renderBars("#cc-expense-chart", summary.charts?.expenses_by_category || []);
		renderBars("#cc-income-chart", summary.charts?.income_by_channel || []);
		renderList(
			"#cc-payables",
			summary.overdue_payables || [],
			(row) =>
				`<button class="cc-dashboard-row" data-form="CC Payable Control" data-name="${escape(
					row.name
				)}"><span><strong>${escape(
					row.provider_name || row.invoice_number || "Cuenta por pagar"
				)}</strong><small>${escape(
					row.due_date || "Sin vencimiento"
				)}</small></span><span><strong class="is-critical">${money(
					row.balance_due_hnl
				)}</strong><small>${escape(row.payable_status_label || "Pendiente")}</small></span></button>`,
			"No hay cuentas vencidas."
		);
		renderList(
			"#cc-low-stock",
			summary.low_stock || [],
			(row) =>
				`<button class="cc-dashboard-row" data-form="CC Material Ledger" data-name="${escape(
					row.name
				)}"><span><strong>${escape(row.material_name || "Material")}</strong><small>${escape(
					row.stock_status === "depleted" ? "Agotado" : "Existencia baja"
				)}</small></span><span><strong>${escape(row.current_qty || 0)} ${escape(
					row.unit || ""
				)}</strong></span></button>`,
			"No hay materiales críticos."
		);
		renderList(
			"#cc-recent-activity",
			summary.recent_activity || [],
			(row) =>
				`<button class="cc-dashboard-row" data-list="CC Audit Log"><span><strong>${escape(
					row.action_label || "Actividad"
				)}</strong><small>${escape(
					row.actor_name || row.actor_role || "Sistema"
				)}</small></span><span><strong>${escape(
					row.record_type_label || "Registro"
				)}</strong><small>${escape(row.posting_date || "")}</small></span></button>`,
			"No hay actividad reciente."
		);
	}

	function setDashboardLoading(loading) {
		body.find(".cc-executive-dashboard").attr("aria-busy", loading ? "true" : "false");
		body.find("#cc-dashboard-refresh-state").prop("hidden", !loading);
	}

	function loadDashboard() {
		const requestId = ++dashboardRequest;
		setDashboardLoading(true);
		return Promise.resolve()
			.then(() =>
				frappe.xcall("erpnext.construcontrol.executive.get_executive_dashboard", {
					project: activeProject,
				})
			)
			.then((summary) => {
				if (requestId !== dashboardRequest) return;
				render(summary || {});
			})
			.catch((error) => {
				if (requestId !== dashboardRequest) return;
				body.find("#cc-alerts").html(
					`<div class="cc-dashboard-alert critical"><span><strong>No se pudo cargar el resumen</strong><small>${escape(
						error?.message || "Revise los datos y permisos del proyecto."
					)}</small></span></div>`
				);
			})
			.finally(() => {
				if (requestId === dashboardRequest) setDashboardLoading(false);
			});
	}

	function openQuickCreate() {
		const dialog = new frappe.ui.Dialog({
			title: "Registrar movimiento",
			fields: [
				{
					fieldname: "type",
					fieldtype: "Select",
					label: "Tipo",
					options: "Ingreso\nGasto\nAvance\nMovimiento de inventario",
					reqd: 1,
				},
			],
			primary_action_label: "Continuar",
			primary_action(values) {
				dialog.hide();
				const routes = {
					Ingreso: ["Form", "CC Funding Source", "new-cc-funding-source-1"],
					Gasto: ["Form", "CC Expense Control", "new-cc-expense-control-1"],
					Avance: ["Form", "CC Progress Update", "new-cc-progress-update-1"],
					"Movimiento de inventario": [
						"Form",
						"CC Inventory Movement",
						"new-cc-inventory-movement-1",
					],
				};
				frappe.set_route(...routes[values.type]);
			},
		});
		dialog.show();
	}

	body.on("click", "[data-alert-index]", function () {
		const alert = (currentSummary.alerts || [])[Number($(this).data("alert-index"))];
		if (Array.isArray(alert?.route) && alert.route.length) frappe.set_route(...alert.route);
	});
	body.on("click", "[data-list]", function () {
		frappe.set_route("List", $(this).data("list"));
	});
	body.on("click", "[data-form][data-name]", function () {
		frappe.set_route("Form", $(this).data("form"), $(this).data("name"));
	});
	body.on("click", "[data-page='project']", () => frappe.set_route("construcontrol-project-center"));

	loadDashboard();
};
