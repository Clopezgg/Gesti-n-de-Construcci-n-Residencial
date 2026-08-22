import assert from "node:assert/strict";
import path from "node:path";

import {
  artifactRoot,
  baseURL,
  apiResponse,
  assertResponseOk,
  browserRequest,
  capture,
  clickDialogPrimary,
  describeSignals,
  fillDialogField,
  gotoRoute,
  normalizedText,
  postArgs,
  postMethod,
  routes,
  safeName,
  waitForRoute,
} from "./nexora_browser_support.mjs";

async function readExecutiveApi(page) {
  const response = await postMethod(
    page,
    "nexora.dashboard.executive.get_executive_snapshot",
    {}
  );
  await assertResponseOk(response, "Executive API request");
  const data = response.payload?.message;
  assert(data?.context, "Executive API returned no context.");
  assert(data?.finance, "Executive API returned no finance section.");
  assert(data?.budgets, "Executive API returned no budget section.");
  assert.equal(
    data.filter_context?.bounded_operational_queries,
    true,
    "Executive API did not use bounded operational queries."
  );
  // RECONSTRUCCIÓN VISUAL DEFINITIVA: "Proyectos activos", "Flujo de fondos" y
  // la comparación contra el período anterior son reales, no un cálculo que
  // solo exista en el cliente.
  assert(data?.projects, "Executive API returned no projects section.");
  assert(
    Array.isArray(data?.cash_flow_monthly),
    "Executive API returned no monthly cash flow."
  );
  assert.equal(
    data.cash_flow_monthly.length,
    6,
    "Monthly cash flow was not exactly 6 months."
  );
  assert(
    data?.previous_period,
    "Executive API returned no previous_period comparison."
  );
  return data;
}

