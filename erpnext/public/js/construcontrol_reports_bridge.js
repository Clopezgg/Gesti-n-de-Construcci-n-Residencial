(() => {
  "use strict";

  const REPORTS = [
    ["FI03", "Cuentas por pagar", "FI03 Cuentas por Pagar"],
    ["PR02", "Presupuesto vs ejecución", "PR02 Presupuesto vs Ejecución"],
    ["PR03", "Fases y desviaciones", "PR03 Fases y Desviaciones"],
    ["MM03", "Inventario crítico", "MM03 Inventario Crítico"],
    ["FI04", "Ingresos y conciliación", "FI04 Ingresos y Conciliación"],
  ];

  function installLinks() {
    const route = window.frappe?.get_route?.() || [];
    if (String(route[0] || "") !== "construcontrol-reporting-center") return;
    const host = document.querySelector(".cc-bi");
    if (!host || host.querySelector(".cc-executive-report-links")) return;
    const section = document.createElement("section");
    section.className = "cc-executive-report-links";
    section.innerHTML = `<div class="cc-executive-report-title"><strong>Reportes ejecutivos</strong><span>Consultas listas para filtrar, imprimir y exportar</span></div><div class="cc-executive-report-grid">${REPORTS.map(row => `<button type="button" data-report="${frappe.utils.escape_html(row[2])}"><span>${row[0]}</span><strong>${row[1]}</strong></button>`).join("")}</div>`;
    const toolbar = host.querySelector(".cc-bi-actions");
    toolbar?.insertAdjacentElement("afterend", section);
    section.addEventListener("click", event => {
      const button = event.target.closest?.("[data-report]");
      if (button) frappe.set_route("query-report", button.dataset.report);
    });
  }

  window.addEventListener("load", () => window.setTimeout(installLinks, 80));
  if (window.frappe?.router?.on) frappe.router.on("change", () => window.setTimeout(installLinks, 80));
})();
