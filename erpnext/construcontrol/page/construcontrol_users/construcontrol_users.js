frappe.pages["construcontrol-users"].on_page_load = function (wrapper) {
  "use strict";

  const page = frappe.ui.make_app_page({parent: wrapper, title: "Usuarios", single_column: true});
  const body = $(wrapper).find(".layout-main-section");
  let state = {users: [], projects: [], roles: [], can_assign_admin: false};
  let requestId = 0;

  page.set_primary_action("Nuevo usuario", () => openUserDialog(), "add");
  page.add_inner_button("Mi perfil", () => frappe.set_route("construcontrol-profile"));

  body.html(`
    <main class="cc-users-page">
      <section class="cc-users-summary">
        <div><small>ADMINISTRACIÓN</small><h2>Usuarios y permisos</h2><p>Acceso real a ConstruControl, roles y proyectos asignados.</p></div>
        <div id="cc-users-counts" class="cc-users-counts"></div>
      </section>
      <section class="cc-users-toolbar">
        <label class="cc-users-search"><span>Buscar</span><input id="cc-users-search" class="form-control" placeholder="Nombre o correo"></label>
        <label><span>Estado</span><select id="cc-users-enabled" class="form-control"><option value="">Todos</option><option value="1">Activos</option><option value="0">Suspendidos</option></select></label>
        <button id="cc-users-refresh" class="btn btn-default" type="button">Actualizar</button>
      </section>
      <section class="cc-users-card">
        <div id="cc-users-loading" class="cc-users-loading" hidden>Actualizando usuarios...</div>
        <div id="cc-users-list" class="cc-users-list"></div>
      </section>
      <p class="cc-users-footnote">Los registros históricos de la migración se conservan para auditoría, pero la administración oficial utiliza las cuentas reales de ERPNext.</p>
    </main>
  `);

  const escape = value => frappe.utils.escape_html(String(value ?? ""));

  function initials(value) {
    return String(value || "U").trim().split(/\s+/).slice(0, 2).map(part => part[0] || "").join("").toUpperCase() || "U";
  }

  function formatMoment(value) {
    if (!value) return "Sin acceso registrado";
    try { return frappe.datetime.str_to_user(value); } catch (_error) { return String(value); }
  }

  function render() {
    const users = state.users || [];
    const active = users.filter(row => row.enabled).length;
    const suspended = users.length - active;
    body.find("#cc-users-counts").html(`<span><strong>${users.length}</strong> usuarios</span><span><strong>${active}</strong> activos</span><span><strong>${suspended}</strong> suspendidos</span>`);

    if (!users.length) {
      body.find("#cc-users-list").html(`<div class="cc-empty-state">No se encontraron usuarios con los filtros seleccionados.</div>`);
      return;
    }

    body.find("#cc-users-list").html(users.map(row => {
      const project = (row.projects || []).join(", ") || "Todos los proyectos autorizados por rol";
      const historical = row.historical_source_id ? `<span class="cc-user-history">Origen histórico conciliado</span>` : "";
      const protectedLabel = row.protected ? `<span class="cc-user-protected">Protegido</span>` : "";
      const action = row.protected
        ? `<button type="button" class="btn btn-xs btn-default" data-profile="${escape(row.user_id)}">Perfil</button>`
        : `<button type="button" class="btn btn-xs btn-default" data-edit-user="${escape(row.user_id)}">Editar</button><button type="button" class="btn btn-xs ${row.enabled ? "btn-default" : "btn-primary"}" data-toggle-user="${escape(row.user_id)}" data-enabled="${row.enabled ? 0 : 1}">${row.enabled ? "Suspender" : "Reactivar"}</button>`;
      return `<article class="cc-user-row">
        <div class="cc-user-avatar">${row.user_image ? `<img src="${escape(row.user_image)}" alt="">` : escape(initials(row.display_name))}</div>
        <div class="cc-user-main"><div class="cc-user-title"><strong>${escape(row.display_name)}</strong><span class="cc-user-role">${escape(row.role)}</span>${protectedLabel}${historical}</div><span>${escape(row.email)}</span><small>Proyecto: ${escape(project)}</small></div>
        <div class="cc-user-access"><span class="${row.enabled ? "is-active" : "is-disabled"}">${row.enabled ? "Activo" : "Suspendido"}</span><small>Último acceso: ${escape(formatMoment(row.last_login || row.last_active))}</small></div>
        <div class="cc-user-actions">${action}</div>
      </article>`;
    }).join(""));
  }

  function setLoading(loading) {
    body.find("#cc-users-loading").prop("hidden", !loading);
    body.find("#cc-users-refresh").prop("disabled", loading);
  }

  function loadUsers() {
    const current = ++requestId;
    setLoading(true);
    return frappe.xcall("erpnext.construcontrol.users.get_user_center", {
      search: body.find("#cc-users-search").val() || "",
      enabled: body.find("#cc-users-enabled").val(),
    }).then(result => {
      if (current !== requestId) return;
      state = result || state;
      render();
    }).finally(() => {
      if (current === requestId) setLoading(false);
    });
  }

  function roleOptions() {
    return (state.roles || []).filter(role => role !== "ADMIN" || state.can_assign_admin).join("\n");
  }

  function projectOptions() {
    return ["", ...(state.projects || []).map(row => row.name)].join("\n");
  }

  function openUserDialog(userId = "") {
    const user = (state.users || []).find(row => row.user_id === userId) || null;
    const dialog = new frappe.ui.Dialog({
      title: user ? "Editar usuario" : "Nuevo usuario",
      fields: [
        {fieldname: "email", fieldtype: "Data", label: "Correo", options: "Email", reqd: 1, read_only: Boolean(user), default: user?.email || ""},
        {fieldname: "first_name", fieldtype: "Data", label: "Nombre", reqd: 1, default: user?.first_name || ""},
        {fieldname: "last_name", fieldtype: "Data", label: "Apellido", default: user?.last_name || ""},
        {fieldname: "role", fieldtype: "Select", label: "Rol", options: roleOptions(), reqd: 1, default: user?.role || "VIEWER"},
        {fieldname: "project", fieldtype: "Select", label: "Proyecto principal", options: projectOptions(), default: user?.projects?.[0] || ""},
        {fieldname: "enabled", fieldtype: "Check", label: "Cuenta activa", default: user ? user.enabled : 1},
      ],
      primary_action_label: user ? "Guardar" : "Crear usuario",
      primary_action(values) {
        dialog.get_primary_btn().prop("disabled", true);
        frappe.xcall("erpnext.construcontrol.users.save_user", values)
          .then(() => {
            dialog.hide();
            frappe.show_alert({message: user ? "Usuario actualizado" : "Usuario creado", indicator: "green"});
            return loadUsers();
          })
          .finally(() => dialog.get_primary_btn().prop("disabled", false));
      },
    });
    dialog.show();
  }

  let searchTimer = null;
  body.on("input", "#cc-users-search", () => {
    window.clearTimeout(searchTimer);
    searchTimer = window.setTimeout(loadUsers, 300);
  });
  body.on("change", "#cc-users-enabled", loadUsers);
  body.on("click", "#cc-users-refresh", loadUsers);
  body.on("click", "[data-edit-user]", function () { openUserDialog(String($(this).data("edit-user"))); });
  body.on("click", "[data-profile]", () => frappe.set_route("construcontrol-profile"));
  body.on("click", "[data-toggle-user]", function () {
    const user = String($(this).data("toggle-user"));
    const enabled = Number($(this).data("enabled"));
    frappe.confirm(enabled ? "¿Reactivar esta cuenta?" : "¿Suspender esta cuenta?", () => {
      frappe.xcall("erpnext.construcontrol.users.set_user_enabled", {user, enabled}).then(loadUsers);
    });
  });

  loadUsers();
};
