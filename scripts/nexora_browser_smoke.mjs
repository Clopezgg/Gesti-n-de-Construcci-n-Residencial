import assert from "node:assert/strict";
import fs from "node:fs/promises";
import path from "node:path";

import { chromium, devices, webkit } from "playwright";

import {
  adminPassword,
  apiResponse,
  artifactRoot,
  assertAuthenticated,
  assertResponseOk,
  authenticate,
  baseURL,
  browserRequest,
  describeSignals,
  gotoRoute,
  normalizedText,
  postArgs,
  routes,
  safeName,
  siteName,
  validateDirectRoutes,
  waitForRoute,
  watchPage,
} from "./nexora_browser_support.mjs";
import {
  captureFailure,
  validateClosing,
  validateCommandBar,
  validateDashboard,
  validateManifest,
  validatePwa,
  validateRealtime,
  validateReports,
  validateResponsiveLayout,
  validateShell,
} from "./nexora_browser_validators.mjs";

const demoProject = "NEXORA 0.1 — Fondo demostrativo";

assert(
  adminPassword,
  "ADMIN_PASSWORD is required for the NEXORA browser validation."
);
await fs.mkdir(artifactRoot, { recursive: true });

const report = {
  base_url: baseURL,
  site: siteName,
  started_at: new Date().toISOString(),
  profiles: [],
};

async function callFrappe(page, options) {
  const response = await postArgs(page, options.method, options.args || {});
  await assertResponseOk(response, `Frappe request ${options.method}`);
  return response.payload?.message;
}

async function replayExecution(page, response, documentNumber) {
  const body = response.request().postData();
  assert(body, "The definitive request did not expose a replayable payload.");
  const csrfToken = await page.evaluate(
    () => window.frappe?.csrf_token || window.csrf_token || ""
  );
  const replay = await browserRequest(page, response.url(), {
    method: "POST",
    headers: {
      "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
      "X-Frappe-Site-Name": siteName,
      "X-Frappe-CSRF-Token": csrfToken,
    },
    body,
  });
  await assertResponseOk(replay, "Idempotent replay request");
  assert.equal(
    String(replay.payload?.message?.document_number || ""),
    documentNumber,
    "The same definitive request generated a second document."
  );
}

/**
 * Una captura de página completa falla cuando la página mide más que el límite del motor
 * —32767 px—, y entonces el error de la captura sustituye al resultado real de la etapa:
 * el recorrido dijo «no se pudo capturar» sobre una etapa cuyo defecto era justamente que
 * la página se había vuelto gigantesca. La altura anómala se registra como dato y la
 * captura se toma de la ventana visible, que es la que se puede tomar.
 *
 * El límite del motor es en píxeles de *dispositivo*, no en píxeles CSS: un umbral fijo
 * en CSS solo es seguro en pantallas de densidad 1×. El iPhone 13 captura a 3×, así que
 * una altura CSS de apenas 11 000 px ya produce un lienzo de más de 32 767 píxeles reales
 * y el aviso de «anómalo» nunca llegaba a dispararse —el umbral fijo de 30 000 se pensó
 * para escritorio y dejaba pasar exactamente el perfil que más lo necesitaba.
 */
async function capture(page, profile, file) {
  const [height, scale] = await page.evaluate(() => [
    document.documentElement?.scrollHeight || 0,
    window.devicePixelRatio || 1,
  ]);
  const maxCssHeight = Math.floor(32_767 / scale) - 500;
  const oversized = height > maxCssHeight;
  if (oversized) {
    profile.oversized_pages = profile.oversized_pages || [];
    profile.oversized_pages.push({ file: path.basename(file), height, scale });
  }
  await page.screenshot({ path: file, fullPage: !oversized });
}

async function resolveFixtureContext(page) {
  const projectResponse = await callFrappe(page, {
    method: "frappe.client.get_value",
    args: {
      doctype: "Project",
      filters: { project_name: demoProject },
      fieldname: "name",
    },
  });
  const [entities, costCenters] = await Promise.all([
    callFrappe(page, {
      method: "frappe.client.get_list",
      args: {
        doctype: "NXR Entity",
        fields: ["name", "display_name"],
        limit_page_length: 1,
        order_by: "creation asc",
      },
    }),
    callFrappe(page, {
      method: "frappe.client.get_list",
      args: {
        doctype: "Cost Center",
        fields: ["name"],
        filters: { is_group: 0 },
        limit_page_length: 1,
        order_by: "creation asc",
      },
    }),
  ]);
  return {
    project: projectResponse?.name || "",
    entity: entities?.[0]?.name || "",
    cost_center: costCenters?.[0]?.name || "",
  };
}

async function routeFromDashboard(page, action, movementCode) {
  await page.evaluate(() => window.frappe.set_route("nexora-dashboard"));
  await waitForRoute(page, "nexora-dashboard");
  await page
    .locator(`#page-nexora-dashboard [data-action="${action}"]`)
    .first()
    .click();
  await waitForRoute(page, "nexora-operations");
  await page.waitForFunction(
    (code) =>
      document.querySelector(
        '#page-nexora-operations [data-field="movement_code"] input'
      )?.value === code,
    movementCode,
    { timeout: 60_000 }
  );
  await page
    .locator("#page-nexora-operations .nxr-guided-wizard")
    .waitFor({ state: "visible", timeout: 60_000 });
}

async function setField(page, name, value) {
  const field = page.locator(`#page-nexora-operations [data-field="${name}"]`);
  const select = field.locator("select").first();
  if (await select.count()) {
    await select.selectOption(String(value));
    return;
  }
  const control = field.locator("input:not([type='hidden']), textarea").first();
  await control.waitFor({ state: "visible", timeout: 30_000 });
  await control.fill(String(value));
  // Aquí hubo un `Escape` para cerrar la lista de sugerencias, y sobraba: la lista la
  // cierra `clickGuidedAction` antes de pulsar. Peor todavía, en un campo Link cerrar la
  // lista con Escape impide que se seleccione la opción, y Frappe descarta al perder el
  // foco lo que no llegó a validarse: el recorrido lo mostró con `project` vacío justo
  // antes de continuar. Escribir y tabular es lo que hace el usuario.
  await control.press("Tab");
  // Un campo que se queda vacío después de rellenarlo es el defecto que costó tres
  // ejecuciones: no se detecta hasta que el asistente se niega a avanzar y ya no se sabe
  // quién lo vació. Se comprueba aquí, sobre el campo, en el momento.
  //
  // En móvil el asistente reordena los campos entre contenedores al ajustar el diseño, y
  // un control de Frappe que se vuelve a pintar pierde lo escrito. Reescribir una vez es
  // lo que hace cualquiera al ver el campo en blanco; si tampoco así se queda, el fallo
  // dice si el `<input>` seguía siendo el mismo, que es lo que distingue «se repintó» de
  // «alguien lo borró».
  const matches = (stored) =>
    stored.replace(/[\s,]/g, "") === String(value).replace(/[\s,]/g, "") ||
    (Number.isFinite(Number(stored.replace(/[\s,]/g, ""))) &&
      Number(stored.replace(/[\s,]/g, "")) === Number(value));

  let stored = await control.inputValue();
  let rewritten = false;
  if (!matches(stored)) {
    rewritten = true;
    await control.fill(String(value));
    await control.press("Tab");
    stored = await control.inputValue();
  }
  assert(
    matches(stored),
    `El campo ${name} no conservó lo que se escribió: se puso «${value}» y quedó «${stored}»` +
      `${rewritten ? " incluso tras reescribirlo" : ""}.`
  );
  if (rewritten) {
    console.warn(
      `[nexora] ${name} se vació al escribirlo y hubo que reescribirlo: la pantalla se repintó encima.`
    );
  }
  written.set(name, String(value));
}

/** Lo último que se escribió en cada campo, para poder comprobarlo cuando importa. */
const written = new Map();

/**
 * Un campo puede conservar el valor al escribirlo y perderlo después: los Link de Frappe
 * validan contra el servidor y descartan lo que no llegó a confirmarse. Comprobarlo justo
 * antes de avanzar convierte «la etapa 2 nunca se abrió» en «el campo project se vació
 * entre que se escribió y el momento de continuar», que es lo que hay que corregir.
 */
async function assertWrittenFieldsHeld(page) {
  const lost = [];
  for (const [name, value] of written) {
    const input = page
      .locator(`#page-nexora-operations [data-field="${name}"]`)
      .locator("input:not([type='hidden']), textarea, select")
      .first();
    if (!(await input.count())) continue;
    const current = await input.inputValue();
    if (!current.trim()) lost.push(`${name} (se escribió «${value}»)`);
  }
  assert(
    !lost.length,
    `Estos campos se vaciaron entre que se escribieron y el momento de continuar: ${lost.join(
      ", "
    )}.`
  );
}