export async function validateDashboard(page, profile) {
  const dashboard = page.locator(
    '#page-nexora-dashboard .nxr-dashboard-shell[data-state="ready"]'
  );
  await dashboard.waitFor({ state: "visible", timeout: 120_000 });
  for (const selector of [
    ".nxr-project-name",
    ".nxr-dashboard-period",
    '.nxr-dashboard-primary-actions [data-action="income"]',
    '.nxr-dashboard-primary-actions [data-action="expense"]',
  ]) {
    await dashboard.locator(selector).first().waitFor({ state: "visible" });
  }
  assert.match(
    normalizedText(
      await dashboard.locator(".nxr-dashboard-period").innerText()
    ),
    /^Período:/,
    "Dashboard did not expose the active period."
  );
  // RECONSTRUCCIÓN VISUAL DEFINITIVA antepuso el panel «Acciones rápidas» al
  // hero original — ambos comparten el mismo atributo real `[data-action]`
  // (mismo manejador real, dos entradas visibles distintas a la misma
  // acción), así que estas dos comprobaciones se acotan al hero explícitamente
  // en vez de usar `.first()` sobre todo el documento.
  assert.equal(
    await dashboard
      .locator('.nxr-dashboard-primary-actions [data-action="income"]')
      .first()
      .innerText(),
    "Registrar fondos"
  );
  assert.equal(
    await dashboard
      .locator('.nxr-dashboard-primary-actions [data-action="expense"]')
      .first()
      .innerText(),
    "Registrar gasto"
  );
  assert.deepEqual(
    profile.page_errors,
    [],
    "Dashboard bootstrap emitted page errors."
  );
  assert.deepEqual(
    profile.console_errors,
    [],
    "Dashboard bootstrap emitted console errors."
  );
  const data = await readExecutiveApi(page);
  assert.equal(
    normalizedText(
      await page
        .locator("#page-nexora-dashboard h2.nxr-project-name")
        .innerText()
    ),
    normalizedText(data.context.project_label)
  );
  // El requisito es que el usuario vea los movimientos recientes, no que exista un
  // `<table>` visible: en móvil la pantalla lo sustituye por tarjetas a propósito
  // (Capítulo 37). Exigir la tabla hacía fallar el perfil de iPhone sobre un diseño
  // correcto.
  await page.waitForFunction(
    () => {
      const table = document.querySelector(
        '#page-nexora-dashboard .nxr-dashboard-recent-rows[data-operational-ledger="ready"]'
      );
      if (!table) return false;
      const cards = table.parentElement?.querySelector(".nxr-mobile-cards");
      return Boolean(table.offsetParent || cards?.offsetParent);
    },
    null,
    { timeout: 60_000 }
  );
  const ledgerResponse = await postArgs(
    page,
    "nexora.financial.service.list_operational_ledger",
    { limit: 20 }
  );
  await assertResponseOk(ledgerResponse, "Operational ledger API request");
  const ledgerRows = ledgerResponse.payload?.message || [];
  const recentRows = await page
    .locator("#page-nexora-dashboard .nxr-dashboard-recent-rows tbody tr")
    .count();
  assert.equal(recentRows, Math.min(ledgerRows.length, 8));
  assert(recentRows >= 3, "Operational ledger rows were not rendered.");
  assert.equal(
    await page
      .locator("#page-nexora-dashboard .nxr-activity-list .nxr-executive-row")
      .count(),
    Math.min(ledgerRows.length, 3)
  );
  await page.waitForFunction(
    () =>
      [
        ...document.querySelectorAll(
          "#page-nexora-dashboard .nxr-evidence-tile img"
        ),
      ].some((image) => image.complete && image.naturalWidth > 0),
    undefined,
    { timeout: 30_000 }
  );
  // NXR-UX-0013 (Bloque 16): el gasto legítimo no es rojo puro — regresión real
  // contra el hexadecimal de Bootstrap (`#c82333`) que `toneColors`/
  // `[data-tone="expense"]` usaban antes de la corrección del Design System; solo
  // se afirma sobre elementos que de verdad renderizaron (dato real, no fabricado).
  const expenseToneColors = await page
    .locator('#page-nexora-dashboard [data-tone="expense"][style*="color"]')
    .evaluateAll((nodes) => nodes.map((node) => node.style.color));
  for (const color of expenseToneColors) {
    assert(
      !/c82333/i.test(color) && !/^rgb\(200,\s*35,\s*51\)$/i.test(color),
      `Un elemento con data-tone="expense" sigue usando el rojo puro anterior: ${color}`
    );
  }
  // RECONSTRUCCIÓN VISUAL DEFINITIVA — la composición ejecutiva exigida por el
  // mandato del propietario: título real, cinco KPI reales (ni más ni menos),
  // bloque central de tres columnas, bloque operativo de dos tablas, acciones
  // rápidas reales e integración SAP con estado real (nunca inventado).
  assert.equal(
    normalizedText(
      await page
        .locator("#page-nexora-dashboard .nxr-panel-header h1")
        .innerText()
    ),
    "Panel principal"
  );
  assert.equal(
    normalizedText(
      await page
        .locator("#page-nexora-dashboard .nxr-panel-header p")
        .innerText()
    ),
    "Resumen ejecutivo del sistema"
  );
  const kpiCards = page.locator("#page-nexora-dashboard .nxr-kpi-card");
  await kpiCards.first().waitFor({ state: "visible", timeout: 30_000 });
  assert.equal(
    await kpiCards.count(),
    5,
    "El panel no mostró exactamente cinco KPI."
  );
  // `innerText` refleja el `text-transform: uppercase` real del CSS (a
  // diferencia de `textContent`) — la referencia visual del mandato muestra las
  // cinco etiquetas en mayúsculas, así que esta comprobación exige el
  // renderizado real, no el texto crudo de `nexora_dashboard.js`.
  assert.deepEqual(
    await kpiCards.locator(".nxr-kpi-label").allInnerTexts(),
    [
      "SALDO DISPONIBLE",
      "COMPROMETIDO",
      "PENDIENTE DE PAGAR",
      "PROYECTOS ACTIVOS",
      "% EJECUCIÓN PROMEDIO",
    ],
    "Las etiquetas de la fila de KPI no coincidieron con el mandato."
  );
  for (const selector of [
    ".nxr-central-budget",
    ".nxr-central-cashflow",
    ".nxr-central-notifications",
  ]) {
    await page
      .locator(`#page-nexora-dashboard .nxr-central-grid ${selector}`)
      .waitFor({ state: "visible", timeout: 30_000 });
  }
  await page
    .locator("#page-nexora-dashboard .nxr-operational-recent-table")
    .waitFor({ state: "visible", timeout: 30_000 });
  await page
    .locator("#page-nexora-dashboard .nxr-operational-projects-table")
    .waitFor({ state: "visible", timeout: 30_000 });
  const quickActionButtons = page.locator(
    "#page-nexora-dashboard .nxr-quick-actions-grid button"
  );
  assert.equal(
    await quickActionButtons.count(),
    6,
    "El panel de Acciones rápidas no mostró las seis acciones reales exigidas."
  );
  assert.deepEqual(await quickActionButtons.allInnerTexts(), [
    "Nueva operación",
    "Nueva solicitud de compra",
    "Nuevo proyecto",
    "Registrar gasto",
    "Cargar evidencia",
    "Generar reporte",
  ]);
  // El administrador real (`SAP_VIEW_ROLES`) sí puede ver la tarjeta — se espera
  // a que `loadSapCard()` resuelva su llamada real antes de afirmar sobre ella.
  const sapCard = page.locator("#page-nexora-dashboard .nxr-sap-card");
  await page.waitForFunction(
    () =>
      !document
        .querySelector("#page-nexora-dashboard .nxr-sap-card")
        ?.hasAttribute("hidden"),
    undefined,
    { timeout: 30_000 }
  );
  const sapBadgeText = normalizedText(
    await sapCard.locator("[data-sap-status-badge]").innerText()
  );
  assert(
    sapBadgeText === "Conectado" || sapBadgeText === "No conectado",
    `La tarjeta SAP no mostró un estado real: "${sapBadgeText}".`
  );
  const footerText = normalizedText(
    await page.locator(".nxr-shell__footer").innerText()
  );
  assert(
    footerText.includes("NEXORA") && !/erpnext|frappe/i.test(footerText),
    `El pie de página no usó exclusivamente identidad NEXORA: "${footerText}".`
  );
  // AUDITORÍA VISUAL Y FUNCIONAL COMPLETA POST-DASHBOARD: evidencia real de
  // navegador (no solo estática) de que no existe una segunda composición
  // completa del panel debajo de la real — la sección "Qué requiere su
  // atención hoy" y la fila de seis métricas quedaron retiradas por duplicar
  // el panel de Notificaciones y la fila de KPI reales.
  assert.equal(
    await page.locator("#page-nexora-dashboard .nxr-agenda").count(),
    0,
    "La sección de agenda retirada sigue presente en el DOM real."
  );
  assert.equal(
    await page.locator("#page-nexora-dashboard .nxr-executive-metrics").count(),
    0,
    "La fila de métricas retirada sigue presente en el DOM real."
  );
  assert.equal(
    await page.locator("#page-nexora-dashboard .nxr-panel-header").count(),
    1,
    "Debe existir exactamente un encabezado real de «Panel principal»."
  );
  profile.dashboard = {
    source_count: data.finance.source_count,
    available_hnl: data.finance.total_available_hnl,
    budget_available_hnl: data.budgets.total_available_hnl,
    pending_count: data.pending_accounts.count,
    evidence_count: data.evidence.count,
    recent_operations: data.recent_operations.length,
    expense_tone_samples: expenseToneColors.length,
  };
}

