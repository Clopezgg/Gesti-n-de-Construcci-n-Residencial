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
const ignoredConsolePatterns = [
  /^Viewport argument key "minimal-ui" not recognized and ignored\.$/,
];
const transientRealtimePatterns = [
  /Error connecting to socket\.io: xhr poll error/i,
  /WebSocket connection to .*\/socket\.io\/.*closed before the connection is established/i,
  /XMLHttpRequest cannot load .*\/socket\.io\/.*transport=polling.*access control checks/i,
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

function matchesAny(value, patterns) {
  return patterns.some((pattern) => pattern.test(String(value)));
}

function safeName(value) {
  return String(value)
    .replace(/[^a-z0-9_-]+/gi, "-")
    .toLowerCase();
}

async function browserRequest(page, url, options = {}) {
  return page.evaluate(
    async ({ target, requestOptions }) => {
      const response = await fetch(target, {
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
    { target: url, requestOptions: options }
  );
}

async function snapshotSession(page, context, stage) {
  const cookies = (await context.cookies(baseURL))
    .filter((cookie) => cookie.name === "sid")
    .map((cookie) => ({
      domain: cookie.domain,
      path: cookie.path,
      httpOnly: cookie.httpOnly,
      secure: cookie.secure,
      sameSite: cookie.sameSite,
      is_guest: !cookie.value || cookie.value === "Guest",
    }));
  const server = await browserRequest(
    page,
    "/api/method/frappe.auth.get_logged_user"
  );
  const browserUser = await page.evaluate(
    () => window.frappe?.session?.user || null
  );
  return {
    stage,
    cookies,
    browser_user: browserUser,
    server_status: server.status,
    server_user: server.payload?.message || null,
  };
}

async function assertAuthenticated(
  page,
  context,
  profile,
  stage,
  { requireBrowserUser = true } = {}
) {
  const snapshot = await snapshotSession(page, context, stage);
  profile.auth_snapshots.push(snapshot);
  assert(
    snapshot.cookies.some((cookie) => cookie.path === "/" && !cookie.is_guest),
    `${stage}: the root Frappe sid cookie is missing or belongs to Guest.`
  );
  assert.equal(
    snapshot.server_status,
    200,
    `${stage}: session probe returned HTTP ${snapshot.server_status}.`
  );
  assert.equal(
    snapshot.server_user,
    "Administrator",
    `${stage}: server session is ${snapshot.server_user || "unknown"}.`
  );
  if (requireBrowserUser) {
    assert.equal(
      snapshot.browser_user,
      "Administrator",
      `${stage}: browser session is ${snapshot.browser_user || "unknown"}.`
    );
  }
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
  assert.equal(
    login.ok,
    true,
    `Browser login failed with HTTP ${login.status}.`
  );
  assert.equal(
    login.payload.message,
    "Logged In",
    `Unexpected login response: ${JSON.stringify(login.payload)}`
  );
  await assertAuthenticated(page, context, profile, "after-login", {
    requireBrowserUser: false,
  });

  const response = await page.goto(`${baseURL}/app/nexora-dashboard`, {
    waitUntil: "domcontentloaded",
    timeout: 120_000,
  });
  assert(response, "The canonical dashboard returned no response.");
  assert(
    response.status() < 400,
    `The canonical dashboard returned HTTP ${response.status()}.`
  );
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
    if (matchesAny(text, transientRealtimePatterns)) {
      profile.transient_realtime_messages.push(text);
    } else {
      profile.page_errors.push(text);
    }
  });
  page.on("console", (message) => {
    if (message.type() !== "error") return;
    const text = message.text();
    if (matchesAny(text, ignoredConsolePatterns)) {
      profile.ignored_console_messages.push(text);
    } else if (matchesAny(text, transientRealtimePatterns)) {
      profile.transient_realtime_messages.push(text);
    } else {
      profile.console_errors.push(text);
    }
  });
  page.on("response", (response) => {
    const status = response.status();
    const url = response.url();
    if (status >= 500) {
      profile.server_errors.push({ status, url });
    } else if (
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
    .locator(`#page-${route} .layout-main-section`)
    .first()
    .waitFor({ state: "visible", timeout: 30_000 });
  await page
    .locator(`#page-${route} .nxr-product-shell`)
    .first()
    .waitFor({ state: "visible", timeout: 30_000 });
}

async function assertRouteContent(page, route) {
  const text = await page.locator(`#page-${route}`).innerText();
  assert(
    !/page not found|404 not found|inicie sesi[oó]n para acceder/i.test(text),
    `${route} rendered an unavailable or unauthenticated page.`
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
  await assertRouteContent(page, route);
  await assertAuthenticated(page, context, profile, `after-route:${route}`);
}

async function validateDirectRoutes(page, profile) {
  for (const route of routes) {
    const response = await browserRequest(page, `/app/${route}`);
    assert.equal(
      response.status,
      200,
      `Direct route /app/${route} returned HTTP ${response.status}.`
    );
    assert(
      !/page not found|404 not found/i.test(response.text),
      `Direct route /app/${route} returned a not-found document.`
    );
    profile.direct_routes.push(route);
  }
}

async function readDashboardApi(page) {
  const csrfToken = await page.evaluate(
    () => window.frappe?.csrf_token || window.csrf_token || ""
  );
  const response = await browserRequest(
    page,
    "/api/method/nexora.dashboard.service.get_dashboard_summary",
    {
      method: "POST",
      headers: {
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        "X-Frappe-Site-Name": siteName,
        "X-Frappe-CSRF-Token": csrfToken,
      },
      body: new URLSearchParams({
        payload: JSON.stringify({}),
      }).toString(),
    }
  );
  assert.equal(
    response.ok,
    true,
    `Dashboard API failed with HTTP ${response.status}.`
  );
  const data = response.payload?.message;
  assert(data, "Dashboard API returned no message.");
  assert(
    data.context &&
      Object.prototype.hasOwnProperty.call(data.context, "project") &&
      normalizedText(data.context.project_label).length > 0,
    "Dashboard API returned an invalid canonical project context."
  );
  return data;
}

async function validateDashboard(page, profile) {
  const data = await readDashboardApi(page);
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
  const recentRows = await page
    .locator("#page-nexora-dashboard .nxr-dashboard-recent-rows tbody tr")
    .count();
  assert.equal(recentRows, Math.min(data.recent_operations.length, 6));
  assert(recentRows >= 3, "Recent operations were not rendered.");
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
  await waitForRoute(page, "nexora-dashboard");
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

async function validateQuickActions(page, context, profile) {
  await gotoRoute(page, context, profile, "nexora-dashboard");
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
  await assertAuthenticated(page, context, profile, "quick-action:expense");

  await gotoRoute(page, context, profile, "nexora-dashboard");
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
  await assertAuthenticated(page, context, profile, "quick-action:income");
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
    return { ok: response.ok, payload: await response.json() };
  });
  assert(result, "NEXORA manifest link is missing.");
  assert.equal(result.ok, true, "NEXORA manifest request failed.");
  assert.equal(result.payload.id, "/app/nexora-dashboard");
  assert.equal(result.payload.start_url, "/app/nexora-dashboard");
  assert.equal(result.payload.scope, "/app/");
  assert.equal(result.payload.display, "standalone");
  assert.deepEqual(result.payload.display_override, ["standalone"]);
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
    const cacheNames = await caches.keys();
    const cachedUrls = [];
    for (const name of cacheNames.filter((item) =>
      item.startsWith("nexora-shell-")
    )) {
      const cache = await caches.open(name);
      cachedUrls.push(...(await cache.keys()).map((request) => request.url));
    }
    return {
      active: registration?.active?.scriptURL || "",
      scope: registration?.scope || "",
      cache_names: cacheNames.filter((item) =>
        item.startsWith("nexora-shell-")
      ),
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
  profile.pwa = { manifest, ...state, offline_banner: "passed" };
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
  assert.equal(
    profile.realtime.connected,
    true,
    "Frappe realtime did not remain connected."
  );
}

async function validateResponsiveLayout(page, profile) {
  const layout = await page.evaluate(() => {
    const viewportWidth = window.innerWidth;
    const overflowing = [];
    for (const selector of [
      ".nxr-dashboard-shell",
      ".nxr-card",
      ".nxr-balance-row",
      ".nxr-list-row",
      ".nxr-evidence-tile",
    ]) {
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
  try {
    await page.screenshot({
      path: path.join(artifactRoot, `${safeName(profile.name)}-failure.png`),
      fullPage: true,
    });
  } catch {
    // The JSON report remains available when screenshot capture is impossible.
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
    direct_routes: [],
    auth_snapshots: [],
    page_errors: [],
    console_errors: [],
    ignored_console_messages: [],
    transient_realtime_messages: [],
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
    await validateCanonicalHome(page);
    await validateDashboard(page, profile);
    await page.screenshot({
      path: path.join(artifactRoot, `${safeName(name)}-dashboard.png`),
      fullPage: true,
    });
    if (name.includes("iphone")) {
      await validateResponsiveLayout(page, profile);
    }
    await validateQuickActions(page, context, profile);
    for (const route of routes) {
      await gotoRoute(page, context, profile, route);
      profile.routes.push(route);
    }
    await validateDirectRoutes(page, profile);
    await gotoRoute(page, context, profile, "nexora-dashboard");
    await validateManifest(page);
    if (pwa) await validatePwa(page, context, profile);
    await validateRealtime(page, profile);
    await assertAuthenticated(page, context, profile, "profile-complete");

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
    assert.deepEqual(
      profile.auth_errors,
      [],
      `${name} received unauthorized responses: ${JSON.stringify(
        profile.auth_errors
      )}`
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