/**
 * Un clic sobre un botón del asistente falla por dos motivos que no son del producto:
 * la barra fija de la aplicación lo tapa por arriba, y una lista de sugerencias abierta
 * lo tapa por abajo. Ambas se resuelven centrando el botón antes de pulsarlo, que es lo
 * que hace una persona sin pensarlo.
 */
async function clickGuidedAction(page, selector) {
  const action = page.locator(`#page-nexora-operations ${selector}`);
  await action.waitFor({ state: "visible", timeout: 60_000 });
  // Quitar el foco cierra la lista de sugerencias que quedara abierta; centrar el botón
  // lo aparta de la barra fija. Ninguna de las dos cosas basta por sí sola: el registro
  // mostró el formulario de búsqueda y el «Create a new Currency» interceptando el mismo
  // clic después de centrarlo.
  await page.evaluate(() => document.activeElement?.blur?.());
  await page.waitForFunction(
    () =>
      ![
        ...document.querySelectorAll(
          "#page-nexora-operations .awesomplete > ul"
        ),
      ].some((list) => list.offsetParent),
    null,
    { timeout: 30_000 }
  );
  await action.evaluate((node) =>
    node.scrollIntoView({ block: "center", inline: "nearest" })
  );
  // Un clic del ratón espera solo a que el botón esté habilitado; `focus` + `Enter` no
  // espera nada, y sobre un botón deshabilitado no hace absolutamente nada. Así se pasó
  // una ejecución entera: el registro definitivo nunca se pidió y el fallo llegó como un
  // tiempo de espera agotado en la llamada, no en el botón que no respondía.
  try {
    await page.waitForFunction(
      (css) => {
        const node = document.querySelector(`#page-nexora-operations ${css}`);
        return (
          Boolean(node) &&
          !node.disabled &&
          node.getAttribute("aria-disabled") !== "true"
        );
      },
      selector,
      { timeout: 60_000 }
    );
  } catch (error) {
    throw new Error(
      `El botón «${selector}» seguía deshabilitado a los 60 s: la pantalla no lo habilitó.`,
      { cause: error }
    );
  }
  // Y se pulsa con el teclado. Un clic del ratón lo puede tapar cualquier cosa que se
  // dibuje encima; `Enter` sobre el botón enfocado activa el mismo manejador sin que
  // nada pueda interponerse, y es como opera quien no usa ratón (Capítulo 37).
  await action.focus();
  await action.press("Enter");
}

async function waitForGuidedStage(page, stage, profile) {
  const locator = page.locator(
    `#page-nexora-operations [data-guided-stage="${stage}"]`
  );
  try {
    await locator.waitFor({ state: "visible", timeout: 60_000 });
  } catch (error) {
    const diagnostics = await guidedReviewDiagnostics(page);
    throw new Error(
      `Guided stage ${stage} never opened: ${JSON.stringify(
        diagnostics
      )}${describeSignals(profile)}`,
      { cause: error }
    );
  }
  return locator;
}

async function waitForOperationalQuiescence(page) {
  await page.waitForLoadState("networkidle", { timeout: 60_000 });
  await page.waitForFunction(
    () => {
      const freeze = document.querySelector(".freeze");
      return (
        !freeze ||
        freeze.hidden ||
        window.getComputedStyle(freeze).display === "none"
      );
    },
    null,
    { timeout: 60_000 }
  );
}

/**
 * Devuelve, campo por campo, el estado que la espera de abajo resume en un solo
 * booleano. Sin esto el rojo dice «Timeout» y no distingue entre «el servidor
 * aprobo pero la consola no habilito el boton», «la revision quedo vacia» y «el
 * asistente retrocedio de etapa»: tres causas con tres correcciones distintas.
 */
async function guidedReviewDiagnostics(page) {
  return page.evaluate(() => {
    const root = document.querySelector("#page-nexora-operations");
    const text = (node) =>
      String(node?.textContent || "")
        .replace(/\s+/g, " ")
        .trim()
        .slice(0, 300);
    const flag = (node, read) => (node ? read(node) : "missing");
    const stage = root?.querySelector('[data-guided-stage="3"]');
    const next = root?.querySelector('[data-guided-next="4"]');
    const original = root?.querySelector(".nxr-execute-movement");
    const preview = root?.querySelector(".nxr-preview-body");
    return {
      visible_stages: [...(root?.querySelectorAll("[data-guided-stage]") || [])]
        .filter((node) => !node.hidden)
        .map((node) => node.dataset.guidedStage),
      review_stage_hidden: flag(stage, (node) => node.hidden),
      continue_button_disabled: flag(next, (node) => node.disabled),
      console_execute_disabled: flag(original, (node) => node.disabled),
      preview_still_empty: flag(preview, (node) =>
        node.classList.contains("nxr-empty")
      ),
      preview_text: text(preview),
      validation_summary: text(root?.querySelector(".nxr-validation-summary")),
      action_status: text(root?.querySelector(".nxr-action-status")),
      // Quién anuló la vista previa: «la información cambió» no dice si la cambió el
      // usuario o la propia pantalla al refrescarse.
      preview_invalidated_by:
        root?.querySelector(".nxr-operational-shell")?.dataset
          .previewInvalidatedBy ?? "still-valid",
      // Qué dato principal falta cuando el asistente se niega a avanzar, y con qué
      // valor quedó cada uno: un campo que la pantalla vaciló y vació se ve aquí.
      guided_missing:
        root?.querySelector(".nxr-guided-wizard")?.dataset.guidedMissing ??
        "not-evaluated",
      primary_values: Object.fromEntries(
        [
          "document_date",
          "project",
          "origin_or_sender",
          "beneficiary",
          "description",
          "channel",
          "currency",
          "original_amount",
          "amount_hnl",
        ].map((name) => [
          name,
          root?.querySelector(
            `[data-field="${name}"] input, [data-field="${name}"] select`
          )?.value ?? "absent",
        ])
      ),
    };
  });
}

async function advanceValidatedGuidedReview(page, label, profile) {
  try {
    await waitForValidatedGuidedReview(page);
  } catch (error) {
    const diagnostics = await guidedReviewDiagnostics(page);
    throw new Error(
      `${label} review never became valid: ${JSON.stringify(
        diagnostics
      )}${describeSignals(profile)}`,
      { cause: error }
    );
  }
  const next = page.locator('#page-nexora-operations [data-guided-next="4"]');
  assert.equal(await next.isVisible(), true, `${label} review is not visible.`);
  assert.equal(await next.isEnabled(), true, `${label} review is not valid.`);
  await clickGuidedAction(page, '[data-guided-next="4"]');
  await waitForGuidedStage(page, 4, profile);
}

async function waitForValidatedGuidedReview(page) {
  await page.waitForFunction(
    (stableForMs) => {
      const stage = document.querySelector(
        '#page-nexora-operations [data-guided-stage="3"]'
      );
      const next = document.querySelector(
        '#page-nexora-operations [data-guided-next="4"]'
      );
      const original = document.querySelector(
        "#page-nexora-operations .nxr-execute-movement"
      );
      const preview = document.querySelector(
        "#page-nexora-operations .nxr-preview-body"
      );
      const valid = Boolean(
        stage &&
          !stage.hidden &&
          next &&
          !next.disabled &&
          original &&
          !original.disabled &&
          preview &&
          !preview.classList.contains("nxr-empty")
      );
      const signature = [
        valid,
        stage?.hidden,
        next?.disabled,
        original?.disabled,
        preview?.classList.contains("nxr-empty"),
        preview?.textContent,
      ].join("|");
      const now = performance.now();
      const probe = window.__nexoraGuidedReviewProbe;
      if (!probe || probe.signature !== signature) {
        window.__nexoraGuidedReviewProbe = { signature, since: now };
        return false;
      }
      return valid && now - probe.since >= stableForMs;
    },
    750,
    { polling: 100, timeout: 60_000 }
  );
}

async function assertGuidedSurface(page, movementCode) {
  const root = page.locator("#page-nexora-operations");
  assert.equal(
    await root.locator(".nxr-guided-progress [data-guided-go]").count(),
    4,
    "The guided operation does not expose four stages."
  );
  const visibleText = await root.locator(".nxr-guided-wizard").innerText();
  for (const expected of [
    "Datos principales",
    "Datos necesarios",
    "Revisión",
    "Registro definitivo",
    "Opciones avanzadas",
  ]) {
    assert(
      visibleText.includes(expected),
      `The guided operation is missing ${expected}.`
    );
  }
  for (const technical of [
    "Usar cuenta existente",
    "Crear cuenta nueva",
    "Datos manuales, no guardar",
  ]) {
    assert(
      !visibleText.includes(technical),
      `Technical account label remained visible: ${technical}`
    );
  }
  assert.equal(
    await root.locator(".nxr-guided-advanced").getAttribute("open"),
    null,
    "Advanced options must be closed initially."
  );
  assert.equal(
    await root.locator(".nxr-preview-movement").count(),
    1,
    "Canonical preview button is missing."
  );
  assert.equal(
    await root.locator(".nxr-execute-movement").count(),
    1,
    "Canonical execution button is missing."
  );
  assert.equal(
    await root.locator('[data-field="movement_code"] input').inputValue(),
    movementCode
  );
}

