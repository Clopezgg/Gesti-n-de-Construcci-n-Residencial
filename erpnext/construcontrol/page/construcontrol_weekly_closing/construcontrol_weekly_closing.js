frappe.pages["construcontrol-weekly-closing"].on_page_load = function (wrapper) {
  frappe.ui.make_app_page({ parent: wrapper, title: "CL01 · Cierre semanal", single_column: true });
  const body = $(wrapper).find(".layout-main-section");
  let preview = null;
  const now = new Date();
  const day = (now.getDay() + 6) % 7;
  const monday = new Date(now);
  monday.setDate(now.getDate() - day);
  const sunday = new Date(monday);
  sunday.setDate(monday.getDate() + 6);
  const iso = date => date.toISOString().slice(0, 10);
  const esc = value => frappe.utils.escape_html(String(value ?? ""));
  const money = value => format_currency(value || 0, "HNL");

  body.html(`
    <style>
      .cc-cl{max-width:1000px}.cc-cl-form{display:grid;grid-template-columns:repeat(4,minmax(150px,1fr));gap:10px;padding:14px;border:1px solid var(--border-color);border-radius:12px;background:var(--card-bg)}.cc-cl-form label{font-weight:600}.cc-cl-form input,.cc-cl-form select{width:100%;min-height:42px;margin-top:5px;border:1px solid var(--border-color);border-radius:8px;padding:8px;background:var(--control-bg);color:var(--text-color)}.cc-cl-actions{display:flex;gap:8px;flex-wrap:wrap;margin:12px 0}.cc-cl-metrics{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:10px}.cc-cl-metric,.cc-cl-panel{padding:14px;border:1px solid var(--border-color);border-radius:12px;background:var(--card-bg)}.cc-cl-metric strong{display:block;font-size:20px;margin-top:4px}.cc-cl-panel{margin-top:12px}@media(max-width:767px){.cc-cl-form{grid-template-columns:1fr}.cc-cl-actions .btn{flex:1 1 100%}}
    </style>
    <div class="cc-cl">
      <div class="cc-cl-form">
        <label>Semana inicia<input id="cc-cl-start" type="date" value="${iso(monday)}"></label>
        <label>Semana termina<input id="cc-cl-end" type="date" value="${iso(sunday)}"></label>
        <label>Proyecto<select id="cc-cl-project"><option value="">Todos los proyectos permitidos</option></select></label>
        <label>Estado<select id="cc-cl-status"><option value="draft">Borrador</option><option value="closed">Cerrado</option></select></label>
      </div>
      <div class="cc-cl-actions"><button class="btn btn-primary" id="cc-cl-preview">Calcular cierre</button><button class="btn btn-default" id="cc-cl-create" disabled>Guardar CL01</button><button class="btn btn-default" id="cc-cl-history">Historial</button></div>
      <div id="cc-cl-result" class="text-muted">Calcule primero el período.</div>
    </div>
  `);

  const params = () => ({
    week_start: body.find("#cc-cl-start").val(),
    week_end: body.find("#cc-cl-end").val(),
    project: body.find("#cc-cl-project").val() || null
  });

  async function loadProjects() {
    try {
      const rows = await frappe.db.get_list("Project", {
        fields: ["name", "project_name"],
        limit: 200,
        order_by: "project_name asc"
      });
      body.find("#cc-cl-project").append(rows.map(row => `<option value="${esc(row.name)}">${esc(row.project_name || row.name)}</option>`).join(""));
    } catch (_error) {}
  }

  body.find("#cc-cl-preview").on("click", async () => {
    preview = null;
    body.find("#cc-cl-create").prop("disabled", true);
    try {
      preview = await frappe.xcall("erpnext.construcontrol.weekly.preview_weekly_closing", params());
      const snapshot = preview.snapshot || {};
      const metrics = [
        ["Saldo inicial", money(snapshot.initial_balance_hnl)],
        ["Ingresos", money(snapshot.income_hnl)],
        ["Gastos", money(snapshot.expense_hnl)],
        ["Saldo final", money(snapshot.final_balance_hnl)],
        ["Pendiente", money(snapshot.pending_expense_hnl)],
        ["Avances", snapshot.progress_update_count || 0]
      ];
      body.find("#cc-cl-result").html(`<div class="cc-cl-metrics">${metrics.map(row => `<div class="cc-cl-metric"><span class="text-muted">${row[0]}</span><strong>${row[1]}</strong></div>`).join("")}</div><div class="cc-cl-panel"><h3>Pendientes</h3>${(snapshot.pending_items || []).length ? `<ul>${snapshot.pending_items.map(item => `<li>${esc(item)}</li>`).join("")}</ul>` : `<p class="text-muted">Sin pendientes detectados.</p>`}</div>`);
      body.find("#cc-cl-create").prop("disabled", false);
    } catch (_error) {}
  });

  body.find("#cc-cl-create").on("click", async () => {
    if (!preview) return;
    try {
      const result = await frappe.xcall("erpnext.construcontrol.weekly.create_weekly_closing", {
        ...params(),
        status: body.find("#cc-cl-status").val()
      });
      frappe.show_alert({ message: `Cierre ${result.name} guardado`, indicator: "green" });
      frappe.set_route("Form", "CC Weekly Closing", result.name);
    } catch (_error) {}
  });

  body.find("#cc-cl-history").on("click", () => frappe.set_route("List", "CC Weekly Closing"));
  loadProjects();
};
