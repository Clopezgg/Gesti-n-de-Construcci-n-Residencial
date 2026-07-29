import assert from "node:assert/strict";
import fs from "node:fs/promises";
import path from "node:path";

import { chromium, devices, webkit } from "playwright";

import {
  adminPassword,
  artifactRoot,
  assertAuthenticated,
  authenticate,
  baseURL,
  browserRequest,
  browserRequestTimeoutMs,
  gotoRoute,
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
  validateDashboard,
  validateManifest,
  validatePwa,
  validateRealtime,
  validateReports,
  validateResponsiveLayout,
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
  return page.evaluate(
    ({ request, timeoutMs }) =>
      new Promise((resolve, reject) => {
        let settled = false;
        const finish = (handler, value) => {
          if (settled) return;
          settled = true;
          window.clearTimeout(timer);
          handler(value);
        };
        const timer = window.setTimeout(
          () =>
            finish(
              reject,
              new Error(
                `Frappe request exceeded ${timeoutMs} ms: ${request.method}`
              )
            ),
          timeoutMs
        );
        window.frappe.call({
          ...request,
          callback: (response) => finish(resolve, response.message),
          error: (error) => finish(reject, error),
        });
      }),
    { request: options, timeoutMs: browserRequestTimeoutMs }
  );
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
  assert.equal(
    replay.ok,
    true,
    `Idempotent replay failed with HTTP ${replay.status}.`
  );
  assert.equal(
    String(replay.payload?.message?.document_number || ""),
    documentNumber,
    "The same definitive request generated a second document."
  );
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
  await control.press("Tab");
}

