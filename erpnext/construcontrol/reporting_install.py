from __future__ import annotations

import frappe

PAGE_NAME = "construcontrol-reporting-center"

PAGE_SCRIPT = r'''
frappe.pages["construcontrol-reporting-center"].on_page_load = function (wrapper) {
  const page = frappe.ui.make_app_page({parent: wrapper, title: "BI01 · Reportes y notificaciones", single_column: true});
  const body = $(wrapper).find(".layout-main-section");
  let lastNotificationLog = null;
  const today = frappe.datetime.get_today();
  const monthStart = today.slice(0, 8) + "01";

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
  const params = () => ({date_from: body.find("#cc-bi-from").val(), date_to: body.find("#cc-bi-to").val(), project: body.find("#cc-bi-project").val() || null});

  async function loadProjects(){
    try {
      const rows = await frappe.db.get_list("Project", {fields:["name","project_name"], filters:{status:["!=","Cancelled"]}, limit:200, order_by:"project_name asc"});
      body.find("#cc-bi-project").append(rows.map(row => `<option value="${esc(row.name)}">${esc(row.project_name || row.name)}</option>`).join(""));
    } catch(_error) {}
  }

  async function loadContacts(){
    try {
      const rows = await frappe.db.get_list("CC Notification Contact", {fields:["name","title","contact_name","phone","authorized","active"], filters:{is_logically_deleted:0}, limit:200, order_by:"title asc"});
      const usable = rows.filter(row => Number(row.active ?? 1) && Number(row.authorized ?? 0));
      body.find("#cc-bi-contact").append(usable.map(row => `<option value="${esc(row.name)}">${esc(row.contact_name || row.title || row.name)} · ${esc(row.phone || "sin teléfono")}</option>`).join(""));
    } catch(_error) {}
  }

  async function refresh(){
    body.find("#cc-bi-status").text("Consultando datos vivos...");
    try {
      const summary = await frappe.xcall("erpnext.construcontrol.reporting.get_reporting_summary", params());
      const t = summary.totals || {}; const c = summary.counts || {};
      const metrics = [["Recibido",money(t.received_hnl)],["Gastado",money(t.spent_hnl)],["Pendiente",money(t.pending_hnl)],["Disponible",money(t.available_hnl)],["Contratado",money(t.contracted_hnl)],["Avance",`${t.overall_progress || 0}%`]];
      body.find("#cc-bi-metrics").html(metrics.map(row => `<div class="cc-bi-metric"><span class="text-muted">${row[0]}</span><strong>${row[1]}</strong></div>`).join(""));
      const renderRows = (rows, target) => body.find(target).html(rows.length ? rows.map(row => `<div class="cc-bi-row"><span>${esc(row.label)}</span><strong>${money(row.amount_hnl)}</strong></div>`).join("") : `<div class="cc-bi-empty">Sin movimientos en el período.</div>`);
      renderRows(summary.expense_categories || [], "#cc-bi-categories"); renderRows(summary.providers || [], "#cc-bi-providers");
      body.find("#cc-bi-phases").html((summary.phases || []).length ? summary.phases.map(row => {const progress=Math.max(0,Math.min(100,Number(row.progress_percent||0))); return `<div class="cc-bi-phase"><div class="cc-bi-row"><span>${esc(row.phase_name || row.name)}</span><strong>${progress}%</strong></div><div class="cc-bi-progress"><span style="width:${progress}%"></span></div></div>`;}).join("") : `<div class="cc-bi-empty">Sin fases para mostrar.</div>`);
      body.find("#cc-bi-status").text(`${summary.period.date_from} a ${summary.period.date_to} · ${c.funds||0} ingresos · ${c.expenses||0} gastos · generado por ${summary.generated_by.role}`);
    } catch(error) {
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
      const result = await frappe.xcall("erpnext.construcontrol.reporting.generate_report_record", {...params(), report_type: body.find("#cc-bi-type").val()});
      frappe.show_alert({message:`Reporte ${result.name} guardado`, indicator:"green"});
      frappe.set_route("Form", "CC Generated Report", result.name);
    } catch(_error) {}
  });

  body.find("#cc-bi-prepare").on("click", async () => {
    const contact = body.find("#cc-bi-contact").val();
    if(!contact){frappe.msgprint("Seleccione un contacto activo y autorizado."); return;}
    try {
      const result = await frappe.xcall("erpnext.construcontrol.reporting.prepare_notification", {...params(), contact, event_type:body.find("#cc-bi-event").val(), message:body.find("#cc-bi-message").val() || null});
      lastNotificationLog = result.log;
      body.find("#cc-bi-notification-result").html(`<div class="cc-bi-result"><p>${esc(result.message)}</p><div class="cc-bi-actions"><a class="btn btn-primary" target="_blank" rel="noopener noreferrer" href="${esc(result.whatsapp_url)}">Abrir WhatsApp</a><button class="btn btn-default" id="cc-bi-sent">Marcar envío manual</button></div></div>`);
      body.find("#cc-bi-sent").on("click", async () => {if(!lastNotificationLog)return; await frappe.xcall("erpnext.construcontrol.reporting.mark_notification_sent", {log_name:lastNotificationLog}); frappe.show_alert({message:"Envío manual confirmado",indicator:"green"}); body.find("#cc-bi-sent").prop("disabled",true);});
    } catch(_error) {}
  });

  Promise.all([loadProjects(), loadContacts()]).then(refresh);
};
'''


