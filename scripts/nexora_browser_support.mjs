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
 *
 * Vive aquí (no en nexora_browser_smoke.mjs, donde nació) porque la auditoría visual de
 * los módulos prioritarios (validateModuleGallery, nexora_browser_validators.mjs) también
 * necesita capturar pantalla, y el arnés de soporte es lo único que ambos archivos ya
 * importan sin crear un ciclo entre ellos.
 */
export async function capture(page, profile, file) {
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

function isTransient(value) {
  return transientPatterns.some((pattern) => pattern.test(String(value)));
}

export async function browserRequest(page, target, options = {}) {
  const { body, headers = {}, ...requestOptions } = options;
  const response = await page
    .context()
    .request.fetch(new URL(target, baseURL).toString(), {
      ...requestOptions,
      headers: {
        "X-Frappe-Site-Name": siteName,
        ...headers,
      },
      data: body,
      failOnStatusCode: false,
      timeout: browserRequestTimeoutMs,
    });
  const result = {
    ok: response.ok(),
    status: response.status(),
    url: response.url(),
    text: await response.text(),
    payload: null,
  };
  await response.dispose();
  try {
    result.payload = JSON.parse(result.text);
  } catch {
    result.payload = null;
  }
  return result;
}

// Frappe devuelve el motivo real del rechazo en `_server_messages` (un JSON dentro
// de otro JSON) y el tipo en `exc_type`. Sin desempaquetarlo, un recorrido fallido
// solo informa `false !== true` y obliga a adivinar qué regla se incumplio.
export function serverReason(body) {
  if (!body) return "";
  let payload = body;
  if (typeof body === "string") {
    try {
      payload = JSON.parse(body);
    } catch {
      return body
        .replace(/<[^>]+>/g, " ")
        .trim()
        .slice(0, 500);
    }
  }
  const reasons = [];
  const raw = payload?._server_messages;
  if (typeof raw === "string") {
    try {
      for (const entry of JSON.parse(raw)) {
        try {
          reasons.push(String(JSON.parse(entry)?.message ?? entry));
        } catch {
          reasons.push(String(entry));
        }
      }
    } catch {
      reasons.push(raw);
    }
  }
  if (payload?.exc_type) reasons.push(`exc_type=${payload.exc_type}`);
  if (!reasons.length && payload?.exception)
    reasons.push(String(payload.exception));
  return reasons
    .join(" · ")
    .replace(/<[^>]+>/g, " ")
    .replace(/\s+/g, " ")
    .trim()
    .slice(0, 500);
}

/**
 * Falla nombrando el estado HTTP y el mensaje que devolvio el servidor.
 * Acepta tanto una `Response` de Playwright como el objeto de `browserRequest`.
 */
export async function assertResponseOk(response, label) {
  const isPlaywright = typeof response.status === "function";
  const ok = isPlaywright ? response.ok() : response.ok;
  if (ok) return;
  const status = isPlaywright ? response.status() : response.status;
  let text = "";
  try {
    text = isPlaywright ? await response.text() : String(response.text ?? "");
  } catch {
    text = "";
  }
  const reason = serverReason(text);
  assert.fail(
    `${label} failed with HTTP ${status}${reason ? `: ${reason}` : "."}`
  );
}

/**
 * Resume en una linea lo que la pagina venia gritando mientras el recorrido
 * esperaba. El informe JSON solo existe dentro del artefacto comprimido, y el
 * log de CI es el unico canal que siempre se puede leer: sin esto, una excepcion
 * de JavaScript ocurrida a mitad del recorrido queda invisible hasta que alguien
 * descarga el zip, y el rojo se lee como un simple «Timeout».
 */
export function describeSignals(profile) {
  const render = (row) =>
    typeof row === "string" ? row : `HTTP ${row?.status} ${row?.url}`;
  const parts = [];
  for (const [label, rows] of [
    ["page errors", profile?.page_errors],
    ["console errors", profile?.console_errors],
    ["server errors", profile?.server_errors],
    ["authorization errors", profile?.auth_errors],
  ]) {
    if (rows?.length) parts.push(`${label}: ${rows.map(render).join(" · ")}`);
  }
  if (!parts.length) return " — the page reported no errors.";
  return ` — ${parts.join(" | ").replace(/\s+/g, " ").slice(0, 1500)}`;
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
  const form = new URLSearchParams();
  for (const [key, value] of Object.entries(args)) {
    form.set(
      key,
      value !== null && typeof value === "object"
        ? JSON.stringify(value)
        : String(value ?? "")
    );
  }
  return browserRequest(page, `/api/method/${method}`, {
    method: "POST",
    headers: {
      "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
      "X-Frappe-Site-Name": siteName,
      "X-Frappe-CSRF-Token": csrfToken,
    },
    body: form.toString(),
  });
}

/**
 * Un `waitForResponse` que expira solo dice «Timeout … waiting for event "response"»: no
 * dice qué llamada se esperaba ni desde qué pantalla, y el recorrido tiene ocho. Aquí
 * cada espera lleva su nombre, de modo que el fallo distinga «la pantalla no pidió la
 * vista previa» de «no pidió el detalle de la búsqueda».
 *
 * Corrección real (bug preexistente del arnés, no de ninguna pantalla): los 16
 * llamadores de esta función crean la promesa antes de la acción que dispara la
 * respuesta y la esperan después — necesario para no perder la respuesta por una
 * carrera. Si esa acción intermedia falla primero por cualquier otra razón, esta
 * promesa queda huérfana: nadie la espera nunca. Cuando el perfil cierra el
 * contexto en su `finally`, `waitForResponse` rechaza con «Target page, context or
 * browser has been closed», ese rechazo dispara el `.catch` de abajo, que vuelve a
 * lanzar — y como ya no hay nadie escuchando esa promesa concreta, Node la trata
 * como un rechazo no manejado y mata el proceso entero, borrando el diagnóstico
 * real del fallo original. El manejador silencioso de la línea siguiente no
 * cambia lo que recibe quien sí espera la promesa (ambos manejadores conviven en
 * la misma promesa): solo evita que Node la considere huérfana cuando nadie más
 * la espera. Ver `nexora_browser_support.test.mjs` para la prueba de regresión.
 */
export function apiResponse(page, fragment, label) {
  const response = page
    .waitForResponse(
      (candidate) =>
        candidate.url().includes(fragment) &&
        candidate.request().method() === "POST",
      { timeout: 120_000 }
    )
    .catch((error) => {
      throw new Error(
        `La pantalla nunca pidió «${label}» (${fragment}) en 120 s.`,
        { cause: error }
      );
    });
  response.catch(() => {});
  return response;
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

/**
 * El acceso es la primera pantalla del producto y durante mucho tiempo fue la del marco.
 * Que responda no basta: si el recorrido solo comprueba que `/login` devuelve 200, la
 * pantalla de NEXORA puede desaparecer y nadie se entera hasta que alguien la abre.
 *
 * Se comprueba lo que hace a esa pantalla ser la nuestra: la marca, la promesa, las tres
 * garantías, el formulario operable y —lo que de verdad importa— que el usuario pueda
 * entrar escribiendo y pulsando, no solo llamando a la API.
 */
export async function validateLoginSurface(page, profile) {
  const login = page.locator(".nxr-login");
  await login.waitFor({ state: "visible", timeout: 60_000 });
  // En el teléfono el lienzo de marca se retira a propósito y la marca vive sobre el
  // formulario. Leer la primera del DOM devolvería la oculta —`innerText` de un elemento
  // que no se pinta es vacío— y el perfil de iPhone fallaría sobre un diseño correcto.
  const visibleBrand = login.locator(".nxr-brand__word:visible").first();
  await visibleBrand.waitFor({ state: "visible", timeout: 30_000 });
  const brand = normalizedText(await visibleBrand.innerText());
  assert.equal(
    brand,
    "NEXORA",
    "La pantalla de acceso no lleva la marca del producto."
  );

  const assurances = await login.locator(".nxr-login__assurances li").count();
  assert.equal(
    assurances,
    3,
    `La pantalla de acceso mostró ${assurances} garantías en vez de las tres que declara el servidor.`
  );

  for (const selector of ["#nxr-usr", "#nxr-pwd", "#nxr-submit"]) {
    const field = login.locator(selector);
    assert.equal(
      await field.count(),
      1,
      `La pantalla de acceso no expone ${selector}.`
    );
  }
  // El error tiene su sitio reservado antes de existir: si se insertara al fallar, el
  // formulario se desplazaría y el usuario pulsaría donde ya no está el botón.
  assert.equal(
    await login.locator("#nxr-feedback").count(),
    1,
    "La pantalla de acceso no reserva el espacio del mensaje de error."
  );
  profile.login_surface = {
    brand,
    assurances,
    password_reveal: Boolean(await login.locator("#nxr-reveal").count()),
  };
}

export async function authenticate(page, context, profile) {
  await context.clearCookies();
  await page.goto(`${baseURL}/login`, {
    waitUntil: "domcontentloaded",
    timeout: 120_000,
  });
  await validateLoginSurface(page, profile);
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
  await assertResponseOk(login, "Login request");
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
