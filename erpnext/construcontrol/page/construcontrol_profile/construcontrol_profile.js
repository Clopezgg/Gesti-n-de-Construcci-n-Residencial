frappe.pages["construcontrol-profile"].on_page_load = function (wrapper) {
  "use strict";

  const page = frappe.ui.make_app_page({
    parent: wrapper,
    title: "Mi perfil",
    single_column: true,
  });
  const body = $(wrapper).find(".layout-main-section");
  page.set_primary_action("Guardar cambios", () => saveProfile(), "save");

  body.html(`
    <div class="cc-profile-page">
      <section class="cc-profile-hero">
        <div id="cc-profile-avatar" class="cc-profile-avatar">CC</div>
        <div class="cc-profile-heading">
          <span id="cc-profile-role" class="cc-profile-role-large">USUARIO</span>
          <h2 id="cc-profile-display-name">Cargando perfil...</h2>
          <p id="cc-profile-email" class="text-muted"></p>
        </div>
      </section>

      <div class="cc-profile-layout">
        <section class="cc-profile-card">
          <div class="cc-profile-card-title"><strong>Información personal</strong><span>Datos visibles dentro de ConstruControl</span></div>
          <div class="cc-profile-form-grid">
            <label>Nombre<input id="cc-first-name" class="form-control" maxlength="140"></label>
            <label>Apellido<input id="cc-last-name" class="form-control" maxlength="140"></label>
            <label>Teléfono<input id="cc-mobile-no" class="form-control" maxlength="40" inputmode="tel"></label>
            <label>Idioma<select id="cc-language" class="form-control"><option value="es">Español</option><option value="en">English</option></select></label>
            <label class="cc-profile-wide">Zona horaria<input id="cc-time-zone" class="form-control" placeholder="America/Tegucigalpa"></label>
          </div>
          <div class="cc-profile-actions"><button id="cc-save-profile" class="btn btn-primary">Guardar cambios</button></div>
        </section>

        <section class="cc-profile-card">
          <div class="cc-profile-card-title"><strong>Seguridad y acceso</strong><span>Estado de la cuenta y sesiones</span></div>
          <div id="cc-security-grid" class="cc-profile-stats"></div>
          <div class="cc-profile-actions"><button id="cc-change-password" class="btn btn-default">Cambiar contraseña</button></div>
        </section>

        <section class="cc-profile-card cc-profile-wide-card">
          <div class="cc-profile-card-title"><strong>Proyectos asignados</strong><span>Obras a las que tiene acceso</span></div>
          <div id="cc-projects" class="cc-profile-projects"><span class="text-muted">Cargando...</span></div>
        </section>

        <section class="cc-profile-card cc-profile-wide-card">
          <div class="cc-profile-card-title"><strong>Actividad reciente</strong><span>Acciones auditadas dentro del sistema</span></div>
          <div id="cc-activity" class="cc-profile-activity"><span class="text-muted">Cargando...</span></div>
        </section>
      </div>
    </div>
  `);

  const style = document.createElement("style");
  style.textContent = `
    .cc-profile-page{max-width:1180px;margin:0 auto;padding:8px 0 24px}.cc-profile-hero{display:flex;align-items:center;gap:18px;padding:22px;border:1px solid var(--border-color);border-radius:18px;background:linear-gradient(135deg,var(--card-bg),var(--subtle-fg));margin-bottom:16px}.cc-profile-avatar{display:grid;width:84px;height:84px;min-width:84px;place-items:center;overflow:hidden;border-radius:24px;background:#175c4c;color:#fff;font-size:24px;font-weight:900}.cc-profile-avatar img{width:100%;height:100%;object-fit:cover}.cc-profile-heading h2{margin:7px 0 2px}.cc-profile-role-large{display:inline-flex;padding:4px 10px;border-radius:999px;background:rgba(23,92,76,.12);color:#175c4c;font-size:12px;font-weight:900;letter-spacing:.06em}.cc-profile-layout{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:14px}.cc-profile-card{min-width:0;padding:18px;border:1px solid var(--border-color);border-radius:16px;background:var(--card-bg)}.cc-profile-wide-card{grid-column:1/-1}.cc-profile-card-title{display:flex;flex-direction:column;margin-bottom:14px}.cc-profile-card-title strong{font-size:16px}.cc-profile-card-title span{color:var(--text-muted);font-size:12px}.cc-profile-form-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px}.cc-profile-form-grid label{display:flex;min-width:0;flex-direction:column;gap:5px;font-size:12px;font-weight:700}.cc-profile-wide{grid-column:1/-1}.cc-profile-actions{display:flex;gap:8px;justify-content:flex-end;margin-top:14px}.cc-profile-stats{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:10px}.cc-profile-stat{padding:12px;border:1px solid var(--border-color);border-radius:12px;background:var(--subtle-fg)}.cc-profile-stat span{display:block;color:var(--text-muted);font-size:11px}.cc-profile-stat strong{display:block;margin-top:3px;overflow-wrap:anywhere}.cc-profile-projects{display:grid;grid-template-columns:repeat(auto-fit,minmax(210px,1fr));gap:10px}.cc-project-card{padding:13px;border:1px solid var(--border-color);border-radius:12px;background:var(--subtle-fg)}.cc-project-card strong,.cc-project-card span{display:block}.cc-project-card span{margin-top:4px;color:var(--text-muted);font-size:12px}.cc-profile-activity{overflow-x:auto}.cc-profile-activity table{width:100%;border-collapse:collapse}.cc-profile-activity th,.cc-profile-activity td{padding:9px;border-bottom:1px solid var(--border-color);text-align:left;vertical-align:top}.cc-profile-activity th{color:var(--text-muted);font-size:11px;text-transform:uppercase}@media(max-width:767px){.cc-profile-hero{align-items:flex-start;padding:16px}.cc-profile-avatar{width:64px;height:64px;min-width:64px;border-radius:18px}.cc-profile-layout,.cc-profile-form-grid{grid-template-columns:1fr}.cc-profile-wide{grid-column:auto}.cc-profile-card{padding:14px}.cc-profile-actions .btn{width:100%}.cc-profile-stats{grid-template-columns:1fr}.cc-profile-activity th:nth-child(3),.cc-profile-activity td:nth-child(3){display:none}}
  `;
  wrapper.appendChild(style);

  let profile = null;

  function escape(value) {
    return frappe.utils.escape_html(String(value ?? ""));
  }

  function initials(name) {
    return String(name || "CC").trim().split(/\s+/).slice(0, 2).map(part => part[0] || "").join("").toUpperCase() || "CC";
  }

  function formatMoment(value) {
    if (!value) return "Sin registro";
    try { return frappe.datetime.str_to_user(value); } catch (_error) { return String(value); }
  }

  function render(data) {
    profile = data;
    body.find("#cc-profile-role").text(data.role || "USER");
    body.find("#cc-profile-display-name").text(data.display_name || data.email || "Usuario");
    body.find("#cc-profile-email").text(data.email || "");
    body.find("#cc-first-name").val(data.first_name || "");
    body.find("#cc-last-name").val(data.last_name || "");
    body.find("#cc-mobile-no").val(data.mobile_no || "");
    body.find("#cc-language").val(data.language || "es");
    body.find("#cc-time-zone").val(data.time_zone || "");

    const avatar = body.find("#cc-profile-avatar");
    avatar.empty();
    if (data.user_image) avatar.html(`<img alt="Foto de perfil" src="${escape(data.user_image)}">`);
    else avatar.text(initials(data.display_name));

    const security = [
      ["Estado", data.enabled ? "Activo" : "Suspendido"],
      ["Último acceso", formatMoment(data.last_login)],
      ["Última actividad", formatMoment(data.last_active)],
      ["Doble factor", data.security?.two_factor_enabled ? "Activado" : "No activado"],
      ["Rol principal", data.role || "USER"],
      ["Permisos", (data.roles || []).join(", ") || "Sin roles adicionales"],
    ];
    body.find("#cc-security-grid").html(security.map(row => `<div class="cc-profile-stat"><span>${escape(row[0])}</span><strong>${escape(row[1])}</strong></div>`).join(""));

    const projects = data.projects || [];
    body.find("#cc-projects").html(projects.length
      ? projects.map(project => `<button class="cc-project-card" data-project="${escape(project.name)}"><strong>${escape(project.project_name || project.name)}</strong><span>${escape(project.status || "Sin estado")} · ${escape(project.percent_complete || 0)}% completado</span></button>`).join("")
      : `<div class="text-muted">No tiene restricciones por proyecto o aún no se le ha asignado una obra específica.</div>`);

    const activity = data.recent_activity || [];
    body.find("#cc-activity").html(activity.length
      ? `<table><thead><tr><th>Fecha</th><th>Acción</th><th>Registro</th><th>Motivo</th></tr></thead><tbody>${activity.map(row => `<tr><td>${escape(row.posting_date || "")}</td><td>${escape(row.action || "Actividad")}</td><td>${escape([row.record_type, row.record_id].filter(Boolean).join(" · "))}</td><td>${escape(row.reason || "")}</td></tr>`).join("")}</tbody></table>`
      : `<div class="text-muted">Todavía no hay actividad auditada asociada a este usuario.</div>`);
  }

  function loadProfile() {
    body.find("#cc-save-profile").prop("disabled", true);
    return frappe.xcall("erpnext.construcontrol.profile.get_my_profile")
      .then(render)
      .finally(() => body.find("#cc-save-profile").prop("disabled", false));
  }

  function saveProfile() {
    const values = {
      first_name: body.find("#cc-first-name").val(),
      last_name: body.find("#cc-last-name").val(),
      mobile_no: body.find("#cc-mobile-no").val(),
      language: body.find("#cc-language").val(),
      time_zone: body.find("#cc-time-zone").val(),
    };
    body.find("#cc-save-profile").prop("disabled", true);
    return frappe.xcall("erpnext.construcontrol.profile.update_my_profile", values)
      .then(data => {
        render(data);
        frappe.show_alert({message: "Perfil actualizado", indicator: "green"});
      })
      .finally(() => body.find("#cc-save-profile").prop("disabled", false));
  }

  body.on("click", "#cc-save-profile", saveProfile);
  body.on("click", "#cc-change-password", () => frappe.set_route("update-password"));
  body.on("click", ".cc-project-card", function () {
    const project = $(this).data("project");
    if (project) frappe.set_route("Form", "Project", project);
  });

  loadProfile();
};
