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
  validateQuickActions,
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

async function validateFundSelector(page, profile, name) {
  await page.evaluate(() => {
    window.__nexoraExpenseDialog = window.nexora.openExpenseDialog();
  });
  const dialog = page
    .locator(".modal.show")
    .filter({ hasText: "Registrar gasto" })
    .last();
  await dialog.waitFor({ state: "visible", timeout: 30_000 });

  await page.evaluate(async (projectLabel) => {
    const activeDialog = window.__nexoraExpenseDialog;
    if (!activeDialog) {
      throw new Error("NEXORA did not return the active expense dialog.");
    }
    const response = await window.frappe.call({
      method: "frappe.client.get_value",
      args: {
        doctype: "Project",
        filters: { project_name: projectLabel },
        fieldname: "name",
      },
    });
    const project = response.message?.name;
    if (!project) {
      throw new Error(`Demo project not found: ${projectLabel}`);
    }
    await activeDialog.set_value("project", project);
  }, demoProject);

  const sourceField = dialog.locator('[data-fieldname="source"]');
  const sourceInput = sourceField.locator("input").first();
  await sourceInput.waitFor({ state: "visible", timeout: 30_000 });
  await page.waitForFunction(
    () => {
      const input = document.querySelector(
        '.modal.show [data-fieldname="source"] input'
      );
      return (
        input &&
        !input.disabled &&
        input.placeholder.includes("seleccionar un fondo")
      );
    },
    undefined,
    { timeout: 60_000 }
  );

  assert.equal(
    await sourceField.locator("select").count(),
    0,
    "The broken native fund select is still present."
  );
  await sourceInput.click();
  await sourceInput.press("ArrowDown");
  const firstOption = sourceField.locator(".awesomplete ul li").first();
  await firstOption.waitFor({ state: "visible", timeout: 30_000 });
  const optionText = (await firstOption.innerText())
    .replace(/\s+/g, " ")
    .trim();
  assert.match(optionText, /Disponible/);
  assert.match(optionText, /Saldo/);
  assert.match(optionText, /Reservado/);
  assert.notEqual(
    await firstOption.evaluate((node) => getComputedStyle(node).color),
    await firstOption.evaluate(
      (node) => getComputedStyle(node).backgroundColor
    ),
    "The fund option text is not visually distinguishable from its background."
  );

  await page.screenshot({
    path: path.join(artifactRoot, `${safeName(name)}-fund-selector.png`),
    fullPage: true,
  });
  await firstOption.click();
  assert(
    (await sourceInput.inputValue()).trim(),
    "No fund was selected from the visible list."
  );
  assert.equal(
    await dialog.locator(".modal-footer .btn-primary").isEnabled(),
    true,
    "Save expense remained disabled after selecting a valid fund."
  );

  profile.fund_selector = {
    control: "Autocomplete",
    visible_option: optionText,
    native_select_present: false,
  };
  await dialog.locator(".btn-modal-close").click();
  await dialog.waitFor({ state: "hidden", timeout: 15_000 });
  await page.evaluate(() => {
    delete window.__nexoraExpenseDialog;
  });
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
    await validateFundSelector(page, profile, name);
    await validateQuickActions(page, context, profile);
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