export async function validateQuickActions(page, context, profile) {
  await gotoRoute(page, context, profile, "nexora-dashboard");
  await page
    .locator('#page-nexora-dashboard [data-action="expense"]')
    .first()
    .click();
  await waitForRoute(page, "nexora-operations");
  await page.waitForFunction(
    () =>
      document.querySelector(
        '#page-nexora-operations [data-field="movement_code"] input'
      )?.value === "102",
    undefined,
    { timeout: 60_000 }
  );
  await page
    .locator('#page-nexora-operations [data-field="document_date"] input')
    .waitFor({ state: "visible", timeout: 60_000 });
  await gotoRoute(page, context, profile, "nexora-dashboard");
  await page
    .locator('#page-nexora-dashboard [data-action="income"]')
    .first()
    .click();
  await waitForRoute(page, "nexora-operations");
  await page.waitForFunction(
    () =>
      document.querySelector(
        '#page-nexora-operations [data-field="movement_code"] input'
      )?.value === "101",
    undefined,
    { timeout: 60_000 }
  );
  await page
    .locator('#page-nexora-operations [data-field="account_mode"] select')
    .waitFor({ state: "visible", timeout: 60_000 });
  await page
    .locator("#page-nexora-operations .nxr-entry-table")
    .waitFor({ state: "visible", timeout: 60_000 });
  assert.equal(
    await page.locator("#page-nexora-operations .nxr-document-tabs").count(),
    1,
    "Operational document tabs are missing."
  );
  assert.equal(
    await page.locator("#page-nexora-operations .nxr-detail-tabs").count(),
    1,
    "Operational detail tabs are missing."
  );
  const accountMode = await page
    .locator('#page-nexora-operations [data-field="account_mode"] select')
    .inputValue();
  assert(
    ["Existing", "New", "Manual"].includes(accountMode),
    `Unexpected account mode: ${accountMode}`
  );
  if (accountMode === "Existing") {
    await page
      .locator('#page-nexora-operations [data-field="financial_account"] input')
      .waitFor({ state: "visible", timeout: 60_000 });
  } else if (accountMode === "New") {
    await page
      .locator('#page-nexora-operations [data-field="account_name"] input')
      .waitFor({ state: "visible", timeout: 60_000 });
    await page
      .locator('#page-nexora-operations [data-field="financial_account"] input')
      .waitFor({ state: "hidden", timeout: 60_000 });
  }
  profile.quick_actions = {
    expense_code: "102",
    income_code: "101",
    account_mode: accountMode,
    transaction_layout: "header-lines-detail",
  };
}

export async function validateReports(page, context, profile, name) {
  await gotoRoute(page, context, profile, "nexora-reports");
  await page
    .locator('#page-nexora-reports .nxr-bi-shell[data-state="ready"]')
    .waitFor({ state: "visible", timeout: 120_000 });
  for (const code of ["FI01", "FI02", "CO01", "PR02", "BI01"]) {
    assert.equal(
      await page.locator(`#page-nexora-reports [data-view="${code}"]`).count(),
      1,
      `${code} report card is missing.`
    );
  }
  await page.locator('#page-nexora-reports [data-view="FI02"]').click();
  await page.waitForFunction(
    () =>
      document
        .querySelector("#page-nexora-reports .nxr-report-title")
        ?.textContent?.includes("FI02"),
    undefined,
    { timeout: 60_000 }
  );
  await page
    .locator("#page-nexora-reports .nxr-report-table")
    .waitFor({ state: "visible", timeout: 60_000 });
  profile.reports = {
    cards: await page.locator("#page-nexora-reports [data-view]").count(),
    active: normalizedText(
      await page.locator("#page-nexora-reports .nxr-report-title").innerText()
    ),
  };
  await capture(
    page,
    profile,
    path.join(artifactRoot, `${safeName(name)}-reports.png`)
  );
}

/**
 * Auditoría visual de los módulos prioritarios que ningún otro paso del recorrido
 * capturaba: Fondos, Entidades, Contratos, Compras (solicitudes, cotizaciones y
 * proveedores son tres pantallas reales distintas) y Proyecto 360°. Cada uno ya se
 * visitaba desde la etapa "rutas" (o ni eso, en el caso de Entidades y Proyecto
 * 360°, que no estaban en `routes`) solo para comprobar que no daba 404 — nunca se
 * había mirado cómo se ve. Sin evidencia visual real no hay forma honesta de auditar
 * la experiencia contra el nivel empresarial pedido; esto es esa evidencia, no un
 * rediseño.
 *
 * No se fija ningún proyecto en el filtro de cada pantalla a propósito: el estado
 * por defecto —lo primero que ve cualquier usuario real al entrar— es la evidencia
 * que hace falta primero. Fijar un proyecto de fixture sería una segunda auditoría,
 * de un estado distinto, y hoy no hay evidencia de que ese sea el estado que más le
 * importa al negocio.
 */
