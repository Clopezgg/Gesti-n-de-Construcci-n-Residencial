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

  function currentRoute() {
    try { return frappe.get_route() || []; } catch (_error) { return []; }
  }

  function isConstruControl(route) {
    const first = String(route[0] || "");
    const second = String(route[1] || "");
    return first.startsWith("construcontrol-") || doctypes.has(first) || doctypes.has(second);
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

  function applyShell() {
    const route = currentRoute();
    const active = isConstruControl(route);
    document.body.classList.toggle("cc-construcontrol-route", active);
    updateConnectionNotice(active);
    updateNavigation(active, route);
  }

  window.addEventListener("online", applyShell);
  window.addEventListener("offline", applyShell);
  window.addEventListener("load", applyShell);
  if (window.frappe?.router?.on) frappe.router.on("change", applyShell);
})();
