import assert from "node:assert/strict";
import fs from "node:fs/promises";
import path from "node:path";
import process from "node:process";

import { chromium, devices, webkit } from "playwright";

const baseURL = String(
  process.env.NEXORA_BASE_URL || "http://127.0.0.1:8080"
).replace(/\/$/, "");
const siteName = String(process.env.SITE_NAME || "nexora-ui-ci");
const adminPassword = String(process.env.ADMIN_PASSWORD || "");
const artifactRoot = path.resolve(
  process.env.BROWSER_ARTIFACT_DIR || "artifacts/nexora-ui/browser"
);
const routes = [
  "nexora-dashboard",
  "nexora-finance",
  "nexora-contracts",
  "nexora-suppliers",
  "nexora-purchase-requests",
  "nexora-evidence",
  "nexora-reports",
  "nexora-search",
];

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

function safeName(value) {
  return value.replace(/[^a-z0-9_-]+/gi, "-").toLowerCase();
}

async function authenticate(context) {
  const response = await context.request.post(`${baseURL}/api/method/login`, {
    form: { usr: "Administrator", pwd: adminPassword },
    headers: { "X-Frappe-Site-Name": siteName },
  });
  assert.equal(
    response.ok(),
    true,
    `Login failed with HTTP ${response.status()}.`
  );
  const payload = await response.json();
  assert.equal(
    payload.message,
    "Logged In",
    `Unexpected login response: ${JSON.stringify(payload)}`
  );
}

function watchPage(page, profile) {
  page.on("pageerror", (error) => profile.page_errors.push(String(error)));
  page.on("console", (message) => {
    if (message.type() === "error") profile.console_errors.push(message.text());
  });
  page.on("response", (response) => {
    if (response.status() >= 500) {
      profile.server_errors.push({
        status: response.status(),
        url: response.url(),
      });
    }
  });
}

async function waitForRoute(page, route) {
  await page.waitForFunction(
    (expected) => {
      const current = window.frappe?.get_route?.() || [];
      const container = document.querySelector(`#page-${expected}`);
      return current[0] === expected && Boolean(container?.offsetParent);
    },
    route,
    { timeout: 120_000 }
  );
  await page
    .locator(`#page-${route} .layout-main-section`)
    .first()
    .waitFor({ state: "visible", timeout: 30_000 });
  await page
    .locator(`#page-${route} .nxr-product-shell`)
    .first()
    .waitFor({ state: "visible", timeout: 30_000 });
}

async function gotoRoute(page, route) {
  const response = await page.goto(`${baseURL}/app/${route}`, {
    waitUntil: "domcontentloaded",
    timeout: 120_000,
  });
  assert(response, `${route} returned no navigation response.`);
  assert(
    response.status() < 400,
    `${route} returned HTTP ${response.status()}.`
  );
  await waitForRoute(page, route);
  const text = await page.locator(`#page-${route}`).innerText();
  assert(
    !/page not found|404 not found/i.test(text),
    `${route} rendered a not-found page.`
  );
}

async function readDashboardApi(page, context) {
  const csrfToken = await page.evaluate(
    () => window.frappe?.csrf_token || window.csrf_token || ""
  );
  const response = await context.request.post(
    `${baseURL}/api/method/nexora.dashboard.service.get_dashboard_summary`,
    {
      form: { payload: JSON.stringify({}) },
      headers: {
        "X-Frappe-Site-Name": siteName,
        "X-Frappe-CSRF-Token": csrfToken,
      },
    }
  );
  assert.equal(
    response.ok(),
    true,
    `Dashboard API failed with HTTP ${response.status()}.`
  );
  const data = (await response.json()).message;
  assert(data, "Dashboard API returned no message.");
  assert(
    data.context &&
      Object.prototype.hasOwnProperty.call(data.context, "project") &&
      normalizedText(data.context?.project_label).length > 0,
    "Dashboard API returned an invalid canonical project context."
  );
  return data;
}

function normalizedText(value) {
  return String(value || "")
    .replace(/\s+/g, " ")
    .trim();
}