export async function validateModuleGallery(page, context, profile, name) {
  const targets = [
    {
      route: "nexora-finance",
      selector: "#page-nexora-finance .nxr-finance-guide",
      file: "fondos",
    },
    {
      route: "nexora-entities",
      selector: "#page-nexora-entities .nxr-entity-grid",
      file: "entidades",
    },
    {
      route: "nexora-contracts",
      selector: "#page-nexora-contracts .nxr-contract-grid",
      file: "contratos",
    },
    {
      route: "nexora-purchase-requests",
      selector: "#page-nexora-purchase-requests .nxr-purchase-request-grid",
      file: "compras-solicitudes",
    },
    {
      route: "nexora-quotations",
      selector: "#page-nexora-quotations .nxr-quotation-grid",
      file: "compras-cotizaciones",
    },
    // Bloque 65 (auditoría de galería de módulos, MASTER BLOCK 3): la cadena de
    // compras seguía sin recorrerse hasta órdenes ni recepciones — ambas pantallas
    // reales, con servicio y cobertura de integración real desde antes (Bloque 63),
    // pero nunca comprobadas en navegador. Inventario, consecuencia real de una
    // recepción completada (Bloque 63), tampoco aparecía.
    {
      route: "nexora-purchase-orders",
      selector: "#page-nexora-purchase-orders .nxr-order-grid",
      file: "compras-ordenes",
    },
    {
      route: "nexora-receipts",
      selector: "#page-nexora-receipts .nxr-receipt-grid",
      file: "compras-recepciones",
    },
    {
      route: "nexora-suppliers",
      selector: "#page-nexora-suppliers .nxr-supplier-grid",
      file: "compras-proveedores",
    },
    {
      route: "nexora-inventory",
      selector: "#page-nexora-inventory .nxr-inventory-grid",
      file: "inventario",
    },
    {
      route: "nexora-project",
      selector: "#page-nexora-project .nxr-project-shell",
      file: "proyecto-360",
    },
    // Bloque 66 (segunda pasada, MASTER BLOCK 3): presupuesto, administración,
    // notificaciones, integraciones y proveedores de IA tienen servicio y página
    // reales pero nunca se habían abierto en un navegador real — el escenario de
    // usuario administrativo (login → usuarios → roles → notificaciones) del
    // mandato del propietario depende de que estas pantallas realmente rendericen,
    // no solo de que su backend responda.
    {
      route: "nexora-budget",
      selector: "#page-nexora-budget .nxr-budget-grid",
      file: "presupuesto",
    },
    {
      route: "nexora-administracion",
      selector: "#page-nexora-administracion .nxr-admin",
      file: "administracion",
    },
    {
      route: "nexora-notifications",
      selector: "#page-nexora-notifications .nxr-notifications",
      file: "notificaciones",
    },
    {
      route: "nexora-integrations",
      selector: "#page-nexora-integrations .nxr-integrations",
      file: "integraciones",
    },
    // Cierre de producción, Paso 2: SAP ganó su propia página en vez de
    // compartir la de integraciones genéricas.
    {
      route: "nexora-sap",
      selector: "#page-nexora-sap .nxr-sap",
      file: "sap",
    },
    {
      route: "nexora-ai-providers",
      selector: "#page-nexora-ai-providers .nxr-ai-providers",
      file: "proveedores-ia",
    },
    // Bloque 96 (MASTER BLOCK 3, Fase 3 ampliada): `nexora-quality` tiene servicio
    // y página reales desde el Bloque 54 (NXR-CAL-001), pero nunca había aparecido
    // en ningún script de navegador — ni siquiera una mención de "quality" en
    // scripts/*.mjs antes de este bloque, confirmado con grep. `MATRIZ_REQUISITOS.md`
    // ya pedía "navegación real en navegador" como criterio para elevar su estado.
    {
      route: "nexora-quality",
      selector: "#page-nexora-quality .nxr-quality-grid",
      file: "calidad",
    },
  ];
  profile.module_gallery = [];
  for (const target of targets) {
    await gotoRoute(page, context, profile, target.route);
    await page
      .locator(target.selector)
      .waitFor({ state: "visible", timeout: 60_000 });
    // Espera por condición real (sin peticiones en vuelo), no un tiempo fijo: cada
    // pantalla pide sus propios datos con un método distinto y sin un evento común
    // que la carcasa emita al terminar.
    await page.waitForLoadState("networkidle");
    await capture(
      page,
      profile,
      path.join(artifactRoot, `${safeName(name)}-${target.file}.png`)
    );
    profile.module_gallery.push(target.route);
  }
}

