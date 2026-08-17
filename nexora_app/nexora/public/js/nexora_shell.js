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

	/**
	 * Los doce destinos, agrupados por la pregunta que responde cada grupo en vez de por
	 * el módulo que los implementa. «Cotizaciones» y «Solicitudes de compra» viven juntas
	 * porque quien busca una busca la otra; «Contratos» y «Entidades» viven juntas porque
	 * son el expediente de con quién se trabaja. Doce iguales en fila obligaban a leerlos
	 * todos; cuatro grupos de tres se recorren de un vistazo.
	 */
	const SECTIONS = [
		{
			label: "Hoy",
			// Cinco, no tres: NXR-UX-0010 (Bloque 17) agregó "Proyecto 360°" como
			// cuarta lente de comprensión junto al resumen global — misma pregunta
			// ("qué está pasando"), alcance distinto (un proyecto en concreto).
			// NXR-CNV-0001 (Bloque 18) agrega "Asistente" como una quinta forma de
			// llegar a esa misma información (y a preparar operaciones) por texto en
			// vez de navegación. Los otros tres grupos siguen en tres.
			items: [
				{ route: "nexora-dashboard", label: "Resumen", icon: "grid" },
				{ route: "nexora-assistant", label: "Asistente", icon: "chat" },
				{ route: "nexora-project", label: "Proyecto 360°", icon: "building" },
				{ route: "nexora-operations", label: "Operación diaria", icon: "flow" },
				{ route: "nexora-search", label: "Buscador", icon: "search" },
			],
		},
		{
			label: "Dinero",
			items: [
				{ route: "nexora-finance", label: "Fondos", icon: "wallet" },
				{ route: "nexora-reports", label: "Reportes", icon: "chart" },
				// Bloque 52 conectó el cierre mensual en la misma página; la etiqueta ya
				// no debe sugerir que solo cubre el cierre semanal.
				{ route: "nexora-closing", label: "Cierres", icon: "lock" },
				// Hallazgo real de auditoría (sesión 2026-08-16): `budget.service` tenía
				// servicio completo pero ni lectura (`list`/`get`, agregados en el
				// Bloque 53) ni ninguna página — no había forma de crear ni consultar un
				// presupuesto sin llamar la API a mano.
				{ route: "nexora-budget", label: "Presupuesto", icon: "chart" },
			],
		},
		{
			label: "Compras",
			items: [
				{ route: "nexora-purchase-requests", label: "Solicitudes", icon: "cart" },
				{ route: "nexora-quotations", label: "Cotizaciones", icon: "tag" },
				// Hallazgo real de auditoría (sesión 2026-08-16): `order_service`
				// (crear/transicionar/pagar una orden de compra) no tenía ninguna
				// página NEXORA — la única vía era el escritorio técnico de Frappe.
				// Rompía GP-04 justo en el paso "orden".
				{ route: "nexora-purchase-orders", label: "Órdenes", icon: "document" },
				{ route: "nexora-suppliers", label: "Proveedores", icon: "truck" },
			],
		},
		{
			label: "Expediente",
			items: [
				{ route: "nexora-contracts", label: "Contratos", icon: "contract" },
				{ route: "nexora-entities", label: "Entidades", icon: "users" },
				{ route: "nexora-evidence", label: "Comprobantes", icon: "document" },
				{ route: "nexora-progress", label: "Avance", icon: "camera" },
				// Hallazgo real de auditoría (sesión 2026-08-16): `quality.service`
				// existe desde el Bloque 13 (ver el comentario al inicio de
				// quality/service.py) pero nunca tuvo ninguna página NEXORA.
				{ route: "nexora-quality", label: "Calidad", icon: "contract" },
			],
		},
		{
			// Hallazgo real de auditoría (sesión 2026-08-16): `inventory.service`
			// (crear bodega/movimiento, transicionar, consultar) no tenía ninguna
			// página NEXORA; la única lectura era el panel de inventario crítico
			// del dashboard, que solo informa después del hecho.
			label: "Inventario",
			items: [{ route: "nexora-inventory", label: "Movimientos", icon: "cart" }],
		},
		{
			// Hallazgo real de auditoría: `nexora-conversation-channels` (WhatsApp) y
			// `nexora-ai-providers` eran páginas reales, con servicio real detrás, pero
			// huérfanas de toda navegación normal — ni un atajo del workspace legado
			// apunta aquí desde que la carcasa reemplazó su barra lateral, y ninguna de
			// las dos vivía en `SECTIONS`, así que tampoco aparecían en el buscador de
			// comandos (que lee de aquí). Solo alcanzables tecleando la URL a mano.
			label: "Configuración",
			items: [
				{ route: "nexora-conversation-channels", label: "Canales", icon: "chat" },
				{ route: "nexora-ai-providers", label: "Proveedores de IA", icon: "chip" },
				// Enmienda del propietario (2026-08-16, Constitución Cap. 14): zona
				// propia de NEXORA para usuarios/roles, separada de `Administrator`.
				// Restringida a NEXORA Administrator (permissions.py: manage_users/
				// view_users); visible en el menú solo para quien tiene el rol, igual
				// que cualquier otro destino — la carcasa no oculta entradas por rol,
				// el servidor rechaza la acción si no corresponde.
				{ route: "nexora-administracion", label: "Administración", icon: "lock" },
			],
		},
	];

	/**
	 * NXR-UX-0014 — barra inferior de teléfono: los cuatro destinos más frecuentes de
	 * `SECTIONS` (uno de "Hoy", uno de "Dinero", más el buscador) y un quinto botón que
	 * abre el mismo cajón que ya existe para todo lo demás. No es una lista nueva de
	 * rutas: son referencias a las mismas cuatro entradas de `SECTIONS`, así que un
	 * cambio de ruta ahí no puede desalinear la barra inferior de la de escritorio. Las
	 * etiquetas son más cortas que en el cajón a propósito — cuatro columnas de un
	 * teléfono no tienen el ancho de una fila de escritorio — pero "Buscar" ya es la
	 * etiqueta exacta que usa el botón de búsqueda de la barra superior (línea de
	 * `data-shell-search` más abajo), así que no es una etiqueta nueva, es la misma.
	 */
	const TABBAR_ITEMS = [
		{ route: "nexora-dashboard", label: "Resumen", icon: "grid" },
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
		menu: "M3.5 5.5h13M3.5 10h13M3.5 14.5h13",
		collapse: "M12.5 5l-4.5 5 4.5 5",
		close: "M5 5l10 10M15 5L5 15",
	};

	const svg = (name) =>
		`<svg viewBox="0 0 20 20" aria-hidden="true" focusable="false"><path d="${ICONS[name]}" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg>`;

	function currentRoute() {
		return String((frappe.get_route?.() || [])[0] || "").toLowerCase();
	}

	/**
	 * La carcasa pertenece a las pantallas de NEXORA. El escritorio del marco —listas,
	 * formularios de doctype, ajustes— se deja intacto: quien administra la instalación
	 * necesita esas herramientas tal como son.
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

	function build() {
		const node = document.createElement("div");
		node.className = "nxr-shell";
		node.dataset.collapsed = collapsed() ? "true" : "false";
		document.documentElement.setAttribute("data-nxr-shell-collapsed", node.dataset.collapsed);
		node.innerHTML = `
			<a class="nxr-shell__skip" href="#body">${__("Saltar al contenido")}</a>
			<aside class="nxr-shell__nav" aria-label="${__("Secciones de NEXORA")}">
				<div class="nxr-shell__brand">
					<svg class="nxr-shell__mark" viewBox="0 0 40 40" aria-hidden="true" focusable="false">
						<rect width="40" height="40" rx="11" fill="currentColor" opacity="0.12"></rect>
						<rect x="0.75" y="0.75" width="38.5" height="38.5" rx="10.25" fill="none"
							stroke="currentColor" stroke-opacity="0.3" stroke-width="1.5"></rect>
						<path d="M12 28V12h4.4l7.2 9.7V12H28v16h-4.4l-7.2-9.7V28z" fill="currentColor"></path>
					</svg>
					<span class="nxr-shell__word">NEXORA</span>
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
								<a class="nxr-shell__link" href="/app/${item.route}" data-shell-route="${item.route}">
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
				<div class="nxr-shell__actions">
					<button type="button" class="nxr-ds-btn nxr-ds-btn--secondary nxr-shell__search" data-shell-search>
						${svg("search")}<span>${__("Buscar")}</span>
					</button>
					<button type="button" class="nxr-ds-btn nxr-ds-btn--primary" data-shell-income>
						${__("Registrar fondos")}
					</button>
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
			</nav>`;
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
		node.querySelector("[data-shell-search]").addEventListener("click", () => {
			frappe.set_route("nexora-search");
		});
		node.querySelector("[data-shell-income]").addEventListener("click", () => {
			window.nexora.openIncomeDialog?.();
		});
		// Navegar dentro de la aplicación no recarga la página: el enlace conserva su
		// `href` real para que se pueda abrir en otra pestaña, y el clic normal lo
		// intercepta el enrutador.
		node.querySelectorAll("[data-shell-route]").forEach((link) => {
			link.addEventListener("click", (event) => {
				if (event.metaKey || event.ctrlKey || event.shiftKey || event.button !== 0) return;
				event.preventDefault();
				openDrawer(false);
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

	function sync() {
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
		if (!intact(shell)) {
			shell?.remove();
			shell = build();
			document.documentElement.classList.add(ROOT_CLASS);
		}
		openDrawer(false);
		paintActive();
		paintContext();
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
			if (row) goToPaletteRoute(row.dataset.commandRoute);
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
			<li class="nxr-command-bar__item" role="option" data-command-route="${item.route}"
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
			goToPaletteRoute(rows[current >= 0 ? current : 0].dataset.commandRoute);
			return;
		}
		event.preventDefault();
		const next =
			event.key === "ArrowDown" ? Math.min(current + 1, rows.length - 1) : Math.max(current - 1, 0);
		rows.forEach((row, index) => row.setAttribute("aria-selected", index === next ? "true" : "false"));
		rows[next].scrollIntoView({ block: "nearest" });
	}

	function goToPaletteRoute(route) {
		if (!route) return;
		closePalette();
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
