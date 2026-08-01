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
  gotoRoute,
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
  "ADMIN_PASSWORD is required for the NEXORA browser validation.",
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
  assert.equal(
    response.ok,
    true,
    `Frappe request failed with HTTP ${response.status}: ${options.method}`,
  );
  return response.payload?.message;
}

async function replayExecution(page, response, documentNumber) {
  const body = response.request().postData();
  assert(body, "The definitive request did not expose a replayable payload.");
  const csrfToken = await page.evaluate(
    () => window.frappe?.csrf_token || window.csrf_token || "",
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
    `Idempotent replay failed with HTTP ${replay.status}.`,
  );
  assert.equal(
    String(replay.payload?.message?.document_number || ""),
    documentNumber,
    "The same definitive request generated a second document.",
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
        '#page-nexora-operations [data-field="movement_code"] input',
      )?.value === code,
    movementCode,
    { timeout: 60_000 },
  );
  await page
    .locator("#page-nexora-operations .nxr-guided-wizard")
    .waitFor({ state: "visible", timeout: 60_000 });
}

/**
 * Fill an operation form field and commit the value to the underlying Frappe control.
 *
 * Clicking an Awesomplete suggestion was evaluated and discarded: the dropdown does not
 * open for every control, and returning early without the blur event left link fields
 * uncommitted, which blocked the guided wizard on stage 1. Filling and blurring with Tab
 * is the behaviour that the guided operations validator actually accepts.
 *
 * @param {Page} page - The Playwright page instance.
 * @param {string} name - The field's data-field identifier.
 * @param {*} value - The value to enter or select.
 */
async function openDetailTab(page, name) {
  const tab = page.locator(`[data-detail-tab="${name}"]`).first();
  if (await tab.count()) {
    // WebKit/iPhone: the tab strip uses -webkit-overflow-scrolling: touch,
    // whose momentum scroll keeps the bounding box shifting so Playwright's
    // actionability "wait for element to be stable" check never resolves.
    // Scroll natively (instant, no momentum) and dispatch the click via the
    // DOM instead of relying on Playwright's visual stability/animation wait.
    await tab.evaluate((el) => {
      el.scrollIntoView({
        behavior: "instant",
        block: "nearest",
        inline: "nearest",
      });
    });
    try {
      await tab.click({ timeout: 5000, force: true });
    } catch (error) {
      await tab.evaluate((el) => el.click());
    }
  }
}

/**
 * Commit a value into a Frappe control across all engines (Chromium, Firefox, WebKit).
 *
 * NEXORA Release, hoy - fix(nexora): WebKit does not reliably dispatch the same
 * blur/change event sequence that `press("Tab")` produces on Chromium/Firefox,
 * so Frappe's async field validation (which flips the guided wizard stage to
 * "valid") never fires and the guided review polling loop times out after 60s
 * on iPhone WebKit runs. This helper explicitly fires native `input` and
 * `change` events and blurs the control, guaranteeing the commit is observed
 * by Frappe's field-change listeners regardless of the underlying browser
 * engine's synthetic event semantics.
 *
 * @param {Page} page - The Playwright page instance.
 * @param {Locator} control - The resolved input/select/textarea control locator.
 */
async function commitControlValue(page, control) {
  await control.press("Tab");
  await control.evaluate((node) => {
    node.dispatchEvent(new Event("input", { bubbles: true }));
    node.dispatchEvent(new Event("change", { bubbles: true }));
    node.blur();
    node.dispatchEvent(new Event("blur", { bubbles: true }));
  });
  await page.waitForTimeout(150);
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
  await commitControlValue(page, control);
}

/**
 * Resolve a document date that NEXORA accepts for the currently active period.
 *
 * The guided operation form renders `document_date` as a Frappe `Date` control, so its
 * visible input expects the user date format (for example `dd-mm-yyyy`), not ISO. Feeding
 * an ISO string makes `frappe.datetime.user_to_str` misparse the value and the operation is
 * rejected with "Fecha fuera del periodo activo". This helper asks the running application
 * for today's date, clamps it into the active period advertised by the guided context and
 * returns the value already formatted for the user-facing control.
 *
 * @param {Page} page - The Playwright page instance.
 * @returns {Promise<string>} Document date formatted with the site's user date format.
 */