export async function validateClosing(page, context, profile) {
  await gotoRoute(page, context, profile, "nexora-closing");
  await page
    .locator('#page-nexora-closing .nxr-closing-shell[data-state="ready"]')
    .waitFor({ state: "visible", timeout: 120_000 });
  await page.locator("#page-nexora-closing .nxr-calculate").click();
  await page
    .locator("#page-nexora-closing .nxr-close-kpis .nxr-bi-kpi")
    .first()
    .waitFor({ state: "visible", timeout: 120_000 });
  const hash = normalizedText(
    await page.locator("#page-nexora-closing .nxr-close-hash").innerText()
  );
  // Si el cálculo se borró después de pintarse, la pantalla dice quién lo borró: sin
  // ese dato la huella vacía no distingue «el motor no respondió» de «algo descartó
  // el cálculo recién pedido».
  const clearedBy = await page
    .locator("#page-nexora-closing .nxr-closing-shell")
    .getAttribute("data-calculation-cleared-by");
  assert.match(
    hash,
    /nexora-analytics-v3/,
    `La huella del motor de cierre quedó en «${hash}» tras calcular; el cálculo fue descartado por: ${
      clearedBy || "nadie"
    }.`
  );
  assert(
    await page.locator("#page-nexora-closing .nxr-close-summary table").count(),
    "Weekly close summary table is missing."
  );
  profile.closing = {
    engine: hash,
    history_rows: await page
      .locator("#page-nexora-closing .nxr-close-history tbody tr")
      .count(),
  };

  // Cierre mensual (Bloque 100, MASTER BLOCK 3): a diferencia del semanal de
  // arriba, crear un cierre mensual lo guarda de inmediato y bloquea el período
  // — nunca sobre el proyecto demo compartido por el resto del recorrido: un
  // cierre ahí rompería cada "operaciones" posterior de este mismo mes, en esta
  // corrida y en todas las siguientes hasta que cambie el mes. Proyecto propio
  // y desechable, creado en el momento, mismo patrón que ya usan las pruebas
  // Python de este repositorio (`_ensure_project(f"...{marker}")`).
  const monthlyProjectResponse = await postArgs(page, "frappe.client.insert", {
    doc: {
      doctype: "Project",
      project_name: `_Browser Monthly Close ${Date.now()}`,
      status: "Open",
    },
  });
  await assertResponseOk(
    monthlyProjectResponse,
    "Isolated monthly-close project creation"
  );
  const monthlyProject = monthlyProjectResponse.payload?.message?.name;
  assert(
    monthlyProject,
    "Monthly-close project creation returned no document name."
  );
  await page.evaluate(
    (project) => window.nexora.context.setActiveProject(project),
    monthlyProject
  );
  await page
    .locator("#page-nexora-closing .nxr-monthly-history")
    .filter({ hasText: "No hay cierres mensuales guardados." })
    .waitFor({ state: "visible", timeout: 60_000 });

  await page.locator("#page-nexora-closing .nxr-monthly-create").click();
  const createDialog = page
    .locator(".modal.show .modal-dialog")
    .filter({ hasText: "Crear cierre mensual" })
    .last();
  await createDialog.waitFor({ state: "visible", timeout: 60_000 });
  const createResponsePromise = apiResponse(
    page,
    "nexora.close.service.create_monthly_close",
    "creación de cierre mensual"
  );
  await clickDialogPrimary(createDialog, page, "Crear cierre mensual");
  await assertResponseOk(
    await createResponsePromise,
    "Monthly close creation request"
  );

  const reviewButton = page
    .locator(
      '#page-nexora-closing .nxr-monthly-history [data-monthly-transition][data-status="In Review"]'
    )
    .first();
  await reviewButton.waitFor({ state: "visible", timeout: 60_000 });
  await reviewButton.click();
  const reviewDialog = page
    .locator(".modal.show .modal-dialog")
    .filter({ hasText: "Cambiar el cierre mensual" })
    .last();
  await reviewDialog.waitFor({ state: "visible", timeout: 60_000 });
  const reviewResponsePromise = apiResponse(
    page,
    "nexora.close.service.transition_monthly_close",
    "transición a En revisión"
  );
  await clickDialogPrimary(reviewDialog, page, "Cambiar a En revisión");
  await assertResponseOk(
    await reviewResponsePromise,
    "Monthly close transition to In Review"
  );

  const approveButton = page
    .locator(
      '#page-nexora-closing .nxr-monthly-history [data-monthly-transition][data-status="Approved"]'
    )
    .first();
  await approveButton.waitFor({ state: "visible", timeout: 60_000 });
  await approveButton.click();
  const approveDialog = page
    .locator(".modal.show .modal-dialog")
    .filter({ hasText: "Cambiar el cierre mensual" })
    .last();
  await approveDialog.waitFor({ state: "visible", timeout: 60_000 });
  const approveResponsePromise = apiResponse(
    page,
    "nexora.close.service.transition_monthly_close",
    "transición a Aprobado"
  );
  await clickDialogPrimary(approveDialog, page, "Cambiar a Aprobado");
  await assertResponseOk(
    await approveResponsePromise,
    "Monthly close transition to Approved"
  );

  const correctButton = page
    .locator("#page-nexora-closing .nxr-monthly-history [data-monthly-correct]")
    .first();
  await correctButton.waitFor({ state: "visible", timeout: 60_000 });
  await correctButton.click();
  const correctDialog = page
    .locator(".modal.show .modal-dialog")
    .filter({ hasText: "Corrección de cierre mensual" })
    .last();
  await correctDialog.waitFor({ state: "visible", timeout: 60_000 });
  await fillDialogField(
    correctDialog,
    "correction_reason",
    "Corrección de cierre mensual validada en navegador real."
  );
  const correctResponsePromise = apiResponse(
    page,
    "nexora.close.service.correct_monthly_close",
    "corrección de cierre mensual"
  );
  await clickDialogPrimary(correctDialog, page, "Registrar corrección");
  await assertResponseOk(
    await correctResponsePromise,
    "Monthly close correction request"
  );

  const monthlyRows = page.locator(
    "#page-nexora-closing .nxr-monthly-history tbody tr"
  );
  await monthlyRows.nth(1).waitFor({ state: "visible", timeout: 60_000 });
  const monthlyRowCount = await monthlyRows.count();
  assert.equal(
    monthlyRowCount,
    2,
    `La corrección de cierre mensual debía dejar 2 filas (original + corrección enlazada), quedaron ${monthlyRowCount}.`
  );
  await capture(page, profile, path.join(artifactRoot, "closing-monthly.png"));
  profile.monthly_closing = {
    project: monthlyProject,
    lifecycle: "Draft → In Review → Approved → correction",
    history_rows: monthlyRowCount,
  };
}

/**
 * La carcasa es lo que hace que el producto no parezca el escritorio del marco. Si
 * desapareciera, todas las pantallas seguirían funcionando y nadie se enteraría hasta
 * abrirlo: por eso se comprueba que está, que la barra del marco no está, y que la
 * navegación marca dónde se encuentra el usuario.
 */