async function validateDashboard(page, context, profile) {
  const data = await readDashboardApi(page, context);
  const shell = page.locator("#page-nexora-dashboard .nxr-dashboard-shell");
  await shell.waitFor({ state: "visible", timeout: 120_000 });
  await page
    .locator('#page-nexora-dashboard .nxr-dashboard-shell[data-state="ready"]')
    .waitFor({ state: "visible", timeout: 120_000 });

  assert.equal(
    normalizedText(
      await page.locator("#page-nexora-dashboard .nxr-project-name").innerText()
    ),
    normalizedText(data.context.project_label)
  );
  assert.equal(
    await page
      .locator("#page-nexora-dashboard .nxr-dashboard-recent-rows tbody tr")
      .count(),
    Math.min(data.recent_operations.length, 6)
  );
  assert(
    (await page
      .locator("#page-nexora-dashboard .nxr-dashboard-recent-rows tbody tr")
      .count()) >= 3,
    "Recent operations were not rendered."
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

  const staleValues = await page
    .locator('#page-nexora-dashboard [data-field]:has-text("—")')
    .count();
  assert.equal(
    staleValues,
    0,
    "Dashboard retained placeholder values after loading."
  );
  profile.dashboard = {
    source_count: data.finance.source_count,
    total_balance_hnl: data.finance.total_balance_hnl,
    total_available_hnl: data.finance.total_available_hnl,
    budget_approved_hnl: data.budgets.total_approved_hnl,
    budget_committed_hnl: data.budgets.total_committed_hnl,
    budget_executed_hnl: data.budgets.total_executed_hnl,
    pending_accounts: data.pending_accounts.count,
    physical_percent: data.progress.physical_percent,
    evidence_count: data.evidence.count,
    recent_operations: data.recent_operations.length,
  };
}

async function validateCanonicalHome(page) {
  await gotoRoute(page, "nexora-dashboard");
  await page
    .locator('#page-nexora-dashboard .nxr-dashboard-shell[data-state="ready"]')
    .waitFor({ state: "visible", timeout: 120_000 });
  const currentRoute = await page.evaluate(
    () => window.frappe?.get_route?.()?.[0] || ""
  );
  assert.equal(
    currentRoute,
    "nexora-dashboard",
    "The canonical NEXORA entry did not resolve to the dashboard."
  );
}

async function validateQuickActions(page) {
  await gotoRoute(page, "nexora-dashboard");
  await page
    .locator('#page-nexora-dashboard .nxr-dashboard-shell[data-state="ready"]')
    .waitFor({ state: "visible", timeout: 120_000 });
  await page
    .locator(
      '#page-nexora-dashboard [data-route="nexora-finance"][data-action="expense"]'
    )
    .first()
    .click();
  await waitForRoute(page, "nexora-finance");
  await page.waitForFunction(
    () =>
      document.querySelector(
        '#page-nexora-finance [data-fieldname="operation_code"] input'
      )?.value === "CONSTRUCTION_PAYMENT",
    undefined,
    { timeout: 60_000 }
  );

  await gotoRoute(page, "nexora-dashboard");
  await page
    .locator('#page-nexora-dashboard .nxr-dashboard-shell[data-state="ready"]')
    .waitFor({ state: "visible", timeout: 120_000 });
  await page
    .locator(
      '#page-nexora-dashboard [data-route="nexora-finance"][data-action="income"]'
    )
    .first()
    .click();
  await waitForRoute(page, "nexora-finance");
  await page
    .locator("#page-nexora-finance .nxr-source-create.nxr-card-highlight")
    .waitFor({ state: "visible", timeout: 60_000 });
}

async function validateManifest(page) {
  await page
    .locator('link[rel="manifest"][data-nexora="1"]')
    .waitFor({ state: "attached", timeout: 30_000 });
  const result = await page.evaluate(async () => {
    const link = document.querySelector(
      'link[rel="manifest"][data-nexora="1"]'
    );
    if (!link) return null;
    const response = await fetch(link.href, {
      cache: "no-store",
      credentials: "same-origin",
    });
    return { href: link.href, ok: response.ok, payload: await response.json() };
  });
  assert(result, "NEXORA manifest link is missing.");
  assert.equal(result.ok, true, "NEXORA manifest request failed.");
  assert.equal(result.payload.id, "/app/nexora-dashboard");
  assert.equal(result.payload.start_url, "/app/nexora-dashboard");
  assert.equal(result.payload.scope, "/app/");
  assert.equal(result.payload.display, "standalone");
  assert(result.payload.icons.some((icon) => icon.sizes === "192x192"));
  assert(result.payload.icons.some((icon) => icon.sizes === "512x512"));
  return result;
}

async function validatePwa(page, context, profile) {
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
    const cacheNames = await caches.keys();
    const requests = [];
    for (const name of cacheNames.filter((item) =>
      item.startsWith("nexora-shell-")
    )) {
      const cache = await caches.open(name);
      requests.push(...(await cache.keys()).map((request) => request.url));
    }
    return {
      active: registration?.active?.scriptURL || "",
      scope: registration?.scope || "",
      cache_names: cacheNames.filter((item) =>
        item.startsWith("nexora-shell-")
      ),
      cached_urls: requests,
    };
  });
  assert.match(state.active, /nexora-service-worker\.js/);
  assert.match(state.scope, /\/app\/$/);
  assert(
    state.cache_names.length >= 1,
    "NEXORA service worker created no shell cache."
  );
  assert(
    state.cached_urls.length >= 1,
    "NEXORA service worker cached no public assets."
  );
  for (const urlValue of state.cached_urls) {
    const url = new URL(urlValue);
    assert.equal(
      url.origin,
      new URL(baseURL).origin,
      "PWA cached a cross-origin resource."
    );
    assert(
      url.pathname.startsWith("/assets/nexora/"),
      `PWA cached a non-shell resource: ${url.pathname}`
    );
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
    assert.match(
      await page.locator(".nxr-offline-banner").innerText(),
      /Sin conexión/
    );
  } finally {
    await context.setOffline(false);
    await page
      .locator(".nxr-offline-banner")
      .waitFor({ state: "detached", timeout: 15_000 });
  }
  profile.pwa = {
    manifest: manifest.payload,
    ...state,
    offline_banner: "passed",
  };
}

