frappe.pages["construcontrol-dashboard"].on_page_load = function (wrapper) {
  frappe.ui.make_app_page({ parent: wrapper, title: "ConstruControl", single_column: true });
  const body = $(wrapper).find(".layout-main-section");

  body.html(`
    <style>
      .cc-hero{padding:22px;border:1px solid var(--border-color);border-radius:14px;background:var(--card-bg);margin-bottom:16px}.cc-hero h2{margin:0 0 6px}.cc-muted{color:var(--text-muted)}
      .cc-metrics{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:12px;margin:16px 0}.cc-metric{border:1px solid var(--border-color);border-radius:12px;padding:14px;background:var(--card-bg)}.cc-metric strong{display:block;font-size:22px;margin-top:5px}
      .cc-modules{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:12px}.cc-module{display:block;border:1px solid var(--border-color);border-radius:12px;padding:14px;background:var(--card-bg);cursor:pointer;text-align:left}.cc-module:hover{border-color:var(--primary);background:var(--subtle-fg)}.cc-code{font-weight:700;color:var(--primary)}
      .cc-alert{padding:12px;border-radius:10px;margin:12px 0;background:var(--yellow-100);color:var(--yellow-900)}
    </style>
    <div class="cc-hero"><div class="cc-code">CC00 · CENTRO DE CONTROL</div><h2>Gestión de obra residencial</h2><div class="cc-muted">Remesas, gastos, contratos, fases, materiales, cierres y auditoría en un solo sistema.</div><div id="cc-demo"></div></div>
    <div id="cc-metrics" class="cc-metrics"></div>
    <h3>Módulos operativos</h3><div id="cc-modules" class="cc-modules"></div>
  `);

  const modules = [
    ["FI01","Fondos e ingresos","Remesas, aportes, depósitos y saldo por fuente","CC Funding Source"],
    ["FI02","Gastos y facturas","Compras, servicios, pagos y comprobación","CC Expense Control"],
    ["CO01","Contratos","Contratistas, valores, pagos y saldos","CC Labor Contract"],
    ["PR01","Fases de obra","Presupuesto, avance, checklist y planificación","CC Construction Phase"],
    ["MM01","Materiales","Existencias, costos y alertas de stock","CC Material Ledger"],
    ["MIGO","Movimientos de inventario","Consumos y ajustes sin stock negativo","CC Inventory Movement"],
    ["MM02","Compras","Solicitudes, cotizaciones y recepción","CC Procurement Request"],
    ["QC01","Avance de obra","Hitos, incidencias y progreso; sin importar fotografías","CC Progress Update"],
    ["CL01","Cierre semanal","Resumen financiero y operativo auditable","CC Weekly Closing"],
    ["BI01","Reportes","Reportes financieros y notificaciones autorizadas","Page:construcontrol-reporting-center"],
    ["AU01","Auditoría","Historial, anulaciones y cambios","CC Audit Log"],
    ["US01","Usuarios y permisos","Acceso operativo sin importar contraseñas","CC User Access"],
    ["MIG","Migración segura","Validar, respaldar, importar y conciliar","Page:construcontrol-migration-console"]
  ];

  body.find("#cc-modules").html(modules.map(m => `<button class="cc-module" data-target="${frappe.utils.escape_html(m[3])}"><span class="cc-code">${m[0]}</span><strong>${m[1]}</strong><div class="cc-muted">${m[2]}</div></button>`).join(""));
  body.on("click", ".cc-module", function () {
    const target = $(this).data("target");
    if (target.startsWith("Page:")) frappe.set_route(target.split(":")[1]);
    else frappe.set_route("List", target);
  });

  const money = value => format_currency(value || 0, "HNL");
  frappe.xcall("erpnext.construcontrol.api.get_dashboard_summary").then(s => {
    const metrics = [
      ["Recibido", money(s.received_hnl)],
      ["Gastado", money(s.spent_hnl)],
      ["Disponible", money(s.available_hnl)],
      ["Contratado", money(s.contracted_hnl)],
      ["Fases", s.phase_count],
      ["Avance", `${s.overall_progress}%`]
    ];
    body.find("#cc-metrics").html(metrics.map(x => `<div class="cc-metric"><span class="cc-muted">${x[0]}</span><strong>${x[1]}</strong></div>`).join(""));
    if (s.demo_present) body.find("#cc-demo").html(`<div class="cc-alert"><b>Datos demo detectados.</b> Se eliminarán mediante el procedimiento oficial después de una migración conciliada.</div>`);
  }).catch(() => body.find("#cc-metrics").html(`<div class="cc-alert">Todavía no hay datos migrados o no tiene permiso para ver el resumen.</div>`));
};