export async function validateShell(page, profile) {
  const shell = page.locator(".nxr-shell");
  await shell.waitFor({ state: "attached", timeout: 60_000 });
  // `.nxr-shell` es `display: contents`: no genera caja propia, así que la
  // comprobación de visibilidad de Playwright —que exige un rectángulo no vacío—
  // nunca resolvería sobre ella. La barra es lo que de verdad se pinta.
  const bar = page.locator(".nxr-shell__bar");
  await bar.waitFor({ state: "visible", timeout: 60_000 });

  const frameworkNavbar = await page.locator("header.navbar:visible").count();
  assert.equal(
    frameworkNavbar,
    0,
    "La barra del escritorio del marco seguía visible sobre la carcasa de NEXORA."
  );

  const destinations = await shell.locator("[data-shell-route]").count();
  // El total esperado se calcula contra la propia fuente real
  // (`window.nexora.shell.sections`/`tabbarItems`, expuesta por
  // `nexora_shell.js` para exactamente este propósito) en vez de un número fijo:
  // un número fijo quedó obsoleto tres veces seguidas (Bloque 16 agregó la barra
  // de pestañas sin actualizarlo — nunca ejecutado como gate de PR—, el Bloque 17
  // lo subió a 17 al agregar "Proyecto 360°", el Bloque 18 lo desactualizó de
  // nuevo al agregar "Asistente"). Calcularlo aquí elimina esa clase de defecto
  // en vez de repetir el parche en el próximo destino nuevo — sigue exigiendo un
  // total exacto, ahora imposible de desincronizar.
  const expectedDestinations = await page.evaluate(() => {
    const shellApi = window.nexora?.shell;
    if (!shellApi) return null;
    const sidebarCount = shellApi.sections.reduce(
      (total, section) => total + section.items.length,
      0
    );
    return sidebarCount + shellApi.tabbarItems.length;
  });
  assert(
    expectedDestinations !== null,
    "window.nexora.shell no expuso sections/tabbarItems."
  );
  assert.equal(
    destinations,
    expectedDestinations,
    `La navegación ofreció ${destinations} destinos en vez de ${expectedDestinations}.`
  );
  const groups = await shell.locator(".nxr-shell__section").count();
  // Mismo defecto que el comentario de arriba ya documentó y corrigió para
  // `destinations` (un número fijo desincronizándose cada vez que se agrega un
  // grupo — esta vez con "Configuración", Bloque 37): se calcula contra la misma
  // fuente real en vez de repetir el número.
  const expectedGroups = await page.evaluate(
    () => window.nexora?.shell?.sections?.length ?? null
  );
  assert(expectedGroups !== null, "window.nexora.shell no expuso sections.");
  assert.equal(
    groups,
    expectedGroups,
    `La navegación mostró ${groups} grupos en vez de ${expectedGroups}.`
  );
  // RECONSTRUCCIÓN VISUAL DEFINITIVA: la barra lateral debe seguir exactamente
  // esta jerarquía de seis grupos, por nombre y por orden, exigida por el
  // mandato del propietario. `.nxr-shell__section-label` ya llevaba
  // `text-transform: uppercase` real desde antes de este bloque — `innerText`
  // refleja ese renderizado real, no el texto crudo de `SECTIONS`.
  assert.deepEqual(
    await shell.locator(".nxr-shell__section-label").allInnerTexts(),
    [
      "INICIO",
      "NÚCLEO DE FONDOS",
      "PROYECTOS",
      "COMPRAS E INVENTARIO",
      "REPORTES E INTELIGENCIA",
      "ADMINISTRACIÓN",
    ]
  );
  // Topbar real: buscador universal centrado y clúster de usuario — ninguno
  // existía antes de este bloque. `nexora_shell.css` los oculta a propósito
  // por debajo de 640px (la barra inferior ya asume la búsqueda y el resto
  // del clúster satura una pantalla de teléfono, mismo criterio ya real que
  // `validateResponsiveLayout` aplica a la barra inferior) — se comprueba el
  // ancho real del viewport, nunca el nombre del perfil.
  const viewportWidth = await page.evaluate(() => window.innerWidth);
  if (viewportWidth > 640) {
    await shell
      .locator(".nxr-shell__universal-search")
      .waitFor({ state: "visible", timeout: 30_000 });
    assert.equal(
      normalizedText(
        await shell.locator(".nxr-shell__universal-search").innerText()
      ),
      "Buscar en NEXORA"
    );
    const userName = normalizedText(
      await shell.locator("[data-shell-username]").innerText()
    );
    assert(
      userName.length > 0,
      "El topbar no mostró el nombre real del usuario."
    );
  } else {
    const searchVisible = await shell
      .locator(".nxr-shell__universal-search")
      .isVisible();
    assert(
      !searchVisible,
      `El buscador universal no debería ser visible en ${profile.name} (${viewportWidth}px).`
    );
  }

  // El usuario tiene que poder saber dónde está sin leer la URL. `paintActive()`
  // marca `aria-current` en todos los elementos `[data-shell-route]` cuya ruta
  // coincide (nexora_shell.js) a propósito: la misma ruta aparece a la vez en la
  // barra lateral y en la barra de pestañas móvil (dos superficies responsive del
  // mismo destino, una visible según el viewport), así que dos marcas totales para
  // una sola ruta es el comportamiento correcto, no una fuga. Lo que de verdad
  // importa es que cada superficie, por separado, marque exactamente un destino.
  const sidebarCurrent = shell.locator(
    '.nxr-shell__sections [data-shell-route][aria-current="page"]'
  );
  assert.equal(
    await sidebarCurrent.count(),
    1,
    "La barra lateral no marcó exactamente un destino como actual."
  );
  assert.equal(
    await sidebarCurrent.getAttribute("data-shell-route"),
    "nexora-dashboard",
    "La barra lateral marcó un destino distinto del que se está viendo."
  );
  const tabbarCurrent = shell.locator(
    '.nxr-shell__tabbar [data-shell-route][aria-current="page"]'
  );
  assert.equal(
    await tabbarCurrent.count(),
    1,
    "La barra de pestañas no marcó exactamente un destino como actual."
  );
  assert.equal(
    await tabbarCurrent.getAttribute("data-shell-route"),
    "nexora-dashboard",
    "La barra de pestañas marcó un destino distinto del que se está viendo."
  );

  // La carcasa no mueve el contenido del marco: flota encima de él con relleno en
  // `<body>`. La primera versión reparentaba `#body` dentro de un marco de contenido
  // propio, y eso desmontaba la pantalla que el enrutador acababa de construir —el
  // recorrido real lo encontró en los tres perfiles como `page_exists: false`—. Aquí se
  // exige lo contrario: que la pantalla siga existiendo y que `#body` no haya cambiado
  // de padre.
  assert.equal(
    await page.locator("#page-nexora-dashboard").count(),
    1,
    "La pantalla del marco desapareció con la carcasa montada."
  );
  assert.equal(
    await page.locator(".nxr-shell__nav #body, .nxr-shell__bar #body").count(),
    0,
    "La carcasa volvió a reparentar el contenido del marco en vez de flotar sobre él."
  );
  profile.shell = { destinations, groups, framework_navbar_visible: false };
}

/**
 * CIERRE ESTRUCTURAL DEL DESK FRAPPE: hallazgo real corregido en este bloque —
 * `System Manager`/`NEXORA Administrator` estaban completamente exentos de la
 * guarda de ruta (`shell_guard_core.resolve_redirect` + `nexora_shell.js
 * ::enforceRouteGuard`), y `role_home_page` (`hooks.py`) nunca tuvo entrada
 * para `System Manager` — el usuario real "Administrator" (que siempre lo
 * tiene) caía sin ningún filtro en el Workspace "Home" genérico de ERPNext
 * ("Let's begin your journey with ERPNext"). `authenticate()` ya inicia este
 * mismo `page` como el usuario real "Administrator" (Bloque 103) — se
 * reutiliza esa sesión real, no una simulada, para ejercer exactamente las
 * tres rutas que el hallazgo nombra.
 */