async function validateIncomeGuided(page, fixtures, profile, name) {
  written.clear();
  await routeFromDashboard(page, "income", "101");
  await assertGuidedSurface(page, "101");
  await setField(page, "project", fixtures.project);
  await setField(page, "origin_or_sender", `Ingreso navegador ${name}`);
  await setField(page, "channel", "Cash");
  await setField(page, "currency", "HNL");
  await setField(page, "original_amount", "125.50");

  const senderBefore = await page
    .locator('#page-nexora-operations [data-field="origin_or_sender"] input')
    .inputValue();
  await assertWrittenFieldsHeld(page);
  await clickGuidedAction(page, '[data-guided-next="2"]');
  await waitForGuidedStage(page, 2, profile);
  const accountText = await page
    .locator("#page-nexora-operations .nxr-human-account-selector")
    .innerText();
  assert(accountText.includes("Cuenta para esta operación"));
  assert(
    accountText.includes(
      "¿Desea guardar esta cuenta para utilizarla nuevamente?"
    )
  );
  await page
    .locator(
      '#page-nexora-operations [name="nxr-guided-save-account"][value="no"]'
    )
    .check();
  assert.equal(
    await page
      .locator('#page-nexora-operations [data-field="account_mode"] select')
      .inputValue(),
    "Manual"
  );

  const advanced = page.locator("#page-nexora-operations .nxr-guided-advanced");
  await advanced.locator("summary").click();
  assert.equal(
    await page
      .locator('#page-nexora-operations [data-field="origin_or_sender"] input')
      .inputValue(),
    senderBefore,
    "Opening advanced options erased guided data."
  );
  await advanced.locator("summary").click();

  await waitForOperationalQuiescence(page);
  const previewResponsePromise = apiResponse(
    page,
    "preview_operational_movement",
    "vista previa del ingreso"
  );
  await clickGuidedAction(page, ".nxr-guided-preview");
  const previewResponse = await previewResponsePromise;
  await assertResponseOk(previewResponse, "Income preview request");
  await advanceValidatedGuidedReview(page, "Income", profile);

  const executeResponsePromise = apiResponse(
    page,
    "execute_operational_movement",
    "registro definitivo del ingreso"
  );
  await clickGuidedAction(page, ".nxr-guided-execute");
  const executeResponse = await executeResponsePromise;
  await assertResponseOk(executeResponse, "Income execution request");
  const result = await executeResponse.json();
  const documentNumber = String(result?.message?.document_number || "");
  const operation = String(result?.message?.operation || "");
  assert.match(documentNumber, /^\d{12}$/);
  assert(operation, "Income execution returned no operation identifier.");
  await replayExecution(page, executeResponse, documentNumber);
  await capture(
    page,
    profile,
    path.join(artifactRoot, `${safeName(name)}-guided-income.png`)
  );
  profile.guided_income = {
    route: "nexora-operations",
    engine: "101",
    operation,
    document_number: documentNumber,
    account_choice: "one-time",
    idempotent_replay: true,
    stages: 4,
  };
}

async function validateExpenseGuided(page, fixtures, profile, name) {
  assert(fixtures.entity, "NEXORA seed created no beneficiary entity.");
  assert(fixtures.cost_center, "ERPNext created no leaf cost center.");
  written.clear();
  await routeFromDashboard(page, "expense", "102");
  await assertGuidedSurface(page, "102");
  await setField(page, "project", fixtures.project);
  await setField(page, "beneficiary", fixtures.entity);
  await setField(page, "description", `Pago navegador ${name}`);
  await setField(page, "amount_hnl", "75.25");
  // El gasto no pregunta moneda ni tasa: se paga desde un fondo en lempiras y el
  // importe ya es `amount_hnl`. La pantalla oculta `currency` para el codigo 102
  // (`toggle("currency", income, false)`), asi que pedirla aqui era llenar un campo
  // que el usuario nunca ve.
  await assertWrittenFieldsHeld(page);
  await clickGuidedAction(page, '[data-guided-next="2"]');
  await waitForGuidedStage(page, 2, profile);
  await setField(page, "payment_method", "Cash");
  await setField(page, "economic_category", "CONSTRUCTION_MATERIALS");
  await setField(page, "cost_center", fixtures.cost_center);
  const allocation = page
    .locator("#page-nexora-operations .nxr-source-amount")
    .first();
  await allocation.waitFor({ state: "visible", timeout: 60_000 });
  await allocation.fill("75.25");
  await allocation.press("Tab");

  await waitForOperationalQuiescence(page);
  const previewResponsePromise = apiResponse(
    page,
    "preview_operational_movement",
    "vista previa del gasto"
  );
  await clickGuidedAction(page, ".nxr-guided-preview");
  const previewResponse = await previewResponsePromise;
  await assertResponseOk(previewResponse, "Expense preview request");
  await waitForGuidedStage(page, 3, profile);
  const reviewText = await page
    .locator("#page-nexora-operations .nxr-guided-review")
    .innerText();
  for (const label of ["Saldo anterior", "Saldo posterior", "Importe"]) {
    assert(reviewText.includes(label), `Expense review is missing ${label}.`);
  }
  await advanceValidatedGuidedReview(page, "Expense", profile);

  const executeResponsePromise = apiResponse(
    page,
    "execute_operational_movement",
    "registro definitivo del gasto"
  );
  await clickGuidedAction(page, ".nxr-guided-execute");
  const executeResponse = await executeResponsePromise;
  await assertResponseOk(executeResponse, "Expense execution request");
  const result = await executeResponse.json();
  const documentNumber = String(result?.message?.document_number || "");
  const operation = String(result?.message?.operation || "");
  assert.match(documentNumber, /^\d{12}$/);
  assert(operation, "Expense execution returned no operation identifier.");
  assert.notEqual(
    documentNumber,
    profile.guided_income.document_number,
    "Income and expense received the same document number."
  );
  await replayExecution(page, executeResponse, documentNumber);
  // NXR-UX-0012 (Bloque 16): resultado explicable — el panel
  // `.nxr-operational-result` (junto a, no en lugar de, la vista previa) debe
  // mostrar el documento real y el saldo anterior/posterior por fuente que
  // `execute_operational_movement` ya devolvió, sin inventar ningún cálculo
  // nuevo en el cliente. Se afirma después de que la ejecución ya tuvo éxito
  // (más arriba), nunca dentro de la espera de la etapa guiada ya conocida
  // como intermitente.
  const resultPanel = page.locator(
    "#page-nexora-operations .nxr-operational-result"
  );
  await resultPanel.waitFor({ state: "visible", timeout: 30_000 });
  const resultText = await resultPanel.innerText();
  assert(
    resultText.includes(documentNumber),
    "Expense result panel did not show the real document number."
  );
  for (const label of ["Saldo anterior", "Saldo posterior", "Importe"]) {
    assert(
      resultText.includes(label),
      `Expense result panel is missing ${label}.`
    );
  }
  await capture(
    page,
    profile,
    path.join(artifactRoot, `${safeName(name)}-guided-expense.png`)
  );
  profile.guided_expense = {
    route: "nexora-operations",
    engine: "102",
    operation,
    document_number: documentNumber,
    allocation: "single-fund",
    idempotent_replay: true,
    stages: 4,
    result_panel_verified: true,
  };
}

async function validateGuidedOperations(page, profile, name) {
  const fixtures = await resolveFixtureContext(page);
  assert(fixtures.project, `Demo project not found: ${demoProject}`);
  await validateIncomeGuided(page, fixtures, profile, name);
  await validateExpenseGuided(page, fixtures, profile, name);
  profile.guided_operations = {
    project: fixtures.project,
    shared_route: true,
    shared_preview_service: true,
    shared_execute_service: true,
    technical_account_labels_visible: false,
  };
}

