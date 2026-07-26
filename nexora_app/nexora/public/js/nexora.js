frappe.provide("nexora");

window.nexora.identity = Object.freeze({
	product: "NEXORA",
	version: "0.1",
	description: "Gestión Integral de Fondos, Proyectos y Operaciones",
});

(() => {
	const PWA_VERSION = "2026.07.26-f1";
	const WORKER_URL = "/nexora-service-worker.js";
	const destinations = [
		{ label: __("Resumen"), href: "/app/nexora-dashboard" },
		{ label: __("Fondos y operaciones"), href: "/app/nexora-finance" },
		{ label: __("Contratos"), href: "/app/nexora-contracts" },
		{ label: __("Proveedores"), href: "/app/nexora-suppliers" },
		{ label: __("Evidencias"), href: "/app/nexora-evidence" },
		{ label: __("Reportes"), href: "/app/nexora-reports" },
	];
	let pwaRegistration = null;

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

	function ensureManifest() {
		let link = document.querySelector('link[rel="manifest"]');
		if (!link) {
			link = document.createElement("link");
			link.rel = "manifest";
			document.head.appendChild(link);
		}
		link.dataset.nexora = "1";
		link.href = `/assets/nexora/manifest.json?v=${encodeURIComponent(PWA_VERSION)}`;
	}

	function setOfflineBanner(offline) {
		let banner = document.querySelector(".nxr-offline-banner");
		if (!offline) {
			banner?.remove();
			return;
		}
		if (!isNexoraLocation(currentLocation()) || banner) return;
		banner = document.createElement("div");
		banner.className = "nxr-offline-banner";
		banner.setAttribute("role", "status");
		banner.textContent = __("Sin conexión. Los datos no se guardarán hasta recuperar internet.");
		document.body.appendChild(banner);
	}

	async function registerPwa() {
		if (
			pwaRegistration ||
			!("serviceWorker" in navigator) ||
			!window.isSecureContext ||
			!isNexoraLocation(currentLocation())
		) {
			return;
		}
		try {
			pwaRegistration = await navigator.serviceWorker.register(WORKER_URL, {
				scope: "/app/",
				updateViaCache: "none",
			});
			await pwaRegistration.update();
			pwaRegistration.active?.postMessage({ type: "CLEAR_OLD_CACHES" });
		} catch (error) {
			console.warn("NEXORA PWA registration failed", error);
		}
	}

	function enhancePwa() {
		if (!isNexoraLocation(currentLocation())) {
			document.querySelector(".nxr-offline-banner")?.remove();
			return;
		}
		ensureManifest();
		setOfflineBanner(!navigator.onLine);
		void registerPwa();
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

	const scheduleRender = () =>
		window.requestAnimationFrame(() => {
			renderNavigation();
			enhancePwa();
		});
	frappe.router?.on?.("change", scheduleRender);
	window.addEventListener("online", () => setOfflineBanner(false));
	window.addEventListener("offline", () => setOfflineBanner(true));
	if (typeof frappe.ready === "function") frappe.ready(scheduleRender);
	else scheduleRender();
})();