async function waitForNexoraDashboardContent(page) {
  // Deliberadamente más laxo que `waitForRoute()`: la ruta desnuda `/app` no
  // pasa por una transición de ruta de cliente (`frappe.set_route()`) — la
  // resuelve el propio servidor vía `desktop:home_page`/`role_home_page`
  // (Bloque 186), así que `frappe.get_route()` puede seguir devolviendo
  // `[""]` incluso cuando el contenido real ya es el correcto (confirmado
  // con evidencia real de CI: el HTML mostraba el panel ejecutivo completo
  // con datos reales mientras `frappe_route` seguía `[""]`). Lo que de
  // verdad importa aquí es el contenido real renderizado, no el mecanismo
  // que lo produjo.
  return page.waitForFunction(
    () => {
      const container = document.querySelector("#page-nexora-dashboard");
      return Boolean(container?.offsetParent) &&
        /resumen ejecutivo/i.test(container.innerText || "")
        ? { url: window.location.href, page_text: container.innerText }
        : null;
    },
    { timeout: 60_000 }
  );
}

export async function validateAdministratorNeverReachesTheGenericDesk(
  page,
  profile
) {
  const onboardingPattern = /let'?s begin your journey with erpnext/i;
  const genericRoutes = ["/app/home", "/app/workspace", "/app"];
  const results = [];
  for (const route of genericRoutes) {
    const navigation = await page.goto(`${baseURL}${route}`, {
      waitUntil: "domcontentloaded",
      timeout: 60_000,
    });
    assert(
      navigation && navigation.status() < 400,
      `La navegación real a ${route} no debió fallar con un error HTTP.`
    );
    await waitForNexoraDashboardContent(page);
    const finalPath = new URL(page.url()).pathname;
    assert(
      finalPath === "/app/nexora-dashboard" || finalPath === "/app",
      `Administrator no debió poder quedarse en ${route} — terminó en ${finalPath}.`
    );
    const bodyText = await page.evaluate(() => document.body.innerText || "");
    assert(
      !onboardingPattern.test(bodyText),
      `El onboarding genérico de ERPNext apareció al navegar a ${route}.`
    );
    results.push({ route, landed_on: finalPath });
  }
  // Deja la sesión en un estado conocido para los pasos siguientes del
  // recorrido — la ruta desnuda `/app` no navega por sí sola a la URL
  // completa de `nexora-dashboard`, y el resto del recorrido sí la asume.
  await page.goto(`${baseURL}/app/nexora-dashboard`, {
    waitUntil: "domcontentloaded",
    timeout: 60_000,
  });
  await waitForRoute(page, "nexora-dashboard");
  profile.administrator_desk_escape_guard = { checks: results };
}

export async function validateWebsitePagesNeverAdvertiseErpnext(page) {
  // Hallazgo real (Bloque 187): curl directo contra el runtime de producción
  // mostró que /login servía el favicon de ERPNext
  // (/assets/erpnext/images/erpnext-favicon.svg) y que una página `www`
  // genérica (404) mostraba el pie "Desarrollado por ERPNext" enlazando a
  // frappe.io. Ambos vienen de un hook de diccionario
  // (`website_context`) y de una plantilla incluida
  // (`templates/includes/footer/footer_powered.html`) que ERPNext declara y
  // que nexora nunca sobreescribía. Corregido en hooks.py y en un archivo de
  // plantilla nuevo — esta comprobación confirma contra un bench real de CI
  // (no solo un archivo estático) que la sobreescritura realmente gana.
  const login = await browserRequest(page, "/login");
  await assertResponseOk(login, "Login page request");
  assert(
    !/erpnext-favicon/i.test(login.text),
    "La página de login sigue sirviendo el favicon de ERPNext."
  );

  const notFound = await browserRequest(
    page,
    "/nexora-brand-audit-route-does-not-exist"
  );
  assert(
    !/desarrollado por\s*<a[^>]*>\s*erpnext/i.test(notFound.text) &&
      !/frappe\.io\/erpnext\?source=website_footer/i.test(notFound.text),
    "Una página genérica del sitio sigue anunciando 'Desarrollado por ERPNext'."
  );
}

export async function validateManifest(page) {
  const link = page.locator('link[rel="manifest"][data-nexora="1"]');
  await link.waitFor({ state: "attached", timeout: 30_000 });
  const href = await link.getAttribute("href");
  assert(href, "NEXORA manifest link has no href.");
  const result = await browserRequest(page, href);
  await assertResponseOk(result, "NEXORA manifest request");
  assert.equal(result.payload.id, "/app/nexora-dashboard");
  assert.equal(result.payload.start_url, "/app/nexora-dashboard");
  assert.equal(result.payload.scope, "/app/");
  assert.equal(result.payload.display, "standalone");
  assert(result.payload.icons.some((icon) => icon.sizes === "192x192"));
  assert(result.payload.icons.some((icon) => icon.sizes === "512x512"));
  return result.payload;
}

export async function validatePwa(page, context, profile) {
  const manifest = await validateManifest(page);
  await page.waitForFunction(
    async () => {
      const registrations = await navigator.serviceWorker?.getRegistrations?.();
      return registrations?.some(
        (registration) =>
          registration.active?.scriptURL.includes("nexora-service-worker.js") &&
          registration.scope.endsWith("/app/")
      );
    },
    undefined,
    { timeout: 120_000 }
  );
  const state = await page.evaluate(async () => {
    const registrations = await navigator.serviceWorker.getRegistrations();
    const registration = registrations.find((entry) =>
      entry.active?.scriptURL.includes("nexora-service-worker.js")
    );
    const cacheNames = (await caches.keys()).filter((name) =>
      name.startsWith("nexora-shell-")
    );
    const cachedUrls = [];
    for (const name of cacheNames) {
      const cache = await caches.open(name);
      cachedUrls.push(...(await cache.keys()).map((request) => request.url));
    }
    return {
      active: registration?.active?.scriptURL || "",
      scope: registration?.scope || "",
      cache_names: cacheNames,
      cached_urls: cachedUrls,
    };
  });
  assert.match(state.active, /nexora-service-worker\.js/);
  assert.match(state.scope, /\/app\/$/);
  assert(state.cache_names.length, "NEXORA created no shell cache.");
  assert(state.cached_urls.length, "NEXORA cached no shell assets.");
  for (const cachedUrl of state.cached_urls) {
    const url = new URL(cachedUrl);
    assert.equal(url.origin, new URL(baseURL).origin);
    assert(url.pathname.startsWith("/assets/nexora/"));
    assert(
      !["/api/", "/private/", "/files/", "/app/"].some((prefix) =>
        url.pathname.startsWith(prefix)
      ),
      `PWA cached a sensitive resource: ${url.pathname}`
    );
  }
  try {
    await context.setOffline(true);
    await page
      .locator(".nxr-offline-banner")
      .waitFor({ state: "visible", timeout: 15_000 });
  } finally {
    await context.setOffline(false);
    await page
      .locator(".nxr-offline-banner")
      .waitFor({ state: "detached", timeout: 15_000 });
  }
  profile.pwa = { manifest, ...state, offline_banner: "passed" };
}