async function validateResponsiveLayout(page, profile) {
  const layout = await page.evaluate(() => {
    const viewportWidth = window.innerWidth;
    const selectors = [
      ".nxr-dashboard-shell",
      ".nxr-card",
      ".nxr-balance-row",
      ".nxr-list-row",
      ".nxr-evidence-tile",
    ];
    const overflowing = [];
    for (const selector of selectors) {
      for (const node of document.querySelectorAll(
        `#page-nexora-dashboard ${selector}`
      )) {
        const rect = node.getBoundingClientRect();
        if (rect.left < -1 || rect.right > viewportWidth + 1) {
          overflowing.push({
            selector,
            left: rect.left,
            right: rect.right,
            viewportWidth,
          });
        }
      }
    }
    const shortActions = [
      ...document.querySelectorAll("#page-nexora-dashboard .nxr-action-btn"),
    ]
      .map((node) => ({
        text: node.textContent.trim(),
        height: node.getBoundingClientRect().height,
      }))
      .filter((item) => item.height < 44);
    return {
      viewport_width: viewportWidth,
      document_width: document.documentElement.scrollWidth,
      overflowing,
      short_actions: shortActions,
    };
  });
  assert.deepEqual(
    layout.overflowing,
    [],
    `iPhone layout overflow: ${JSON.stringify(layout)}`
  );
  assert.deepEqual(
    layout.short_actions,
    [],
    `iPhone actions under 44px: ${JSON.stringify(layout)}`
  );
  profile.responsive = layout;
}

async function captureFailure(page, profile, error) {
  const stem = `${safeName(profile.name)}-failure`;
  try {
    await page.screenshot({
      path: path.join(artifactRoot, `${stem}.png`),
      fullPage: true,
    });
  } catch {
    // The page may already be closed; the JSON report still records the failure.
  }
  profile.error = error?.stack || String(error);
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
    page_errors: [],
    console_errors: [],
    server_errors: [],
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
    await authenticate(context);
    await validateCanonicalHome(page);
    await validateDashboard(page, context, profile);
    await page.screenshot({
      path: path.join(artifactRoot, `${safeName(name)}-dashboard.png`),
      fullPage: true,
    });
    if (name.includes("iphone")) await validateResponsiveLayout(page, profile);
    await validateQuickActions(page);
    for (const route of routes) {
      await gotoRoute(page, route);
      profile.routes.push(route);
    }
    await gotoRoute(page, "nexora-dashboard");
    await page
      .locator(
        '#page-nexora-dashboard .nxr-dashboard-shell[data-state="ready"]'
      )
      .waitFor({ state: "visible", timeout: 120_000 });
    await validateManifest(page);
    if (pwa) await validatePwa(page, context, profile);
    assert.deepEqual(profile.page_errors, [], `${name} emitted page errors.`);
    assert.deepEqual(
      profile.console_errors,
      [],
      `${name} emitted console errors: ${profile.console_errors.join(" | ")}`
    );
    assert.deepEqual(
      profile.server_errors,
      [],
      `${name} received HTTP 5xx responses.`
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
