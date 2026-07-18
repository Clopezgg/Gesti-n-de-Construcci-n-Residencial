frappe.pages["construcontrol-reporting-center"].on_page_load = function (wrapper) {
  frappe.ui.make_app_page({ parent: wrapper, title: "BI01 · Reportes y notificaciones", single_column: true });
  const body = $(wrapper).find(".layout-main-section");
  let lastNotificationLog = null;
  const today = frappe.datetime.get_today();
  const monthStart = `${today.slice(0, 8)}01`;

  body.html(`
    <style>
      .cc-bi{max-width:1200px}.cc-bi-toolbar{display:grid;grid-template-columns:repeat(4,minmax(150px,1fr));gap:10px;align-items:end;padding:14px;border:1px solid var(--border-color);border-radius:12px;background:var(--card-bg)}
      .cc-bi-toolbar label{display:block;font-weight:600}.cc-bi-toolbar input,.cc-bi-toolbar select,.cc-bi textarea{width:100%;min-height:42px;margin-top:5px;border:1px solid var(--border-color);border-radius:8px;padding:8px;background:var(--control-bg);color:var(--text-color)}
      .cc-bi-actions{display:flex;gap:8px;flex-wrap:wrap;margin:12px 0}.cc-bi-metrics{display:grid;grid-template-columns:repeat(auto-fit,minmax(155px,1fr));gap:10px;margin:12px 0}.cc-bi-metric{padding:14px;border:1px solid var(--border-color);border-radius:12px;background:var(--card-bg)}.cc-bi-metric strong{display:block;margin-top:4px;font-size:20px}
      .cc-bi-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px}.cc-bi-card{padding:14px;border:1px solid var(--border-color);border-radius:12px;background:var(--card-bg)}.cc-bi-row{display:flex;justify-content:space-between;gap:10px;padding:8px 0;border-bottom:1px solid var(--border-color)}.cc-bi-row:last-child{border-bottom:0}.cc-bi-empty{color:var(--text-muted);padding:12px 0}.cc-bi-result{margin-top:10px;padding:10px;border-radius:8px;background:var(--subtle-fg)}
      .cc-bi-phase{margin:10px 0}.cc-bi-progress{height:8px;background:var(--control-bg);border-radius:99px;overflow:hidden}.cc-bi-progress span{display:block;height:100%;background:var(--primary)}
      @media(max-width:767px){.cc-bi-toolbar{grid-template-columns:1fr}.cc-bi-grid{grid-template-columns:1fr}.cc-bi-actions .btn{flex:1 1 100%}}
    </style>
    <div class="cc-bi">
      <div class="cc-bi-toolbar">
        <label>Desde<input id="cc-bi-from" type="date" value="${monthStart}"></label>
        <label>Hasta<input id="cc-bi-to" type="date" value="${today}"></label>
        <label>Proyecto<select id="cc-bi-project"><option value="">Todos los proyectos permitidos</option></select></label>
        <label>Tipo de reporte<select id="cc-bi-type"><option value="financial">Financiero</option><option value="expenses">Gastos</option><option value="contracts">Contratos</option><option value="phases">Fases</option><option value="weekly">Cierre semanal</option></select></label>
      </div>
      <div class="cc-bi-actions"><button class="btn btn-primary" id="cc-bi-refresh">Actualizar datos</button><button class="btn btn-default" id="cc-bi-generate">Guardar reporte BI01</button><button class="btn btn-default" id="cc-bi-reports">Historial de reportes</button></div>
      <div id="cc-bi-status" class="text-muted">Cargando datos vivos...</div>
      <div id="cc-bi-metrics" class="cc-bi-metrics"></div>
      <div class="cc-bi-grid">
        <section class="cc-bi-card"><h3>Gastos por categoría</h3><div id="cc-bi-categories"></div></section>
        <section class="cc-bi-card"><h3>Principales proveedores</h3><div id="cc-bi-providers"></div></section>
        <section class="cc-bi-card"><h3>Avance por fase</h3><div id="cc-bi-phases"></div></section>
        <section class="cc-bi-card"><h3>Notificación manual autorizada</h3><p class="text-muted">ConstruControl prepara el mensaje y el enlace. El envío se confirma manualmente; no se exponen tokens externos.</p><label>Contacto<select id="cc-bi-contact"><option value="">Seleccione un contacto autorizado</option></select></label><label>Evento<select id="cc-bi-event"><option value="income">Ingreso/remesa</option><option value="expense">Gasto</option><option value="material">Material</option><option value="inventory">Inventario</option><option value="progress">Avance</option><option value="weekly">Cierre semanal</option><option value="report">Reporte</option><option value="manual">Manual</option></select></label><label>Mensaje opcional<textarea id="cc-bi-message" rows="4" maxlength="1500" placeholder="Vacío usa la plantilla segura del sistema"></textarea></label><div class="cc-bi-actions"><button class="btn btn-primary" id="cc-bi-prepare">Preparar WhatsApp</button><button class="btn btn-default" id="cc-bi-contacts">Contactos</button><button class="btn btn-default" id="cc-bi-rules">Reglas</button><button class="btn btn-default" id="cc-bi-logs">Historial</button></div><div id="cc-bi-notification-result"></div></section>
      </div>
    </div>
  `);

  const money = value => format_currency(value || 0, "HNL");
  const esc = value => frappe.utils.escape_html(String(value ?? ""));
  const params = () => ({
    date_from: body.find("#cc-bi-from").val(),
    date_to: body.find("#cc-bi-to").val(),
    project: body.find("#cc-bi-project").val() || null
  });

  async function loadProjects() {
    try {
      const rows = await frappe.db.get_list("Project", {
        fields: ["name", "project_name"],
        filters: { status: ["!=", "Cancelled"] },
        limit: 200,
        order_by: "project_name asc"
      });
      body.find("#cc-bi-project").append(rows.map(row => `<option value="${esc(row.name)}">${esc(row.project_name || row.name)}</option>`).join(""));
    } catch (_error) {}
  }

  async function loadContacts() {
    try {
      const rows = await frappe.db.get_list("CC Notification Contact", {
        fields: ["name", "title", "contact_name", "phone", "authorized", "active"],
        filters: { is_logically_deleted: 0 },
        limit: 200,
        order_by: "title asc"
      });
      const usable = rows.filter(row => Number(row.active ?? 1) && Number(row.authorized ?? 0));
      body.find("#cc-bi-contact").append(usable.map(row => `<option value="${esc(row.name)}">${esc(row.contact_name || row.title || row.name)} · ${esc(row.phone || "sin teléfono")}</option>`).join(""));
    } catch (_error) {}
  }

  async function refresh() {
    body.find("#cc-bi-status").text("Consultando datos vivos...");
    try {
      const summary = await frappe.xcall("erpnext.construcontrol.reporting.get_reporting_summary", params());
      const totals = summary.totals || {};
      const counts = summary.counts || {};
      const metrics = [
        ["Recibido", money(totals.received_hnl)],
        ["Gastado", money(totals.spent_hnl)],
        ["Pendiente", money(totals.pending_hnl)],
        ["Disponible", money(totals.available_hnl)],
        ["Contratado", money(totals.contracted_hnl)],
        ["Avance", `${totals.overall_progress || 0}%`]
      ];
      body.find("#cc-bi-metrics").html(metrics.map(row => `<div class="cc-bi-metric"><span class="text-muted">${row[0]}</span><strong>${row[1]}</strong></div>`).join(""));
      const renderRows = (rows, target) => body.find(target).html(rows.length ? rows.map(row => `<div class="cc-bi-row"><span>${esc(row.label)}</span><strong>${money(row.amount_hnl)}</strong></div>`).join("") : `<div class="cc-bi-empty">Sin movimientos en el período.</div>`);
      renderRows(summary.expense_categories || [], "#cc-bi-categories");
      renderRows(summary.providers || [], "#cc-bi-providers");
      body.find("#cc-bi-phases").html((summary.phases || []).length ? summary.phases.map(row => {
        const progress = Math.max(0, Math.min(100, Number(row.progress_percent || 0)));
        return `<div class="cc-bi-phase"><div class="cc-bi-row"><span>${esc(row.phase_name || row.name)}</span><strong>${progress}%</strong></div><div class="cc-bi-progress"><span style="width:${progress}%"></span></div></div>`;
      }).join("") : `<div class="cc-bi-empty">Sin fases para mostrar.</div>`);
      body.find("#cc-bi-status").text(`${summary.period.date_from} a ${summary.period.date_to} · ${counts.funds || 0} ingresos · ${counts.expenses || 0} gastos · generado por ${summary.generated_by.role}`);
    } catch (_error) {
      body.find("#cc-bi-status").html(`<span class="text-danger">No se pudo consultar el reporte. Revise permisos y fechas.</span>`);
    }
  }

  body.find("#cc-bi-refresh").on("click", refresh);
  body.find("#cc-bi-reports").on("click", () => frappe.set_route("List", "CC Generated Report"));
  body.find("#cc-bi-contacts").on("click", () => frappe.set_route("List", "CC Notification Contact"));
  body.find("#cc-bi-rules").on("click", () => frappe.set_route("List", "CC Notification Rule"));
  body.find("#cc-bi-logs").on("click", () => frappe.set_route("List", "CC Notification Log"));

  body.find("#cc-bi-generate").on("click", async () => {
    try {
      const result = await frappe.xcall("erpnext.construcontrol.reporting.generate_report_record", {
        ...params(),
        report_type: body.find("#cc-bi-type").val()
      });
      frappe.show_alert({ message: `Reporte ${result.name} guardado`, indicator: "green" });
      frappe.set_route("Form", "CC Generated Report", result.name);
    } catch (_error) {}
  });

  body.find("#cc-bi-prepare").on("click", async () => {
    const contact = body.find("#cc-bi-contact").val();
    if (!contact) {
      frappe.msgprint("Seleccione un contacto activo y autorizado.");
      return;
    }
    try {
      const result = await frappe.xcall("erpnext.construcontrol.reporting.prepare_notification", {
        ...params(),
        contact,
        event_type: body.find("#cc-bi-event").val(),
        message: body.find("#cc-bi-message").val() || null
      });
      lastNotificationLog = result.log;
      body.find("#cc-bi-notification-result").html(`<div class="cc-bi-result"><p>${esc(result.message)}</p><div class="cc-bi-actions"><a class="btn btn-primary" target="_blank" rel="noopener noreferrer" href="${esc(result.whatsapp_url)}">Abrir WhatsApp</a><button class="btn btn-default" id="cc-bi-sent">Marcar envío manual</button></div></div>`);
      body.find("#cc-bi-sent").on("click", async () => {
        if (!lastNotificationLog) return;
        await frappe.xcall("erpnext.construcontrol.reporting.mark_notification_sent", { log_name: lastNotificationLog });
        frappe.show_alert({ message: "Envío manual confirmado", indicator: "green" });
        body.find("#cc-bi-sent").prop("disabled", true);
      });
    } catch (_error) {}
  });

  Promise.all([loadProjects(), loadContacts()]).then(refresh);
};