async function guidedDocumentDate(page) {
  return page.evaluate(() => {
    const today = window.frappe.datetime.get_today();
    let context = null;
    try {
      context = JSON.parse(
        window.sessionStorage?.getItem("nexora:guided-operation-context") ||
          "null",
      );
    } catch (_error) {
      context = null;
    }
    let target = today;
    if (context?.from_date && target < context.from_date)
      target = context.from_date;
    if (context?.to_date && target > context.to_date) target = context.to_date;
    return window.frappe.datetime.str_to_user(target);
  });
}

/**
 * Fill the guided `document_date` control and assert the application stored a usable date.
 * @param {Page} page - The Playwright page instance.
 */
async function setGuidedDocumentDate(page) {
  const value = await guidedDocumentDate(page);
  const control = page
    .locator('#page-nexora-operations [data-field="document_date"] input')
    .first();
  await control.waitFor({ state: "visible", timeout: 30_000 });
  await control.fill(value);
  await commitControlValue(page, control);
  await page.waitForFunction(
    (expected) => {
      const input = document.querySelector(
        '#page-nexora-operations [data-field="document_date"] input',
      );
      if (!input?.value) return false;
      const normalized = String(
        window.frappe.datetime.user_to_str?.(input.value) || input.value,
      ).slice(0, 10);
      return normalized === expected;
    },
    String(
      await page.evaluate(
        (userValue) => window.frappe.datetime.user_to_str(userValue),
        value,
      ),
    ),
    { timeout: 30_000 },
  );
}

/**
 * Read the value the guided validator sees for a primary field.
 * @param {Page} page - The Playwright page instance.
 * @param {string[]} names - Primary field identifiers to inspect.
 * @returns {Promise<string[]>} Names whose control is currently empty.
 */
async function emptyPrimaryFields(page, names) {
  return page.evaluate(
    (fieldNames) =>
      fieldNames.filter((name) => {
        const wrapper = document.querySelector(
          `#page-nexora-operations [data-field="${name}"]`,
        );
        const node = wrapper?.querySelector(
          "input:not([type='hidden']),select,textarea",
        );
        return !String(node?.value || "").trim();
      }),
    names,
  );
}

/**
 * Fill every primary field and keep them filled until the guided validator can accept them.
 *
 * The guided wizard re-renders its conditional fields whenever project, currency, channel or
 * payment method change, and that refresh can wipe a value that was typed moments earlier.
 * Filling once is therefore not enough: this helper re-applies any control that ends up empty
 * and only returns when every primary field holds a value, which is exactly what
 * `validatePrimary` reads before allowing the transition to stage 2.
 *
 * @param {Page} page - The Playwright page instance.
 * @param {Array<[string, string]>} entries - Ordered field name and value pairs.
 */
async function fillPrimaryFields(page, entries) {
  const names = entries.map(([name]) => name);
  for (const [name, value] of entries) await setField(page, name, value);
  for (let attempt = 0; attempt < 8; attempt += 1) {
    const missing = await emptyPrimaryFields(page, names);
    if (!missing.length) return;
    for (const name of missing) {
      const entry = entries.find(([candidate]) => candidate === name);
      if (entry) await setField(page, entry[0], entry[1]);
    }
  }
  const missing = await emptyPrimaryFields(page, names);
  assert.equal(
    missing.length,
    0,
    `The guided operation kept clearing primary fields: ${missing.join(", ")}`,
  );
}

async function waitForGuidedStage(page, stage) {
  const locator = page.locator(
    `#page-nexora-operations [data-guided-stage="${stage}"]`,
  );
  await locator.waitFor({ state: "visible", timeout: 60_000 });
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
    { timeout: 60_000 },
  );
}

/**
 * Collect the operational messages a human would read when a preview does not validate.
 * @param {Page} page - The Playwright page instance.
 * @returns {Promise<string>} A single line describing validation, status and dialog text.
 */
