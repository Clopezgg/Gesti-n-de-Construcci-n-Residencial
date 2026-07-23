frappe.provide("nexora");

window.nexora.identity = Object.freeze({
	product: "NEXORA",
	version: "0.1",
	description: "Gestión Integral de Fondos, Proyectos y Operaciones",
});

(() => {
	const destinations = [
		{ label: __("Resumen"), href: "/app/nexora" },
		{ label: __("Fondos"), href: "/app/nexora-finance" },
		{ label: __("Fuentes"), href: "/app/nxr-fund-source" },
		{ label: __("Libro Central"), href: "/app/nxr-operation" },
	];

	function currentLocation() {
		return {
			path: window.location.pathname.toLowerCase(),
			route: (frappe.get_route?.() || []).join("/").toLowerCase(),
		};
	}

	function isNexoraLocation({ path, route }) {
		return (
			path === "/app/nexora" ||
			path.startsWith("/app/nexora-") ||
			path.startsWith("/app/nxr-") ||
			route === "nexora" ||
			route === "nexora-finance" ||
			route.includes("nxr fund source") ||
			route.includes("nxr operation")
		);
	}

	function renderNavigation() {
		const location = currentLocation();
		const existing = document.querySelector(".nxr-product-shell");
		if (!isNexoraLocation(location)) {
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
						(item) =>
							`<a href="${item.href}" class="${
								location.path === item.href || location.path.startsWith(`${item.href}/`)
									? "is-active"
									: ""
							}">${frappe.utils.escape_html(item.label)}</a>`
					)
					.join("")}
			</nav>`;
		if (!existing) main.prepend(shell);
	}

	const scheduleRender = () => window.requestAnimationFrame(renderNavigation);
	frappe.router?.on?.("change", scheduleRender);
	if (typeof frappe.ready === "function") frappe.ready(scheduleRender);
	else scheduleRender();
})();
