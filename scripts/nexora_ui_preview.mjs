/**
 * NEXORA · Vista previa visual
 * ============================
 *
 * El recorrido en navegador real comprueba que las pantallas **funcionan**; este script
 * enseña cómo **se ven**. Son dos preguntas distintas y ninguna responde a la otra: una
 * pantalla puede pasar todas las etapas y seguir pareciendo un formulario de 2011.
 *
 * Monta las hojas del producto sobre el marcado real —la plantilla de acceso con sus
 * variables resueltas, y la carcasa tal como la construye `nexora_shell.js`— y captura
 * cada superficie en escritorio, tableta y teléfono. No sustituye al recorrido: no toca el
 * servidor ni prueba nada. Sirve para poder mirar el resultado sin desplegar.
 *
 *   node scripts/nexora_ui_preview.mjs
 */

import fs from "node:fs/promises";
import path from "node:path";
import process from "node:process";

// Playwright puede vivir fuera del proyecto (por ejemplo en un entorno de trabajo sin
// dependencias instaladas): se resuelve en tiempo de ejecución para no exigir su sitio.
const { chromium } = await import(
  process.env.NEXORA_PLAYWRIGHT || "playwright"
);

const root = process.cwd();
const outDir = path.resolve(
  process.env.NEXORA_PREVIEW_DIR || "artifacts/nexora-ui/preview"
);
const cssDir = path.join(root, "nexora_app/nexora/public/css");

const VIEWPORTS = [
  { name: "escritorio", width: 1440, height: 900 },
  { name: "tableta", width: 834, height: 1112 },
  { name: "telefono", width: 390, height: 844 },
];

const read = (file) => fs.readFile(file, "utf-8");

/**
 * La plantilla de acceso es Jinja. Aquí se resuelve lo mínimo para poder mirarla: las
 * tres garantías que declara el servidor y las cadenas traducibles. No se reimplementa la
 * plantilla —eso crearía una segunda versión que divergiría—: se sustituye sobre el
 * archivo real, de modo que un cambio en él se ve aquí sin tocar nada.
 */