async function waitForGuidedStage(page, stage) {
  const locator = page.locator(
    `#page-nexora-operations [data-guided-stage="${stage}"]`
  );
  await locator.waitFor({ state: "visible", timeout: 60_000 });
  return locator;
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
  await page.locator('#page-nexora-operations [data-guided-next="2"]').click();
  await waitForGuidedStage(page, 2);
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

  const previewResponsePromise = page.waitForResponse(
    (response) =>
      response.url().includes("preview_operational_movement") &&
      response.request().method() === "POST",
    { timeout: 120_000 }
  );
  await page.locator("#page-nexora-operations .nxr-guided-preview").click();
  const previewResponse = await previewResponsePromise;
  assert.equal(previewResponse.ok(), true, "Income preview request failed.");
  await waitForGuidedStage(page, 3);
  assert.equal(
    await page
      .locator('#page-nexora-operations [data-guided-next="4"]')
      .isEnabled(),
    true,
    "Income review did not enable definitive registration."
  );
  await page.locator('#page-nexora-operations [data-guided-next="4"]').click();
  await waitForGuidedStage(page, 4);

  const executeResponsePromise = page.waitForResponse(
    (response) =>
      response.url().includes("execute_operational_movement") &&
      response.request().method() === "POST",
    { timeout: 120_000 }
  );
  await page.locator("#page-nexora-operations .nxr-guided-execute").click();
  const executeResponse = await executeResponsePromise;
  assert.equal(executeResponse.ok(), true, "Income execution request failed.");
  const result = await executeResponse.json();
  const documentNumber = String(result?.message?.document_number || "");
  const operation = String(result?.message?.operation || "");
  assert.match(documentNumber, /^\d{12}$/);
  assert(operation, "Income execution returned no operation identifier.");
  await replayExecution(page, executeResponse, documentNumber);
  await page.screenshot({
    path: path.join(artifactRoot, `${safeName(name)}-guided-income.png`),
    fullPage: true,
  });
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
  await routeFromDashboard(page, "expense", "102");
  await assertGuidedSurface(page, "102");
  await setField(page, "project", fixtures.project);
  await setField(page, "beneficiary", fixtures.entity);
  await setField(page, "description", `Pago navegador ${name}`);
  await setField(page, "amount_hnl", "75.25");
  await setField(page, "currency", "HNL");
  await page.locator('#page-nexora-operations [data-guided-next="2"]').click();
  await waitForGuidedStage(page, 2);
  await setField(page, "payment_method", "Cash");
  await setField(page, "economic_category", "CONSTRUCTION_MATERIALS");
  await setField(page, "cost_center", fixtures.cost_center);
  const allocation = page
    .locator("#page-nexora-operations .nxr-source-amount")
    .first();
  await allocation.waitFor({ state: "visible", timeout: 60_000 });
  await allocation.fill("75.25");
  await allocation.press("Tab");

  const previewResponsePromise = page.waitForResponse(
    (response) =>
      response.url().includes("preview_operational_movement") &&
      response.request().method() === "POST",
    { timeout: 120_000 }
  );
  await page.locator("#page-nexora-operations .nxr-guided-preview").click();
  const previewResponse = await previewResponsePromise;
  assert.equal(previewResponse.ok(), true, "Expense preview request failed.");
  await waitForGuidedStage(page, 3);
  const reviewText = await page
    .locator("#page-nexora-operations .nxr-guided-review")
    .innerText();
  for (const label of ["Saldo anterior", "Saldo posterior", "Importe"]) {
    assert(reviewText.includes(label), `Expense review is missing ${label}.`);
  }
  await page.locator('#page-nexora-operations [data-guided-next="4"]').click();
  await waitForGuidedStage(page, 4);

  const executeResponsePromise = page.waitForResponse(
    (response) =>
      response.url().includes("execute_operational_movement") &&
      response.request().method() === "POST",
    { timeout: 120_000 }
  );
  await page.locator("#page-nexora-operations .nxr-guided-execute").click();
  const executeResponse = await executeResponsePromise;
  assert.equal(executeResponse.ok(), true, "Expense execution request failed.");
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
  await page.screenshot({
    path: path.join(artifactRoot, `${safeName(name)}-guided-expense.png`),
    fullPage: true,
  });
  profile.guided_expense = {
    route: "nexora-operations",
    engine: "102",
    operation,
    document_number: documentNumber,
    allocation: "single-fund",
    idempotent_replay: true,
    stages: 4,
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
  const searchResponsePromise = page.waitForResponse(
    (response) =>
      response.url().includes("universal_search_consolidated") &&
      response.request().method() === "POST",
    { timeout: 120_000 }
  );
  await query.press("Enter");
  const searchResponse = await searchResponsePromise;
  assert.equal(searchResponse.ok(), true, "Universal search request failed.");
  const row = searchPage
    .locator(".nxr-search-results tbody tr")
    .filter({ hasText: documentNumber })
    .first();
  await row.waitFor({ state: "visible", timeout: 60_000 });

  const detailResponsePromise = page.waitForResponse(
    (response) =>
      response.url().includes("get_search_result_detail") &&
      response.request().method() === "POST",
    { timeout: 120_000 }
  );
  await row.locator("[data-search-doctype]").click();
  const detailResponse = await detailResponsePromise;
  assert.equal(
    detailResponse.ok(),
    true,
    "Consolidated search detail request failed."
  );
  const detail = searchPage.locator(".nxr-search-detail-body");
  await detail
    .getByText(documentNumber, { exact: true })
    .waitFor({ state: "visible", timeout: 60_000 });
  assert(
    (await detail.innerText()).includes("Efecto financiero"),
    "Consolidated search detail omitted the financial effect."
  );
  await page.screenshot({
    path: path.join(artifactRoot, `${safeName(name)}-universal-search.png`),
    fullPage: true,
  });
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

async function validateControlledCorrection(page, profile, name) {
  const expense = profile.guided_expense;
  await page.evaluate(
    ({ doctype, operation }) =>
      window.frappe.set_route("Form", doctype, operation),
    { doctype: "NXR Operation", operation: expense.operation }
  );
  await page.waitForFunction(
    (operation) =>
      window.cur_frm?.doctype === "NXR Operation" &&
      window.cur_frm?.docname === operation &&
      !window.cur_frm?.is_new?.(),
    expense.operation,
    { timeout: 120_000 }
  );
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

  const previewResponsePromise = page.waitForResponse(
    (response) =>
      response.url().includes("preview_operational_movement") &&
      response.request().method() === "POST",
    { timeout: 120_000 }
  );
  await dialog.locator(".modal-footer .btn-primary").click();
  const previewResponse = await previewResponsePromise;
  assert.equal(
    previewResponse.ok(),
    true,
    "Controlled correction preview request failed."
  );
  await dialog
    .getByText("El original no será eliminado ni sobrescrito.", {
      exact: true,
    })
    .waitFor({ state: "visible", timeout: 60_000 });

  const executeResponsePromise = page.waitForResponse(
    (response) =>
      response.url().includes("execute_operational_movement") &&
      response.request().method() === "POST",
    { timeout: 120_000 }
  );
  await dialog.locator(".modal-footer .btn-primary").click();
  const executeResponse = await executeResponsePromise;
  assert.equal(
    executeResponse.ok(),
    true,
    "Controlled correction execution request failed."
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
  await page.screenshot({
    path: path.join(
      artifactRoot,
      `${safeName(name)}-controlled-correction.png`
    ),
    fullPage: true,
  });
  profile.controlled_correction = {
    original_document_number: original.document_number,
    correction_document_number: correctionDocument,
    segregation: "requester-approver-executor",
    original_preserved: true,
  };
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
  try {
    await authenticate(page, context, profile);
    await waitForRoute(page, "nexora-dashboard");
    await validateDashboard(page, profile);
    await page.screenshot({
      path: path.join(artifactRoot, `${safeName(name)}-dashboard.png`),
      fullPage: true,
    });
    await validateGuidedOperations(page, profile, name);
    await validateUniversalSearch(page, context, profile, name);
    await validateControlledCorrection(page, profile, name);
    await validateReports(page, context, profile);
    await validateClosing(page, context, profile);
    for (const route of routes) {
      await gotoRoute(page, context, profile, route);
      profile.routes.push(route);
    }
    await validateDirectRoutes(page, profile);
    await gotoRoute(page, context, profile, "nexora-dashboard");
    await validateManifest(page);
    if (pwa) await validatePwa(page, context, profile);
    if (name.includes("iphone")) await validateResponsiveLayout(page, profile);
    await validateRealtime(page, profile);
    await assertAuthenticated(page, context, profile, "profile-complete");
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
    profile.status = "passed";
  } catch (error) {
    profile.status = "failed";
    await captureFailure(page, profile, error);
    throw error;
  } finally {
    await context.close();
    await browser.close();
  }
}

try {
  await runProfile(
    chromium,
    "desktop-chromium",
    { viewport: { width: 1440, height: 900 } },
    { pwa: true }
  );
  await runProfile(webkit, "iphone-13-webkit", devices["iPhone 13"]);
  report.ok = true;
} catch (error) {
  report.ok = false;
  report.error = error?.stack || String(error);
  throw error;
} finally {
  report.completed_at = new Date().toISOString();
  await fs.writeFile(
    path.join(artifactRoot, "nexora-browser-report.json"),
    `${JSON.stringify(report, null, 2)}\n`,
    "utf-8"
  );
}
