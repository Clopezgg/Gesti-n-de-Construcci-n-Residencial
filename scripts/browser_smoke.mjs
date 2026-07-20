import assert from "node:assert/strict";
import fs from "node:fs/promises";
import path from "node:path";
import process from "node:process";

import { chromium, devices } from "playwright";

const baseURL = String(
  process.env.CONSTRUCONTROL_BASE_URL || "http://127.0.0.1:8080"
).replace(/\/$/, "");
const siteName = String(process.env.SITE_NAME || "construcontrol-ci");
const adminPassword = String(process.env.ADMIN_PASSWORD || "");
const artifactRoot = path.resolve(
  process.env.BROWSER_ARTIFACT_DIR || "artifacts/gate-c/browser"
);
const routes = [
  "construcontrol-dashboard",
  "construcontrol-profile",
  "construcontrol-project-center",
  "construcontrol-users",
  "construcontrol-integrations",
  "construcontrol-reporting-center",
  "construcontrol-weekly-closing",
  "construcontrol-migration-console",
];

assert(
  adminPassword,
  "ADMIN_PASSWORD is required for the browser certification."
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
    `Login failed with HTTP ${response.status()}`
  );
  const payload = await response.json();
  assert.equal(
    payload.message,
    "Logged In",
    `Unexpected login response: ${JSON.stringify(payload)}`
  );
}

async function waitForDesk(page, route) {
  const stateHandle = await page.waitForFunction(
    (expected) => {
      const current = window.frappe?.get_route?.() || [];
      const currentRoute = current[0] || "";
      const bodyLength = document.body?.innerText?.trim().length || 0;
      const pathname = window.location.pathname;
      if (currentRoute === expected && bodyLength > 20) {
        return { ready: true, currentRoute, bodyLength, pathname };
      }
      if (
        currentRoute === "setup-wizard" ||
        pathname.includes("/setup-wizard") ||
        pathname === "/login"
      ) {
        return {
          ready: false,
          currentRoute: currentRoute || "login",
          bodyLength,
          pathname,
        };
      }
      return null;
    },
    route,
    { timeout: 120_000 }
  );
  const state = await stateHandle.jsonValue();
  await stateHandle.dispose();
  assert.equal(
    state.ready,
    true,
    `${route} was blocked by ${state.currentRoute || "unknown"} at ${
      state.pathname || "unknown"
    }`
  );
  await page
    .locator(".page-container, .layout-main-section, .page-head")
    .first()
    .waitFor({
      state: "visible",
      timeout: 120_000,
    });
}

async function exercisePwa(page) {
  const manifest = await page.evaluate(async () => {
    const link = document.querySelector('link[rel="manifest"]');
    if (!link) return null;
    const response = await fetch(link.href, {
      cache: "no-store",
      credentials: "same-origin",
    });
    return { href: link.href, ok: response.ok, payload: await response.json() };
  });
  assert(manifest, "Manifest link is missing from the Desk document.");
  assert.equal(manifest.ok, true, "Manifest request failed.");
  assert.equal(manifest.payload.start_url, "/app/construcontrol-dashboard");
  const iconSizes = new Set(
    (manifest.payload.icons || []).map((icon) => icon.sizes)
  );
  assert(iconSizes.has("192x192"), "PWA manifest lacks the 192x192 icon.");
  assert(iconSizes.has("512x512"), "PWA manifest lacks the 512x512 icon.");

  const evidenceInput = await page.evaluate(async () => {
    const input = document.createElement("input");
    input.type = "file";
    input.setAttribute("capture", "environment");
    document.body.appendChild(input);
    await new Promise((resolve) => window.setTimeout(resolve, 250));
    const result = {
      accept: input.accept,
      camera_gallery: input.getAttribute("data-cc-camera-gallery") || "",
      capture: input.getAttribute("capture"),
    };
    input.remove();
    return result;
  });
  assert.match(evidenceInput.accept, /image\/\*/);
  assert.match(evidenceInput.accept, /application\/pdf/);
  assert.equal(evidenceInput.camera_gallery, "enabled");
  assert.equal(evidenceInput.capture, null);

  const duplicateGuard = await page.evaluate(async () => {
    let accepted = 0;
    const button = document.createElement("button");
    button.className = "primary-action";
    button.addEventListener("click", () => {
      accepted += 1;
    });
    document.body.appendChild(button);
    button.click();
    button.click();
    await new Promise((resolve) => window.setTimeout(resolve, 50));
    button.remove();
    return accepted;
  });
  assert.equal(
    duplicateGuard,
    1,
    "Duplicate save guard accepted two immediate actions."
  );

  await page.waitForFunction(
    async () => Boolean(await navigator.serviceWorker?.getRegistration?.("/")),
    undefined,
    { timeout: 120_000 }
  );
  const serviceWorker = await page.evaluate(async () => {
    const registration = await navigator.serviceWorker.getRegistration("/");
    return {
      active: registration?.active?.scriptURL || "",
      scope: registration?.scope || "",
    };
  });
  assert.match(serviceWorker.active, /construcontrol-service-worker\.js/);
  assert.match(serviceWorker.scope, /\/$/);

  const versionResponse = await page.evaluate(async () => {
    const response = await fetch(
      "/assets/erpnext/construcontrol/deploy-version.json",
      {
        cache: "no-store",
        credentials: "same-origin",
      }
    );
    return { ok: response.ok, payload: await response.json() };
  });
  assert.equal(versionResponse.ok, true, "Deploy version endpoint failed.");
  assert(
    versionResponse.payload.version,
    "Deploy version has no version value."
  );

  return {
    manifest_href: manifest.href,
    service_worker: serviceWorker,
    deploy_version: versionResponse.payload.version,
    duplicate_guard_accepted: duplicateGuard,
    evidence_input: evidenceInput,
  };
}