async function validateUniversalSearch(page, context, profile, name) {
  const documentNumber = profile.guided_expense.document_number;
  await gotoRoute(page, context, profile, "nexora-search");
  const searchPage = page.locator("#page-nexora-search");
  const query = searchPage.locator('[data-fieldname="query"] input').first();
  await query.waitFor({ state: "visible", timeout: 60_000 });
  await query.fill(documentNumber);
  const searchResponsePromise = apiResponse(
    page,
    "universal_search_consolidated",
    "búsqueda universal"
  );
  await query.press("Enter");
  const searchResponse = await searchResponsePromise;
  await assertResponseOk(searchResponse, "Universal search request");
  // En el ancho del teléfono la pantalla oculta la tabla y muestra tarjetas a propósito
  // (Capítulo 37). Exigir la fila visible hacía fallar el perfil de iPhone sobre un
  // diseño correcto: la fila existía y estaba oculta. Se acepta la representación que el
  // usuario tiene delante, sea cual sea; las tarjetas copian el contenido de la celda,
  // así que el enlace al detalle sigue dentro.
  const row = searchPage
    .locator(
      ".nxr-search-results tbody tr:visible, " +
        ".nxr-search-results .nxr-mobile-cards article:visible"
    )
    .filter({ hasText: documentNumber })
    .first();
  await row.waitFor({ state: "visible", timeout: 60_000 });

  const detailResponsePromise = apiResponse(
    page,
    "get_search_result_detail",
    "detalle del resultado de búsqueda"
  );
  const detailLink = row.locator("[data-search-doctype]").first();
  await detailLink.evaluate((node) =>
    node.scrollIntoView({ block: "center", inline: "nearest" })
  );
  await detailLink.click();
  const detailResponse = await detailResponsePromise;
  await assertResponseOk(detailResponse, "Consolidated search detail request");
  const detail = searchPage.locator(".nxr-search-detail-body");
  await detail
    .getByText(documentNumber, { exact: true })
    .waitFor({ state: "visible", timeout: 60_000 });
  assert(
    (await detail.innerText()).includes("Efecto financiero"),
    "Consolidated search detail omitted the financial effect."
  );
  await capture(
    page,
    profile,
    path.join(artifactRoot, `${safeName(name)}-universal-search.png`)
  );
  profile.universal_search = {
    query: documentNumber,
    result: "NXR Operation",
    consolidated_financial_effect: true,
  };
}

async function clickRegisteredAction(page, label) {
  await page.waitForFunction(
    (expected) =>
      [
        ...document.querySelectorAll(".page-actions button, .page-actions a"),
      ].some((element) => element.textContent?.trim() === expected),
    label,
    { timeout: 60_000 }
  );
  await page.evaluate((expected) => {
    const action = [
      ...document.querySelectorAll(".page-actions button, .page-actions a"),
    ].find((element) => element.textContent?.trim() === expected);
    if (!action) throw new Error(`Action not found: ${expected}`);
    action.click();
  }, label);
}

async function fillDialogField(dialog, fieldname, value) {
  const control = dialog
    .locator(
      `.frappe-control[data-fieldname="${fieldname}"] input, ` +
        `.frappe-control[data-fieldname="${fieldname}"] textarea`
    )
    .first();
  await control.waitFor({ state: "visible", timeout: 30_000 });
  await control.fill(value);
  await control.press("Tab");
}

/**
 * El botón principal de un diálogo de Frappe nace habilitado, pero el diálogo puede
 * quedarse validando y desactivarlo. Pulsar un botón deshabilitado no hace nada y el
 * fallo aparece 120 s después en la llamada que nunca se pidió, no en el botón mudo.
 */
async function clickDialogPrimary(dialog, page, label) {
  const action = dialog.locator(".modal-footer .btn-primary").last();
  await action.waitFor({ state: "visible", timeout: 60_000 });
  try {
    await action.evaluate(
      (node) =>
        new Promise((resolve, reject) => {
          const deadline = Date.now() + 60_000;
          const check = () => {
            if (!node.disabled && node.getAttribute("aria-disabled") !== "true")
              return resolve(true);
            if (Date.now() > deadline) return reject(new Error("disabled"));
            setTimeout(check, 200);
          };
          check();
        })
    );
  } catch (error) {
    throw new Error(
      `El botón «${label}» del diálogo seguía deshabilitado a los 60 s.`,
      { cause: error }
    );
  }
  await action.scrollIntoViewIfNeeded();
  await action.click();
}

async function openOperationForm(page, operation) {
  await page.evaluate(
    ({ doctype, name }) => {
      // Misma guarda que `gotoRoute`: sin ella, un router ausente sale como un
      // `TypeError` dentro de `page.evaluate` que no nombra su causa.
      if (!window.frappe?.set_route) {
        throw new Error("Frappe SPA router is unavailable.");
      }
      window.frappe.set_route("Form", doctype, name);
    },
    { doctype: "NXR Operation", name: operation }
  );
  await page.waitForFunction(
    (name) =>
      window.cur_frm?.doctype === "NXR Operation" &&
      window.cur_frm?.docname === name &&
      !window.cur_frm?.is_new?.(),
    operation,
    { timeout: 120_000 }
  );
}

async function validateControlledCorrection(page, profile, name) {
  const expense = profile.guided_expense;
  await openOperationForm(page, expense.operation);
  const original = await page.evaluate(() => ({
    document_number: String(window.cur_frm.doc.document_number || ""),
    amount_hnl: String(window.cur_frm.doc.amount_hnl || ""),
  }));
  assert.equal(original.document_number, expense.document_number);
  await clickRegisteredAction(page, "Anular operación");

  const dialog = page
    .locator(".modal.show .modal-dialog")
    .filter({ hasText: "Anular operación" })
    .last();
  await dialog.waitFor({ state: "visible", timeout: 60_000 });
  await fillDialogField(dialog, "requester", "nexora.operator@example.test");
  await fillDialogField(dialog, "approved_by", "nexora.manager@example.test");
  await fillDialogField(
    dialog,
    "reason",
    `Anulación validada en navegador real ${name}`
  );

  const previewResponsePromise = apiResponse(
    page,
    "preview_operational_movement",
    "vista previa de la corrección"
  );
  await clickDialogPrimary(dialog, page, "Anular operación · vista previa");
  const previewResponse = await previewResponsePromise;
  await assertResponseOk(
    previewResponse,
    "Controlled correction preview request"
  );
  await dialog
    .getByText("El original no será eliminado ni sobrescrito.", {
      exact: true,
    })
    .waitFor({ state: "visible", timeout: 60_000 });

  const executeResponsePromise = apiResponse(
    page,
    "execute_operational_movement",
    "registro definitivo de la corrección"
  );
  await clickDialogPrimary(dialog, page, "Anular operación · registro");
  const executeResponse = await executeResponsePromise;
  await assertResponseOk(
    executeResponse,
    "Controlled correction execution request"
  );
  const result = await executeResponse.json();
  const correctionDocument = String(result?.message?.document_number || "");
  assert.match(correctionDocument, /^\d{12}$/);
  assert.notEqual(
    correctionDocument,
    original.document_number,
    "Correction reused the original document number."
  );
  await page.waitForFunction(
    ({ documentNumber, amount }) =>
      String(window.cur_frm?.doc?.document_number || "") === documentNumber &&
      String(window.cur_frm?.doc?.amount_hnl || "") === amount &&
      String(window.cur_frm?.doc?.status || "").startsWith("Compensated"),
    { documentNumber: original.document_number, amount: original.amount_hnl },
    { timeout: 120_000 }
  );
  await capture(
    page,
    profile,
    path.join(artifactRoot, `${safeName(name)}-controlled-correction.png`)
  );
  profile.controlled_correction = {
    original_document_number: original.document_number,
    correction_document_number: correctionDocument,
    segregation: "requester-approver-executor",
    original_preserved: true,
  };
}

/**
 * Capítulo 53: «Como mínimo: crear, editar, consultar, aprobar, rechazar, anular,
 * corregir y exportar.» El recorrido ya cubría crear (asistente), consultar (búsqueda
 * universal) y anular (movimiento 303). Lo que sigue recorre las cinco restantes sobre
 * la pantalla donde el producto las ofrece de verdad, no sobre una simulación.
 *
 * Dos de ellas no tienen la forma ingenua que sugiere su nombre, y conviene decirlo
 * aquí en vez de dejar que el lector lo deduzca:
 *
 * - **Editar** un documento contabilizado no existe y no debe existir: el libro es
 *   inmutable. El producto responde con la corrección auditada, que conserva el
 *   original y registra el antes y el después. Recorrer «editar» es, por tanto,
 *   comprobar las dos mitades: que la pantalla se niega a editar en sitio —y lo dice—
 *   y que el camino que sí ofrece cambia el dato de verdad.
 * - **Aprobar** y **rechazar** viven en el expediente documental: un comprobante se
 *   valida o se rechaza, y solo entonces puede sustituirse por una versión nueva.
 */
