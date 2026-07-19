frappe.pages["construcontrol-dashboard"].on_page_load = function (wrapper) {
  "use strict";

  const page = frappe.ui.make_app_page({parent: wrapper, title: "ConstruControl", single_column: true});
  const body = $(wrapper).find(".layout-main-section");
  let activeProject = null;
  let syncingProjectField = false;
  let dashboardRequest = 0;

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
      <section id="cc-executive-hero" class="cc-executive-hero"><div><small>CC00 · CENTRO EJECUTIVO</small><h2>Gestión residencial integral</h2><p>Actualizando el estado total de la obra...</p></div><div class="cc-hero-status"><span id="cc-dashboard-refresh-state" class="cc-refresh-state" hidden>Actualizando</span><span id="cc-schedule-status" class="cc-schedule-status">Cargando</span></div></section>
      <section id="cc-alerts" class="cc-alert-stack"></section>
      <section id="cc-financial-metrics" class="cc-executive-metrics"></section>
      <div class="cc-executive-grid">
        <section class="cc-executive-card"><div class="cc-card-header"><div><strong>Avance de la obra</strong><span>Comparación física y financiera</span></div><button class="btn btn-xs btn-default" data-page="project">Detalle</button></div><div id="cc-progress-summary"></div></section>
        <section class="cc-executive-card"><div class="cc-card-header"><div><strong>Gastos por categoría</strong><span>Distribución de la ejecución</span></div><button class="btn btn-xs btn-default" data-list="CC Expense Control">Gastos</button></div><div id="cc-expense-chart" class="cc-bar-chart"></div></section>
        <section class="cc-executive-card"><div class="cc-card-header"><div><strong>Ingresos por canal</strong><span>Remesas, depósitos y transferencias</span></div><button class="btn btn-xs btn-default" data-list="CC Funding Source">Ingresos</button></div><div id="cc-income-chart" class="cc-bar-chart"></div></section>
        <section class="cc-executive-card"><div class="cc-card-header"><div><strong>Cuentas por pagar</strong><span>Próximas y vencidas</span></div><button class="btn btn-xs btn-default" data-list="CC Payable Control">Ver todas</button></div><div id="cc-payables" class="cc-dashboard-list"></div></section>
        <section class="cc-executive-card"><div class="cc-card-header"><div><strong>Inventario crítico</strong><span>Materiales bajos o agotados</span></div><button class="btn btn-xs btn-default" data-list="CC Material Ledger">Inventario</button></div><div id="cc-low-stock" class="cc-dashboard-list"></div></section>
        <section class="cc-executive-card"><div class="cc-card-header"><div><strong>Actividad reciente</strong><span>Acciones auditadas del sistema</span></div><button class="btn btn-xs btn-default" data-list="CC Audit Log">Auditoría</button></div><div id="cc-recent-activity" class="cc-dashboard-list"></div></section>
        <section class="cc-executive-card cc-executive-wide"><div class="cc-card-header"><div><strong>Módulos ConstruControl</strong><span>Acceso rápido sin salir de la aplicación</span></div></div><div id="cc-module-grid" class="cc-module-grid"></div></section>
      </div>
    </main>
  `);

  const style = document.createElement("style");
  style.textContent = `
    .cc-executive-dashboard{max-width:1480px;margin:0 auto;padding:5px 0 30px}.cc-executive-hero{display:flex;align-items:flex-start;justify-content:space-between;gap:18px;padding:21px;border:1px solid var(--border-color);border-radius:19px;background:linear-gradient(135deg,var(--card-bg),var(--subtle-fg));margin-bottom:12px}.cc-executive-hero small{color:#175c4c;font-weight:900;letter-spacing:.08em}.cc-executive-hero h2{margin:5px 0}.cc-executive-hero p{margin:0;color:var(--text-muted)}.cc-hero-status{display:flex;align-items:center;gap:7px;flex-wrap:wrap;justify-content:flex-end}.cc-refresh-state{display:inline-flex;padding:6px 10px;border-radius:999px;background:var(--subtle-fg);color:var(--text-muted);font-size:11px;font-weight:700}.cc-refresh-state[hidden]{display:none}.cc-schedule-status{display:inline-flex;padding:6px 11px;border-radius:999px;background:rgba(23,92,76,.12);color:#175c4c;font-weight:800}.cc-schedule-status.delayed{background:var(--red-100);color:var(--red-700)}.cc-schedule-status.at_risk{background:var(--yellow-100);color:var(--yellow-800)}.cc-alert-stack{display:grid;gap:8px;margin-bottom:12px}.cc-dashboard-alert{display:flex;align-items:flex-start;gap:10px;padding:11px 13px;border:1px solid var(--border-color);border-radius:12px;background:var(--card-bg)}.cc-dashboard-alert.critical{border-color:var(--red-300);background:var(--red-100)}.cc-dashboard-alert.attention{border-color:var(--yellow-300);background:var(--yellow-100)}.cc-dashboard-alert.normal{border-color:var(--green-300);background:var(--green-100)}.cc-dashboard-alert strong,.cc-dashboard-alert span{display:block}.cc-dashboard-alert span{margin-top:2px;font-size:12px}.cc-executive-metrics{display:grid;grid-template-columns:repeat(6,minmax(0,1fr));gap:9px;margin-bottom:12px}.cc-executive-metric{min-width:0;padding:13px;border:1px solid var(--border-color);border-radius:14px;background:var(--card-bg)}.cc-executive-metric span,.cc-executive-metric strong{display:block}.cc-executive-metric span{color:var(--text-muted);font-size:11px}.cc-executive-metric strong{overflow:hidden;margin-top:4px;font-size:18px;text-overflow:ellipsis}.cc-executive-metric.is-negative strong{color:var(--red-700)}.cc-executive-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:12px}.cc-executive-card{min-width:0;padding:15px;border:1px solid var(--border-color);border-radius:16px;background:var(--card-bg)}.cc-executive-wide{grid-column:1/-1}.cc-card-header{display:flex;align-items:flex-start;justify-content:space-between;gap:9px;margin-bottom:12px}.cc-card-header>div{min-width:0}.cc-card-header strong,.cc-card-header span{display:block}.cc-card-header span{color:var(--text-muted);font-size:11px}.cc-progress-pair{display:grid;gap:12px}.cc-progress-block span,.cc-progress-block strong{display:block}.cc-progress-line{height:10px;overflow:hidden;margin-top:5px;border-radius:999px;background:var(--subtle-fg)}.cc-progress-line i{display:block;height:100%;border-radius:inherit;background:#175c4c}.cc-progress-line.financial i{background:#3b6ea8}.cc-progress-details{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:7px;margin-top:12px}.cc-progress-details>div{padding:8px;border-radius:10px;background:var(--subtle-fg)}.cc-progress-details span,.cc-progress-details strong{display:block}.cc-progress-details span{color:var(--text-muted);font-size:10px}.cc-bar-chart{display:flex;flex-direction:column;gap:9px}.cc-bar-row{display:grid;grid-template-columns:minmax(90px,1fr) minmax(100px,2fr) auto;gap:8px;align-items:center}.cc-bar-label{overflow:hidden;text-overflow:ellipsis;white-space:nowrap;font-size:12px}.cc-bar-track{height:8px;overflow:hidden;border-radius:999px;background:var(--subtle-fg)}.cc-bar-track i{display:block;height:100%;border-radius:inherit;background:#175c4c}.cc-bar-value{font-size:11px;font-weight:800}.cc-dashboard-list{display:flex;flex-direction:column}.cc-dashboard-row{display:flex;align-items:flex-start;justify-content:space-between;gap:11px;padding:9px 0;border-bottom:1px solid var(--border-color);text-align:left}.cc-dashboard-row:last-child{border-bottom:0}.cc-dashboard-row strong,.cc-dashboard-row small{display:block}.cc-dashboard-row small{color:var(--text-muted)}.cc-dashboard-row .is-critical{color:var(--red-700)}.cc-module-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(190px,1fr));gap:9px}.cc-module-tile{display:flex;align-items:flex-start;gap:9px;min-height:76px;padding:12px;border:1px solid var(--border-color);border-radius:13px;background:var(--card-bg);text-align:left}.cc-module-tile:hover{border-color:#175c4c;background:rgba(23,92,76,.07)}.cc-module-code{display:grid;min-width:39px;height:39px;place-items:center;border-radius:11px;background:rgba(23,92,76,.12);color:#175c4c;font-size:11px;font-weight:900}.cc-module-tile strong,.cc-module-tile small{display:block}.cc-module-tile small{margin-top:3px;color:var(--text-muted)}@media(max-width:1200px){.cc-executive-metrics{grid-template-columns:repeat(3,minmax(0,1fr))}.cc-executive-grid{grid-template-columns:repeat(2,minmax(0,1fr))}}@media(max-width:767px){.cc-executive-hero{flex-direction:column;padding:15px}.cc-hero-status{justify-content:flex-start}.cc-executive-metrics{grid-template-columns:repeat(2,minmax(0,1fr))}.cc-executive-grid{grid-template-columns:1fr}.cc-executive-wide{grid-column:auto}.cc-executive-card{padding:14px}.cc-bar-row{grid-template-columns:minmax(75px,1fr) minmax(80px,1.5fr);}.cc-bar-value{grid-column:2}.cc-module-grid{grid-template-columns:1fr}}
  `;
  wrapper.appendChild(style);

  const modules = [
    ["PRJ", "Centro de proyecto", "Presupuesto, fases y avance", "Page:construcontrol-project-center"],
    ["FI01", "Ingresos", "Remesas, depósitos y transferencias", "CC Funding Source"],
    ["FI02", "Gastos", "Facturas, aprobaciones y pagos", "CC Expense Control"],
    ["FI03", "Cuentas por pagar", "Saldos, vencimientos y pagos parciales", "CC Payable Control"],
    ["CO01", "Contratos", "Valores, pagos y saldos", "CC Labor Contract"],
    ["PR01", "Fases", "Planificación y progreso", "CC Construction Phase"],
    ["MM01", "Materiales", "Existencias y costos", "CC Material Ledger"],
    ["MIGO", "Inventario", "Consumos y ajustes", "CC Inventory Movement"],
    ["MM02", "Compras", "Solicitudes y recepción", "CC Procurement Request"],
    ["QC01", "Avance", "Hitos, calidad e incidencias", "CC Progress Update"],
    ["CL01", "Cierre semanal", "Control periódico auditable", "Page:construcontrol-weekly-closing"],
    ["BI01", "Reportes", "Análisis y exportaciones", "Page:construcontrol-reporting-center"],
    ["INT", "Integraciones", "Conexiones administrables", "Page:construcontrol-integrations"],
    ["US01", "Usuarios", "Perfiles y permisos", "CC User Access"],
  ];
  if (frappe.user.has_role("System Manager")) modules.push(["MIG", "Migración", "Historial y respaldo", "Page:construcontrol-migration-console"]);
  body.find("#cc-module-grid").html(modules.map(item => `<button class="cc-module-tile" data-target="${frappe.utils.escape_html(item[3])}"><span class="cc-module-code">${item[0]}</span><span><strong>${item[1]}</strong><small>${item[2]}</small></span></button>`).join(""));

  const escape = value => frappe.utils.escape_html(String(value ?? ""));
  const money = value => format_currency(value || 0, "HNL");

  function renderMetrics(summary) {
    const f = summary.financial || {};
    const metrics = [
      ["Ingresos recibidos", money(f.received_hnl)],
      ["Gasto ejecutado", money(f.spent_hnl)],
      ["Caja disponible", money(f.cash_available_hnl)],
      ["Comprometido", money(f.committed_hnl)],
      ["Presupuesto disponible", money(f.available_budget_hnl), f.available_budget_hnl < 0],
      ["Cuentas por pagar", money(f.payable_balance_hnl)],
    ];
    body.find("#cc-financial-metrics").html(metrics.map(row => `<div class="cc-executive-metric ${row[2] ? "is-negative" : ""}"><span>${escape(row[0])}</span><strong>${row[1]}</strong></div>`).join(""));
  }

  function renderProgress(summary) {
    const p = summary.progress || {};
    const physical = Math.min(Math.max(p.physical_percent || 0, 0), 100);
    const financial = Math.min(Math.max(p.financial_percent || 0, 0), 100);
    body.find("#cc-progress-summary").html(`<div class="cc-progress-pair"><div class="cc-progress-block"><span class="text-muted">Avance físico</span><strong>${physical}%</strong><div class="cc-progress-line"><i style="width:${physical}%"></i></div></div><div class="cc-progress-block"><span class="text-muted">Avance financiero</span><strong>${financial}%</strong><div class="cc-progress-line financial"><i style="width:${financial}%"></i></div></div></div><div class="cc-progress-details"><div><span>Fases</span><strong>${p.phase_count || 0}</strong></div><div><span>Atrasadas</span><strong>${p.delayed_phase_count || 0}</strong></div><div><span>En riesgo</span><strong>${p.at_risk_phase_count || 0}</strong></div></div>`);
  }

  function renderBars(selector, rows) {
    const max = Math.max(...(rows || []).map(row => row.amount_hnl || 0), 1);
    body.find(selector).html(rows?.length ? rows.slice(0, 7).map(row => `<div class="cc-bar-row"><span class="cc-bar-label">${escape(row.label)}</span><span class="cc-bar-track"><i style="width:${Math.max((row.amount_hnl / max) * 100, 2)}%"></i></span><span class="cc-bar-value">${money(row.amount_hnl)}</span></div>`).join("") : `<span class="text-muted">Sin datos para mostrar.</span>`);
  }

  function renderList(selector, rows, renderer, empty) {
    body.find(selector).html(rows?.length ? rows.map(renderer).join("") : `<span class="text-muted">${escape(empty)}</span>`);
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
      () => window.setTimeout(() => { syncingProjectField = false; }, 0),
      () => { syncingProjectField = false; },
    );
  }

  function render(summary) {
    activeProject = summary.project || null;
    syncProjectSelector(activeProject);
    body.find("#cc-executive-hero h2").text(summary.project_name || "Gestión residencial integral");
    body.find("#cc-executive-hero p").text(`${summary.progress?.phase_count || 0} fases · ${summary.counts?.contract_count || 0} contratos · ${summary.counts?.expense_count || 0} gastos controlados`);
    body.find("#cc-schedule-status").attr("class", `cc-schedule-status ${summary.progress?.schedule_status || ""}`).text(summary.progress?.schedule_status || "on_track");
    body.find("#cc-alerts").html((summary.alerts || []).map(alert => `<div class="cc-dashboard-alert ${escape(alert.level)}"><span>●</span><div><strong>${escape(alert.title)}</strong><span>${escape(alert.message)}</span></div></div>`).join(""));
    renderMetrics(summary);
    renderProgress(summary);
    renderBars("#cc-expense-chart", summary.charts?.expenses_by_category || []);
    renderBars("#cc-income-chart", summary.charts?.income_by_channel || []);
    renderList("#cc-payables", summary.overdue_payables || [], row => `<button class="cc-dashboard-row" data-form="CC Payable Control" data-name="${escape(row.name)}"><span><strong>${escape(row.provider_name || row.invoice_number || row.name)}</strong><small>${escape(row.due_date || "Sin vencimiento")}</small></span><span><strong class="is-critical">${money(row.balance_due_hnl)}</strong><small>${escape(row.payable_status || "pending")}</small></span></button>`, "No hay cuentas vencidas.");
    renderList("#cc-low-stock", summary.low_stock || [], row => `<button class="cc-dashboard-row" data-form="CC Material Ledger" data-name="${escape(row.name)}"><span><strong>${escape(row.material_name)}</strong><small>${escape(row.stock_status || "")}</small></span><span><strong>${escape(row.current_qty || 0)} ${escape(row.unit || "")}</strong><small>Existencia</small></span></button>`, "No hay materiales críticos.");
    renderList("#cc-recent-activity", summary.recent_activity || [], row => `<button class="cc-dashboard-row" data-list="CC Audit Log"><span><strong>${escape(row.action || "Actividad")}</strong><small>${escape(row.actor_name || row.actor_role || "Sistema")}</small></span><span><strong>${escape(row.record_type || "")}</strong><small>${escape(row.posting_date || "")}</small></span></button>`, "No hay actividad reciente.");
  }

  function setDashboardLoading(loading) {
    body.find(".cc-executive-dashboard").attr("aria-busy", loading ? "true" : "false");
    body.find("#cc-dashboard-refresh-state").prop("hidden", !loading);
  }

  function loadDashboard() {
    const requestId = ++dashboardRequest;
    setDashboardLoading(true);
    return Promise.resolve()
      .then(() => frappe.xcall("erpnext.construcontrol.executive.get_executive_dashboard", {project: activeProject}))
      .then(summary => {
        if (requestId !== dashboardRequest) return;
        render(summary || {});
      })
      .catch(error => {
        if (requestId !== dashboardRequest) return;
        body.find("#cc-alerts").html(`<div class="cc-dashboard-alert critical"><div><strong>No se pudo cargar el resumen</strong><span>${escape(error?.message || "Revise los datos y permisos del proyecto.")}</span></div></div>`);
      })
      .then(() => {
        if (requestId === dashboardRequest) setDashboardLoading(false);
      });
  }

  function openQuickCreate() {
    const dialog = new frappe.ui.Dialog({title: "Registrar movimiento", fields: [{fieldname:"type",fieldtype:"Select",label:"Tipo",options:"Ingreso\nGasto\nAvance\nMovimiento de inventario",reqd:1}], primary_action_label:"Continuar", primary_action(values) { dialog.hide(); const routes = {Ingreso:["Form","CC Funding Source","new-cc-funding-source-1"],Gasto:["Form","CC Expense Control","new-cc-expense-control-1"],Avance:["Form","CC Progress Update","new-cc-progress-update-1"],"Movimiento de inventario":["Form","CC Inventory Movement","new-cc-inventory-movement-1"]}; frappe.set_route(...routes[values.type]); }}); dialog.show();
  }

  body.on("click", "[data-target]", function () { const target = $(this).data("target"); if (String(target).startsWith("Page:")) frappe.set_route(String(target).split(":")[1]); else frappe.set_route("List", target); });
  body.on("click", "[data-list]", function () { frappe.set_route("List", $(this).data("list")); });
  body.on("click", "[data-form][data-name]", function () { frappe.set_route("Form", $(this).data("form"), $(this).data("name")); });
  body.on("click", "[data-page='project']", () => frappe.set_route("construcontrol-project-center"));

  loadDashboard();
};