async function exerciseProfile(browser, name, contextOptions) {
  const context = await browser.newContext({
    ...contextOptions,
    baseURL,
    extraHTTPHeaders: { "X-Frappe-Site-Name": siteName },
  });
  const profile = { name, routes: [], page_errors: [], server_errors: [] };
  try {
    await authenticate(context);
    const page = await context.newPage();
    page.on("pageerror", (error) => profile.page_errors.push(String(error)));
    page.on("response", (response) => {
      if (response.status() >= 500) {
        profile.server_errors.push({
          status: response.status(),
          url: response.url(),
        });
      }
    });

    for (const route of routes) {
      const response = await page.goto(`${baseURL}/app/${route}`, {
        waitUntil: "domcontentloaded",
        timeout: 120_000,
      });
      assert(response, `${route} returned no navigation response.`);
      assert(
        response.status() < 400,
        `${route} returned HTTP ${response.status()}`
      );
      await waitForDesk(page, route);
      const bodyText = await page.locator("body").innerText();
      assert(
        !/404|page not found|not found/i.test(bodyText),
        `${route} rendered a not-found page.`
      );
      const screenshot = path.join(
        artifactRoot,
        `${safeName(name)}-${route}.png`
      );
      await page.screenshot({ path: screenshot, fullPage: true });
      profile.routes.push({
        route,
        screenshot,
        body_length: bodyText.trim().length,
      });
    }

    await page.goto(`${baseURL}/app/construcontrol-dashboard`, {
      waitUntil: "domcontentloaded",
      timeout: 120_000,
    });
    await waitForDesk(page, "construcontrol-dashboard");
    await page.evaluate(() =>
      window.frappe.set_route("construcontrol-profile")
    );
    await waitForDesk(page, "construcontrol-profile");
    await page.goBack({ waitUntil: "domcontentloaded" });
    await waitForDesk(page, "construcontrol-dashboard");

    profile.pwa = await exercisePwa(page);
    assert.deepEqual(profile.page_errors, [], `${name} emitted page errors.`);
    assert.deepEqual(
      profile.server_errors,
      [],
      `${name} received HTTP 5xx responses.`
    );
    profile.viewport = page.viewportSize();
    return profile;
  } finally {
    await context.close();
  }
}

const browser = await chromium.launch({ headless: true });
try {
  report.profiles.push(
    await exerciseProfile(browser, "desktop", {
      viewport: { width: 1440, height: 900 },
    })
  );
  report.profiles.push(
    await exerciseProfile(browser, "iphone-13", {
      ...devices["iPhone 13"],
    })
  );
  report.completed_at = new Date().toISOString();
  report.ok = true;
} catch (error) {
  report.completed_at = new Date().toISOString();
  report.ok = false;
  report.error = error?.stack || String(error);
  throw error;
} finally {
  await fs.writeFile(
    path.join(artifactRoot, "browser-report.json"),
    `${JSON.stringify(report, null, 2)}\n`
  );
  await browser.close();
}