async function validateAccountedCorrection(page, profile, name) {
  const income = profile.guided_income;
  await openOperationForm(page, income.operation);

  // Primera mitad de «editar»: la negativa. Sin comprobarla, el recorrido demostraría
  // que la corrección funciona pero no que el atajo esté cerrado, que es justo lo que
  // protege la auditoría (Capítulos 20 y 39).
  //
  // El aviso se busca por lo que el usuario lee, no por el contenedor donde Frappe
  // decide pintarlo: un cambio de clase en el marco convertiría una advertencia visible
  // en un rojo que culpa al producto. `innerText` solo devuelve texto visible, que es
  // exactamente la condición que interesa.
  const refusal = await page.evaluate(() => {
    const shown = String(document.body.innerText || "");
    const formMessage = String(
      document.querySelector(".form-message")?.textContent || ""
    );
    return {
      warns_in_place_edit: shown.includes("No edite sus campos directamente"),
      // Si el aviso vive en otro contenedor —el caso que motiva mirar el texto visible—,
      // leer solo `.form-message` diría «(ninguno)» y dejaría el fallo sin pista. La
      // reserva es lo que el usuario tiene delante.
      intro_sample: (formMessage || shown.slice(0, 200))
        .replace(/\s+/g, " ")
        .trim(),
      save_disabled: Boolean(window.cur_frm?.save_disabled),
      read_only_fields: ["operation_date", "amount", "exchange_rate", "project"]
        .filter((fieldname) =>
          Boolean(window.cur_frm?.get_docfield?.(fieldname)?.read_only)
        )
        .sort(),
    };
  });
  assert(
    refusal.warns_in_place_edit,
    `El documento contabilizado no advirtió al usuario que no se edita en sitio; el aviso visible decía «${
      refusal.intro_sample || "(ninguno)"
    }».`
  );
  assert(
    refusal.save_disabled,
    "El documento contabilizado seguía permitiendo guardar cambios directos."
  );
  assert.deepEqual(
    refusal.read_only_fields,
    ["amount", "exchange_rate", "operation_date", "project"],
    "El documento contabilizado dejó campos financieros editables en sitio."
  );

  // Segunda mitad: el camino que sí existe. El diálogo se abre con el número puesto y
  // busca el documento solo, así que la espera se arma antes de pulsar.
  const lookupResponsePromise = apiResponse(
    page,
    "get_operation_for_correction",
    "carga del documento a corregir"
  );
  await clickRegisteredAction(page, "Corregir fecha o datos");
  const lookupResponse = await lookupResponsePromise;
  await assertResponseOk(lookupResponse, "Accounted correction lookup request");

  const dialog = page
    .locator(".modal.show .modal-dialog")
    .filter({ hasText: "Corregir operación contabilizada" })
    .last();
  await dialog.waitFor({ state: "visible", timeout: 60_000 });
  await dialog
    .locator(".alert")
    .filter({ hasText: income.document_number })
    .first()
    .waitFor({ state: "visible", timeout: 60_000 });

  const correctedSender = `Ingreso corregido ${name}`;
  await fillDialogField(dialog, "origin_or_sender", correctedSender);
  await fillDialogField(dialog, "source_name", correctedSender);
  await fillDialogField(
    dialog,
    "reason",
    `Corrección de datos validada en navegador real ${name}`
  );

  const previewResponsePromise = apiResponse(
    page,
    "preview_operation_correction",
    "vista previa de la corrección de datos"
  );
  await clickDialogPrimary(dialog, page, "Corregir datos · vista previa");
  const previewResponse = await previewResponsePromise;
  await assertResponseOk(
    previewResponse,
    "Accounted correction preview request"
  );
  await dialog
    .getByText("Diferencia financiera", { exact: false })
    .first()
    .waitFor({ state: "visible", timeout: 60_000 });

  const executeResponsePromise = apiResponse(
    page,
    "execute_operation_correction",
    "aplicación de la corrección de datos"
  );
  await clickDialogPrimary(dialog, page, "Corregir datos · aplicar");
  const executeResponse = await executeResponsePromise;
  await assertResponseOk(
    executeResponse,
    "Accounted correction execution request"
  );
  const result = await executeResponse.json();
  const correctionDocument = String(
    result?.message?.correction_document_number || ""
  );
  assert.equal(
    String(result?.message?.document_number || ""),
    income.document_number,
    "La corrección se aplicó sobre un documento distinto del ingreso recorrido."
  );
  assert.match(correctionDocument, /^\d{12}$/);
  assert.notEqual(
    correctionDocument,
    income.document_number,
    "La corrección reutilizó el número del documento original."
  );

  // Que el servidor conteste no significa que el dato haya cambiado para quien lo
  // consulta después: se vuelve a leer el documento por su número.
  const effective = await callFrappe(page, {
    method: "nexora.financial.service.get_operation_for_correction",
    args: { document: income.document_number },
  });
  assert.equal(
    String(effective?.origin_or_sender || ""),
    correctedSender,
    `El documento corregido seguía mostrando «${
      effective?.origin_or_sender || ""
    }» en vez de «${correctedSender}».`
  );
  await capture(
    page,
    profile,
    path.join(artifactRoot, `${safeName(name)}-accounted-correction.png`)
  );
  profile.accounted_correction = {
    document_number: income.document_number,
    correction_document_number: correctionDocument,
    in_place_edit_refused: true,
    corrected_field: "origin_or_sender",
    corrected_value: correctedSender,
  };
}

/**
 * El comprobante exige archivo privado real: el servidor comprueba que el `File` existe,
 * que es privado y que su contenido no está vacío (`_file_snapshot`).
 *
 * El archivo se sube por el mismo `upload_file` que usa el cargador de Frappe, con la
 * sesión viva del navegador. Lo que el Capítulo 53 manda recorrer son las ocho
 * operaciones del producto —registrar, consultar, aprobar, sustituir, rechazar—, y esas
 * se hacen aquí pulsando los botones de la pantalla; el selector de ficheros es del
 * marco, no de NEXORA, y conducirlo a ciegas solo añadiría una causa de fallo ajena.
 */
async function uploadPrivateFile(page, fileName, contents) {
  const csrfToken = await page.evaluate(
    () => window.frappe?.csrf_token || window.csrf_token || ""
  );
  const response = await browserRequest(page, "/api/method/upload_file", {
    method: "POST",
    headers: { "X-Frappe-CSRF-Token": csrfToken },
    multipart: {
      file: {
        name: fileName,
        mimeType: "text/plain",
        buffer: Buffer.from(contents, "utf-8"),
      },
      file_name: fileName,
      is_private: "1",
      folder: "Home/Attachments",
    },
  });
  await assertResponseOk(response, `Private upload of ${fileName}`);
  const fileUrl = String(response.payload?.message?.file_url || "");
  assert(
    fileUrl.startsWith("/private/files/"),
    `El archivo quedó en «${fileUrl}» y el comprobante exige almacenamiento privado.`
  );
  return fileUrl;
}

async function setEvidenceField(page, fieldname, value) {
  const control = page.locator(
    `#page-nexora-evidence .frappe-control[data-fieldname="${fieldname}"]`
  );
  const select = control.locator("select").first();
  if (await select.count()) {
    await select.selectOption(String(value));
    return;
  }
  const input = control.locator("input:not([type='hidden'])").first();
  await input.waitFor({ state: "visible", timeout: 60_000 });
  await input.fill(String(value));
  await input.press("Tab");
  const stored = await input.inputValue();
  assert.equal(
    stored,
    String(value),
    `El campo ${fieldname} del comprobante no conservó «${value}»: quedó «${stored}».`
  );
}

/**
 * El archivo privado se pone en el control `Attach` por su API porque un `Attach` no
 * tiene caja de texto donde escribir: su valor lo fija el cargador. El resto de la
 * pantalla se opera escribiendo y pulsando, como cualquiera.
 */
async function setEvidenceAttachment(page, fieldname, fileUrl) {
  const outcome = await page.evaluate(
    async ({ fieldname, fileUrl }) => {
      const wrapper =
        document.querySelector("#page-nexora-evidence") ||
        window.frappe?.pages?.["nexora-evidence"];
      const pageObject =
        wrapper?.page || window.frappe?.pages?.["nexora-evidence"]?.page;
      if (!pageObject?.fields_dict) {
        return { applied: false, reason: "la pantalla no expone sus campos" };
      }
      const control = pageObject.fields_dict[fieldname];
      if (!control) {
        return {
          applied: false,
          reason: `no existe el campo ${fieldname}; hay ${Object.keys(
            pageObject.fields_dict
          ).join(", ")}`,
        };
      }
      await control.set_value(fileUrl);
      return { applied: true, value: String(control.get_value() || "") };
    },
    { fieldname, fileUrl }
  );
  assert(
    outcome.applied,
    `No se pudo adjuntar «${fileUrl}» en ${fieldname}: ${outcome.reason}.`
  );
  assert.equal(
    outcome.value,
    fileUrl,
    `El adjunto ${fieldname} quedó en «${outcome.value}» en vez de «${fileUrl}».`
  );
}

async function registerEvidence(page, { fileUrl, supersedes = "" }, label) {
  await setEvidenceAttachment(page, "file_url", fileUrl);
  if (supersedes) await setEvidenceField(page, "supersedes", supersedes);
  const responsePromise = apiResponse(
    page,
    "register_evidence",
    `registro del comprobante ${label}`
  );
  await clickRegisteredAction(page, "Registrar comprobante");
  const response = await responsePromise;
  await assertResponseOk(response, `Evidence registration (${label})`);
  const result = (await response.json())?.message || {};
  assert.match(
    String(result.document_number || ""),
    /^\d{12}$/,
    `El comprobante ${label} no recibió número de documento.`
  );
  assert(result.evidence, `El comprobante ${label} no devolvió identificador.`);
  return {
    evidence: String(result.evidence),
    document_number: String(result.document_number),
    version: Number(result.version),
    status: String(result.status || ""),
  };
}

