(() => {
  "use strict";

  const CONSTRUCONTROL_DOCTYPES = new Set([
    "CC Approval Request", "CC Audit Log", "CC Automation Execution", "CC Automation Rule",
    "CC Backup Snapshot", "CC Business Partner Profile", "CC Catalog Profile", "CC Change Order",
    "CC Construction Phase", "CC Crew Attendance", "CC Crew Member", "CC Daily Site Log",
    "CC Digital Signature", "CC Document Template", "CC Equipment Control", "CC Evidence",
    "CC Expense Control", "CC Funding Source", "CC Generated Report", "CC Immutable Audit Event",
    "CC Inventory Movement", "CC Labor Contract", "CC Material Ledger", "CC Notification Contact",
    "CC Notification Log", "CC Notification Rule", "CC Payable Control", "CC Procurement Request",
    "CC Progress Update", "CC Project Profile", "CC Safety Incident", "CC Tool Loan",
    "CC User Access", "CC User Permission Override", "CC Weekly Closing",
    "ConstruControl Settings", "ConstruControl Migration Run", "ConstruControl Legacy Record"
  ]);

  const MODULES = [
    { code: "CC00", label: "Inicio", icon: "⌂", target: ["construcontrol-dashboard"], group: "principal" },
    { code: "FI01", label: "Ingresos", icon: "+", target: ["List", "CC Funding Source"], group: "finanzas" },
    { code: "FI02", label: "Gastos", icon: "−", target: ["List", "CC Expense Control"], group: "finanzas" },
    { code: "FI03", label: "Cuentas por pagar", icon: "▤", target: ["List", "CC Payable Control"], group: "finanzas" },
    { code: "CO01", label: "Contratos", icon: "▧", target: ["List", "CC Labor Contract"], group: "obra" },
    { code: "PR01", label: "Fases", icon: "◫", target: ["List", "CC Construction Phase"], group: "obra" },
    { code: "QC01", label: "Avance", icon: "✓", target: ["List", "CC Progress Update"], group: "obra" },
    { code: "MM01", label: "Materiales", icon: "▦", target: ["List", "CC Material Ledger"], group: "materiales" },
    { code: "MIGO", label: "Inventario", icon: "⇄", target: ["List", "CC Inventory Movement"], group: "materiales" },
    { code: "MM02", label: "Compras", icon: "⌑", target: ["List", "CC Procurement Request"], group: "materiales" },
    { code: "CL01", label: "Cierres", icon: "▣", target: ["List", "CC Weekly Closing"], group: "control" },
    { code: "BI01", label: "Reportes", icon: "▥", target: ["construcontrol-reporting-center"], group: "control" },
    { code: "AU01", label: "Auditoría", icon: "◎", target: ["List", "CC Audit Log"], group: "control" },
    { code: "US01", label: "Usuarios", icon: "♙", target: ["List", "CC User Access"], group: "administracion" },
    { code: "INT", label: "Integraciones", icon: "⌘", target: ["Workspace", "Integraciones"], group: "administracion" },
    { code: "MIG", label: "Migración", icon: "⇧", target: ["construcontrol-migration-console"], group: "administracion", admin: true }
  ];

  const MOBILE_PRIMARY_CODES = new Set(["CC00", "FI01", "FI02", "QC01"]);
  const ADMIN_LABELS = [
    "Migración segura", "Ejecuciones de migración", "Registros originales preservados",
    "Configuración ConstruControl", "ConstruControl Migration Run", "ConstruControl Legacy Record"
  ];

  function currentRoute() {
    try {
      return window.frappe?.get_route?.() || [];
    } catch (_error) {
      return [];
    }
  }

  function isSystemManager() {
    const roles = window.frappe?.user_roles || window.frappe?.boot?.user?.roles || [];
    return Array.isArray(roles) && roles.includes("System Manager");
  }

  function availableModules() {
    return MODULES.filter(module => !module.admin || isSystemManager());
  }

  function isConstruControlRoute(route) {
    const first = String(route[0] || "");
    const second = String(route[1] || "");
    return first === "construcontrol"
      || first.startsWith("construcontrol-")
      || CONSTRUCONTROL_DOCTYPES.has(first)
      || CONSTRUCONTROL_DOCTYPES.has(second);
  }

  function sameRoute(route, target) {
    if (target[0] === "Workspace") {
      return String(route[0] || "") === "Workspaces" && String(route[1] || "") === target[1];
    }
    if (target.length === 1) return String(route[0] || "") === target[0];
    return String(route[0] || "") === target[0] && String(route[1] || "") === target[1];
  }

  function routeTitle(route) {
    const matched = availableModules().find(module => sameRoute(route, module.target));
    if (matched) return matched.label;
    if (String(route[0] || "") === "Form" && route[1]) return String(route[1]);
    if (String(route[0] || "") === "List" && route[1]) return String(route[1]);
    return "ConstruControl";
  }

  function navigate(target) {
    closeMoreMenu();
    if (target[0] === "Workspace") {
      frappe.set_route("Workspaces", target[1]);
      return;
    }
    frappe.set_route(...target);
  }

  function safeVisibleName(...candidates) {
    for (const candidate of candidates) {
      const value = String(candidate || "").trim();
      if (value && !value.includes("@") && value.toLowerCase() !== "guest") return value;
    }
    return "Administrador";
  }

  function installMetadata() {
    const metadata = [
      ["link", "manifest", "/assets/erpnext/construcontrol/manifest.webmanifest"],
      ["link", "apple-touch-icon", "/assets/erpnext/construcontrol/apple-touch-icon-180.png"],
      ["link", "icon", "/assets/erpnext/construcontrol/favicon-32.png"]
    ];
    for (const [tag, rel, href] of metadata) {
      let node = document.querySelector(`${tag}[rel="${rel}"][data-construcontrol]`);
      if (!node) {
        node = document.createElement(tag);
        node.rel = rel;
        node.dataset.construcontrol = "1";
        document.head.appendChild(node);
      }
      node.href = href;
    }

    let theme = document.querySelector('meta[name="theme-color"][data-construcontrol]');
    if (!theme) {
      theme = document.createElement("meta");
      theme.name = "theme-color";
      theme.dataset.construcontrol = "1";
      document.head.appendChild(theme);
    }
    theme.content = "#175c4c";

    let capable = document.querySelector('meta[name="apple-mobile-web-app-capable"][data-construcontrol]');
    if (!capable) {
      capable = document.createElement("meta");
      capable.name = "apple-mobile-web-app-capable";
      capable.content = "yes";
      capable.dataset.construcontrol = "1";
      document.head.appendChild(capable);
    }

    let title = document.querySelector('meta[name="apple-mobile-web-app-title"][data-construcontrol]');
    if (!title) {
      title = document.createElement("meta");
      title.name = "apple-mobile-web-app-title";
      title.content = "ConstruControl";
      title.dataset.construcontrol = "1";
      document.head.appendChild(title);
    }
  }

  function createRouteButton(module, className) {
    const button = document.createElement("button");
    button.type = "button";
    button.className = className;
    button.dataset.route = JSON.stringify(module.target);
    button.dataset.code = module.code;
    button.setAttribute("aria-label", module.label);

    const icon = document.createElement("span");
    icon.className = "cc-shell-icon";
    icon.setAttribute("aria-hidden", "true");
    icon.textContent = module.icon;

    const text = document.createElement("span");
    text.className = "cc-shell-label";
    text.textContent = module.label;

    button.append(icon, text);
    button.addEventListener("click", () => navigate(module.target));
    return button;
  }

  function ensureDesktopSidebar() {
    let sidebar = document.querySelector(".cc-desktop-sidebar");
    if (sidebar) return sidebar;

    sidebar = document.createElement("aside");
    sidebar.className = "cc-desktop-sidebar";
    sidebar.setAttribute("aria-label", "Módulos de ConstruControl");

    const brand = document.createElement("button");
    brand.type = "button";
    brand.className = "cc-brand";
    brand.setAttribute("aria-label", "Ir al inicio de ConstruControl");
    brand.addEventListener("click", () => navigate(["construcontrol-dashboard"]));

    const mark = document.createElement("span");
    mark.className = "cc-brand-mark";
    mark.textContent = "CC";
    const words = document.createElement("span");
    words.className = "cc-brand-words";
    words.innerHTML = "<strong>ConstruControl</strong><small>Gestión residencial</small>";
    brand.append(mark, words);
    sidebar.appendChild(brand);

    const groups = [
      ["principal", "Principal"], ["finanzas", "Finanzas"], ["obra", "Obra"],
      ["materiales", "Materiales"], ["control", "Control"], ["administracion", "Administración"]
    ];
    for (const [group, label] of groups) {
      const modules = availableModules().filter(module => module.group === group);
      if (!modules.length) continue;
      const section = document.createElement("section");
      section.className = "cc-sidebar-group";
      const heading = document.createElement("div");
      heading.className = "cc-sidebar-heading";
      heading.textContent = label;
      section.appendChild(heading);
      for (const module of modules) section.appendChild(createRouteButton(module, "cc-sidebar-link"));
      sidebar.appendChild(section);
    }

    document.body.appendChild(sidebar);
    return sidebar;
  }

  function ensureTopbar() {
    let topbar = document.querySelector(".cc-app-topbar");
    if (topbar) return topbar;

    topbar = document.createElement("header");
    topbar.className = "cc-app-topbar";

    const back = document.createElement("button");
    back.type = "button";
    back.className = "cc-topbar-button cc-topbar-back";
    back.setAttribute("aria-label", "Regresar");
    back.textContent = "‹";
    back.addEventListener("click", () => {
      if (window.history.length > 1) window.history.back();
      else navigate(["construcontrol-dashboard"]);
    });

    const titleWrap = document.createElement("div");
    titleWrap.className = "cc-topbar-title-wrap";
    const eyebrow = document.createElement("small");
    eyebrow.textContent = "CONSTRUCONTROL";
    const title = document.createElement("strong");
    title.className = "cc-topbar-title";
    title.textContent = "Inicio";
    titleWrap.append(eyebrow, title);

    const home = document.createElement("button");
    home.type = "button";
    home.className = "cc-topbar-button cc-topbar-home";
    home.setAttribute("aria-label", "Inicio");
    home.textContent = "⌂";
    home.addEventListener("click", () => navigate(["construcontrol-dashboard"]));

    const profile = document.createElement("button");
    profile.type = "button";
    profile.className = "cc-profile-button";
    profile.setAttribute("aria-label", "Abrir perfil");
    profile.addEventListener("click", () => frappe.set_route("Form", "User", frappe.session.user));
    const profileRole = document.createElement("span");
    profileRole.className = "cc-profile-role";
    profileRole.textContent = isSystemManager() ? "ADMIN" : "USUARIO";
    const profileName = document.createElement("span");
    profileName.className = "cc-profile-name";
    profileName.textContent = safeVisibleName(window.frappe?.boot?.user?.full_name);
    profile.append(profileRole, profileName);

    topbar.append(back, titleWrap, home, profile);
    document.body.appendChild(topbar);
    return topbar;
  }

  function ensureMobileNavigation() {
    let nav = document.querySelector(".cc-mobile-nav");
    if (nav) return nav;

    nav = document.createElement("nav");
    nav.className = "cc-mobile-nav";
    nav.setAttribute("aria-label", "Navegación móvil de ConstruControl");

    for (const module of availableModules().filter(item => MOBILE_PRIMARY_CODES.has(item.code))) {
      nav.appendChild(createRouteButton(module, "cc-mobile-link"));
    }

    const more = document.createElement("button");
    more.type = "button";
    more.className = "cc-mobile-link cc-more-toggle";
    more.dataset.action = "more";
    more.setAttribute("aria-label", "Abrir todos los módulos");
    more.setAttribute("aria-expanded", "false");
    const icon = document.createElement("span");
    icon.className = "cc-shell-icon";
    icon.textContent = "•••";
    const label = document.createElement("span");
    label.className = "cc-shell-label";
    label.textContent = "Más";
    more.append(icon, label);
    more.addEventListener("click", toggleMoreMenu);
    nav.appendChild(more);

    document.body.appendChild(nav);
    return nav;
  }

  function ensureMoreMenu() {
    let backdrop = document.querySelector(".cc-more-backdrop");
    let sheet = document.querySelector(".cc-more-sheet");
    if (backdrop && sheet) return;

    backdrop = document.createElement("button");
    backdrop.type = "button";
    backdrop.className = "cc-more-backdrop";
    backdrop.hidden = true;
    backdrop.setAttribute("aria-label", "Cerrar menú");
    backdrop.addEventListener("click", closeMoreMenu);

    sheet = document.createElement("section");
    sheet.className = "cc-more-sheet";
    sheet.hidden = true;
    sheet.setAttribute("role", "dialog");
    sheet.setAttribute("aria-modal", "true");
    sheet.setAttribute("aria-label", "Todos los módulos");

    const header = document.createElement("div");
    header.className = "cc-more-header";
    const title = document.createElement("strong");
    title.textContent = "Todos los módulos";
    const close = document.createElement("button");
    close.type = "button";
    close.className = "cc-more-close";
    close.setAttribute("aria-label", "Cerrar");
    close.textContent = "×";
    close.addEventListener("click", closeMoreMenu);
    header.append(title, close);

    const grid = document.createElement("div");
    grid.className = "cc-more-grid";
    for (const module of availableModules()) grid.appendChild(createRouteButton(module, "cc-more-module"));
    sheet.append(header, grid);
    document.body.append(backdrop, sheet);
  }

  function openMoreMenu() {
    ensureMoreMenu();
    const backdrop = document.querySelector(".cc-more-backdrop");
    const sheet = document.querySelector(".cc-more-sheet");
    const toggle = document.querySelector(".cc-more-toggle");
    if (!backdrop || !sheet) return;
    backdrop.hidden = false;
    sheet.hidden = false;
    toggle?.setAttribute("aria-expanded", "true");
    document.body.classList.add("cc-more-open");
    sheet.querySelector("button")?.focus();
  }

  function closeMoreMenu() {
    const backdrop = document.querySelector(".cc-more-backdrop");
    const sheet = document.querySelector(".cc-more-sheet");
    const toggle = document.querySelector(".cc-more-toggle");
    if (backdrop) backdrop.hidden = true;
    if (sheet) sheet.hidden = true;
    toggle?.setAttribute("aria-expanded", "false");
    document.body.classList.remove("cc-more-open");
  }

  function toggleMoreMenu() {
    const sheet = document.querySelector(".cc-more-sheet");
    if (!sheet || sheet.hidden) openMoreMenu();
    else closeMoreMenu();
  }

  function updateConnectionNotice(active) {
    let banner = document.querySelector(".cc-offline-banner");
    if (active && !navigator.onLine && !banner) {
      banner = document.createElement("div");
      banner.className = "cc-offline-banner";
      banner.setAttribute("role", "status");
      banner.textContent = "Sin conexión. No cierre la aplicación ni guarde cambios hasta recuperar Internet.";
      document.body.prepend(banner);
    } else if ((!active || navigator.onLine) && banner) {
      banner.remove();
    }
  }

  function ensureCloseAction(route) {
    const isForm = String(route[0] || "") === "Form";
    const actions = document.querySelector(".page-actions");
    if (!actions) return;
    let close = actions.querySelector(".cc-close-view");
    if (!close) {
      close = document.createElement("button");
      close.type = "button";
      close.className = "btn btn-default btn-sm cc-close-view";
      close.addEventListener("click", () => {
        if (isForm && route[1]) frappe.set_route("List", route[1]);
        else navigate(["construcontrol-dashboard"]);
      });
      actions.prepend(close);
    }
    close.textContent = isForm ? "Cerrar" : "Inicio";
  }

  function enforceAdminVisibility() {
    if (isSystemManager()) return;
    document.querySelectorAll("a, button, .link-item, .shortcut-widget-box").forEach(element => {
      const text = String(element.textContent || "").trim();
      if (!ADMIN_LABELS.some(label => text.includes(label))) return;
      const row = element.closest(".link-item, .shortcut-widget-box, .widget, .list-row") || element;
      row.remove();
    });
  }

  async function updateIdentity() {
    const profile = document.querySelector(".cc-profile-button");
    if (!profile) return;
    try {
      const identity = await frappe.xcall("erpnext.construcontrol.api.get_current_identity");
      const role = String(identity.role || "USER").trim().toUpperCase();
      const name = safeVisibleName(identity.display_name, window.frappe?.boot?.user?.full_name);
      profile.querySelector(".cc-profile-role").textContent = role;
      profile.querySelector(".cc-profile-name").textContent = name;
      profile.setAttribute("aria-label", `Abrir perfil de ${name}. Rol ${role}`);
    } catch (_error) {
      // The navigation remains usable when identity data is temporarily unavailable.
    }
  }

  function updateActiveState(route) {
    document.querySelectorAll("[data-route]").forEach(button => {
      let target = [];
      try { target = JSON.parse(button.dataset.route || "[]"); } catch (_error) { target = []; }
      const active = sameRoute(route, target);
      button.classList.toggle("is-active", active);
      button.setAttribute("aria-current", active ? "page" : "false");
    });

    const topbarTitle = document.querySelector(".cc-topbar-title");
    if (topbarTitle) topbarTitle.textContent = routeTitle(route);
  }

  function removeShell() {
    document.querySelector(".cc-desktop-sidebar")?.remove();
    document.querySelector(".cc-app-topbar")?.remove();
    document.querySelector(".cc-mobile-nav")?.remove();
    document.querySelector(".cc-more-backdrop")?.remove();
    document.querySelector(".cc-more-sheet")?.remove();
    document.body.classList.remove("cc-construcontrol-route", "cc-more-open");
  }

  function applyShell() {
    const route = currentRoute();
    const active = isConstruControlRoute(route);
    updateConnectionNotice(active);
    if (!active) {
      removeShell();
      return;
    }

    document.body.classList.add("cc-construcontrol-route");
    ensureDesktopSidebar();
    ensureTopbar();
    ensureMobileNavigation();
    ensureMoreMenu();
    updateActiveState(route);
    closeMoreMenu();

    window.setTimeout(() => {
      ensureCloseAction(route);
      enforceAdminVisibility();
      updateIdentity();
    }, 50);
    window.setTimeout(() => {
      ensureCloseAction(route);
      enforceAdminVisibility();
    }, 500);
  }

  installMetadata();
  window.addEventListener("online", applyShell);
  window.addEventListener("offline", applyShell);
  window.addEventListener("load", applyShell);
  window.addEventListener("keydown", event => {
    if (event.key === "Escape") closeMoreMenu();
  });
  if (window.frappe?.router?.on) frappe.router.on("change", applyShell);

  if (document.body && window.MutationObserver) {
    let scheduled = false;
    const observer = new MutationObserver(() => {
      if (scheduled || !document.body.classList.contains("cc-construcontrol-route")) return;
      scheduled = true;
      window.setTimeout(() => {
        scheduled = false;
        const route = currentRoute();
        ensureCloseAction(route);
        enforceAdminVisibility();
      }, 40);
    });
    observer.observe(document.body, { childList: true, subtree: true });
  }
})();
