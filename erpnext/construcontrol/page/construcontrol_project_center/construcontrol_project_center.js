frappe.pages["construcontrol-project-center"].on_page_load = function (wrapper) {
  "use strict";

  const page = frappe.ui.make_app_page({
    parent: wrapper,
    title: "Centro de proyecto",
    single_column: true,
  });
  const body = $(wrapper).find(".layout-main-section");
  let activeProject = null;

  page.add_field({
    label: "Proyecto",
    fieldtype: "Link",
    fieldname: "project",
    options: "Project",
    change() {
      activeProject = this.get_value();
      load();
    },
  });
  page.set_primary_action("Actualizar indicadores", () => load(), "refresh");

  body.html(`
    <div class="cc-project-center">
      <section id="cc-project-hero" class="cc-project-hero"><span class="text-muted">Cargando proyecto...</span></section>
      <section id="cc-project-metrics" class="cc-project-metrics"></section>
      <div class="cc-project-grid">
        <section class="cc-project-card cc-project-wide"><div class="cc-project-title"><strong>Fases de obra</strong><button class="btn btn-xs btn-default" data-route="phases">Ver todas</button></div><div id="cc-phase-list"></div></section>
        <section class="cc-project-card"><div class="cc-project-title"><strong>Contratos activos</strong><button class="btn btn-xs btn-default" data-route="contracts">Ver todos</button></div><div id="cc-contract-list"></div></section>
        <section class="cc-project-card"><div class="cc-project-title"><strong>Materiales críticos</strong><button class="btn btn-xs btn-default" data-route="materials">Ver inventario</button></div><div id="cc-material-list"></div></section>
        <section class="cc-project-card cc-project-wide"><div class="cc-project-title"><strong>Avances recientes</strong><button class="btn btn-xs btn-default" data-route="progress">Registrar avance</button></div><div id="cc-progress-list"></div></section>
      </div>
    </div>
  `);

  const style = document.createElement("style");
  style.textContent = `
    .cc-project-center{max-width:1420px;margin:0 auto;padding:6px 0 28px}.cc-project-hero{display:flex;align-items:flex-start;justify-content:space-between;gap:16px;padding:20px;border:1px solid var(--border-color);border-radius:18px;background:linear-gradient(135deg,var(--card-bg),var(--subtle-fg));margin-bottom:13px}.cc-project-hero h2{margin:4px 0}.cc-project-status{display:inline-flex;padding:5px 10px;border-radius:999px;background:rgba(23,92,76,.12);color:#175c4c;font-size:12px;font-weight:800}.cc-project-status.is-critical{background:var(--red-100);color:var(--red-700)}.cc-project-status.is-attention{background:var(--yellow-100);color:var(--yellow-800)}.cc-project-metrics{display:grid;grid-template-columns:repeat(6,minmax(0,1fr));gap:10px;margin-bottom:13px}.cc-project-metric{min-width:0;padding:13px;border:1px solid var(--border-color);border-radius:14px;background:var(--card-bg)}.cc-project-metric span,.cc-project-metric strong{display:block}.cc-project-metric span{color:var(--text-muted);font-size:11px}.cc-project-metric strong{overflow:hidden;margin-top:4px;font-size:18px;text-overflow:ellipsis}.cc-project-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:13px}.cc-project-card{min-width:0;padding:15px;border:1px solid var(--border-color);border-radius:16px;background:var(--card-bg)}.cc-project-wide{grid-column:1/-1}.cc-project-title{display:flex;align-items:center;justify-content:space-between;gap:8px;margin-bottom:12px}.cc-phase-row{display:grid;grid-template-columns:minmax(160px,1.4fr) repeat(4,minmax(90px,1fr));gap:8px;align-items:center;padding:10px 0;border-bottom:1px solid var(--border-color)}.cc-phase-row:last-child{border-bottom:0}.cc-row-label{min-width:0}.cc-row-label strong,.cc-row-label small{display:block}.cc-row-label strong{overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.cc-row-label small{color:var(--text-muted)}.cc-progress-bar{height:7px;overflow:hidden;border-radius:999px;background:var(--subtle-fg)}.cc-progress-bar i{display:block;height:100%;border-radius:inherit;background:#175c4c}.cc-simple-list{display:flex;flex-direction:column}.cc-simple-row{display:flex;align-items:flex-start;justify-content:space-between;gap:12px;padding:10px 0;border-bottom:1px solid var(--border-color)}.cc-simple-row:last-child{border-bottom:0}.cc-simple-row strong,.cc-simple-row small{display:block}.cc-simple-row small{color:var(--text-muted)}.cc-stock-low{color:var(--yellow-800)}.cc-stock-depleted{color:var(--red-700)}@media(max-width:1100px){.cc-project-metrics{grid-template-columns:repeat(3,minmax(0,1fr))}.cc-phase-row{grid-template-columns:minmax(150px,1.4fr) repeat(2,minmax(90px,1fr))}.cc-phase-row>*:nth-child(4),.cc-phase-row>*:nth-child(5){display:none}}@media(max-width:767px){.cc-project-hero{flex-direction:column;padding:15px}.cc-project-metrics{grid-template-columns:repeat(2,minmax(0,1fr))}.cc-project-grid{grid-template-columns:1fr}.cc-project-wide{grid-column:auto}.cc-phase-row{display:block}.cc-phase-row>*{margin:7px 0}.cc-phase-row>*:nth-child(4),.cc-phase-row>*:nth-child(5){display:block}}
  `;
  wrapper.appendChild(style);

  function escape(value) {
    return frappe.utils.escape_html(String(value ?? ""));
  }

  function money(value) {
    return format_currency(value || 0, "HNL");
  }

  function render(summary) {
    if (!summary.project) {
      body.find("#cc-project-hero").html(`<div><h2>Sin proyecto activo</h2><p class="text-muted">Configure un perfil de proyecto para comenzar.</p></div>`);
      body.find("#cc-project-metrics,#cc-phase-list,#cc-contract-list,#cc-material-list,#cc-progress-list").empty();
      return;
    }
    activeProject = summary.project;
    page.fields_dict.project?.set_value(summary.project);
    const statusClass = summary.alert_level === "critical" ? "is-critical" : summary.alert_level === "attention" ? "is-attention" : "";
    body.find("#cc-project-hero").html(`<div><small class="text-muted">PROYECTO ACTIVO</small><h2>${escape(summary.project_name || summary.project)}</h2><p class="text-muted">${summary.phase_count || 0} fases · ${summary.delayed_phase_count || 0} atrasadas · ${summary.at_risk_phase_count || 0} en riesgo</p></div><span class="cc-project-status ${statusClass}">${escape(summary.schedule_status || "on_track")}</span>`);

    const metrics = [
      ["Presupuesto actualizado", money(summary.updated_budget_hnl)],
      ["Comprometido", money(summary.committed_hnl)],
      ["Costo real", money(summary.actual_cost_hnl)],
      ["Disponible", money(summary.available_budget_hnl)],
      ["Avance físico", `${summary.physical_progress_percent || 0}%`],
      ["Avance financiero", `${summary.financial_progress_percent || 0}%`],
    ];
    body.find("#cc-project-metrics").html(metrics.map(row => `<div class="cc-project-metric"><span>${escape(row[0])}</span><strong>${row[1]}</strong></div>`).join(""));

    const phases = summary.phases || [];
    body.find("#cc-phase-list").html(phases.length ? phases.map(row => `<button class="cc-phase-row" data-doctype="CC Construction Phase" data-name="${escape(row.name)}"><span class="cc-row-label"><strong>${escape(row.phase_name)}</strong><small>${escape(row.schedule_status)}</small></span><span><small class="text-muted">Presupuesto</small><strong>${money(row.budget_hnl)}</strong></span><span><small class="text-muted">Costo real</small><strong>${money(row.actual_cost_hnl)}</strong></span><span><small class="text-muted">Físico</small><strong>${row.physical_progress_percent || 0}%</strong></span><span><small class="text-muted">Financiero</small><strong>${row.financial_progress_percent || 0}%</strong></span><span class="cc-progress-bar"><i style="width:${Math.min(Math.max(row.physical_progress_percent || 0, 0), 100)}%"></i></span></button>`).join("") : `<span class="text-muted">No hay fases registradas.</span>`);

    const contracts = summary.contracts || [];
    body.find("#cc-contract-list").html(`<div class="cc-simple-list">${contracts.length ? contracts.map(row => `<button class="cc-simple-row" data-doctype="CC Labor Contract" data-name="${escape(row.name)}"><span><strong>${escape(row.contractor_name || row.contract_code)}</strong><small>${escape(row.status || "")}</small></span><span><strong>${money(row.balance_hnl)}</strong><small>Saldo</small></span></button>`).join("") : `<span class="text-muted">No hay contratos registrados.</span>`}</div>`);

    const materials = summary.materials || [];
    body.find("#cc-material-list").html(`<div class="cc-simple-list">${materials.length ? materials.map(row => `<button class="cc-simple-row" data-doctype="CC Material Ledger" data-name="${escape(row.name)}"><span><strong>${escape(row.material_name)}</strong><small class="cc-stock-${escape(row.stock_status)}">${escape(row.stock_status || "available")}</small></span><span><strong>${escape(row.current_qty || 0)} ${escape(row.unit || "")}</strong><small>Existencia</small></span></button>`).join("") : `<span class="text-muted">No hay materiales registrados.</span>`}</div>`);

    const progress = summary.recent_progress || [];
    body.find("#cc-progress-list").html(`<div class="cc-simple-list">${progress.length ? progress.map(row => `<button class="cc-simple-row" data-doctype="CC Progress Update" data-name="${escape(row.name)}"><span><strong>${escape(row.title || "Actualización de avance")}</strong><small>${escape(row.posting_date || "")} · ${escape(row.responsible || "")}</small></span><span><strong>${escape(row.progress_percent || 0)}%</strong><small>${escape(row.quality || "")}</small></span></button>`).join("") : `<span class="text-muted">No hay actualizaciones recientes.</span>`}</div>`);
  }

  function load() {
    frappe.dom.freeze("Actualizando indicadores de obra...");
    return frappe.xcall("erpnext.construcontrol.construction.get_project_center", {project: activeProject})
      .then(render)
      .finally(() => frappe.dom.unfreeze());
  }

  body.on("click", "[data-doctype][data-name]", function () {
    frappe.set_route("Form", $(this).data("doctype"), $(this).data("name"));
  });
  body.on("click", "[data-route]", function () {
    const route = $(this).data("route");
    const targets = {
      phases: ["List", "CC Construction Phase"],
      contracts: ["List", "CC Labor Contract"],
      materials: ["List", "CC Material Ledger"],
      progress: ["Form", "CC Progress Update", "new-cc-progress-update-1"],
    };
    if (targets[route]) frappe.set_route(...targets[route]);
  });

  load();
};