async function reviewEvidence(page, decision, label) {
  const button = page
    .locator(
      `#page-nexora-evidence .nxr-review-fields .nxr-ds-btn--${
        decision === "Validated" ? "success" : "danger"
      }`
    )
    .first();
  await button.waitFor({ state: "visible", timeout: 60_000 });
  await button.evaluate((node) =>
    node.scrollIntoView({ block: "center", inline: "nearest" })
  );
  const responsePromise = apiResponse(
    page,
    "review_evidence",
    `decisión «${label}» sobre el comprobante`
  );
  await button.click();
  const response = await responsePromise;
  await assertResponseOk(response, `Evidence review (${label})`);
  const result = (await response.json())?.message || {};
  assert.equal(
    String(result.status || ""),
    decision,
    `La decisión «${label}» dejó el comprobante en «${result.status}».`
  );
  return String(result.document_number || "");
}

/** Consultar: el documento tiene que aparecer donde el usuario mira, sea tabla o tarjeta. */
async function assertEvidenceListed(page, documentNumber) {
  const listed = page
    .locator(
      "#page-nexora-evidence .nxr-evidence-rows tbody tr:visible, " +
        "#page-nexora-evidence .nxr-evidence-rows .nxr-mobile-cards article:visible"
    )
    .filter({ hasText: documentNumber })
    .first();
  try {
    await listed.waitFor({ state: "visible", timeout: 60_000 });
  } catch (error) {
    // Leer la lista para el diagnóstico puede fallar por lo mismo que acaba de fallar la
    // espera. Si eso ocurre, el error de Playwright sustituiría al mensaje que nombra el
    // comprobante: el diagnóstico se perdería justo cuando hace falta.
    let rendered = "(la lista no se pudo leer)";
    try {
      rendered = normalizedText(
        await page
          .locator("#page-nexora-evidence .nxr-evidence-rows")
          .innerText({ timeout: 5_000 })
      );
    } catch {
      // Se conserva el texto de reserva: el error útil es el original.
    }
    throw new Error(
      `El comprobante ${documentNumber} no apareció en la lista; se veía: «${rendered.slice(
        0,
        300
      )}».`,
      { cause: error }
    );
  }
}

async function validateEvidenceLifecycle(page, context, profile, name) {
  const fixtures = await resolveFixtureContext(page);
  assert(fixtures.project, `Demo project not found: ${demoProject}`);
  await gotoRoute(page, context, profile, "nexora-evidence");
  await page
    .locator("#page-nexora-evidence .nxr-evidence-review")
    .waitFor({ state: "visible", timeout: 120_000 });

  await setEvidenceField(page, "project", fixtures.project);
  await setEvidenceField(page, "evidence_kind", "Payment Proof");
  await setEvidenceField(page, "channel", "WhatsApp");

  // Crear.
  const firstUrl = await uploadPrivateFile(
    page,
    `nexora-comprobante-${safeName(name)}-v1.txt`,
    `Comprobante original del recorrido ${name}.`
  );
  const first = await registerEvidence(page, { fileUrl: firstUrl }, "original");
  assert.equal(
    first.version,
    1,
    "El primer comprobante no nació en versión 1."
  );
  assert.equal(first.status, "Uploaded");

  // Consultar.
  await assertEvidenceListed(page, first.document_number);

  // Aprobar.
  const approved = await reviewEvidence(page, "Validated", "Validar");
  assert.equal(approved, first.document_number);

  // Editar: la versión nueva sustituye a la anterior sin borrarla. Un archivo distinto
  // es obligatorio —el servidor rechaza sustituir por el mismo contenido—, que es
  // exactamente lo que significa corregir un documento y conservar el historial.
  const secondUrl = await uploadPrivateFile(
    page,
    `nexora-comprobante-${safeName(name)}-v2.txt`,
    `Comprobante corregido del recorrido ${name}: importe y fecha revisados.`
  );
  const second = await registerEvidence(
    page,
    { fileUrl: secondUrl, supersedes: first.evidence },
    "sustituto"
  );
  assert.equal(
    second.version,
    2,
    `La sustitución quedó en versión ${second.version} en vez de 2.`
  );
  assert.notEqual(
    second.document_number,
    first.document_number,
    "La sustitución reutilizó el número del comprobante original."
  );
  const preserved = await callFrappe(page, {
    method: "frappe.client.get_value",
    args: {
      doctype: "NXR Evidence",
      filters: { name: first.evidence },
      fieldname: ["document_number", "status", "version"],
    },
  });
  assert.equal(
    String(preserved?.document_number || ""),
    first.document_number,
    "El comprobante original desapareció al sustituirlo."
  );
  assert.equal(Number(preserved?.version), 1);
  assert.equal(
    String(preserved?.status || ""),
    "Superseded",
    `El comprobante original quedó en «${preserved?.status}» tras sustituirlo: debía marcarse sustituido, no perderse.`
  );

  // Rechazar.
  await assertEvidenceListed(page, second.document_number);
  const rejected = await reviewEvidence(page, "Rejected", "Rechazar");
  assert.equal(rejected, second.document_number);

  await capture(
    page,
    profile,
    path.join(artifactRoot, `${safeName(name)}-evidence-lifecycle.png`)
  );
  profile.evidence_lifecycle = {
    created: first.document_number,
    approved: first.document_number,
    superseded_by: second.document_number,
    rejected: second.document_number,
    original_preserved: true,
    versions: [1, 2],
  };
}

async function setProgressField(page, fieldname, value) {
  const control = page.locator(
    `#page-nexora-progress .frappe-control[data-fieldname="${fieldname}"]`
  );
  const select = control.locator("select").first();
  if (await select.count()) {
    await select.selectOption(String(value));
    return;
  }
  // "Small Text" (p. ej. `description`) se pinta como <textarea>, no <input> — el
  // resto de campos de esta página sí son <input>.
  const input = control.locator("input:not([type='hidden']), textarea").first();
  await input.waitFor({ state: "visible", timeout: 60_000 });
  await input.fill(String(value));
  await input.press("Tab");
  const stored = await input.inputValue();
  // Un campo Percent/Float real reformatea a precisión fija al perder el foco
  // (p. ej. "35" → "35.00") — eso es Frappe funcionando, no una pérdida del
  // dato. Solo lo rechazamos si ni el texto ni el valor numérico coinciden.
  const numericMatch =
    stored !== "" &&
    value !== "" &&
    !Number.isNaN(Number(stored)) &&
    !Number.isNaN(Number(value)) &&
    Number(stored) === Number(value);
  assert(
    stored === String(value) || numericMatch,
    `El campo ${fieldname} de avance no conservó «${value}»: quedó «${stored}».`
  );
}

/**
 * Igual que `setEvidenceAttachment`: el `Attach` de la fotografía no tiene caja de texto,
 * así que el archivo se pone por la API del control, no escribiendo. En un iPhone real el
 * mismo control abre el selector nativo de cámara/galería sin código adicional (NXR-AVA-0005) —
 * este recorrido no puede pulsar la cámara física, pero sí ejercer el control real end-to-end
 * en el motor WebKit real de los perfiles `ipad-gen7-webkit`/`iphone-13-webkit`.
 */
async function setProgressAttachment(page, fieldname, fileUrl) {
  const outcome = await page.evaluate(
    async ({ fieldname, fileUrl }) => {
      const wrapper =
        document.querySelector("#page-nexora-progress") ||
        window.frappe?.pages?.["nexora-progress"];
      const pageObject =
        wrapper?.page || window.frappe?.pages?.["nexora-progress"]?.page;
      if (!pageObject?.fields_dict) {
        return { applied: false, reason: "la pantalla no expone sus campos" };
      }
      const control = pageObject.fields_dict[fieldname];
      if (!control) {
        return {
          applied: false,
          reason: `no existe el campo ${fieldname}; hay ${Object.keys(
            pageObject.fields_dict
          ).join(", ")}`,
        };
      }
      await control.set_value(fileUrl);
      return { applied: true, value: String(control.get_value() || "") };
    },
    { fieldname, fileUrl }
  );
  assert(
    outcome.applied,
    `No se pudo adjuntar «${fileUrl}» en ${fieldname}: ${outcome.reason}.`
  );
  assert.equal(
    outcome.value,
    fileUrl,
    `El adjunto ${fieldname} quedó en «${outcome.value}» en vez de «${fileUrl}».`
  );
}

async function clickProgressReviewAction(page, label) {
  const button = page
    .locator("#page-nexora-progress .nxr-review-fields button")
    .filter({ hasText: label })
    .first();
  await button.waitFor({ state: "visible", timeout: 60_000 });
  await button.click();
}