def _custom_fields() -> dict[str, list[dict[str, object]]]:
    return {
        "CC Generated Report": [
            {"fieldname":"report_type","label":"Tipo de reporte","fieldtype":"Select","options":"financial\nexpenses\ncontracts\nphases\nweekly","insert_after":"description","in_list_view":1},
            {"fieldname":"date_from","label":"Desde","fieldtype":"Date","insert_after":"report_type","in_list_view":1},
            {"fieldname":"date_to","label":"Hasta","fieldtype":"Date","insert_after":"date_from","in_list_view":1},
            {"fieldname":"generated_at","label":"Generado","fieldtype":"Datetime","read_only":1,"insert_after":"date_to"},
            {"fieldname":"generated_by_name","label":"Generado por","fieldtype":"Data","read_only":1,"insert_after":"generated_at","in_list_view":1},
            {"fieldname":"generated_by_email","label":"Correo","fieldtype":"Data","read_only":1,"insert_after":"generated_by_name"},
            {"fieldname":"generated_by_role","label":"Rol","fieldtype":"Data","read_only":1,"insert_after":"generated_by_email","in_list_view":1},
            {"fieldname":"filters_json","label":"Filtros","fieldtype":"Code","options":"JSON","read_only":1,"insert_after":"generated_by_role"},
            {"fieldname":"totals_json","label":"Totales","fieldtype":"Code","options":"JSON","read_only":1,"insert_after":"filters_json"},
        ],
        "CC Notification Contact": [
            {"fieldname":"contact_name","label":"Nombre del contacto","fieldtype":"Data","insert_after":"description","in_list_view":1},
            {"fieldname":"phone","label":"Teléfono con código de país","fieldtype":"Data","insert_after":"contact_name","in_list_view":1},
            {"fieldname":"relationship","label":"Relación","fieldtype":"Data","insert_after":"phone"},
            {"fieldname":"preferred_channel","label":"Canal preferido","fieldtype":"Select","options":"whatsapp\ninternal\ncopy","default":"whatsapp","insert_after":"relationship"},
            {"fieldname":"authorized","label":"Autorizado para notificaciones","fieldtype":"Check","default":"0","insert_after":"preferred_channel","in_list_view":1},
            {"fieldname":"active","label":"Activo","fieldtype":"Check","default":"1","insert_after":"authorized","in_list_view":1},
            {"fieldname":"notes","label":"Notas","fieldtype":"Small Text","insert_after":"active"},
        ],
        "CC Notification Rule": [
            {"fieldname":"event_type","label":"Evento","fieldtype":"Select","options":"income\nexpense\nmaterial\ninventory\nprogress\nweekly\nreport\nmanual","insert_after":"description","in_list_view":1},
            {"fieldname":"channel","label":"Canal","fieldtype":"Select","options":"whatsapp\ninternal\ncopy","default":"whatsapp","insert_after":"event_type","in_list_view":1},
            {"fieldname":"contact","label":"Contacto","fieldtype":"Link","options":"CC Notification Contact","insert_after":"channel"},
            {"fieldname":"message_template","label":"Plantilla","fieldtype":"Small Text","insert_after":"contact"},
            {"fieldname":"active","label":"Activa","fieldtype":"Check","default":"1","insert_after":"message_template","in_list_view":1},
        ],
        "CC Notification Log": [
            {"fieldname":"event_type","label":"Evento","fieldtype":"Data","read_only":1,"insert_after":"description","in_list_view":1},
            {"fieldname":"channel","label":"Canal","fieldtype":"Data","read_only":1,"insert_after":"event_type","in_list_view":1},
            {"fieldname":"contact","label":"Contacto","fieldtype":"Link","options":"CC Notification Contact","read_only":1,"insert_after":"channel"},
            {"fieldname":"recipient","label":"Destinatario","fieldtype":"Data","read_only":1,"insert_after":"contact"},
            {"fieldname":"message","label":"Mensaje","fieldtype":"Small Text","read_only":1,"insert_after":"recipient"},
            {"fieldname":"prepared_at","label":"Preparado","fieldtype":"Datetime","read_only":1,"insert_after":"message"},
            {"fieldname":"sent_at","label":"Enviado","fieldtype":"Datetime","read_only":1,"insert_after":"prepared_at"},
            {"fieldname":"delivery_status","label":"Estado de entrega","fieldtype":"Select","options":"prepared\ncopied\nsent_manual\nfailed\nblocked","read_only":1,"insert_after":"sent_at","in_list_view":1},
            {"fieldname":"related_doctype","label":"Tipo relacionado","fieldtype":"Link","options":"DocType","read_only":1,"insert_after":"delivery_status"},
            {"fieldname":"related_name","label":"Registro relacionado","fieldtype":"Dynamic Link","options":"related_doctype","read_only":1,"insert_after":"related_doctype"},
            {"fieldname":"whatsapp_url","label":"Enlace manual","fieldtype":"Small Text","read_only":1,"insert_after":"related_name"},
            {"fieldname":"error_message","label":"Error","fieldtype":"Small Text","read_only":1,"insert_after":"whatsapp_url"},
        ],
    }


def ensure_reporting_integration() -> None:
    from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

    create_custom_fields(_custom_fields(), update=True)
    values = {
        "doctype": "Page",
        "name": PAGE_NAME,
        "page_name": PAGE_NAME,
        "title": "BI01 · Reportes y notificaciones",
        "module": "ConstruControl",
        "standard": "No",
        "system_page": 0,
        "script": PAGE_SCRIPT,
    }
    if frappe.db.exists("Page", PAGE_NAME):
        page = frappe.get_doc("Page", PAGE_NAME)
        for fieldname, value in values.items():
            if fieldname != "doctype":
                page.set(fieldname, value)
        page.set("roles", [])
    else:
        page = frappe.get_doc(values)
    for role in ("System Manager","ConstruControl Manager","ConstruControl Operator","ConstruControl Auditor","ConstruControl Viewer"):
        page.append("roles", {"role": role})
    page.save(ignore_permissions=True) if page.name and not page.is_new() else page.insert(ignore_permissions=True)
