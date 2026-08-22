frappe.provide("nexora");

/**
 * NEXORA · Carcasa
 * ================
 *
 * Lo que había antes: doce enlaces de texto en una tira con desplazamiento horizontal,
 * inyectados dentro del cuerpo de la página y reconstruidos con `innerHTML` **seis veces
 * por navegación** —temporizadores en 0, 50, 150, 300, 600 y 1000 ms—, sobre el escritorio
 * del marco, con su barra, su logotipo y su buscador arriba. Doce destinos iguales en una
 * fila no son una navegación: son una lista de enlaces, y obligan a leerlos todos cada vez.
 *
 * Lo que hay ahora: una barra superior y una navegación lateral propias, construidas una
 * sola vez y actualizadas por estado, con los destinos agrupados por la pregunta que
 * responde cada grupo. Flotan sobre el contenido; no lo envuelven.
 *
 * Tres reglas de convivencia con Frappe, y las tres importan:
 *
 * 1. La carcasa solo se monta en rutas de NEXORA. Fuera de ellas se desmonta entera y el
 *    escritorio queda exactamente como estaba: este producto vive dentro de una
 *    instalación que también se administra por el escritorio, y romperlo dejaría sin
 *    herramientas a quien la mantiene.
 * 2. No se borra nada del marco. Se oculta con una clase en la raíz y se retira al salir.
 *    Un `remove()` sobre la barra de Frappe sería irreversible sin recargar.
 * 3. **No se mueve nada del marco.** La primera versión reparentaba `#body` —donde el
 *    enrutador construye cada pantalla— dentro de un marco de contenido propio. El
 *    recorrido real lo encontró en los tres perfiles: `#page-nexora-dashboard` dejaba de
 *    existir tras el primer arranque. Mover la raíz que el enrutador usa para montar sus
 *    páginas la desmonta; no la repinta, desaparece. La carcasa se limita a reservar su
 *    espacio con relleno en `<body>` (`nexora_shell.css`) y a flotar por encima.
 */
