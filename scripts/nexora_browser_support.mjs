import assert from "node:assert/strict";
import path from "node:path";
import process from "node:process";

export const baseURL = String(
  process.env.NEXORA_BASE_URL || "http://127.0.0.1:8080"
).replace(/\/$/, "");
export const siteName = String(process.env.SITE_NAME || "nexora-ui-ci");
export const adminPassword = String(process.env.ADMIN_PASSWORD || "");
export const artifactRoot = path.resolve(
  process.env.BROWSER_ARTIFACT_DIR || "artifacts/nexora-ui/browser"
);
export const browserRequestTimeoutMs = Number.parseInt(
  process.env.NEXORA_BROWSER_REQUEST_TIMEOUT_MS || "120000",
  10
);
export const routes = [
  "nexora-dashboard",
  "nexora-operations",
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

export function normalizedText(value) {
  return String(value || "")
    .replace(/\s+/g, " ")
    .trim();
}

export function safeName(value) {
  return String(value)
    .replace(/[^a-z0-9_-]+/gi, "-")
    .toLowerCase();
}

function isTransient(value) {
  return transientPatterns.some((pattern) => pattern.test(String(value)));
}

export async function browserRequest(page, target, options = {}) {
  return page.evaluate(
    async ({ url, requestOptions, timeoutMs }) => {
      const controller = new AbortController();
      const timer = window.setTimeout(
        () =>
          controller.abort(
            new Error(`Browser request exceeded ${timeoutMs} ms: ${url}`)
          ),
        timeoutMs
      );
      try {
        const response = await fetch(url, {
          credentials: "include",
          cache: "no-store",
          ...requestOptions,
          signal: controller.signal,
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
      } finally {
        window.clearTimeout(timer);
      }
    },
    {
      url: target,
      requestOptions: options,
      timeoutMs: browserRequestTimeoutMs,
    }
  );
}

export async function postMethod(page, method, payload = {}) {
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

export async function postArgs(page, method, args = {}) {
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
    body: new URLSearchParams(args).toString(),
  });
}

export async function assertAuthenticated(page, context, profile, stage) {
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
      (cookie) =>
        cookie.path === "/" && cookie.value && cookie.value !== "Guest"
    ),
  });
  assert(
    cookies.some(
      (cookie) =>
        cookie.path === "/" && cookie.value && cookie.value !== "Guest"
    ),
    `${stage}: authenticated root sid cookie is missing.`
  );
  assert.equal(server.status, 200, `${stage}: session probe failed.`);
  assert.equal(
    server.payload?.message,
    "Administrator",
    `${stage}: server user changed.`
  );
  assert.equal(browserUser, "Administrator", `${stage}: browser user changed.`);
}

export async function authenticate(page, context, profile) {
  await context.clearCookies();
  await page.goto(`${baseURL}/login`, {
    waitUntil: "domcontentloaded",
    timeout: 120_000,
  });
  const login = await browserRequest(page, "/api/method/login", {
    method: "POST",
    headers: {
      "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
      "X-Frappe-Site-Name": siteName,
    },
    body: new URLSearchParams({
      usr: "Administrator",
      pwd: adminPassword,
    }).toString(),
  });
  assert.equal(login.ok, true, `Login failed with HTTP ${login.status}.`);
  assert.equal(
    login.payload.message,
    "Logged In",
    "Unexpected login response."
  );
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

export function watchPage(page, profile) {
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

export async function waitForRoute(page, route) {
  let routeSnapshot;
  try {
    const handle = await page.waitForFunction(
      (expected) => {
        const current = window.frappe?.get_route?.() || [];
        const container = document.querySelector(`#page-${expected}`);
        const text = String(container?.innerText || "");
        const ready =
          current[0] === expected &&
          Boolean(container?.offsetParent) &&
          !/page not found|404 not found|inicie sesi[oó]n para acceder/i.test(
            text
          );
        return ready
          ? {
              url: window.location.href,
              frappe_route: current,
              page_visible: true,
              page_text: text,
            }
          : null;
      },
      route,
      { timeout: 120_000 }
    );
    routeSnapshot = await handle.jsonValue();
    await handle.dispose();
  } catch (error) {
    const diagnostics = await page.evaluate((expected) => {
      const container = document.querySelector(`#page-${expected}`);
      return {
        url: window.location.href,
        frappe_route: window.frappe?.get_route?.() || [],
        page_exists: Boolean(container),
        page_visible: Boolean(container?.offsetParent),
        page_text: String(container?.innerText || "").slice(0, 1000),
      };
    }, route);
    throw new Error(
      `${route} did not reach a stable rendered state: ${JSON.stringify(
        diagnostics
      )}`,
      { cause: error }
    );
  }
  const text = String(routeSnapshot?.page_text || "");
  assert(
    !/page not found|404 not found|inicie sesi[oó]n para acceder/i.test(text),
    `${route} rendered an unavailable page.`
  );
  return routeSnapshot;
}

export async function gotoRoute(page, context, profile, route) {
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

export async function validateDirectRoutes(page, profile) {
  for (const route of routes) {
    const response = await browserRequest(page, `/app/${route}`);
    assert.equal(
      response.status,
      200,
      `/app/${route} returned HTTP ${response.status}.`
    );
    assert(
      !/page not found|404 not found/i.test(response.text),
      `/app/${route} returned a not-found document.`
    );
    profile.direct_routes.push(route);
  }
}