async function guidedReviewDiagnostics(page) {
  return page.evaluate(() => {
    const text = (selector) => {
      const node = document.querySelector(selector);
      if (!node) return "<ausente>";
      if (node.hasAttribute("hidden")) return "<oculto>";
      return String(node.textContent || "")
        .replace(/\s+/g, " ")
        .trim();
    };
    const modal = [...document.querySelectorAll(".modal.show .modal-content")]
      .map((node) =>
        String(node.textContent || "")
          .replace(/\s+/g, " ")
          .trim(),
      )
      .join(" || ");
    const preview = document.querySelector(
      "#page-nexora-operations .nxr-preview-body",
    );
    const execute = document.querySelector(
      "#page-nexora-operations .nxr-execute-movement",
    );
    return [
      `validation=${text("#page-nexora-operations .nxr-validation-summary")}`,
      `status=${text("#page-nexora-operations .nxr-action-status")}`,
      `previewEmpty=${
        preview ? preview.classList.contains("nxr-empty") : "<ausente>"
      }`,
      `previewText=${text("#page-nexora-operations .nxr-preview-body").slice(
        0,
        400,
      )}`,
      `executeDisabled=${execute ? execute.disabled : "<ausente>"}`,
      `modal=${modal.slice(0, 400) || "<ninguno>"}`,
    ].join(" | ");
  });
}

async function advanceValidatedGuidedReview(page, label) {
  try {
    await waitForValidatedGuidedReview(page);
  } catch (error) {
    const diagnostics = await guidedReviewDiagnostics(page);
    error.message = `${label} review never became valid. ${diagnostics}\n${error.message}`;
    throw error;
  }
  const stage = page.locator('#page-nexora-operations [data-guided-stage="3"]');
  if (!(await stage.isVisible())) {
    const go = page.locator('#page-nexora-operations [data-guided-go="3"]');
    if (await go.count()) await go.click();
    await waitForGuidedStage(page, 3);
  }
  const next = page.locator('#page-nexora-operations [data-guided-next="4"]');
  assert.equal(await next.isVisible(), true, `${label} review is not visible.`);
  assert.equal(await next.isEnabled(), true, `${label} review is not valid.`);
  await next.click();
  await waitForGuidedStage(page, 4);
}

/**
 * Wait until the guided review stage is visible, populated and stable.
 * @param {Page} page - The Playwright page instance.
 */
