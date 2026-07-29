import assert from "node:assert/strict";
import path from "node:path";

import {
  artifactRoot,
  baseURL,
  browserRequest,
  gotoRoute,
  normalizedText,
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
  assert.equal(
    response.ok,
    true,
    `Executive API failed with HTTP ${response.status}.`
  );
  const data = response.payload?.message;
  assert(data?.context, "Executive API returned no context.");
  assert(data?.finance, "Executive API returned no finance section.");
  assert(data?.budgets, "Executive API returned no budget section.");
  assert.equal(
    data.filter_context?.bounded_operational_queries,
    true,
    "Executive API did not use bounded operational queries."
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
    '[data-action="income"]',
    '[data-action="expense"]',
  ]) {
    await dashboard.locator(selector).first().waitFor({ state: "visible" });
  }
  assert.match(
    normalizedText(await dashboard.locator(".nxr-dashboard-period").innerText()),
    /^Período:/,
    "Dashboard did not expose the active period."
  );
  assert.equal(
    await dashboard.locator('[data-action="income"]').first().innerText(),
    "Registrar ingreso"
  );
  assert.equal(
    await dashboard.locator('[data-action="expense"]').first().innerText(),
    "Registrar gasto"
  );
  assert.deepEqual(profile.page_errors, [], "Dashboard bootstrap emitted page errors.");
  assert.deepEqual(profile.console_errors, [], "Dashboard bootstrap emitted console errors.");
  const data = await readExecutiveApi(page);
  assert.equal(
    normalizedText(
      await page
        .locator("#page-nexora-dashboard h2.nxr-project-name")
        .innerText()
    ),
    normalizedText(data.context.project_label)
  );
  await page
    .locator(
      '#page-nexora-dashboard .nxr-dashboard-recent-rows[data-operational-ledger="ready"]'
    )
    .waitFor({ state: "visible", timeout: 60_000 });
  const ledgerRows = await page.evaluate(
    () =>
      new Promise((resolve, reject) => {
        window.frappe.call({
          method: "nexora.financial.service.list_operational_ledger",
          type: "POST",
          args: { limit: 20 },
          callback: (response) => resolve(response.message || []),
          error: reject,
        });
      })
  );
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
  profile.dashboard = {
    source_count: data.finance.source_count,
    available_hnl: data.finance.total_available_hnl,
    budget_available_hnl: data.budgets.total_available_hnl,
    pending_count: data.pending_accounts.count,
    evidence_count: data.evidence.count,
    recent_operations: data.recent_operations.length,
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

export async function validateReports(page, context, profile) {
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
  assert.match(hash, /nexora-analytics-v3/);
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
}

export async function validateManifest(page) {
  await page
    .locator('link[rel="manifest"][data-nexora="1"]')
    .waitFor({ state: "attached", timeout: 30_000 });
  const result = await page.evaluate(async () => {
    const link = document.querySelector(
      'link[rel="manifest"][data-nexora="1"]'
    );
    const response = await fetch(link.href, {
      cache: "no-store",
      credentials: "same-origin",
    });
    return { ok: response.ok, payload: await response.json() };
  });
  assert.equal(result.ok, true, "NEXORA manifest request failed.");
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
    return {
      viewport_width: width,
      document_width: document.documentElement.scrollWidth,
      overflowing,
    };
  });
  assert.deepEqual(
    result.overflowing,
    [],
    `iPhone overflow: ${JSON.stringify(result)}`
  );
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
  try {
    await page.screenshot({
      path: path.join(artifactRoot, `${safeName(profile.name)}-failure.png`),
      fullPage: true,
    });
  } catch {
    // The JSON report still records the failure when screenshot capture is unavailable.
  }
}
