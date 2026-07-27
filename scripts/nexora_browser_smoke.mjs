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
  "nexora-closing",
  "nexora-search",
];
const transientPatterns = [
  /Error connecting to socket\.io: xhr poll error/i,
  /WebSocket connection to .*\/socket\.io\/.*closed before the connection is established/i,
  /XMLHttpRequest cannot load .*\/socket\.io\/.*transport=polling.*access control checks/i,
  /^Viewport argument key "minimal-ui" not recognized and ignored\.$/,
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

function normalizedText(value) {
  return String(value || "")
    .replace(/\s+/g, " ")
    .trim();
}

function safeName(value) {
  return String(value)
    .replace(/[^a-z0-9_-]+/gi, "-")
    .toLowerCase();
}

function isTransient(value) {
  return transientPatterns.some((pattern) => pattern.test(String(value)));
}

async function browserRequest(page, target, options = {}) {
  return page.evaluate(
    async ({ url, requestOptions }) => {
      const response = await fetch(url, {
        credentials: "include",
        cache: "no-store",
        ...requestOptions,
      });
      const text = await response.text();
      let payload = null;
      try {
        payload = JSON.parse(text);
      } catch {
        payload = null;
      }
      return {
        ok: response.ok,
        status: response.status,
        url: response.url,
        text,
        payload,
      };
    },
    { url: target, requestOptions: options }
  );
}

async function postMethod(page, method, payload = {}) {
  const csrfToken = await page.evaluate(
    () => window.frappe?.csrf_token || window.csrf_token || ""
  );
  return browserRequest(page, `/api/method/${method}`, {
    method: "POST",
    headers: {
      "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
      "X-Frappe-Site-Name": siteName,
      "X-Frappe-CSRF-Token": csrfToken,
    },
    body: new URLSearchParams({ payload: JSON.stringify(payload) }).toString(),
  });
}

async function assertAuthenticated(page, context, profile, stage) {
  const cookies = (await context.cookies(baseURL)).filter(
    (cookie) => cookie.name === "sid"
  );
  const server = await browserRequest(
    page,
    "/api/method/frappe.auth.get_logged_user"
  );
  const browserUser = await page.evaluate(
    () => window.frappe?.session?.user || null
  );
  profile.auth_snapshots.push({
    stage,
    browser_user: browserUser,
    server_status: server.status,
    server_user: server.payload?.message || null,
    root_sid: cookies.some(
      (cookie) => cookie.path === "/" && cookie.value && cookie.value !== "Guest"
    ),
  });
  assert(
    cookies.some(
      (cookie) => cookie.path === "/" && cookie.value && cookie.value !== "Guest"
    ),
    `${stage}: authenticated root sid cookie is missing.`
  );
  assert.equal(server.status, 200, `${stage}: session probe failed.`);
  assert.equal(server.payload?.message, "Administrator", `${stage}: server user changed.`);
  assert.equal(browserUser, "Administrator", `${stage}: browser user changed.`);
}

async function authenticate(page, context, profile) {
  await context.clearCookies();
  await page.goto(`${baseURL}/login`, {
    waitUntil: "domcontentloaded",
    timeout: 120_000,
  });
  const login = await page.evaluate(
    async ({ password, site }) => {
      const response = await fetch("/api/method/login", {
        method: "POST",
        credentials: "include",
        headers: {
          "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
          "X-Frappe-Site-Name": site,
        },
        body: new URLSearchParams({
          usr: "Administrator",
          pwd: password,
        }).toString(),
      });
      let payload = {};
      try {
        payload = await response.json();
      } catch {
        payload = {};
      }
      return { ok: response.ok, status: response.status, payload };
    },
    { password: adminPassword, site: siteName }
  );
  assert.equal(login.ok, true, `Login failed with HTTP ${login.status}.`);
  assert.equal(login.payload.message, "Logged In", "Unexpected login response.");
  const response = await page.goto(`${baseURL}/app/nexora-dashboard`, {
    waitUntil: "domcontentloaded",
    timeout: 120_000,
  });
  assert(response && response.status() < 400, "Dashboard bootstrap failed.");
  await page.waitForFunction(
    () => window.frappe?.session?.user === "Administrator",
    undefined,
    { timeout: 60_000 }
  );
  await assertAuthenticated(page, context, profile, "dashboard-bootstrap");
}

function watchPage(page, profile) {
  page.on("pageerror", (error) => {
    const text = String(error);
    if (isTransient(text)) profile.transient_messages.push(text);
    else profile.page_errors.push(text);
  });
  page.on("console", (message) => {
    if (message.type() !== "error") return;
    const text = message.text();
    if (isTransient(text)) profile.transient_messages.push(text);
    else profile.console_errors.push(text);
  });
  page.on("response", (response) => {
    const status = response.status();
    const url = response.url();
    if (status >= 500) profile.server_errors.push({ status, url });
    if (
      [401, 403].includes(status) &&
      (url.includes("/api/") || url.includes("/app/"))
    ) {
      profile.auth_errors.push({ status, url });
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
    .locator(`#page-${route} .nxr-product-shell`)
    .first()
    .waitFor({ state: "visible", timeout: 60_000 });
  const text = await page.locator(`#page-${route}`).innerText();
  assert(
    !/page not found|404 not found|inicie sesi[oó]n para acceder/i.test(text),
    `${route} rendered an unavailable page.`
  );
}

async function gotoRoute(page, context, profile, route) {
  await assertAuthenticated(page, context, profile, `before-route:${route}`);
  await page.evaluate((expected) => {
    if (!window.frappe?.set_route) {
      throw new Error("Frappe SPA router is unavailable.");
    }
    window.frappe.set_route(expected);
  }, route);
  await waitForRoute(page, route);
  await assertAuthenticated(page, context, profile, `after-route:${route}`);
}

async function validateDirectRoutes(page, profile) {
  for (const route of routes) {
    const response = await browserRequest(page, `/app/${route}`);
    assert.equal(response.status, 200, `/app/${route} returned HTTP ${response.status}.`);
    assert(
      !/page not found|404 not found/i.test(response.text),
      `/app/${route} returned a not-found document.`
    );
    profile.direct_routes.push(route);
  }
}

async function readExecutiveApi(page) {
  const response = await postMethod(
    page,
    "nexora.dashboard.executive.get_executive_snapshot",
    {}
  );
  assert.equal(response.ok, true, `Executive API failed with HTTP ${response.status}.`);
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

async function validateDashboard(page, profile) {
  await page
    .locator('#page-nexora-dashboard .nxr-dashboard-shell[data-state="ready"]')
    .waitFor({ state: "visible", timeout: 120_000 });
  const data = await readExecutiveApi(page);
  assert.equal(
    normalizedText(
      await page.locator("#page-nexora-dashboard .nxr-project-name").innerText()
    ),
    normalizedText(data.context.project_label)
  );
  const recentRows = await page
    .locator("#page-nexora-dashboard .nxr-dashboard-recent-rows tbody tr")
    .count();
  assert.equal(recentRows, Math.min(data.recent_operations.length, 6));
  assert(recentRows >= 3, "Recent operations were not rendered.");
  await page.waitForFunction(
    () =>
      [...document.querySelectorAll("#page-nexora-dashboard .nxr-evidence-tile img")].some(
        (image) => image.complete && image.naturalWidth > 0
      ),
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

async function validateQuickActions(page, context, profile) {
  await gotoRoute(page, context, profile, "nexora-dashboard");
  await page
    .locator('#page-nexora-dashboard [data-action="expense"]')
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
  await gotoRoute(page, context, profile, "nexora-dashboard");
  await page
    .locator('#page-nexora-dashboard [data-action="income"]')
    .first()
    .click();
  await waitForRoute(page, "nexora-finance");
  await page
    .locator("#page-nexora-finance .nxr-source-create.nxr-card-highlight")
    .waitFor({ state: "visible", timeout: 60_000 });
}

async function validateReports(page, context, profile) {
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
      document.querySelector("#page-nexora-reports .nxr-report-title")?.textContent?.includes("FI02"),
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

async function validateClosing(page, context, profile) {
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

async function validateManifest(page) {
  await page
    .locator('link[rel="manifest"][data-nexora="1"]')
    .waitFor({ state: "attached", timeout: 30_000 });
  const result = await page.evaluate(async () => {
    const link = document.querySelector('link[rel="manifest"][data-nexora="1"]');
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

async function validateResponsiveLayout(page, profile) {
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
  assert.deepEqual(result.overflowing, [], `iPhone overflow: ${JSON.stringify(result)}`);
  profile.responsive = result;
}

async function validateRealtime(page, profile) {
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

async function captureFailure(page, profile, error) {
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

async function runProfile(browserType, name, contextOptions, { pwa = false } = {}) {
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
    assert.deepEqual(profile.console_errors, [], `${name} emitted console errors.`);
    assert.deepEqual(profile.server_errors, [], `${name} received HTTP 5xx responses.`);
    assert.deepEqual(profile.auth_errors, [], `${name} received authorization errors.`);
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