async function waitForValidatedGuidedReview(page) {
  await page.waitForFunction(
    (stableForMs) => {
      const next = document.querySelector(
        '#page-nexora-operations [data-guided-next="4"]',
      );
      const original = document.querySelector(
        "#page-nexora-operations .nxr-execute-movement",
      );
      const preview = document.querySelector(
        "#page-nexora-operations .nxr-preview-body",
      );
      const valid = Boolean(
        next &&
        !next.disabled &&
        original &&
        !original.disabled &&
        preview &&
        !preview.classList.contains("nxr-empty"),
      );
      const signature = [
        valid,
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
    { polling: 100, timeout: 60_000 },
  );
}

async function assertGuidedSurface(page, movementCode) {
  const root = page.locator("#page-nexora-operations");
  assert.equal(
    await root.locator(".nxr-guided-progress [data-guided-go]").count(),
    4,
    "The guided operation does not expose four stages.",
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
      `The guided operation is missing ${expected}.`,
    );
  }
  for (const technical of [
    "Usar cuenta existente",
    "Crear cuenta nueva",
    "Datos manuales, no guardar",
  ]) {
    assert(
      !visibleText.includes(technical),
      `Technical account label remained visible: ${technical}`,
    );
  }
  assert.equal(
    await root.locator(".nxr-guided-advanced").getAttribute("open"),
    null,
    "Advanced options must be closed initially.",
  );
  assert.equal(
    await root.locator(".nxr-preview-movement").count(),
    1,
    "Canonical preview button is missing.",
  );
  assert.equal(
    await root.locator(".nxr-execute-movement").count(),
    1,
    "Canonical execution button is missing.",
  );
  assert.equal(
    await root.locator('[data-field="movement_code"] input').inputValue(),
    movementCode,
  );
}

/**
 * Validates the guided income operation flow and records its execution result.
 * @param {Page} page - The Playwright page instance.
 * @param {Object} fixtures - Fixture values used to populate the operation.
 * @param {Object} profile - Profile report object updated with validation results.
 * @param {string} name - Name used to identify the browser run.
 */
async function validateIncomeGuided(page, fixtures, profile, name) {
  await routeFromDashboard(page, "income", "101");
  await assertGuidedSurface(page, "101");
  await setGuidedDocumentDate(page);
  await fillPrimaryFields(page, [
    ["project", fixtures.project],
    ["channel", "Cash"],
    ["currency", "HNL"],
    ["original_amount", "125.50"],
    ["origin_or_sender", `Ingreso navegador ${name}`],
  ]);

  if ((await emptyPrimaryFields(page, ["document_date"])).length) {
    await setGuidedDocumentDate(page);
  }

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
      "¿Desea guardar esta cuenta para utilizarla nuevamente?",
    ),
  );
  await page
    .locator(
      '#page-nexora-operations [name="nxr-guided-save-account"][value="no"]',
    )
    .check();
  assert.equal(
    await page
      .locator('#page-nexora-operations [data-field="account_mode"] select')
      .inputValue(),
    "Manual",
  );

  const advanced = page.locator("#page-nexora-operations .nxr-guided-advanced");
  await advanced.locator("summary").click();
  assert.equal(
    await page
      .locator('#page-nexora-operations [data-field="origin_or_sender"] input')
      .inputValue(),
    senderBefore,
    "Opening advanced options erased guided data.",
  );
  await advanced.locator("summary").click();

  await waitForOperationalQuiescence(page);
  const previewResponsePromise = page.waitForResponse(
    (response) =>
      response.url().includes("preview_operational_movement") &&
      response.request().method() === "POST",
    { timeout: 120_000 },
  );
  await page.locator("#page-nexora-operations .nxr-guided-preview").click();
  const previewResponse = await previewResponsePromise;
  assert.equal(previewResponse.ok(), true, "Income preview request failed.");
  await advanceValidatedGuidedReview(page, "Income");

  const executeResponsePromise = page.waitForResponse(
    (response) =>
      response.url().includes("execute_operational_movement") &&
      response.request().method() === "POST",
    { timeout: 120_000 },
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

/**
 * Validates the guided expense operation flow and records its execution results.
 * @param {Page} page - The Playwright page instance.
 * @param {Object} fixtures - Seeded project, beneficiary entity, and cost center data.
 * @param {Object} profile - Profile report object updated with expense results.
 * @param {string} name - Browser profile name used in the expense description and screenshot filename.
 */
async function validateExpenseGuided(page, fixtures, profile, name) {
  assert(fixtures.entity, "NEXORA seed created no beneficiary entity.");
  assert(fixtures.cost_center, "ERPNext created no leaf cost center.");
  await routeFromDashboard(page, "expense", "102");
  await assertGuidedSurface(page, "102");
  await setGuidedDocumentDate(page);
  await openDetailTab(page, "amount");
  await fillPrimaryFields(page, [
    ["project", fixtures.project],
    ["currency", "HNL"],
    ["amount_hnl", "75.25"],
    ["beneficiary", fixtures.entity],
    ["description", `Pago navegador ${name}`],
  ]);

  if ((await emptyPrimaryFields(page, ["document_date"])).length) {
    await setGuidedDocumentDate(page);
  }
  await page.locator('#page-nexora-operations [data-guided-next="2"]').click();
  await waitForGuidedStage(page, 2);
  await setField(page, "payment_method", "Cash");
  await setField(page, "account_name", "Caja General");
  await setField(page, "economic_category", "CONSTRUCTION_MATERIALS");
  await setField(page, "cost_center", fixtures.cost_center);
  const allocation = page
    .locator("#page-nexora-operations .nxr-source-amount")
    .first();
  await allocation.waitFor({ state: "visible", timeout: 60_000 });
  await allocation.fill("75.25");
  await allocation.press("Tab");

  await waitForOperationalQuiescence(page);
  const previewResponsePromise = page.waitForResponse(
    (response) =>
      response.url().includes("preview_operational_movement") &&
      response.request().method() === "POST",
    { timeout: 120_000 },
  );
  await page.locator("#page-nexora-operations .nxr-guided-preview").click();
  const previewResponse = await previewResponsePromise;
  if (!previewResponse.ok()) {
    const bodyText = await previewResponse.text().catch(() => "<no body>");
    console.error(
      "Expense preview failure status",
      previewResponse.status(),
      bodyText,
    );
  }
  assert.equal(previewResponse.ok(), true, "Expense preview request failed.");
  await waitForGuidedStage(page, 3);
  const reviewText = await page
    .locator("#page-nexora-operations .nxr-guided-review")
    .innerText();
  for (const label of ["Saldo anterior", "Saldo posterior", "Importe"]) {
    assert(reviewText.includes(label), `Expense review is missing ${label}.`);
  }
  await advanceValidatedGuidedReview(page, "Expense");

  const executeResponsePromise = page.waitForResponse(
    (response) =>
      response.url().includes("execute_operational_movement") &&
      response.request().method() === "POST",
    { timeout: 120_000 },
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
    "Income and expense received the same document number.",
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
    { timeout: 120_000 },
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
    { timeout: 120_000 },
  );
  await row.locator("[data-search-doctype]").click();
  const detailResponse = await detailResponsePromise;
  assert.equal(
    detailResponse.ok(),
    true,
    "Consolidated search detail request failed.",
  );
  const detail = searchPage.locator(".nxr-search-detail-body");
  await detail
    .getByText(documentNumber, { exact: true })
    .waitFor({ state: "visible", timeout: 60_000 });
  assert(
    (await detail.innerText()).includes("Efecto financiero"),
    "Consolidated search detail omitted the financial effect.",
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
    { timeout: 60_000 },
  );
  await page.evaluate((expected) => {
    const action = [
      ...document.querySelectorAll(".page-actions button, .page-actions a"),
    ].find((element) => element.textContent?.trim() === expected);
    if (!action) throw new Error(`Action not found: ${expected}`);
    action.click();
  }, label);
}

async function fillDialogField(page, dialog, fieldname, value) {
  const control = dialog
    .locator(
      `.frappe-control[data-fieldname="${fieldname}"] input, ` +
        `.frappe-control[data-fieldname="${fieldname}"] textarea`,
    )
    .first();
  await control.waitFor({ state: "visible", timeout: 30_000 });
  await control.fill(value);
  await commitControlValue(page, control);
}

async function validateControlledCorrection(page, profile, name) {
  const expense = profile.guided_expense;
  await page.evaluate(
    ({ doctype, operation }) =>
      window.frappe.set_route("Form", doctype, operation),
    { doctype: "NXR Operation", operation: expense.operation },
  );
  await page.waitForFunction(
    (operation) =>
      window.cur_frm?.doctype === "NXR Operation" &&
      window.cur_frm?.docname === operation &&
      !window.cur_frm?.is_new?.(),
    expense.operation,
    { timeout: 120_000 },
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
  await fillDialogField(
    page,
    dialog,
    "requester",
    "nexora.operator@example.test",
  );
  await fillDialogField(
    page,
    dialog,
    "approved_by",
    "nexora.manager@example.test",
  );
  await fillDialogField(
    page,
    dialog,
    "reason",
    `Anulación validada en navegador real ${name}`,
  );

  const previewResponsePromise = page.waitForResponse(
    (response) =>
      response.url().includes("preview_operational_movement") &&
      response.request().method() === "POST",
    { timeout: 120_000 },
  );
  await dialog.locator(".modal-footer .btn-primary").click();
  const previewResponse = await previewResponsePromise;
  assert.equal(
    previewResponse.ok(),
    true,
    "Controlled correction preview request failed.",
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
    { timeout: 120_000 },
  );
  await dialog.locator(".modal-footer .btn-primary").click();
  const executeResponse = await executeResponsePromise;
  assert.equal(
    executeResponse.ok(),
    true,
    "Controlled correction execution request failed.",
  );
  const result = await executeResponse.json();
  const correctionDocument = String(result?.message?.document_number || "");
  assert.match(correctionDocument, /^\d{12}$/);
  assert.notEqual(
    correctionDocument,
    original.document_number,
    "Correction reused the original document number.",
  );
  await page.waitForFunction(
    ({ documentNumber, amount }) =>
      String(window.cur_frm?.doc?.document_number || "") === documentNumber &&
      String(window.cur_frm?.doc?.amount_hnl || "") === amount &&
      String(window.cur_frm?.doc?.status || "").startsWith("Compensated"),
    { documentNumber: original.document_number, amount: original.amount_hnl },
    { timeout: 120_000 },
  );
  await page.screenshot({
    path: path.join(
      artifactRoot,
      `${safeName(name)}-controlled-correction.png`,
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
  { pwa = false } = {},
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
      `${name} emitted console errors.`,
    );
    assert.deepEqual(
      profile.server_errors,
      [],
      `${name} received HTTP 5xx responses.`,
    );
    assert.deepEqual(
      profile.auth_errors,
      [],
      `${name} received authorization errors.`,
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
    { pwa: true },
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
    "utf-8",
  );
}