/**
 * NXR-UX-0008 — paleta de comandos real (Ctrl+K/Cmd+K). Abre el atajo, filtra por
 * texto sobre una etiqueta real del cajón lateral, navega con Enter, y confirma
 * que la ruta cambió — el mismo `frappe.set_route` que usa el resto de la
 * carcasa, no una ruta inventada por el recorrido.
 */
export async function validateCommandBar(page, profile) {
  const modifier = process.platform === "darwin" ? "Meta" : "Control";
  await page.keyboard.press(`${modifier}+k`);
  const bar = page.locator(".nxr-command-bar");
  await bar.waitFor({ state: "visible", timeout: 15_000 });
  const input = bar.locator("[data-command-input]");
  await input.waitFor({ state: "visible" });
  await input.fill("Reportes");
  const list = bar.locator("[data-command-list] [data-command-route]");
  await list.first().waitFor({ state: "visible", timeout: 15_000 });
  assert(
    (await list.count()) > 0,
    "El filtro de la paleta de comandos no encontró ningún destino real."
  );
  await page.keyboard.press("Enter");
  await waitForRoute(page, "nexora-reports");
  await bar.waitFor({ state: "hidden", timeout: 15_000 });
  await page.keyboard.press(`${modifier}+k`);
  await bar.waitFor({ state: "visible", timeout: 15_000 });
  await page.keyboard.press("Escape");
  await bar.waitFor({ state: "hidden", timeout: 15_000 });
  profile.command_bar = {
    opened: true,
    filtered_to: "nexora-reports",
    escape_closes: true,
  };
}

export async function validateResponsiveLayout(page, profile) {
  const result = await page.evaluate(() => {
    const width = window.innerWidth;
    const overflowing = [];
    for (const node of document.querySelectorAll(
      ".nxr-product-shell, .nxr-executive-card, .nxr-bi-card, .nxr-bi-table-card"
    )) {
      if (!node.offsetParent) continue;
      const rect = node.getBoundingClientRect();
      if (rect.left < -1 || rect.right > width + 1) {
        overflowing.push({
          class_name: node.className,
          left: rect.left,
          right: rect.right,
          width,
        });
      }
    }
    const tabbar = document.querySelector(".nxr-shell__tabbar");
    // `.nxr-shell__tabbar` es `position: fixed`: `offsetParent` es `null` para
    // cualquier elemento de posición fija en la mayoría de motores, aunque esté
    // realmente visible — no es un indicador válido de visibilidad aquí (a
    // diferencia del resto de elementos de este archivo, ninguno fijo). Se lee
    // el estilo computado real.
    const tabbarVisible = Boolean(
      tabbar && window.getComputedStyle(tabbar).display !== "none"
    );
    const tabbarRoutes = tabbar
      ? Array.from(tabbar.querySelectorAll("[data-shell-route]")).map((node) =>
          node.getAttribute("data-shell-route")
        )
      : [];
    return {
      viewport_width: width,
      document_width: document.documentElement.scrollWidth,
      overflowing,
      tabbar_visible: tabbarVisible,
      tabbar_routes: tabbarRoutes,
    };
  });
  assert.deepEqual(
    result.overflowing,
    [],
    `Desbordamiento horizontal en ${profile.name}: ${JSON.stringify(result)}`
  );
  // NXR-UX-0014 (Bloque 16): navegación móvil inferior — visible únicamente por
  // debajo del punto de quiebre real de `nexora_shell.css` (`@media (max-width:
  // 640px)`), nunca en tableta/escritorio, con al menos un destino real
  // (reutiliza `SECTIONS`, nunca una lista de rutas propia).
  if (result.viewport_width <= 640) {
    assert(
      result.tabbar_visible,
      `La navegación móvil inferior no es visible en ${profile.name} (${result.viewport_width}px).`
    );
    assert(
      result.tabbar_routes.length > 0,
      `La navegación móvil inferior no expone ningún destino real en ${profile.name}.`
    );
  } else {
    assert(
      !result.tabbar_visible,
      `La navegación móvil inferior no debería ser visible en ${profile.name} (${result.viewport_width}px).`
    );
  }
  profile.responsive = result;
}

export async function validateRealtime(page, profile) {
  await page.waitForFunction(
    () => Boolean(window.frappe?.realtime?.socket?.connected),
    undefined,
    { timeout: 60_000 }
  );
  profile.realtime = await page.evaluate(() => ({
    connected: Boolean(window.frappe?.realtime?.socket?.connected),
    transport:
      window.frappe?.realtime?.socket?.io?.engine?.transport?.name || "unknown",
  }));
}

export async function captureFailure(page, profile, error) {
  profile.error = error?.stack || String(error);
  // Las senales de la pagina se comprueban al final del perfil, asi que un fallo
  // anterior las descarta sin mostrarlas. Publicarlas aqui es lo que convierte un
  // «Timeout» en una causa con nombre.
  console.error(`[nexora] ${profile.name} failed${describeSignals(profile)}`);
  try {
    await page.screenshot({
      path: path.join(artifactRoot, `${safeName(profile.name)}-failure.png`),
      fullPage: true,
    });
  } catch {
    // The JSON report still records the failure when screenshot capture is unavailable.
  }
}
