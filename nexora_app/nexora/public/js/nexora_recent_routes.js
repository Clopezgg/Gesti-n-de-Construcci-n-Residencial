frappe.provide("nexora");

/**
 * Atajos de navegación reciente: qué pantallas de NEXORA visitó esta persona hace
 * poco, para retomar un trabajo interrumpido sin recorrer la navegación entera. Se
 * guarda en `localStorage`, por usuario -un equipo compartido no debe mezclar el
 * historial de dos personas distintas-, y solo recuerda rutas de NEXORA: el resto del
 * escritorio del marco no es parte de este producto.
 */
(() => {
	"use strict";

	const MAX_ENTRIES = 6;
	const STORAGE_PREFIX = "nexora:recent-routes:";

	function storageKey() {
		return `${STORAGE_PREFIX}${frappe.session?.user || "guest"}`;
	}

	function isNexoraRoute(route) {
		return typeof route === "string" && route.startsWith("nexora-");
	}

	/** Las etiquetas viven en la carcasa (`nexora_shell.js`); repetirlas aquí las
	 * dejaría divergiendo la primera vez que alguien renombrara un destino ahí. */
	function labelFor(route) {
		const sections = window.nexora.shell?.sections || [];
		for (const section of sections) {
			const match = section.items?.find((item) => item.route === route);
			if (match) return match.label;
		}
		return route;
	}

	function read() {
		try {
			const raw = window.localStorage.getItem(storageKey());
			const parsed = raw ? JSON.parse(raw) : [];
			return Array.isArray(parsed) ? parsed : [];
		} catch (_error) {
			return [];
		}
	}

	function write(entries) {
		try {
			window.localStorage.setItem(storageKey(), JSON.stringify(entries));
		} catch (_error) {
			// Almacenamiento lleno o deshabilitado (modo privado): la función queda en
			// silencio, no es motivo para romper la navegación.
		}
	}

	function record(route) {
		if (!isNexoraRoute(route)) return;
		const entries = read().filter((entry) => entry.route !== route);
		entries.unshift({ route, visited_at: Date.now() });
		write(entries.slice(0, MAX_ENTRIES));
	}

	function list() {
		const current = String((frappe.get_route?.() || [])[0] || "").toLowerCase();
		return read()
			.filter((entry) => entry.route !== current)
			.map((entry) => ({ ...entry, label: labelFor(entry.route) }));
	}

	function onRouteChange() {
		const route = String((frappe.get_route?.() || [])[0] || "").toLowerCase();
		record(route);
	}

	function install() {
		frappe.router?.on?.("change", onRouteChange);
		onRouteChange();
	}

	// Igual que la carcasa: `frappe.get_route()` no es fiable hasta que el enrutador
	// resolvió la ruta inicial desde la URL.
	if (typeof frappe.ready === "function") frappe.ready(install);
	else install();

	window.nexora.recentRoutes = Object.freeze({ list });
})();