async function renderLogin() {
  const source = await read(
    path.join(root, "nexora_app/nexora/www/login.html")
  );
  const body = source
    .split("{% block page_content %}")[1]
    .split("{% endblock %}")[0];
  const script = source
    .split("{% block script %}")[1]
    .split("{% endblock %}")[0];

  const assurances = [
    [
      "Libro inmutable",
      "Ningún documento contabilizado se edita ni se borra: se corrige dejando rastro.",
    ],
    [
      "Segregación de funciones",
      "Solicitar, aprobar y ejecutar son siempre tres personas distintas.",
    ],
    [
      "Cierre semanal certificado",
      "Cada semana queda cerrada con su huella verificable y su respaldo.",
    ],
  ];

  let html = body;
  // El macro de marca se expande una vez y se reutiliza en los dos sitios donde aparece.
  const brand = html
    .split("{%- macro brand() -%}")[1]
    .split("{%- endmacro -%}")[0];
  html = html.replace(
    /\{%-? macro brand\(\) -?%\}[\s\S]*?\{%-? endmacro -?%\}/,
    ""
  );
  html = html.replaceAll("{{ brand() }}", brand);

  // El bucle de garantías.
  const loop = html
    .split("{%- for item in nexora_assurances %}")[1]
    .split("{%- endfor %}")[0];
  html = html.replace(
    /\{%-? for item in nexora_assurances %\}[\s\S]*?\{%-? endfor %\}/,
    assurances
      .map(([title, detail]) =>
        loop
          .replaceAll("{{ item.title }}", title)
          .replaceAll("{{ item.detail }}", detail)
      )
      .join("\n")
  );

  // Ramas condicionales: se muestra el camino que ve un usuario normal.
  html = html.replace(/\{%-? if not disable_user_pass_login %\}/, "");
  html =
    html.split("{%- else %}")[0] +
    html.split("{%- endif %}").slice(1).join("{%- endif %}");
  html = html.replace(
    /\{%-? if login_with_email_link %\}[\s\S]*?\{%-? endif %\}/g,
    ""
  );
  html = html.replace(
    /\{%-? if provider_logins %\}[\s\S]*?\{%-? endif %\}/g,
    ""
  );

  // Cadenas traducibles y variables sueltas.
  html = html.replace(/\{\{ _\('([^']*)'\) \}\}/g, "$1");
  html = html.replace(/\{\{ _\("([^"]*)"\) \}\}/g, "$1");
  html = html.replace(/\{\{ login_label or _\("([^"]*)"\) \}\}/g, "$1");
  html = html.replace(/\{\{ nexora_home \}\}/g, "/app/nexora-dashboard");
  html = html.replace(/\{[{%][\s\S]*?[%}]\}/g, "");

  return { html, script };
}

/**
 * La carcasa la construye JavaScript. En vez de copiar su marcado —que se quedaría atrás
 * al primer cambio—, se ejecuta el módulo real dentro de la página con lo justo de Frappe
 * para que arranque, y se captura lo que produce.
 */
const SHELL_HARNESS = `
	window.frappe = {
		provide: (name) => {
			const parts = name.split(".");
			let target = window;
			for (const part of parts) target = target[part] = target[part] || {};
		},
		get_route: () => ["nexora-dashboard"],
		boot: { home_page: "nexora-dashboard" },
		router: { on: () => {} },
		set_route: () => {},
		utils: { escape_html: (value) => String(value).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" })[c]) },
		ready: (fn) => fn(),
	};
	window.__ = (value) => value;
	window.nexora = window.nexora || {};
`;

/** Muestra de la banda de agenda, con la mezcla de severidades que se ve un lunes. */
const AGENDA_SAMPLE = [
  [
    "critical",
    "Pago vencido",
    "Estimación 3 · Constructora del Valle · L 184,200.00",
    "Revisar",
  ],
  [
    "critical",
    "Fondo por debajo del mínimo",
    "Remesa BAC 4471 quedó en L 12,400.00",
    "Ver",
  ],
  [
    "warning",
    "Pago próximo",
    "Anticipo materiales · Ferretería Sula · L 63,900.00",
    "Revisar",
  ],
  [
    "warning",
    "Ingresos sin conciliar",
    "3 ingreso(s) esperan su respaldo documental.",
    "Conciliar",
  ],
  [
    "info",
    "Cierre semanal sin confirmar",
    "La semana del 27 al 2 sigue abierta.",
    "Cerrar",
  ],
];

function agendaMarkup() {
  const rows = AGENDA_SAMPLE.map(
    ([level, title, detail, action]) =>
      '<li class="nxr-agenda-item" data-level="' +
      level +
      '"><span class="nxr-agenda-mark"></span><span class="nxr-agenda-text"><strong>' +
      title +
      "</strong><small>" +
      detail +
      '</small></span><button type="button" class="nxr-agenda-action">' +
      action +
      "</button></li>"
  ).join("");
  return (
    '<section class="nxr-agenda"><header><h3>Qué requiere su atención hoy</h3>' +
    '<span class="nxr-agenda-count">5 de 7</span></header>' +
    '<ol class="nxr-agenda-list">' +
    rows +
    "</ol></section>"
  );
}

async function capture(page, name, viewport) {
  await page.setViewportSize({
    width: viewport.width,
    height: viewport.height,
  });
  await page.waitForTimeout(150);
  const file = path.join(outDir, `${name}-${viewport.name}.png`);
  await page.screenshot({ path: file });
  return file;
}

async function main() {
  await fs.mkdir(outDir, { recursive: true });
  const [designSystem, loginCss, shellCss, commandCss, shellJs] =
    await Promise.all([
      read(path.join(cssDir, "nexora_design_system.css")),
      read(path.join(cssDir, "nexora_login.css")),
      read(path.join(cssDir, "nexora_shell.css")),
      read(path.join(cssDir, "nexora_command_center.css")),
      read(path.join(root, "nexora_app/nexora/public/js/nexora_shell.js")),
    ]);
  const login = await renderLogin();

  // El entorno puede traer su propio Chromium ya descargado; `NEXORA_CHROMIUM` lo señala.
  const executablePath = process.env.NEXORA_CHROMIUM || undefined;
  const browser = await chromium.launch({ headless: true, executablePath });
  const context = await browser.newContext({
    locale: "es-HN",
    deviceScaleFactor: 2,
  });
  const page = await context.newPage();
  const produced = [];

  // ── Acceso ───────────────────────────────────────────────────────────────
  await page.setContent(
    `<!doctype html><html lang="es"><head><meta charset="utf-8">
		<style>${designSystem}</style><style>${loginCss}</style>
		<style>body{margin:0}</style></head><body>${
      login.html
    }<script>${login.script.replace(
      /<\/?script>/g,
      ""
    )}</script></body></html>`,
    { waitUntil: "domcontentloaded" }
  );
  for (const viewport of VIEWPORTS)
    produced.push(await capture(page, "acceso", viewport));

  // Y el estado de error, que es la mitad del diseño de un formulario.
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.evaluate(() => {
    document.getElementById("nxr-usr").value = "carlos@constructora.hn";
    document.getElementById("nxr-pwd").value = "incorrecta";
    document.getElementById("nxr-feedback").innerHTML =
      '<div class="nxr-ds-notice nxr-ds-notice--danger">Usuario o contraseña incorrectos.</div>';
  });
  produced.push(
    await capture(page, "acceso-error", {
      name: "escritorio",
      width: 1440,
      height: 900,
    })
  );

  // ── Carcasa ──────────────────────────────────────────────────────────────
  const contentSample = `
		<div id="body"><div class="main-section"><div class="page-container">
			<div style="padding:24px 28px">
				<p class="nxr-ds-eyebrow">Resumen ejecutivo</p>
				<h1 class="nxr-ds-title" style="margin:6px 0 20px">Buenos días, Carlos</h1>
				${agendaMarkup()}
				<div style="height:20px"></div>
				<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:16px">
					${[
            ["Disponible", "L 1,284,500.00", "money-in"],
            ["Comprometido", "L 412,900.00", "money-out"],
            ["Ejecutado esta semana", "L 96,340.00", "money-out"],
            ["Comprobantes por revisar", "7", "money-out"],
          ]
            .map(
              ([label, value, tone]) => `
						<div class="nxr-ds-card" style="padding:18px 20px">
							<p class="nxr-ds-eyebrow" style="margin-bottom:10px">${label}</p>
							<p class="nxr-ds-numeric" style="margin:0;font-size:var(--nxr-text-2xl);font-weight:600;color:var(--nxr-${tone})">${value}</p>
						</div>`
            )
            .join("")}
				</div>
			</div>
		</div></div></div>`;

  await page.setContent(
    `<!doctype html><html lang="es"><head><meta charset="utf-8">
		<style>${designSystem}</style><style>${shellCss}</style><style>${commandCss}</style>
		<style>body{margin:0}</style></head><body>${contentSample}
		<script>${SHELL_HARNESS}</script><script>${shellJs}</script></body></html>`,
    { waitUntil: "domcontentloaded" }
  );
  await page.waitForSelector(".nxr-shell", { timeout: 15_000 });
  for (const viewport of VIEWPORTS)
    produced.push(await capture(page, "carcasa", viewport));

  // La navegación contraída: el estado que elige quien trabaja con la tabla ancha.
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.evaluate(() => {
    document.querySelector(".nxr-shell").dataset.collapsed = "true";
  });
  produced.push(
    await capture(page, "carcasa-contraida", {
      name: "escritorio",
      width: 1440,
      height: 900,
    })
  );

  // El cajón abierto en el teléfono.
  await page.setViewportSize({ width: 390, height: 844 });
  await page.evaluate(() => {
    const shell = document.querySelector(".nxr-shell");
    shell.dataset.collapsed = "false";
    shell.dataset.drawer = "open";
    shell.querySelector("[data-shell-close]").hidden = false;
  });
  produced.push(
    await capture(page, "carcasa-cajon", {
      name: "telefono",
      width: 390,
      height: 844,
    })
  );

  await context.close();
  await browser.close();

  for (const file of produced) console.log(path.relative(root, file));
}

await main();
