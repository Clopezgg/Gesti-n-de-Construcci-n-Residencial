frappe.provide("nexora");

/**
 * Capítulo 33: «Las tablas deberán permitir trabajar. No únicamente consultar.»
 *
 * Las dieciséis tablas de NEXORA se pintan con `innerHTML` en diez pantallas distintas
 * y ninguna se podía ordenar; solo Reportes exportaba. Resolver eso pantalla por
 * pantalla habría creado diez variantes del mismo comportamiento, que es justo lo que
 * prohíbe el Capítulo 34. Este módulo mejora desde un único lugar las tablas que sirven
 * para trabajar —ver `isWorkSurface`—: la pantalla no necesita pedirlo ni conocerlo.
 *
 * No reordena datos en el servidor ni pagina: ordena y exporta lo que el usuario ya
 * tiene delante, que es lo que convierte una lista en una herramienta.
 */
(() => {
	"use strict";

	const ENHANCED = "nxrTableEnhanced";
	/** Tablas mejoradas que siguen en el documento, con lo que hay que soltar al irse. */
	const active = new Map();

	function release() {
		for (const [table, entry] of active) {
			if (table.isConnected) continue;
			entry.observer.disconnect();
			active.delete(table);
		}
	}

	const MONEY = /^[-+]?[\s€$L]*[\d.,]+$/;

	const text = (node) =>
		String(node?.textContent || "")
			.replace(/\s+/g, " ")
			.trim();

	/** Convierte una celda en algo comparable sin perder el orden natural del dato. */
	function sortKey(value) {
		const raw = String(value || "").trim();
		if (!raw) return { empty: true, number: 0, text: "" };
		const iso = raw.match(/^(\d{4})-(\d{2})-(\d{2})/);
		if (iso) return { empty: false, number: Number(`${iso[1]}${iso[2]}${iso[3]}`), text: raw };
		// Fecha corta local: 05/08/2026.
		const local = raw.match(/^(\d{1,2})[/-](\d{1,2})[/-](\d{4})$/);
		if (local) {
			const pad = (part) => String(part).padStart(2, "0");
			return {
				empty: false,
				number: Number(`${local[3]}${pad(local[2])}${pad(local[1])}`),
				text: raw,
			};
		}
		if (MONEY.test(raw)) {
			// Los importes llegan formateados: se quitan separadores de millar y símbolo.
			const numeric = Number(raw.replace(/[^\d,.-]/g, "").replace(/,(?=\d{3}\b)/g, ""));
			if (Number.isFinite(numeric)) return { empty: false, number: numeric, text: raw };
		}
		return { empty: false, number: Number.NaN, text: raw.toLocaleLowerCase("es") };
	}

	function compare(left, right) {
		if (left.empty !== right.empty) return left.empty ? 1 : -1;
		const numeric = !Number.isNaN(left.number) && !Number.isNaN(right.number);
		if (numeric && left.number !== right.number) return left.number - right.number;
		return left.text.localeCompare(right.text, "es", { numeric: true });
	}

	function bodyRows(table) {
		const body = table.tBodies[0];
		return body ? [...body.rows].filter((row) => row.cells.length > 1) : [];
	}

	function sortBy(table, index, direction) {
		const body = table.tBodies[0];
		if (!body) return;
		const rows = bodyRows(table);
		const decorated = rows.map((row, position) => ({
			row,
			position,
			key: sortKey(text(row.cells[index])),
		}));
		decorated.sort((a, b) => {
			const result = compare(a.key, b.key);
			// Empate: se conserva el orden original, que suele ser el cronológico.
			return (result || a.position - b.position) * direction;
		});
		decorated.forEach((entry) => body.appendChild(entry.row));
	}

	function csv(table) {
		const escape = (value) => `"${String(value).replace(/"/g, '""')}"`;
		const lines = [];
		for (const row of [...table.rows]) {
			lines.push([...row.cells].map((cell) => escape(text(cell))).join(","));
		}
		// BOM para que Excel reconozca los acentos sin pedir importación manual.
		return `\uFEFF${lines.join("\r\n")}\r\n`;
	}

	function download(table, label) {
		const blob = new Blob([csv(table)], { type: "text/csv;charset=utf-8" });
		const url = URL.createObjectURL(blob);
		const link = document.createElement("a");
		link.href = url;
		link.download = `${label}.csv`;
		document.body.appendChild(link);
		link.click();
		link.remove();
		URL.revokeObjectURL(url);
	}

	function summarize(table, summary) {
		const count = bodyRows(table).length;
		const message = count ? __("{0} filas", [count]) : __("Sin filas que mostrar por ahora.");
		if (summary.textContent !== message) summary.textContent = message;
	}

	/**
	 * En móvil la pantalla sustituye la tabla por tarjetas y la oculta. La barra debe
	 * irse con ella: ofrecer «Exportar CSV» y un recuento sobre una tabla que el usuario
	 * no ve es prometer sobre algo que no está delante.
	 */
	function syncToolbar(table, bar) {
		const hidden = !table.offsetParent;
		if (bar.hidden !== hidden) bar.hidden = hidden;
	}

	function toolbar(table, label) {
		const bar = document.createElement("div");
		bar.className = "nxr-table-toolbar";
		const summary = document.createElement("span");
		summary.className = "nxr-table-summary";
		summary.setAttribute("role", "status");
		const action = document.createElement("button");
		action.type = "button";
		action.className = "btn btn-xs btn-default nxr-table-export";
		action.textContent = __("Exportar CSV");
		action.addEventListener("click", () => download(table, label));
		bar.append(summary, action);
		return { bar, summary };
	}

	/**
	 * No toda `<table>` es una superficie de trabajo. El resumen de la línea del
	 * movimiento tiene una sola fila: ordenarla no significa nada, exportarla tampoco, y
	 * la barra solo empuja el formulario hacia abajo —lo suficiente para meter el botón
	 * «Continuar» del asistente debajo de la barra fija de la aplicación y romper un
	 * flujo que funcionaba—. El Capítulo 34 pide un único componente reutilizable, no que
	 * toda tabla se convierta en una rejilla de datos.
	 */
	function isWorkSurface(table) {
		if (table.dataset.nxrTable === "plain") return false;
		return bodyRows(table).length > 1;
	}

	function enhance(table) {
		if (table.dataset[ENHANCED] === "1") return;
		const head = table.tHead?.rows?.[0];
		if (!head || !table.tBodies.length) return;
		// Se reevalúa en cada pasada: una tabla que empieza vacía y luego se llena entra
		// aquí cuando de verdad tiene filas que ordenar.
		if (!isWorkSurface(table)) return;
		table.dataset[ENHANCED] = "1";

		const label = frappe.scrub(
			text(table.closest("section, .nxr-card")?.querySelector("strong")) ||
				String(frappe.get_route?.()?.[0] || "nexora-tabla")
		);
		const { bar, summary } = toolbar(table, label);
		table.parentNode.insertBefore(bar, table);

		[...head.cells].forEach((cell, index) => {
			cell.classList.add("nxr-sortable");
			cell.tabIndex = 0;
			cell.setAttribute("role", "columnheader");
			cell.setAttribute("aria-sort", "none");
			const activate = () => {
				const ascending = cell.getAttribute("aria-sort") !== "ascending";
				[...head.cells].forEach((other) => other.setAttribute("aria-sort", "none"));
				cell.setAttribute("aria-sort", ascending ? "ascending" : "descending");
				sortBy(table, index, ascending ? 1 : -1);
			};
			cell.addEventListener("click", activate);
			cell.addEventListener("keydown", (event) => {
				if (event.key !== "Enter" && event.key !== " ") return;
				event.preventDefault();
				activate();
			});
		});

		const refresh = () => {
			summarize(table, summary);
			syncToolbar(table, bar);
		};
		refresh();
		// La pantalla repinta el cuerpo cuando cambian los datos: el resumen la sigue.
		const observer = new MutationObserver(refresh);
		observer.observe(table.tBodies[0], {
			childList: true,
			subtree: true,
			characterData: true,
		});
		// Las pantallas repintan con `innerHTML`: la tabla mejorada se sustituye entera y
		// varias veces por sesión. Sin registro, cada una dejaba su observador y su
		// listener de `resize` vivos reteniendo un nodo que ya no está en el documento.
		active.set(table, { refresh, observer });
	}

	// Girar el teléfono cambia qué representación se muestra sin tocar el DOM. Un único
	// listener global atiende a todas: uno por tabla multiplicaba el trabajo y la fuga.
	window.addEventListener(
		"resize",
		() => {
			release();
			for (const entry of active.values()) entry.refresh();
		},
		{ passive: true }
	);

	function enhanceAll() {
		release();
		const route = String(frappe.get_route?.()?.[0] || "");
		if (!route.startsWith("nexora-")) return;
		document
			.querySelectorAll(`#page-${route} table.table:not([data-nxr-table-enhanced])`)
			.forEach(enhance);
	}

	let scheduled = false;
	function schedule() {
		if (scheduled) return;
		scheduled = true;
		requestAnimationFrame(() => {
			scheduled = false;
			enhanceAll();
		});
	}

	window.nexora.tables = Object.freeze({ enhance, enhanceAll: schedule, sortKey, csv });

	function install() {
		new MutationObserver(schedule).observe(document.documentElement, {
			childList: true,
			subtree: true,
		});
		frappe.router?.on?.("change", schedule);
		schedule();
	}

	if (typeof frappe.ready === "function") frappe.ready(install);
	else install();
})();
