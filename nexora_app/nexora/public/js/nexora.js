frappe.provide("nexora");

window.nexora.identity = Object.freeze({
	product: "NEXORA",
	version: "0.1",
	description: "Gestión Integral de Fondos, Proyectos y Operaciones",
});

(() => {
	const destinations = [
		{ label: __("Resumen"), href: "/app/nexora", route: "nexora" },
		{ label: __("Fondos"), href: "/app/nexora-finance", route: "nexora-finance" },
		{ label: __("Fuentes"), href: "/app/nxr-fund-source", route: "nxr-fund-source" },
		{ label: __("Libro Central"), href: "/app/nxr-operation", route: "nxr-operation" },
	];

	function currentRoute() {
		return (frappe.get_route?.() || []).join("/").toLowerCase();
	}

	function isNexoraRoute(route) {
		return route === "nexora" || route === "nexora-finance" || route.startsWith("nxr-");
	}

	function renderNavigation() {
		const route = currentRoute();
		const existing = document.querySelector(".nxr-product-shell");
		if (!isNexoraRoute(route)) {
			existing?.remove();
			return;
		}
		const main = document.querySelector(".layout-main-section");
		if (!main) return;
		const shell = existing || document.createElement("section");
		shell.className = "nxr-product-shell";
		shell.setAttribute("aria-label", __("Navegación principal de NEXORA"));
		shell.innerHTML = `
			<div class="nxr-product-heading">
				<div>
					<span class="nxr-product-version">NEXORA 0.1</span>
					<strong>${__("Fondos, proyectos y operaciones")}</strong>
				</div>
				<div class="nxr-capabilities" aria-label="${__("Capacidades disponibles")}">
					<span>${__("Ingresos")}</span><span>${__("Salidas")}</span>
					<span>${__("Multifuente")}</span><span>${__("Auditoría")}</span>
				</div>
			</div>
			<nav class="nxr-product-nav">
				${destinations
					.map(
						(item) => `<a href="${item.href}" class="${
							route === item.route || route.startsWith(`${item.route}/`) ? "is-active" : ""
						}">${frappe.utils.escape_html(item.label)}</a>`
					)
					.join("")}
			</nav>`;
		if (!existing) main.prepend(shell);
	}

	const scheduleRender = () => window.requestAnimationFrame(renderNavigation);
	frappe.router?.on?.("change", scheduleRender);
	frappe.ready(scheduleRender);
})();