/**
 * NXR-AVA-0005/NXR-AVA-0006: la página `nexora-progress` (Bloque 25) existe y tiene prueba
 * de contrato desde su construcción, pero nunca se había ejercido en un navegador real — ni
 * la carga de fotografía, ni el feed cronológico que la muestra, ni la transición de estado.
 * Este recorrido crea un registro real con foto, confirma que aparece en el feed con la
 * fotografía visible, y lo transiciona Draft→Submitted→Approved contra el motor de estados
 * real, en los tres perfiles reales (incluidos los dos WebKit).
 */
async function validateProgressLifecycle(page, context, profile, name) {
  const fixtures = await resolveFixtureContext(page);
  assert(fixtures.project, `Demo project not found: ${demoProject}`);
  await gotoRoute(page, context, profile, "nexora-progress");
  await page
    .locator("#page-nexora-progress .nxr-progress-grid")
    .waitFor({ state: "visible", timeout: 120_000 });

  await setProgressField(page, "project", fixtures.project);
  await setProgressField(page, "phase", "Cimentación");
  await setProgressField(
    page,
    "description",
    `Avance registrado por el recorrido ${name}.`
  );
  await setProgressField(page, "progress_percent", "35");

  const photoUrl = await uploadPrivateFile(
    page,
    `nexora-avance-${safeName(name)}.txt`,
    `Fotografía de avance del recorrido ${name}.`
  );
  await setProgressAttachment(page, "photos", photoUrl);

  const createResponsePromise = apiResponse(
    page,
    "create_progress_record",
    "registro de avance"
  );
  await clickRegisteredAction(page, "Registrar avance");
  const createResponse = await createResponsePromise;
  await assertResponseOk(createResponse, "Progress record creation");
  const created = (await createResponse.json())?.message || {};
  assert.match(
    String(created.document_number || ""),
    /^\d{12}$/,
    "El registro de avance no recibió número de documento."
  );
  assert.equal(String(created.status || ""), "Draft");

  const card = page
    .locator("#page-nexora-progress .nxr-progress-rows .nxr-progress-card")
    .filter({ hasText: created.document_number })
    .first();
  await card.waitFor({ state: "visible", timeout: 60_000 });
  assert.equal(
    await card.locator(".nxr-progress-photo").count(),
    1,
    "El registro de avance apareció en el feed sin la fotografía adjunta."
  );

  const submitResponsePromise = apiResponse(
    page,
    "transition_progress_record",
    "envío a revisión"
  );
  await clickProgressReviewAction(page, "Enviar a revisión");
  const submitResponse = await submitResponsePromise;
  await assertResponseOk(submitResponse, "Progress record submission");
  assert.equal(
    String((await submitResponse.json())?.message?.status || ""),
    "Submitted"
  );

  const approveResponsePromise = apiResponse(
    page,
    "transition_progress_record",
    "aprobación"
  );
  await clickProgressReviewAction(page, "Aprobar");
  const approveResponse = await approveResponsePromise;
  await assertResponseOk(approveResponse, "Progress record approval");
  assert.equal(
    String((await approveResponse.json())?.message?.status || ""),
    "Approved"
  );

  await capture(
    page,
    profile,
    path.join(artifactRoot, `${safeName(name)}-progress-lifecycle.png`)
  );
  profile.progress_lifecycle = {
    created: created.document_number,
    photo_in_feed: true,
    final_status: "Approved",
  };
}

/**
 * Exportar. Dos salidas distintas y las dos son del usuario: el libro completo como CSV
 * —la promesa del Capítulo 33— y el documento suelto como impresión descargable.
 *
 * En el ancho del teléfono la pantalla sustituye la tabla por tarjetas y retira la barra
 * con ella a propósito (Capítulo 37), así que ahí no hay CSV que pulsar. El recorrido no
 * lo disimula: registra qué salida ejerció cada perfil y, al final, exige que el CSV se
 * haya descargado de verdad en algún perfil. Una comprobación que se salta sola en los
 * tres perfiles no comprueba nada.
 */
/**
 * `nexora_tables.js` decide si la barra de exportación se ve mirando
 * `table.getClientRects().length` (Capítulo 34); si la barra nunca aparece, «Timeout» no
 * distingue entre «la tabla se convirtió en superficie de trabajo y la barra se atascó
 * oculta» y «la tabla nunca llegó a mejorarse». Se reproduce aquí exactamente la misma
 * lectura que usa el módulo, para que un fallo diga cuál de las dos cosas pasó.
 */
async function exportToolbarDiagnostics(page) {
  return page.evaluate(() => {
    const ledger = document.querySelector(
      "#page-nexora-operations .nxr-operational-ledger"
    );
    const table = ledger?.querySelector("table.nxr-ledger-table") || null;
    const bar = ledger?.querySelector(".nxr-table-toolbar") || null;
    return {
      ledger_connected: Boolean(ledger?.isConnected),
      table_connected: Boolean(table?.isConnected),
      table_enhanced: table?.dataset?.nxrTableEnhanced === "1",
      table_client_rects: table ? table.getClientRects().length : "missing",
      table_row_count: table
        ? table.querySelectorAll("tbody tr").length
        : "missing",
      toolbar_present: Boolean(bar),
      toolbar_hidden_attribute: bar ? bar.hidden : "missing",
      toolbar_client_rects: bar ? bar.getClientRects().length : "missing",
    };
  });
}

async function validateExportSurfaces(page, context, profile, name) {
  await gotoRoute(page, context, profile, "nexora-operations");
  const ledger = page.locator(
    "#page-nexora-operations .nxr-operational-ledger"
  );
  await ledger.waitFor({ state: "visible", timeout: 120_000 });
  const table = ledger.locator("table.nxr-ledger-table").first();
  await table.waitFor({ state: "attached", timeout: 120_000 });
  await page.waitForFunction(
    () =>
      (
        document.querySelectorAll(
          "#page-nexora-operations .nxr-ledger-table tbody tr"
        ) || []
      ).length > 1,
    null,
    { timeout: 60_000 }
  );

  const exported = { csv: null, document: null };
  if (await table.isVisible()) {
    const action = ledger.locator(".nxr-table-toolbar .nxr-table-export");
    try {
      await action.waitFor({ state: "visible", timeout: 60_000 });
    } catch (error) {
      const diagnostics = await exportToolbarDiagnostics(page);
      throw new Error(
        `El botón de exportación del libro operativo nunca se mostró: ${JSON.stringify(
          diagnostics
        )}`,
        { cause: error }
      );
    }
    const downloadPromise = page.waitForEvent("download", { timeout: 60_000 });
    await action.click();
    const download = await downloadPromise;
    const file = await download.path();
    assert(file, "La exportación CSV no dejó archivo descargado.");
    const csv = await fs.readFile(file, "utf-8");
    assert(
      csv.startsWith("﻿"),
      "El CSV salió sin BOM: Excel abriría los acentos rotos."
    );
    assert(
      csv.includes(profile.guided_income.document_number),
      `El CSV exportado no contenía el documento ${profile.guided_income.document_number}.`
    );
    exported.csv = {
      file_name: download.suggestedFilename(),
      bytes: csv.length,
      // El generador emite CRLF, pero el informe es evidencia que se consulta después:
      // una cifra que se vuelve «1» si algún día sale con LF es peor que no tenerla.
      rows: csv.trim().split(/\r?\n/).length,
    };
  } else {
    // La tabla está oculta a propósito: entonces las tarjetas tienen que estar delante.
    const cards = ledger.locator(".nxr-mobile-cards article:visible").first();
    await cards.waitFor({ state: "visible", timeout: 60_000 });
    assert.equal(
      await ledger.locator(".nxr-table-toolbar:visible").count(),
      0,
      "La barra de exportación siguió visible sobre una tabla que el usuario no ve."
    );
    exported.csv = { skipped: "la pantalla muestra tarjetas en este ancho" };
  }

  // El documento suelto se descarga en cualquier ancho: es la salida que sí tiene el
  // teléfono, y comprobarla exige que la impresión responda, no que el botón exista.
  const printResponse = await browserRequest(
    page,
    `/printview?doctype=${encodeURIComponent(
      "NXR Operation"
    )}&name=${encodeURIComponent(
      profile.guided_income.operation
    )}&trigger_print=1`
  );
  assert.equal(
    printResponse.status,
    200,
    `La descarga del documento respondió ${printResponse.status}.`
  );
  assert(
    printResponse.text.includes(profile.guided_income.document_number),
    "La impresión descargable no contenía el número del documento."
  );
  exported.document = {
    operation: profile.guided_income.operation,
    document_number: profile.guided_income.document_number,
    status: printResponse.status,
  };
  profile.exports = exported;
}

