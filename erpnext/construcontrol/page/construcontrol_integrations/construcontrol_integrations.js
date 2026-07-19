frappe.pages["construcontrol-integrations"].on_page_load = function (wrapper) {
  "use strict";

  const page = frappe.ui.make_app_page({parent: wrapper, title: "Integraciones", single_column: true});
  const body = $(wrapper).find(".layout-main-section");
  page.set_primary_action("Nueva integración", () => createIntegration(), "add");
  page.add_inner_button("Archivadas", () => load(true));

  body.html(`
    <div class="cc-integrations-page">
      <section class="cc-integrations-hero"><div><small>ADMINISTRACIÓN ÚNICA</small><h2>Integraciones</h2><p>Active, configure, pruebe o retire conexiones sin duplicar módulos ni exponer credenciales.</p></div><span id="cc-integration-count" class="cc-integration-count">0 activas</span></section>
      <div id="cc-integrations-grid" class="cc-integrations-grid"><span class="text-muted">Cargando integraciones...</span></div>
    </div>
  `);

  const style = document.createElement("style");
  style.textContent = `
    .cc-integrations-page{max-width:1260px;margin:0 auto;padding:6px 0 28px}.cc-integrations-hero{display:flex;align-items:flex-start;justify-content:space-between;gap:16px;padding:20px;border:1px solid var(--border-color);border-radius:18px;background:linear-gradient(135deg,var(--card-bg),var(--subtle-fg));margin-bottom:14px}.cc-integrations-hero small{color:#175c4c;font-weight:900;letter-spacing:.08em}.cc-integrations-hero h2{margin:5px 0}.cc-integrations-hero p{margin:0;color:var(--text-muted)}.cc-integration-count{display:inline-flex;padding:6px 11px;border-radius:999px;background:rgba(23,92,76,.12);color:#175c4c;font-weight:800}.cc-integrations-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:12px}.cc-integration-card{display:flex;min-width:0;flex-direction:column;padding:16px;border:1px solid var(--border-color);border-radius:16px;background:var(--card-bg)}.cc-integration-card.is-disabled{opacity:.75}.cc-integration-head{display:flex;align-items:flex-start;gap:11px}.cc-integration-icon{display:grid;width:46px;min-width:46px;height:46px;overflow:hidden;place-items:center;border-radius:13px;background:var(--integration-color,#175c4c);color:#fff;font-weight:900}.cc-integration-icon img{width:100%;height:100%;object-fit:contain;background:#fff;padding:5px}.cc-integration-name{min-width:0;flex:1}.cc-integration-name strong,.cc-integration-name small{display:block}.cc-integration-name strong{overflow:hidden;text-overflow:ellipsis;white-space:nowrap;font-size:15px}.cc-integration-name small{color:var(--text-muted)}.cc-integration-status{display:inline-flex;padding:3px 8px;border-radius:999px;background:var(--subtle-fg);font-size:11px;font-weight:800}.cc-integration-status.healthy{background:var(--green-100);color:var(--green-700)}.cc-integration-status.warning{background:var(--yellow-100);color:var(--yellow-800)}.cc-integration-status.error{background:var(--red-100);color:var(--red-700)}.cc-integration-description{min-height:44px;margin:12px 0;color:var(--text-muted)}.cc-integration-meta{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:8px;margin-bottom:12px}.cc-integration-meta>div{padding:8px;border-radius:10px;background:var(--subtle-fg)}.cc-integration-meta span,.cc-integration-meta strong{display:block}.cc-integration-meta span{color:var(--text-muted);font-size:10px}.cc-integration-meta strong{overflow:hidden;text-overflow:ellipsis;white-space:nowrap;font-size:12px}.cc-integration-actions{display:flex;flex-wrap:wrap;gap:6px;margin-top:auto}.cc-integration-actions .btn{flex:1 1 auto}.cc-integration-protected{color:#175c4c;font-size:11px;font-weight:800}@media(max-width:767px){.cc-integrations-hero{flex-direction:column;padding:15px}.cc-integrations-grid{grid-template-columns:1fr}.cc-integration-card{padding:14px}.cc-integration-actions .btn{flex-basis:46%}}
  `;
  wrapper.appendChild(style);

  function escape(value) { return frappe.utils.escape_html(String(value ?? "")); }
  function initials(value) { return String(value || "IN").split(/\s+/).slice(0,2).map(part => part[0] || "").join("").toUpperCase(); }
  function icon(row) {
    if (row.icon_file) return `<span class="cc-integration-icon" style="--integration-color:${escape(row.brand_color || "#175c4c")}"><img alt="" src="${escape(row.icon_file)}"></span>`;
    return `<span class="cc-integration-icon" style="--integration-color:${escape(row.brand_color || "#175c4c")}">${escape(initials(row.integration_name))}</span>`;
  }
  function render(rows) {
    const active = rows.filter(row => row.enabled && !row.is_logically_deleted).length;
    body.find("#cc-integration-count").text(`${active} activas`);
    body.find("#cc-integrations-grid").html(rows.length ? rows.map(row => `
      <article class="cc-integration-card ${row.enabled ? "" : "is-disabled"}" data-name="${escape(row.name)}">
        <div class="cc-integration-head">${icon(row)}<div class="cc-integration-name"><strong>${escape(row.integration_name)}</strong><small>${escape(row.category)} · ${escape(row.provider_type)}</small></div><span class="cc-integration-status ${escape(row.status)}">${escape(row.status)}</span></div>
        <p class="cc-integration-description">${escape(row.description || "Sin descripción")}</p>
        <div class="cc-integration-meta"><div><span>Credencial</span><strong>${row.credential_configured ? "Configurada" : "No configurada"}</strong></div><div><span>Última prueba</span><strong>${escape(row.last_test_status || "not_tested")}</strong></div></div>
        ${row.is_protected ? `<div class="cc-integration-protected">Integración esencial protegida</div>` : ``}
        <div class="cc-integration-actions">
          <button class="btn btn-sm ${row.enabled ? "btn-default" : "btn-primary"}" data-action="toggle" data-enabled="${row.enabled ? 0 : 1}">${row.enabled ? "Desactivar" : "Activar"}</button>
          <button class="btn btn-sm btn-default" data-action="test">Probar</button>
          <button class="btn btn-sm btn-default" data-action="configure">Configurar</button>
          ${row.is_protected ? `` : `<button class="btn btn-sm btn-default" data-action="archive">Archivar</button><button class="btn btn-sm btn-danger" data-action="delete">Eliminar</button>`}
        </div>
      </article>`).join("") : `<div class="text-muted">No hay integraciones registradas.</div>`);
  }
  function load(includeArchived=false) {
    return frappe.xcall("erpnext.construcontrol.integrations.list_integrations", {include_archived: includeArchived ? 1 : 0}).then(render);
  }
  function selected(button) { return $(button).closest(".cc-integration-card").data("name"); }
  function createIntegration() {
    frappe.prompt([
      {fieldname:"integration_name",fieldtype:"Data",label:"Nombre",reqd:1},
      {fieldname:"category",fieldtype:"Select",label:"Categoría",options:"custom\ndata\ncommunication\nfinance\ndocument",default:"custom",reqd:1},
      {fieldname:"provider_type",fieldtype:"Select",label:"Proveedor",options:"custom\napi\nwebhook\nwhatsapp",default:"custom",reqd:1},
      {fieldname:"endpoint_url",fieldtype:"Data",label:"URL HTTPS"},
      {fieldname:"description",fieldtype:"Small Text",label:"Descripción"},
    ], values => frappe.xcall("erpnext.construcontrol.integrations.create_custom_integration", values).then(() => load()), "Nueva integración", "Crear");
  }
  body.on("click", "[data-action]", function () {
    const name = selected(this); const action = $(this).data("action");
    if (action === "configure") return frappe.set_route("Form", "CC Integration Registry", name);
    if (action === "toggle") return frappe.xcall("erpnext.construcontrol.integrations.set_integration_enabled", {name, enabled: $(this).data("enabled")}).then(() => load());
    if (action === "test") return frappe.xcall("erpnext.construcontrol.integrations.test_integration", {name}).then(row => { frappe.msgprint({title:"Resultado de prueba",indicator:row.last_test_status === "passed" ? "green" : row.last_test_status === "warning" ? "orange" : "red",message:escape(row.last_test_message)}); load(); });
    if (action === "archive") return frappe.confirm("¿Archivar esta integración personalizada?", () => frappe.xcall("erpnext.construcontrol.integrations.archive_integration", {name, archived:1}).then(() => load()));
    if (action === "delete") return frappe.prompt([{fieldname:"confirmation",fieldtype:"Data",label:"Escriba ELIMINAR",reqd:1}], values => frappe.xcall("erpnext.construcontrol.integrations.delete_custom_integration", {name, confirmation:values.confirmation}).then(() => load()), "Eliminar integración", "Eliminar");
  });
  load();
};
