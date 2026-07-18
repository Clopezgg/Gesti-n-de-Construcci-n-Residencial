(() => {
  "use strict";

  const doctypes = new Set([
    "CC Funding Source", "CC Expense Control", "CC Labor Contract",
    "CC Construction Phase", "CC Material Ledger", "CC Inventory Movement",
    "CC Procurement Request", "CC Progress Update", "CC Weekly Closing",
    "CC Audit Log", "CC User Access"
  ]);

  const items = [
    ["⌂", "Inicio", ["construcontrol-dashboard"]],
    ["＋", "Ingresos", ["List", "CC Funding Source"]],
    ["−", "Gastos", ["List", "CC Expense Control"]],
    ["▦", "Materiales", ["List", "CC Material Ledger"]],
    ["✓", "Avance", ["List", "CC Progress Update"]]
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

  function sameRoute(current, target) {
    return target.length === 1
      ? String(current[0] || "") === target[0]
      : String(current[0] || "") === target[0] && String(current[1] || "") === target[1];
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

  function updateNavigation(active, route) {
    let nav = document.querySelector(".cc-mobile-nav");
    if (!active) {
      nav?.remove();
      return;
    }
    if (!nav) {
      nav = document.createElement("nav");
      nav.className = "cc-mobile-nav";
      nav.setAttribute("aria-label", "Navegación móvil de ConstruControl");
      for (const [icon, label, target] of items) {
        const button = document.createElement("button");
        button.type = "button";
        button.dataset.route = JSON.stringify(target);
        button.innerHTML = `<span class="cc-nav-icon" aria-hidden="true">${icon}</span><span>${label}</span>`;
        button.addEventListener("click", () => frappe.set_route(...target));
        nav.appendChild(button);
      }
      document.body.appendChild(nav);
    }
    for (const button of nav.querySelectorAll("button")) {
      const target = JSON.parse(button.dataset.route || "[]");
      const selected = sameRoute(route, target);
      button.classList.toggle("is-active", selected);
      button.setAttribute("aria-current", selected ? "page" : "false");
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

  async function showIdentityBadge() {
    const hero = document.querySelector(".cc-hero");
    if (!hero || hero.querySelector(".cc-identity-badge")) return;
    try {
      const identity = await frappe.xcall("erpnext.construcontrol.api.get_current_identity");
      const badge = document.createElement("div");
      badge.className = "cc-identity-badge";
      badge.textContent = `${identity.role} · ${identity.display_name}`;
      badge.title = `Correo: ${identity.email}`;
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
    if (active) {
      window.setTimeout(enhancePage, 50);
      window.setTimeout(enhancePage, 500);
    }
  }

  installMetadata();
  window.addEventListener("online", applyShell);
  window.addEventListener("offline", applyShell);
  window.addEventListener("load", applyShell);
  if (window.frappe?.router?.on) frappe.router.on("change", applyShell);
})();