async function runProfile(
  browserType,
  name,
  contextOptions,
  { pwa = false } = {}
) {
  const browser = await browserType.launch({ headless: true });
  const profile = {
    name,
    engine: browserType.name(),
    routes: [],
    direct_routes: [],
    auth_snapshots: [],
    page_errors: [],
    console_errors: [],
    transient_messages: [],
    server_errors: [],
    auth_errors: [],
  };
  report.profiles.push(profile);
  const context = await browser.newContext({
    ...contextOptions,
    locale: "es-HN",
    baseURL,
    extraHTTPHeaders: { "X-Frappe-Site-Name": siteName },
  });
  const page = await context.newPage();
  watchPage(page, profile);

  // Cada etapa se ejecuta aunque la anterior haya fallado, y todas las averías se
  // reportan juntas. Abortar en la primera convertía cada ejecución de CI —ocho minutos—
  // en un solo dato: se corregía un defecto y la siguiente ejecución revelaba el
  // siguiente, escondido detrás. Las etapas que dependen de datos de otra se saltan
  // explícitamente y dicen por qué, en vez de fallar por arrastre.
  profile.stages = [];
  const done = new Set();
  const step = async (id, fn, { needs = [] } = {}) => {
    const missing = needs.filter((dependency) => !done.has(dependency));
    if (missing.length) {
      profile.stages.push({
        id,
        status: "skipped",
        reason: `depende de ${missing.join(", ")}, que no llegó a completarse`,
      });
      return false;
    }
    try {
      await fn();
      profile.stages.push({ id, status: "passed" });
      done.add(id);
      return true;
    } catch (error) {
      profile.stages.push({
        id,
        status: "failed",
        error: error?.message || String(error),
      });
      await captureFailure(page, profile, error).catch(() => {});
      return false;
    }
  };

  try {
    // La sesión es la única condición sin la cual nada tiene sentido: si falla, se
    // abandona el perfil en vez de acumular veinte fallos derivados.
    await authenticate(page, context, profile);
    await waitForRoute(page, "nexora-dashboard");

    await step("carcasa", () => validateShell(page, profile));
    await step("panel", async () => {
      await validateDashboard(page, profile);
      await capture(
        page,
        profile,
        path.join(artifactRoot, `${safeName(name)}-dashboard.png`)
      );
    });
    await step("operaciones", () =>
      validateGuidedOperations(page, profile, name)
    );
    await step(
      "busqueda",
      () => validateUniversalSearch(page, context, profile, name),
      { needs: ["operaciones"] }
    );
    await step(
      "anulacion",
      () => validateControlledCorrection(page, profile, name),
      { needs: ["operaciones"] }
    );
    await step(
      "correccion",
      () => validateAccountedCorrection(page, profile, name),
      { needs: ["operaciones"] }
    );
    await step("comprobantes", () =>
      validateEvidenceLifecycle(page, context, profile, name)
    );
    await step("avance", () =>
      validateProgressLifecycle(page, context, profile, name)
    );
    await step(
      "exportacion",
      () => validateExportSurfaces(page, context, profile, name),
      { needs: ["operaciones"] }
    );
    await step("reportes", () => validateReports(page, context, profile));
    await step("cierre", () => validateClosing(page, context, profile));
    await step("rutas", async () => {
      for (const route of routes) {
        await gotoRoute(page, context, profile, route);
        profile.routes.push(route);
      }
      await validateDirectRoutes(page, profile);
      await gotoRoute(page, context, profile, "nexora-dashboard");
    });
    await step("paleta", async () => {
      await validateCommandBar(page, profile);
      await gotoRoute(page, context, profile, "nexora-dashboard");
    });
    await step("manifiesto", () => validateManifest(page));
    if (pwa) await step("pwa", () => validatePwa(page, context, profile));
    await step("responsive", () => validateResponsiveLayout(page, profile));
    await step("tiempo-real", () => validateRealtime(page, profile));
    await step("sesion-viva", () =>
      assertAuthenticated(page, context, profile, "profile-complete")
    );
    await step("sin-errores", async () => {
      assert.deepEqual(profile.page_errors, [], `${name} emitted page errors.`);
      assert.deepEqual(
        profile.console_errors,
        [],
        `${name} emitted console errors.`
      );
      assert.deepEqual(
        profile.server_errors,
        [],
        `${name} received HTTP 5xx responses.`
      );
      assert.deepEqual(
        profile.auth_errors,
        [],
        `${name} received authorization errors.`
      );
    });

    // El Capítulo 53 en una sola vista: qué operación quedó cubierta y con qué documento.
    // Un recorrido que las ejerce pero no las nombra obliga a leer el código para saber
    // si están las ocho, y eso no es evidencia consultable (Capítulo 44).
    profile.chapter_53 = {
      crear: profile.guided_income?.document_number || null,
      editar: profile.accounted_correction?.in_place_edit_refused
        ? profile.accounted_correction.corrected_value
        : null,
      consultar: profile.universal_search?.query || null,
      aprobar: profile.evidence_lifecycle?.approved || null,
      rechazar: profile.evidence_lifecycle?.rejected || null,
      anular: profile.controlled_correction?.correction_document_number || null,
      corregir:
        profile.accounted_correction?.correction_document_number || null,
      exportar: profile.exports?.document?.document_number || null,
    };

    const broken = profile.stages.filter((stage) => stage.status !== "passed");
    if (broken.length) {
      profile.status = "failed";
      throw new Error(
        `[${name}] ${broken.length} etapa(s) sin superar:\n` +
          broken
            .map(
              (stage) =>
                `  · ${stage.id}: ${
                  stage.status === "skipped" ? stage.reason : stage.error
                }`
            )
            .join("\n")
      );
    }
    profile.status = "passed";
  } catch (error) {
    profile.status = "failed";
    // Las etapas ya guardaron su captura; aquí solo llegan los fallos de sesión y el
    // resumen. El perfil viaja en el mensaje: «la pantalla nunca pidió la vista previa»
    // no dice si fue en escritorio, en tableta o en el teléfono.
    const message = String(error?.message || error);
    throw new Error(
      message.startsWith(`[${name}]`) ? message : `[${name}] ${message}`,
      { cause: error }
    );
  } finally {
    await context.close();
    await browser.close();
  }
}

// Capítulo 54: escritorio, tableta, móvil y PWA. La tableta no es un escritorio estrecho
// ni un teléfono grande: es el ancho donde las rejillas cambian de columnas y donde la
// aplicación decide entre tabla y tarjetas.
//
// Los tres se recorren siempre. Antes, un fallo en escritorio dejaba tableta y teléfono
// sin ejecutar, así que hacían falta tantas ejecuciones como perfiles rotos hubiera.
const profileRuns = [
  [
    chromium,
    "desktop-chromium",
    { viewport: { width: 1440, height: 900 } },
    { pwa: true },
  ],
  [webkit, "ipad-gen7-webkit", devices["iPad (gen 7)"], { pwa: true }],
  [webkit, "iphone-13-webkit", devices["iPhone 13"], { pwa: true }],
];
const failures = [];
for (const [engine, profileName, contextOptions, options] of profileRuns) {
  try {
    await runProfile(engine, profileName, contextOptions, options);
  } catch (error) {
    failures.push(error?.message || String(error));
    report.errors = failures;
  }
}
try {
  if (failures.length) throw new Error(failures.join("\n\n"));
  // La exportación a CSV se salta donde la pantalla muestra tarjetas en vez de tabla, y
  // eso es correcto (Capítulo 37). Que se saltara en los tres perfiles no lo sería:
  // significaría que nadie la ejerció y que la etapa pasó sin comprobar nada.
  report.csv_export_profiles = report.profiles
    .filter((profile) => profile.exports?.csv?.file_name)
    .map((profile) => profile.name);
  assert(
    report.csv_export_profiles.length,
    "Ningún perfil descargó el CSV: la exportación quedó sin comprobar en los tres."
  );
  report.ok = true;
} catch (error) {
  report.ok = false;
  report.error = error?.stack || String(error);
  report.error_message = error?.message || String(error);
} finally {
  report.completed_at = new Date().toISOString();
  await fs.writeFile(
    path.join(artifactRoot, "nexora-browser-report.json"),
    `${JSON.stringify(report, null, 2)}\n`,
    "utf-8"
  );
}

if (!report.ok) {
  // El diagnóstico va al final, y solo, a propósito. Lanzar el error dejaba que Node
  // imprimiera la traza detrás del mensaje, y la herramienta que lee el registro solo
  // devuelve la cola: el motivo —qué campo faltaba, quién anuló la vista previa— quedaba
  // fuera de la ventana visible y había que adivinarlo. Un diagnóstico que no se puede
  // leer no diagnostica (Capítulo 51).
  console.error(`\n${report.error}`);
  console.error(
    `\n[nexora] CAUSA DEL FALLO\n${report.error_message}\n[nexora] fin del diagnóstico\n`
  );
  process.exitCode = 1;
}