(() => {
	"use strict";

	const ROOT_CLASS = "nxr-shell-active";
	const COLLAPSE_KEY = "nexora:shell-collapsed";
	const THEME_KEY = "nexora:shell-theme";

	/**
	 * RECONSTRUCCIÓN VISUAL DEFINITIVA (mandato del propietario): la navegación debe
	 * seguir exactamente esta jerarquía de seis grupos por nombre y orden — Inicio,
	 * Núcleo de fondos, Proyectos, Compras e inventario, Reportes e inteligencia,
	 * Administración. Ningún destino real que ya existía se elimina: los que no
	 * tenían una casilla exacta en esa lista (Asistente, Buscador, Notificaciones,
	 * Cotizaciones, Entidades, Calidad, Canales, Proveedores de IA, SAP) se doblan
	 * dentro del grupo más afín en vez de inventarse una ruta nueva o borrarse una
	 * real — "reutiliza todo lo existente que sea correcto" del propio mandato.
	 * "Estados de cuenta"/"Indicadores"/"Exportaciones" no tienen página propia:
	 * son vistas reales dentro de la misma página `nexora-reports` (mismo mecanismo
	 * ya real de `frappe.route_options.nexora_report` que lee `nexora_reports.js`),
	 * así que llevan `report` en vez de inventar un destino que no existe.
	 */
	const SECTIONS = [
		{
			label: "Inicio",
			items: [
				{ route: "nexora-dashboard", label: "Inicio", icon: "grid" },
				{ route: "nexora-assistant", label: "Asistente", icon: "chat" },
				{ route: "nexora-search", label: "Buscador", icon: "search" },
				{ route: "nexora-notifications", label: "Notificaciones", icon: "bell" },
			],
		},
		{
			label: "Núcleo de fondos",
			items: [
				{ route: "nexora-finance", label: "Fondos", icon: "wallet" },
				{ route: "nexora-operations", label: "Operaciones", icon: "flow" },
				{ route: "nexora-reports", label: "Estados de cuenta", icon: "chart", report: "FI01" },
				{ route: "nexora-closing", label: "Cierre mensual", icon: "lock" },
			],
		},
		{
			label: "Proyectos",
			items: [
				{ route: "nexora-project", label: "Proyectos", icon: "building" },
				{ route: "nexora-budget", label: "Presupuestos", icon: "chart" },
				{ route: "nexora-progress", label: "Avances", icon: "camera" },
				{ route: "nexora-evidence", label: "Evidencias", icon: "document" },
				{ route: "nexora-contracts", label: "Contratos", icon: "contract" },
				{ route: "nexora-quality", label: "Calidad", icon: "contract" },
			],
		},
		{
			label: "Compras e inventario",
			items: [
				{ route: "nexora-purchase-requests", label: "Solicitudes", icon: "cart" },
				{ route: "nexora-quotations", label: "Cotizaciones", icon: "tag" },
				{ route: "nexora-purchase-orders", label: "Órdenes de compra", icon: "document" },
				{ route: "nexora-receipts", label: "Recepciones", icon: "truck" },
				{ route: "nexora-inventory", label: "Inventario", icon: "cart" },
				{ route: "nexora-suppliers", label: "Proveedores", icon: "truck" },
				{ route: "nexora-entities", label: "Entidades", icon: "users" },
			],
		},
		{
			label: "Reportes e inteligencia",
			items: [
				{ route: "nexora-reports", label: "Reportes", icon: "chart" },
				{ route: "nexora-reports", label: "Indicadores", icon: "chart", report: "PR03" },
				{ route: "nexora-reports", label: "Exportaciones", icon: "document" },
			],
		},
		{
			label: "Administración",
			items: [
				{ route: "nexora-administracion", label: "Usuarios y permisos", icon: "lock" },
				{ route: "nexora-integrations", label: "Configuración", icon: "plug" },
				{ route: "nexora-conversation-channels", label: "Canales", icon: "chat" },
				{ route: "nexora-ai-providers", label: "Proveedores de IA", icon: "chip" },
				{ route: "nexora-sap", label: "SAP", icon: "server" },
			],
		},
	];

	/**
	 * NXR-UX-0014 — barra inferior de teléfono: los cuatro destinos más frecuentes de
	 * `SECTIONS` (uno de "Inicio", uno de "Núcleo de fondos", más el buscador) y un quinto botón que
	 * abre el mismo cajón que ya existe para todo lo demás. No es una lista nueva de
	 * rutas: son referencias a las mismas cuatro entradas de `SECTIONS`, así que un
	 * cambio de ruta ahí no puede desalinear la barra inferior de la de escritorio. Las
	 * etiquetas son más cortas que en el cajón a propósito — cuatro columnas de un
	 * teléfono no tienen el ancho de una fila de escritorio — pero "Buscar" ya es la
	 * etiqueta exacta que usa el botón de búsqueda de la barra superior (línea de
	 * `data-shell-search` más abajo), así que no es una etiqueta nueva, es la misma.
	 */
	const TABBAR_ITEMS = [
		{ route: "nexora-dashboard", label: "Inicio", icon: "grid" },
		{ route: "nexora-operations", label: "Operar", icon: "flow" },
		{ route: "nexora-finance", label: "Fondos", icon: "wallet" },
		{ route: "nexora-search", label: "Buscar", icon: "search" },
	];

	/** Trazos de 20×20, sin relleno: heredan el color y pesan lo mismo entre sí. */
	const ICONS = {
		grid: "M3.5 3.5h5.2v5.2H3.5zM11.3 3.5h5.2v5.2h-5.2zM3.5 11.3h5.2v5.2H3.5zM11.3 11.3h5.2v5.2h-5.2z",
		chat: "M3.5 4.5h13v8H8.3L6 15.2V12.5H3.5z",
		building:
			"M5 16.5V3.5h7v13M9 16.5V3.5M5 6.5h1.4M5 9.5h1.4M5 12.5h1.4M10.6 6.5H12M10.6 9.5H12M10.6 12.5H12M2.8 16.5h14.4",
		flow: "M4 5.5h7M4 10h12M4 14.5h7M13.5 3.5L16 5.5l-2.5 2M6.5 12.5L4 14.5l2.5 2",
		search: "M9 3.6a5.4 5.4 0 1 0 0 10.8A5.4 5.4 0 0 0 9 3.6zM12.9 12.9l3.5 3.5",
		wallet: "M3.5 6.2h13v9.3h-13zM3.5 6.2l9.6-2.1v2.1M13.2 10.8h2",
		chart: "M3.5 16.5h13M6 13.5V8M10 13.5V4.5M14 13.5v-4",
		lock: "M5.5 9h9v7.5h-9zM7.5 9V6.6a2.5 2.5 0 0 1 5 0V9",
		cart: "M2.8 3.5h2l2 8.6h7.6l1.8-6.2H6.1M8 15.6h.01M14 15.6h.01",
		tag: "M3.5 3.5h6l7 7-6 6-7-7zM6.6 6.6h.01",
		truck: "M2.8 5.5h8.4v7.4H2.8zM11.2 8.3h3l2 2.6v2H11.2zM6 15.2h.01M14 15.2h.01",
		contract: "M5 2.8h6.6L15 6.2v11H5zM11.2 2.8v3.6H15M7.6 10h5M7.6 13h3.4",
		users: "M7.3 9.2a2.6 2.6 0 1 0 0-5.2 2.6 2.6 0 0 0 0 5.2zM2.8 16.4c0-2.5 2-4.2 4.5-4.2s4.5 1.7 4.5 4.2M13.2 5.2a2.3 2.3 0 0 1 0 4.4M14.4 12.6c1.7.5 2.8 1.8 2.8 3.8",
		document: "M5 2.8h6.6L15 6.2v11H5zM11.2 2.8v3.6H15M7.6 12.6l1.7 1.7 3.3-3.6",
		camera: "M4 6.5h2.3l.9-1.6h5.6l.9 1.6H16v8.5H4zM10 8.7a2.6 2.6 0 1 0 0 5.2 2.6 2.6 0 0 0 0-5.2z",
		chip: "M6 6h8v8H6zM6 3v3M10 3v3M14 3v3M6 14v3M10 14v3M14 14v3M3 6h3M3 10h3M3 14h3M14 6h3M14 10h3M14 14h3",
		plug: "M7 8V3.5M13 8V3.5M5.5 8h9v3a4.5 4.5 0 0 1-9 0zM10 15v2.5",
		server: "M3.5 4h11v3h-11zM3.5 8.5h11v3h-11zM3.5 13h11v3h-11zM6 5.5h.01M6 10h.01M6 14.5h.01",
		bell: "M10 3.2a4.3 4.3 0 0 0-4.3 4.3v2.6L4 13h12l-1.7-2.9V7.5A4.3 4.3 0 0 0 10 3.2zM8.3 15.5a1.7 1.7 0 0 0 3.4 0",
		menu: "M3.5 5.5h13M3.5 10h13M3.5 14.5h13",
		collapse: "M12.5 5l-4.5 5 4.5 5",
		close: "M5 5l10 10M15 5L5 15",
		help: "M10 17a7 7 0 1 0 0-14 7 7 0 0 0 0 14zM7.8 7.6a2.2 2.2 0 1 1 3.3 1.9c-.7.4-1.1.9-1.1 1.8v.2M10 13.6h.01",
		theme: "M10 6.5a3.5 3.5 0 1 0 0 7 3.5 3.5 0 0 0 0-7zM10 2.5v2M10 15.5v2M4.5 4.5l1.4 1.4M14.1 14.1l1.4 1.4M2.5 10h2M15.5 10h2M4.5 15.5l1.4-1.4M14.1 5.9l1.4-1.4",
	};

	const svg = (name) =>
		`<svg viewBox="0 0 20 20" aria-hidden="true" focusable="false"><path d="${ICONS[name]}" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg>`;

	function currentRoute() {
		return String((frappe.get_route?.() || [])[0] || "").toLowerCase();
	}

	/**
	 * Decide si la carcasa fija (sidebar + barra superior propias) debe mostrarse
	 * alrededor de la ruta actual — nunca decide si el usuario puede *llegar* a esa
	 * ruta (eso es `enforceRouteGuard()`/`resolve_redirect()`, ver más abajo, y ya no
	 * exime a ningún rol). Deliberadamente no incluye `/app/nxr-*`: las vistas nativas
	 * de documento de NEXORA (`NXR Operation`, `NXR Contract`, etc.) tienen su propio
	 * reskin real (`nexora_native_desk.css`) en vez de la carcasa fija, para no romper
	 * su barra de acciones nativa (enviar, cancelar, imprimir…).
	 */
	function belongsToNexora() {
		const route = currentRoute();
		const path = window.location.pathname.toLowerCase();
		return (
			route.startsWith("nexora-") ||
			path.startsWith("/app/nexora-") ||
			(path === "/app" && frappe.boot?.home_page === "nexora-dashboard")
		);
	}

	/**
	 * Bloque 154 — dos capas de guarda del Desk crudo. Esta es la capa de cliente: cubre
	 * el cambio de ruta *dentro* de la SPA ya cargada, que nunca vuelve a tocar al
	 * servidor — por eso `nexora.shell_guard.enforce` (Python, `before_request`) no basta
	 * solo, ya que ese solo actúa en una navegación nueva (URL tecleada, enlace suelto,
	 * recarga). Deliberadamente distinta de `belongsToNexora()`, que decide qué oculta la
	 * carcasa y a propósito no incluye `/app/nxr-*`: esas son vistas nativas de Frappe con
	 * su propia barra de acciones (enviar, cancelar…), que ahí sí hace falta. Esta guarda
	 * decide algo distinto — quién puede aterrizar — y debe dejar pasar los enlaces reales
	 * del producto a `NXR Contract`/`NXR Operation`/`NXR Fund Source`/`NXR Entity
	 * Compliance`/`NXR Monthly Close`/`NXR Weekly Close` (`get_form_link`, ya en uso en
	 * varias pantallas) para todos los roles.
	 *
	 * CORRECCIÓN ESTRUCTURAL DEL DESK FRAPPE: `System Manager`/`NEXORA Administrator`
	 * ya no quedan exentos de esta guarda — esa excepción era exactamente cómo el
	 * usuario "Administrator" real llegaba al Workspace "Home" genérico de ERPNext
	 * dentro de la SPA ya cargada (p. ej. tras pulsar un enlace suelto a `/app/home`
	 * sin recargar la página). Mismo criterio que `nexora.shell_guard_core.resolve_redirect`
	 * del lado servidor: ningún rol de NEXORA queda fuera de esta guarda.
	 */
	const NEXORA_SCOPED_ROLES = [
		"System Manager",
		"NEXORA Administrator",
		"NEXORA Finance Manager",
		"NEXORA Finance Operator",
		"NEXORA Auditor",
		"NEXORA Project Viewer",
	];

	function routeGuardApplies() {
		const roles = frappe.user_roles || [];
		return roles.some((role) => NEXORA_SCOPED_ROLES.includes(role));
	}

	/**
	 * Bloque 155 — hallazgo real: `frappe.get_route()[0]` no es el slug del DocType
	 * para las vistas nativas de Frappe, es el tipo de vista (`"Form"`, `"List"`);
	 * el slug real vive en `route[1]` cuando existe. Solo las páginas propias de
	 * NEXORA (`Page` planas, sin envoltorio) devuelven el slug directamente en
	 * `route[0]` — por eso `route.startsWith("nxr-")` nunca podía reconocer un
	 * enlace real a `NXR Operation`/`NXR Contract` (`["Form", "NXR Operation",
	 * name]`) como exento: los rebotaba al panel pese a que
	 * `nexora.shell_guard_core.ALLOWED_APP_PREFIXES` ya los dejaba pasar en el
	 * servidor — confirmado con `__nxrRouteWatch` real en CI (`[null, "Form",
	 * "nexora-dashboard"]`). `window.location.pathname` no tiene esa ambigüedad:
	 * es la misma fuente que usa `resolve_redirect()` del lado servidor, y
	 * `belongsToNexora()` ya la usa como respaldo del mismo modo.
	 */
	function isExemptRoute(route) {
		if (!route || route.startsWith("nexora-") || route.startsWith("nxr-")) {
			return true;
		}
		const path = window.location.pathname.toLowerCase();
		return path.startsWith("/app/nexora-") || path.startsWith("/app/nxr-");
	}

	function enforceRouteGuard() {
		// Bloque 154, diagnóstico dejado a propósito: `nexora_browser_smoke.mjs`
		// reportó un rol restringido atascado en `List/User/List` sesenta segundos
		// después de `frappe.set_route("user")`. `window.__nxrGuardCalls`/
		// `__nxrGuardLastDecision` confirmaron la causa real: esta función SÍ se
		// ejecuta y SÍ redirige (`"allowed:nexora-dashboard"` como última decisión),
		// pero el router de Frappe sigue resolviendo la vista de lista original de
		// forma asíncrona (permisos, ajustes de la lista) y reafirma esa ruta
		// después, sin volver a disparar `"change"` — deshaciendo la redirección sin
		// que esta función se entere. Dos reafirmaciones escalonadas bastan para
		// ganarle a esa resolución tardía sin depender de un evento que no existe.
		window.__nxrGuardCalls = (window.__nxrGuardCalls || 0) + 1;
		if (!routeGuardApplies()) {
			window.__nxrGuardLastDecision = "not-applicable";
			return false;
		}
		const route = currentRoute();
		if (isExemptRoute(route)) {
			window.__nxrGuardLastDecision = `allowed:${route}`;
			return false;
		}
		window.__nxrGuardLastDecision = `redirecting:${route}`;
		frappe.set_route("nexora-dashboard");
		const reassert = () => {
			const still = currentRoute();
			if (!isExemptRoute(still)) {
				frappe.set_route("nexora-dashboard");
			}
		};
		window.setTimeout(reassert, 300);
		window.setTimeout(reassert, 1200);
		return true;
	}

	let shell = null;

	function collapsed() {
		try {
			return window.localStorage?.getItem(COLLAPSE_KEY) === "1";
		} catch (error) {
			return false;
		}
	}

	function persistCollapsed(value) {
		try {
			window.localStorage?.setItem(COLLAPSE_KEY, value ? "1" : "0");
		} catch (error) {
			/* Un navegador sin almacenamiento no impide usar la aplicación. */
		}
	}

	/**
	 * Selector de tema real: `nexora_design_system.css` ya define
	 * `:root[data-theme="dark"]` para todos sus tokens `--nxr-*` — este botón solo
	 * fija ese atributo en `<html>` y lo recuerda, no inventa una segunda paleta.
	 */
	function storedTheme() {
		try {
			return window.localStorage?.getItem(THEME_KEY) || null;
		} catch (error) {
			return null;
		}
	}

	function applyTheme(theme) {
		if (theme === "dark" || theme === "light") {
			document.documentElement.setAttribute("data-theme", theme);
		} else {
			document.documentElement.removeAttribute("data-theme");
		}
	}

	function currentTheme() {
		const explicit = document.documentElement.getAttribute("data-theme");
		if (explicit === "dark" || explicit === "light") return explicit;
		return window.matchMedia?.("(prefers-color-scheme: dark)").matches ? "dark" : "light";
	}

	function toggleTheme() {
		const next = currentTheme() === "dark" ? "light" : "dark";
		applyTheme(next);
		try {
			window.localStorage?.setItem(THEME_KEY, next);
		} catch (error) {
			/* Un navegador sin almacenamiento solo pierde la persistencia, no el cambio. */
		}
	}

	applyTheme(storedTheme());

	function build() {
		const node = document.createElement("div");
		node.className = "nxr-shell";
		node.dataset.collapsed = collapsed() ? "true" : "false";
		document.documentElement.setAttribute("data-nxr-shell-collapsed", node.dataset.collapsed);
		node.innerHTML = `
			<a class="nxr-shell__skip" href="#body">${__("Saltar al contenido")}</a>
			<aside class="nxr-shell__nav" aria-label="${__("Secciones de NEXORA")}">
				<div class="nxr-shell__brand">
					<span class="nxr-shell__mark-chip">
						<svg class="nxr-shell__mark" viewBox="0 0 240 240" role="img" aria-label="${__("NEXORA")}" focusable="false">
							<path d="M176 48A88 88 0 1 0 176 192" stroke="#0A1F33" stroke-width="24" stroke-linecap="square"></path>
							<path d="M83 78l10-7 10 5 9-4 7 8 11-1 2 11 10 5-4 10 4 10-10 5-2 11-11-1-7 8-9-4-10 5-10-7 2-11-8-7 8-7-2-11z"
								fill="#AEB6BF" stroke="#17212B" stroke-width="4" stroke-linejoin="miter"></path>
							<path d="M91 164V86l63 74V82" stroke="#0070F2" stroke-width="22" stroke-linecap="square"></path>
							<path d="M91 86l63 74" stroke="#0057D2" stroke-width="22" stroke-linecap="square"></path>
							<path d="M173 46h16" stroke="#00A6A6" stroke-width="8" stroke-linecap="square"></path>
						</svg>
					</span>
					<span class="nxr-shell__word" aria-hidden="true">NEXORA</span>
					<button type="button" class="nxr-shell__collapse" data-shell-collapse
						aria-label="${__("Contraer la navegación")}">${svg("collapse")}</button>
				</div>
				<nav class="nxr-shell__sections">
					${SECTIONS.map(
						(section) => `
						<div class="nxr-shell__section">
							<p class="nxr-shell__section-label">${frappe.utils.escape_html(__(section.label))}</p>
							${section.items
								.map(
									(item) => `
								<a class="nxr-shell__link" href="/app/${item.route}" data-shell-route="${item.route}"${
										item.report ? ` data-shell-report="${item.report}"` : ""
									}>
									${svg(item.icon)}
									<span>${frappe.utils.escape_html(__(item.label))}</span>
								</a>`
								)
								.join("")}
						</div>`
					).join("")}
				</nav>
			</aside>
			<div class="nxr-shell__scrim" data-shell-close hidden></div>
			<header class="nxr-shell__bar">
				<button type="button" class="nxr-shell__icon-btn nxr-shell__drawer" data-shell-drawer
					aria-label="${__("Abrir la navegación")}" aria-expanded="false">${svg("menu")}</button>
				<div class="nxr-shell__context">
					<span class="nxr-shell__crumb" data-shell-crumb></span>
					<span class="nxr-shell__project" data-shell-project></span>
				</div>
				<button type="button" class="nxr-shell__universal-search" data-shell-search
					aria-label="${__("Buscar en NEXORA")}">
					${svg("search")}<span>${__("Buscar en NEXORA")}</span>
				</button>
				<div class="nxr-shell__actions">
					<button type="button" class="nxr-ds-btn nxr-ds-btn--primary nxr-shell__income" data-shell-income>
						${__("Registrar fondos")}
					</button>
					<button type="button" class="nxr-shell__icon-btn nxr-shell__topbar-icon" data-shell-help
						aria-label="${__("Ayuda")}" title="${__("Ayuda")}">${svg("help")}</button>
					<a class="nxr-shell__icon-btn nxr-shell__topbar-icon" href="/app/nexora-notifications"
						data-shell-notifications aria-label="${__("Notificaciones")}"
						title="${__("Notificaciones")}">${svg(
			"bell"
		)}<span class="nxr-shell__badge" data-shell-unread hidden></span></a>
					<button type="button" class="nxr-shell__icon-btn nxr-shell__topbar-icon" data-shell-theme
						aria-label="${__("Cambiar tema")}" title="${__("Cambiar tema")}">${svg("theme")}</button>
					<div class="nxr-shell__user" data-shell-user>
						<span class="nxr-shell__avatar" data-shell-avatar aria-hidden="true"></span>
						<span class="nxr-shell__user-meta">
							<strong data-shell-username></strong>
							<small data-shell-role></small>
						</span>
					</div>
				</div>
			</header>
			<nav class="nxr-shell__tabbar" aria-label="${__("Navegación principal")}">
				${TABBAR_ITEMS.map(
					(item) => `
					<a class="nxr-shell__tab" href="/app/${item.route}" data-shell-route="${item.route}">
						${svg(item.icon)}
						<span>${frappe.utils.escape_html(__(item.label))}</span>
					</a>`
				).join("")}
				<button type="button" class="nxr-shell__tab" data-shell-tab-more aria-haspopup="true" aria-expanded="false">
					${svg("menu")}
					<span>${__("Más")}</span>
				</button>
			</nav>
			<footer class="nxr-shell__footer">
				<span class="nxr-shell__footer-mark">NEXORA</span>
				<span class="nxr-shell__footer-text">${__("Gestión Integral de Fondos, Proyectos y Operaciones")}</span>
			</footer>`;
		document.body.appendChild(node);

		node.querySelector("[data-shell-collapse]").addEventListener("click", () => {
			const next = node.dataset.collapsed !== "true";
			node.dataset.collapsed = next ? "true" : "false";
			// Vive también en `<html>` porque el relleno de `<body>` que le reserva sitio a
			// la navegación no es descendiente de `.nxr-shell`: no hay otro ancestro común
			// desde el que una regla CSS pueda leer este estado.
			document.documentElement.setAttribute("data-nxr-shell-collapsed", node.dataset.collapsed);
			persistCollapsed(next);
		});
		node.querySelector("[data-shell-drawer]").addEventListener("click", () => openDrawer(true));
		node.querySelector("[data-shell-close]").addEventListener("click", () => openDrawer(false));
		// El quinto botón de la barra inferior abre el mismo cajón que el de la barra
		// superior — no es un segundo menú, es el mismo, alcanzable con el pulgar.
		node.querySelector("[data-shell-tab-more]").addEventListener("click", () => openDrawer(true));
		// El buscador universal del topbar abre la misma paleta de comandos real de
		// Ctrl/Cmd+K (`openPalette()`, definida más abajo en este mismo cierre) — no
		// es un segundo buscador, es el mismo, con una entrada siempre visible en vez
		// de solo un atajo de teclado.
		node.querySelector("[data-shell-search]").addEventListener("click", () => openPalette());
		node.querySelector("[data-shell-income]").addEventListener("click", () => {
			window.nexora.openIncomeDialog?.();
		});
		node.querySelector("[data-shell-help]").addEventListener("click", () => openHelp());
		node.querySelector("[data-shell-theme]").addEventListener("click", () => toggleTheme());
		// Atributo propio, deliberadamente distinto de `[data-shell-route]`: esta
		// campana es un atajo real hacia un destino que YA existe en `SECTIONS`
		// ("Notificaciones", grupo "Inicio") — contarla junto a `[data-shell-route]`
		// duplicaría ese mismo destino en el total que `validateShell` calcula
		// contra `window.nexora.shell.sections`/`tabbarItems`.
		node.querySelector("[data-shell-notifications]").addEventListener("click", (event) => {
			if (event.metaKey || event.ctrlKey || event.shiftKey || event.button !== 0) return;
			event.preventDefault();
			openDrawer(false);
			frappe.set_route("nexora-notifications");
		});
		// Navegar dentro de la aplicación no recarga la página: el enlace conserva su
		// `href` real para que se pueda abrir en otra pestaña, y el clic normal lo
		// intercepta el enrutador.
		node.querySelectorAll("[data-shell-route]").forEach((link) => {
			link.addEventListener("click", (event) => {
				if (event.metaKey || event.ctrlKey || event.shiftKey || event.button !== 0) return;
				event.preventDefault();
				openDrawer(false);
				if (link.dataset.shellReport) {
					frappe.route_options = {
						...(frappe.route_options || {}),
						nexora_report: link.dataset.shellReport,
					};
				}
				frappe.set_route(link.dataset.shellRoute);
			});
		});
		document.addEventListener("keydown", (event) => {
			if (event.key === "Escape") openDrawer(false);
		});
		return node;
	}

	/** Una carcasa montada pero sin sus piezas: el marco la vació al repintar. */
	function intact(node) {
		return Boolean(node?.isConnected && node.querySelector("[data-shell-drawer]"));
	}

	/**
	 * El manejador de `Escape` vive en el documento y sobrevive a la carcasa, así que puede
	 * llegar aquí cuando ya no queda nada que abrir ni cerrar. El recorrido real lo mostró
	 * en iPhone como dos `TypeError: null is not an object`: la referencia seguía viva y sus
	 * hijos no. Se comprueban las piezas, no solo la referencia.
	 */
	function openDrawer(open) {
		if (!intact(shell)) return;
		const scrim = shell.querySelector("[data-shell-close]");
		if (!scrim) return;
		shell.dataset.drawer = open ? "open" : "closed";
		scrim.hidden = !open;
		// Dos disparadores abren el mismo cajón (la hamburguesa de escritorio/tableta y
		// "Más" de la barra inferior de teléfono): los dos reflejan el mismo estado.
		shell.querySelectorAll("[data-shell-drawer], [data-shell-tab-more]").forEach((trigger) => {
			trigger.setAttribute("aria-expanded", open ? "true" : "false");
		});
	}

	function paintActive() {
		if (!shell) return;
		const route = currentRoute();
		let active = null;
		shell.querySelectorAll("[data-shell-route]").forEach((link) => {
			const current = link.dataset.shellRoute === route;
			if (current) {
				link.setAttribute("aria-current", "page");
				active = link;
			} else if (link.hasAttribute("aria-current")) {
				link.removeAttribute("aria-current");
			}
		});
		const crumb = shell.querySelector("[data-shell-crumb]");
		const label = active?.querySelector("span")?.textContent || __("NEXORA");
		if (crumb && crumb.textContent !== label) crumb.textContent = label;
	}

	/**
	 * El proyecto activo se lee del contexto compartido, no de la pantalla. La barra tiene
	 * que decir sobre qué se está trabajando en todo momento: un panel financiero sin ese
	 * dato invita a registrar un gasto en el proyecto equivocado.
	 */
	function paintContext() {
		if (!shell) return;
		const slot = shell.querySelector("[data-shell-project]");
		if (!slot) return;
		const context = window.nexora.context?.get?.() || {};
		const text = context.project ? String(context.project) : __("Todos los proyectos");
		if (slot.textContent !== text) slot.textContent = text;
	}

	/**
	 * Nombre, rol e iniciales reales — del mismo contexto compartido
	 * (`window.nexora.context`) que ya usa `nexora_dashboard.js`, nunca un segundo
	 * mapa de roles duplicado. Si ninguna pantalla cargó el contexto todavía, se
	 * muestra el usuario real de la sesión con la etiqueta genérica ya establecida
	 * en el resto de la aplicación, y se corrige sola en cuanto el contexto llegue
	 * (`nexora:context-changed` ya dispara `schedule()`).
	 */
	function paintUser() {
		if (!shell) return;
		const nameSlot = shell.querySelector("[data-shell-username]");
		const roleSlot = shell.querySelector("[data-shell-role]");
		const avatarSlot = shell.querySelector("[data-shell-avatar]");
		if (!nameSlot || !roleSlot || !avatarSlot) return;
		const context = window.nexora.context?.get?.() || {};
		const fullName = frappe.boot?.user_info?.[frappe.session.user]?.fullname || frappe.session.user;
		const name = context.user_label || fullName;
		const role = context.role_label || __("Usuario NEXORA");
		if (nameSlot.textContent !== name) nameSlot.textContent = name;
		if (roleSlot.textContent !== role) roleSlot.textContent = role;
		const initials =
			String(name)
				.trim()
				.split(/\s+/)
				.slice(0, 2)
				.map((part) => part.charAt(0).toUpperCase())
				.join("") || "N";
		if (avatarSlot.textContent !== initials) avatarSlot.textContent = initials;
	}

	let unreadRequested = false;
	function refreshUnreadBadge() {
		if (!shell || unreadRequested) return;
		unreadRequested = true;
		frappe.call({
			method: "nexora.notifications.service.list_notifications",
			type: "POST",
			args: { payload: { read: 0, limit: 50 } },
			callback: (response) => {
				unreadRequested = false;
				const badge = shell?.querySelector("[data-shell-unread]");
				if (!badge) return;
				const count = (response?.message || []).length;
				badge.hidden = !count;
				badge.textContent = count > 9 ? "9+" : String(count);
			},
			error: () => {
				unreadRequested = false;
			},
		});
	}

	function openHelp() {
		frappe.msgprint({
			title: __("Ayuda de NEXORA"),
			indicator: "blue",
			message: [
				`<p>${frappe.utils.escape_html(
					__("Gestión Integral de Fondos, Proyectos y Operaciones.")
				)}</p>`,
				`<p><strong>${frappe.utils.escape_html(
					__("Ctrl/Cmd + K")
				)}</strong> — ${frappe.utils.escape_html(__("Abrir el buscador universal"))}</p>`,
				`<p><strong>${frappe.utils.escape_html(__("Esc"))}</strong> — ${frappe.utils.escape_html(
					__("Cerrar diálogos y menús abiertos")
				)}</p>`,
			].join(""),
		});
	}

	function sync() {
		if (enforceRouteGuard()) return;
		const wanted = belongsToNexora();
		if (!wanted) {
			if (shell) {
				shell.remove();
				shell = null;
				document.documentElement.classList.remove(ROOT_CLASS);
				document.documentElement.removeAttribute("data-nxr-shell-collapsed");
			}
			return;
		}
		const justBuilt = !intact(shell);
		if (justBuilt) {
			shell?.remove();
			shell = build();
			document.documentElement.classList.add(ROOT_CLASS);
		}
		openDrawer(false);
		paintActive();
		paintContext();
		paintUser();
		if (justBuilt) refreshUnreadBadge();
	}

	let scheduled = false;
	function schedule() {
		if (scheduled) return;
		scheduled = true;
		requestAnimationFrame(() => {
			scheduled = false;
			sync();
		});
	}

	window.nexora.shell = Object.freeze({ sections: SECTIONS, tabbarItems: TABBAR_ITEMS, sync: schedule });

	/**
	 * NXR-UX-0008 — paleta de comandos (Ctrl+K / Cmd+K).
	 *
	 * No es un catálogo nuevo de destinos: son las mismas entradas de `SECTIONS` que ya
	 * pinta el cajón lateral, aplanadas y filtrables por texto. Una segunda lista aquí
	 * se habría desalineado de la real la primera vez que alguien agregara una página sin
	 * tocar dos sitios — se lee `SECTIONS` en el momento de abrir, nunca se copia.
	 */
	let palette = null;

	function paletteItems() {
		return SECTIONS.flatMap((section) =>
			section.items.map((item) => ({ ...item, section: section.label }))
		);
	}

	function buildPalette() {
		const bar = document.createElement("div");
		bar.className = "nxr-command-bar";
		bar.hidden = true;
		bar.innerHTML = `
			<div class="nxr-command-bar__scrim" data-command-close></div>
			<div class="nxr-command-bar__panel" role="dialog" aria-modal="true" aria-label="${__("Qué necesita hacer")}">
				<input type="text" class="nxr-command-bar__input" data-command-input
					placeholder="${__("Buscar una sección de NEXORA…")}" autocomplete="off" />
				<ul class="nxr-command-bar__list" data-command-list role="listbox"></ul>
			</div>`;
		document.body.appendChild(bar);
		bar.querySelector("[data-command-close]").addEventListener("click", () => closePalette());
		const input = bar.querySelector("[data-command-input]");
		input.addEventListener("input", () => renderPaletteList(bar, input.value));
		input.addEventListener("keydown", (event) => onPaletteKeydown(event, bar));
		bar.querySelector("[data-command-list]").addEventListener("click", (event) => {
			const row = event.target.closest("[data-command-route]");
			if (row) goToPaletteRoute(row.dataset.commandRoute, row.dataset.commandReport);
		});
		return bar;
	}

	function renderPaletteList(node, query) {
		const list = node.querySelector("[data-command-list]");
		const normalized = String(query || "")
			.trim()
			.toLowerCase();
		const items = paletteItems().filter(
			(item) => !normalized || __(item.label).toLowerCase().includes(normalized)
		);
		list.innerHTML = items
			.map(
				(item, index) => `
			<li class="nxr-command-bar__item" role="option" data-command-route="${item.route}"${
					item.report ? ` data-command-report="${item.report}"` : ""
				}
				aria-selected="${index === 0 ? "true" : "false"}">
				${svg(item.icon)}<span>${frappe.utils.escape_html(__(item.label))}</span>
				<small>${frappe.utils.escape_html(__(item.section))}</small>
			</li>`
			)
			.join("");
	}

	function onPaletteKeydown(event, node) {
		if (event.key === "Escape") {
			event.preventDefault();
			closePalette();
			return;
		}
		if (event.key !== "ArrowDown" && event.key !== "ArrowUp" && event.key !== "Enter") return;
		const rows = [...node.querySelectorAll("[data-command-route]")];
		if (!rows.length) return;
		const current = rows.findIndex((row) => row.getAttribute("aria-selected") === "true");
		if (event.key === "Enter") {
			event.preventDefault();
			const target = rows[current >= 0 ? current : 0];
			goToPaletteRoute(target.dataset.commandRoute, target.dataset.commandReport);
			return;
		}
		event.preventDefault();
		const next =
			event.key === "ArrowDown" ? Math.min(current + 1, rows.length - 1) : Math.max(current - 1, 0);
		rows.forEach((row, index) => row.setAttribute("aria-selected", index === next ? "true" : "false"));
		rows[next].scrollIntoView({ block: "nearest" });
	}

	function goToPaletteRoute(route, report) {
		if (!route) return;
		closePalette();
		if (report) frappe.route_options = { ...(frappe.route_options || {}), nexora_report: report };
		frappe.set_route(route);
	}

	function openPalette() {
		if (!belongsToNexora()) return;
		if (!palette?.isConnected || !palette.querySelector("[data-command-input]")) {
			palette?.remove();
			palette = buildPalette();
		}
		palette.hidden = false;
		const input = palette.querySelector("[data-command-input]");
		input.value = "";
		renderPaletteList(palette, "");
		input.focus();
	}

	function closePalette() {
		if (palette) palette.hidden = true;
	}

	function install() {
		frappe.router?.on?.("change", schedule);
		document.addEventListener("nexora:context-changed", schedule);
		document.addEventListener("keydown", (event) => {
			if (!(event.key === "k" || event.key === "K") || !(event.ctrlKey || event.metaKey)) return;
			if (!belongsToNexora() && (!palette || palette.hidden)) return;
			event.preventDefault();
			if (palette && !palette.hidden) closePalette();
			else openPalette();
		});
		schedule();
	}

	if (typeof frappe.ready === "function") frappe.ready(install);
	else install();
})();
