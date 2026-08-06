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
 * responde cada grupo. La pantalla del marco se dibuja dentro del marco de contenido.
 *
 * Dos reglas de convivencia con Frappe, y las dos importan:
 *
 * 1. La carcasa solo se monta en rutas de NEXORA. Fuera de ellas se desmonta entera y el
 *    escritorio queda exactamente como estaba: este producto vive dentro de una
 *    instalación que también se administra por el escritorio, y romperlo dejaría sin
 *    herramientas a quien la mantiene.
 * 2. No se borra nada del marco. Se oculta con una clase en la raíz y se retira al salir.
 *    Un `remove()` sobre la barra de Frappe sería irreversible sin recargar.
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
			items: [
				{ route: "nexora-dashboard", label: "Resumen", icon: "grid" },
				{ route: "nexora-operations", label: "Operación diaria", icon: "flow" },
				{ route: "nexora-search", label: "Buscador", icon: "search" },
			],
		},
		{
			label: "Dinero",
			items: [
				{ route: "nexora-finance", label: "Fondos", icon: "wallet" },
				{ route: "nexora-reports", label: "Reportes", icon: "chart" },
				{ route: "nexora-closing", label: "Cierre semanal", icon: "lock" },
			],
		},
		{
			label: "Compras",
			items: [
				{ route: "nexora-purchase-requests", label: "Solicitudes", icon: "cart" },
				{ route: "nexora-quotations", label: "Cotizaciones", icon: "tag" },
				{ route: "nexora-suppliers", label: "Proveedores", icon: "truck" },
			],
		},
		{
			label: "Expediente",
			items: [
				{ route: "nexora-contracts", label: "Contratos", icon: "contract" },
				{ route: "nexora-entities", label: "Entidades", icon: "users" },
				{ route: "nexora-evidence", label: "Comprobantes", icon: "document" },
			],
		},
	];

	/** Trazos de 20×20, sin relleno: heredan el color y pesan lo mismo entre sí. */
	const ICONS = {
		grid: "M3.5 3.5h5.2v5.2H3.5zM11.3 3.5h5.2v5.2h-5.2zM3.5 11.3h5.2v5.2H3.5zM11.3 11.3h5.2v5.2h-5.2z",
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
		node.innerHTML = `
			<a class="nxr-shell__skip" href="#nxr-shell-content">${__("Saltar al contenido")}</a>
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
						${__("Registrar ingreso")}
					</button>
				</div>
			</header>
			<div class="nxr-shell__content" id="nxr-shell-content"></div>`;
		document.body.appendChild(node);

		node.querySelector("[data-shell-collapse]").addEventListener("click", () => {
			const next = node.dataset.collapsed !== "true";
			node.dataset.collapsed = next ? "true" : "false";
			persistCollapsed(next);
		});
		node.querySelector("[data-shell-drawer]").addEventListener("click", () => openDrawer(true));
		node.querySelector("[data-shell-close]").addEventListener("click", () => openDrawer(false));
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

	function openDrawer(open) {
		if (!shell) return;
		shell.dataset.drawer = open ? "open" : "closed";
		shell.querySelector("[data-shell-close]").hidden = !open;
		shell.querySelector("[data-shell-drawer]").setAttribute("aria-expanded", open ? "true" : "false");
	}

	/**
	 * El contenido del marco se traslada dentro del marco de contenido en vez de
	 * duplicarlo. Mover el nodo conserva sus manejadores y su estado: recrearlo habría
	 * dejado sin efecto todo lo que las pantallas montaron encima.
	 */
	function adopt(node) {
		const container = document.getElementById("body") || document.querySelector(".main-section");
		const slot = node.querySelector(".nxr-shell__content");
		if (!container || !slot || container.parentElement === slot) return;
		slot.appendChild(container);
	}

	function release(node) {
		const container = node?.querySelector(".nxr-shell__content > #body");
		if (container) document.body.appendChild(container);
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
				release(shell);
				shell.remove();
				shell = null;
				document.documentElement.classList.remove(ROOT_CLASS);
			}
			return;
		}
		if (!shell) {
			shell = build();
			document.documentElement.classList.add(ROOT_CLASS);
		}
		adopt(shell);
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

	window.nexora.shell = Object.freeze({ sections: SECTIONS, sync: schedule });

	function install() {
		frappe.router?.on?.("change", schedule);
		document.addEventListener("nexora:context-changed", schedule);
		schedule();
	}

	if (typeof frappe.ready === "function") frappe.ready(install);
	else install();
})();
