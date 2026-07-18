(() => {
  "use strict";

  const doctypes = new Set([
    "CC Funding Source", "CC Expense Control", "CC Labor Contract",
    "CC Construction Phase", "CC Material Ledger", "CC Inventory Movement",
    "CC Procurement Request", "CC Progress Update", "CC Weekly Closing",
    "CC Audit Log", "CC User Access"
  ]);

  const primaryItems = [
    { icon: "⌂", label: "Inicio", target: ["construcontrol-dashboard"] },
    { icon: "＋", label: "Ingresos", target: ["List", "CC Funding Source"] },
    { icon: "−", label: "Gastos", target: ["List", "CC Expense Control"] },
    { icon: "▦", label: "Materiales", target: ["List", "CC Material Ledger"] }
  ];

  const moreItems = [
    { code: "CO01", label: "Contratos", target: ["List", "CC Labor Contract"] },
    { code: "PR01", label: "Fases de obra", target: ["List", "CC Construction Phase"] },
    { code: "MIGO", label: "Inventario", target: ["List", "CC Inventory Movement"] },
    { code: "MM02", label: "Compras", target: ["List", "CC Procurement Request"] },
    { code: "QC01", label: "Avance", target: ["List", "CC Progress Update"] },
    { code: "CL01", label: "Cierres", target: ["List", "CC Weekly Closing"] },
    { code: "BI01", label: "Reportes", target: ["construcontrol-reporting-center"] },
    { code: "AU01", label: "Auditoría", target: ["List", "CC Audit Log"] },
    { code: "US01", label: "Usuarios", target: ["List", "CC User Access"] }
  ];

  const adminMoreItems = [
    { code: "MIG", label: "Migración segura", target: ["construcontrol-migration-console"] }
  ];

  const adminLabels = [
    "Migración segura",
    "Ejecuciones de migración",
    "Registros originales preservados",
    "Configuración ConstruControl"
  ];

  function installMetadata() {
    if (!document.querySelector('link[rel="manifest"][data-construcontrol]')) {
      const manifest = document.createElement("link");
      manifest.rel = "manifest";
      manifest.href = "/assets/erpnext/construcontrol/manifest.webmanifest";
      manifest.dataset.construcontrol = "1";
      document.head.appendChild(manifest);
    }
    if (!document.querySelector('meta[name="theme-color"][data-construcontrol]')) {
      const theme = document.createElement("meta");
      theme.name = "theme-color";
      theme.content = "#1f6f5f";
      theme.dataset.construcontrol = "1";
      document.head.appendChild(theme);
    }
    if (!document.querySelector('link[rel="apple-touch-icon"][data-construcontrol]')) {
      const icon = document.createElement("link");
      icon.rel = "apple-touch-icon";
      icon.href = "/assets/erpnext/construcontrol/icon.svg";
      icon.dataset.construcontrol = "1";
      document.head.appendChild(icon);
    }
  }

  function currentRoute() {
    try { return frappe.get_route() || []; } catch (_error) { return []; }
  }

  function isConstruControl(route) {
    const first = String(route[0] || "");
    const second = String(route[1] || "");
    return first === "construcontrol" || first.startsWith("construcontrol-") || doctypes.has(first) || doctypes.has(second);
  }

  function isSystemManager() {
    const roles = window.frappe?.user_roles || window.frappe?.boot?.user?.roles || [];
    return roles.includes("System Manager");
  }

  function availableMoreItems() {
    return isSystemManager() ? [...moreItems, ...adminMoreItems] : moreItems;
  }

  function sameRoute(current, target) {
    return target.length === 1
      ? String(current[0] || "") === target[0]
      : String(current[0] || "") === target[0] && String(current[1] || "") === target[1];
  }

  function goTo(target) {
    closeMoreMenu();
    frappe.set_route(...target);
  }

  function updateConnectionNotice(active) {
    let banner = document.querySelector(".cc-offline-banner");
    if (active && !navigator.onLine && !banner) {
      banner = document.createElement("div");
      banner.className = "cc-offline-banner";
      banner.setAttribute("role", "status");
      banner.textContent = "Sin conexión. Espere a recuperar Internet antes de guardar.";
      document.body.prepend(banner);
    } else if ((!active || navigator.onLine) && banner) {
      banner.remove();
    }
  }

  function createPrimaryButton(item) {
    const button = document.createElement("button");
    button.type = "button";
    button.dataset.route = JSON.stringify(item.target);
    button.setAttribute("aria-label", item.label);

    const icon = document.createElement("span");
    icon.className = "cc-nav-icon";
    icon.setAttribute("aria-hidden", "true");
    icon.textContent = item.icon;

    const label = document.createElement("span");
    label.textContent = item.label;

    button.append(icon, label);
    button.addEventListener("click", () => goTo(item.target));
    return button;
  }

  function createMoreButton() {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "cc-more-toggle";
    button.dataset.action = "more";
    button.setAttribute("aria-label", "Abrir todos los módulos");
    button.setAttribute("aria-expanded", "false");

    const icon = document.createElement("span");
    icon.className = "cc-nav-icon";
    icon.setAttribute("aria-hidden", "true");
    icon.textContent = "•••";

    const label = document.createElement("span");
    label.textContent = "Más";

    button.append(icon, label);
    button.addEventListener("click", toggleMoreMenu);
    return button;
  }

  function createModuleButton(item) {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "cc-more-module";
    button.dataset.route = JSON.stringify(item.target);

    const code = document.createElement("span");
    code.className = "cc-more-code";
    code.textContent = item.code;

    const label = document.createElement("strong");
    label.textContent = item.label;

    button.append(code, label);
    button.addEventListener("click", () => goTo(item.target));
    return button;
  }

  function ensureMoreMenu(active) {
    let backdrop = document.querySelector(".cc-more-backdrop");
    let sheet = document.querySelector(".cc-more-sheet");

    if (!active) {
      backdrop?.remove();
      sheet?.remove();
      return;
    }

    if (!backdrop) {
      backdrop = document.createElement("button");
      backdrop.type = "button";
      backdrop.className = "cc-more-backdrop";
      backdrop.hidden = true;
      backdrop.setAttribute("aria-label", "Cerrar menú de módulos");
      backdrop.addEventListener("click", closeMoreMenu);
      document.body.appendChild(backdrop);
    }

    if (!sheet) {
      sheet = document.createElement("section");
      sheet.className = "cc-more-sheet";
      sheet.hidden = true;
      sheet.setAttribute("role", "dialog");
      sheet.setAttribute("aria-modal", "true");
      sheet.setAttribute("aria-label", "Todos los módulos de ConstruControl");

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
      for (const item of availableMoreItems()) grid.appendChild(createModuleButton(item));

      sheet.append(header, grid);
      document.body.appendChild(sheet);
    }
  }

  function openMoreMenu() {
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

  function updateNavigation(active, route) {
    let nav = document.querySelector(".cc-mobile-nav");
    if (!active) {
      nav?.remove();
      ensureMoreMenu(false);
      return;
    }

    if (!nav) {
      nav = document.createElement("nav");
      nav.className = "cc-mobile-nav";
      nav.setAttribute("aria-label", "Navegación móvil de ConstruControl");
      for (const item of primaryItems) nav.appendChild(createPrimaryButton(item));
      nav.appendChild(createMoreButton());
      document.body.appendChild(nav);
    }

    ensureMoreMenu(true);
    const moreSelected = availableMoreItems().some(item => sameRoute(route, item.target));
    for (const button of nav.querySelectorAll("button")) {
      const target = JSON.parse(button.dataset.route || "[]");
      const selected = button.dataset.action === "more" ? moreSelected : sameRoute(route, target);
      button.classList.toggle("is-active", selected);
      button.setAttribute("aria-current", selected ? "page" : "false");
    }

    for (const button of document.querySelectorAll(".cc-more-module")) {
      const target = JSON.parse(button.dataset.route || "[]");
      button.classList.toggle("is-active", sameRoute(route, target));
    }
  }

  function enforceAdminVisibility() {
    if (isSystemManager()) return;
    document.querySelectorAll('[data-target="Page:construcontrol-migration-console"]').forEach(element => element.remove());
    document.querySelectorAll("a, button, .link-item, .shortcut-widget-box").forEach(element => {
      const text = String(element.textContent || "").trim();
      if (adminLabels.some(label => text.includes(label))) {
        const row = element.closest(".link-item, .shortcut-widget-box, .widget, .list-row") || element;
        row.remove();
      }
    });
  }

  function safeVisibleName(...candidates) {
    for (const candidate of candidates) {
      const value = String(candidate || "").trim();
      if (!value || value.includes("@") || value.casefold?.() === "guest") continue;
      return value;
    }
    return "";
  }

  async function showIdentityBadge() {
    const hero = document.querySelector(".cc-hero");
    if (!hero || hero.querySelector(".cc-identity-badge")) return;
    try {
      const identity = await frappe.xcall("erpnext.construcontrol.api.get_current_identity");
      const roleLabel = String(identity.role || "USER").trim().toUpperCase();
      const visibleName = safeVisibleName(window.frappe?.boot?.user?.full_name, identity.display_name);
      const badge = document.createElement("div");
      badge.className = "cc-identity-badge";
      badge.dataset.role = roleLabel;
      badge.setAttribute("aria-label", visibleName ? `${roleLabel}, ${visibleName}` : roleLabel);
      badge.title = `Rol: ${roleLabel}`;

      const role = document.createElement("span");
      role.className = "cc-identity-role";
      role.textContent = roleLabel;
      badge.appendChild(role);

      if (visibleName) {
        const name = document.createElement("span");
        name.className = "cc-identity-name";
        name.textContent = visibleName;
        badge.appendChild(name);
      }

      hero.prepend(badge);
    } catch (_error) {
      // The page remains usable even when the identity endpoint is unavailable.
    }
  }

  function enhancePage() {
    enforceAdminVisibility();
    showIdentityBadge();
  }

  function applyShell() {
    const route = currentRoute();
    const active = isConstruControl(route);
    document.body.classList.toggle("cc-construcontrol-route", active);
    updateConnectionNotice(active);
    updateNavigation(active, route);
    closeMoreMenu();
    if (active) {
      window.setTimeout(enhancePage, 50);
      window.setTimeout(enhancePage, 500);
    }
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
    const observer = new MutationObserver(() => {
      const hero = document.querySelector(".cc-hero");
      if (document.body.classList.contains("cc-construcontrol-route") && hero && !hero.querySelector(".cc-identity-badge")) {
        window.setTimeout(enhancePage, 20);
      }
    });
    observer.observe(document.body, { childList: true, subtree: true });
  }
})();
