(() => {
	"use strict";

	const MODULES = [
		["CC00", "Inicio", "⌂", ["construcontrol-dashboard"], "Principal"],
		["FI01", "Ingresos", "+", ["List", "CC Funding Source"], "Finanzas"],
		["FI02", "Gastos", "−", ["List", "CC Expense Control"], "Finanzas"],
		["FI03", "Cuentas por pagar", "▤", ["List", "CC Payable Control"], "Finanzas"],
		["CO01", "Contratos", "▧", ["List", "CC Labor Contract"], "Obra"],
		["PR01", "Fases", "◫", ["List", "CC Construction Phase"], "Obra"],
		["QC01", "Avance", "✓", ["List", "CC Progress Update"], "Obra"],
		["MM01", "Materiales", "▦", ["List", "CC Material Ledger"], "Materiales"],
		["MIGO", "Inventario", "⇄", ["List", "CC Inventory Movement"], "Materiales"],
		["MM02", "Compras", "⌑", ["List", "CC Procurement Request"], "Materiales"],
		["CL01", "Cierres", "▣", ["construcontrol-closing-center"], "Control"],
		["BI01", "Reportes", "▥", ["construcontrol-reporting-center"], "Control"],
		["AU01", "Auditoría", "◎", ["List", "CC Audit Log"], "Control"],
		["US01", "Usuarios", "♙", ["construcontrol-users"], "Administración", "manager"],
		["INT", "Integraciones", "⌘", ["construcontrol-integrations"], "Administración", "admin"],
		["MIG", "Migración", "⇧", ["construcontrol-migration-console"], "Administración", "admin"],
	];
	const TITLES = {
		"CC Funding Source": "Ingresos",
		"CC Expense Control": "Gastos",
		"CC Payable Control": "Cuentas por pagar",
		"CC Labor Contract": "Contratos",
		"CC Construction Phase": "Fases",
		"CC Progress Update": "Avances de obra",
		"CC Material Ledger": "Materiales",
		"CC Inventory Movement": "Movimientos de inventario",
		"CC Procurement Request": "Compras",
		"CC Weekly Closing": "Cierres semanales",
		"CC Audit Log": "Auditoría",
		"CC Financial Institution": "Instituciones financieras",
		"CC Generated Report": "Reportes generados",
		"CC Notification Contact": "Contactos de notificación",
		"CC Notification Rule": "Reglas de notificación",
		"CC Notification Log": "Historial de notificaciones",
		"CC Approval Request": "Aprobaciones",
		"CC Evidence": "Evidencias",
		"CC Change Order": "Órdenes de cambio",
		"CC Daily Site Log": "Bitácora diaria",
		"CC Safety Incident": "Seguridad",
		"CC Equipment Control": "Equipos",
		"CC Tool Loan": "Préstamos de herramientas",
		"CC Project Profile": "Proyecto",
		"CC Integration Registry": "Integraciones",
		"CC Crew Attendance": "Asistencia de cuadrilla",
		"CC Crew Member": "Personal de obra",
	};
	const SINGULAR = {
		"CC Funding Source": "ingreso",
		"CC Expense Control": "gasto",
		"CC Payable Control": "cuenta por pagar",
		"CC Labor Contract": "contrato",
		"CC Construction Phase": "fase",
		"CC Progress Update": "avance",
		"CC Material Ledger": "material",
		"CC Inventory Movement": "movimiento",
		"CC Procurement Request": "solicitud de compra",
		"CC Weekly Closing": "cierre",
		"CC Financial Institution": "institución",
		"CC Approval Request": "aprobación",
		"CC Evidence": "evidencia",
		"CC Change Order": "orden de cambio",
		"CC Daily Site Log": "bitácora",
		"CC Safety Incident": "incidente",
		"CC Equipment Control": "equipo",
		"CC Tool Loan": "préstamo",
	};
	const CC_TYPES = new Set(Object.keys(TITLES));
	const MOBILE = new Set(["CC00", "FI01", "FI02", "QC01"]);

	const getRoute = () => {
		try {
			return frappe.get_route() || [];
		} catch (_) {
			return [];
		}
	};
	const roleSet = () => new Set(window.frappe?.user_roles || window.frappe?.boot?.user?.roles || []);
	const admin = () => roleSet().has("System Manager");
	const manager = () => admin() || roleSet().has("ConstruControl Manager");
	const roleLabel = () =>
		admin()
			? "ADMIN"
			: roleSet().has("ConstruControl Manager")
			? "MANAGER"
			: roleSet().has("ConstruControl Operator")
			? "OPERATOR"
			: roleSet().has("ConstruControl Auditor")
			? "AUDITOR"
			: "VIEWER";
	const items = () =>
		MODULES.filter((row) => row[5] !== "admin" || admin()).filter(
			(row) => row[5] !== "manager" || manager()
		);
	const isCC = (route) =>
		String(route[0] || "").startsWith("construcontrol-") ||
		CC_TYPES.has(String(route[0] || "")) ||
		CC_TYPES.has(String(route[1] || ""));
	const same = (route, target) =>
		target.length === 1 ? route[0] === target[0] : route[0] === target[0] && route[1] === target[1];
	const go = (target) => {
		closeMore();
		frappe.set_route(...target);
	};
	const title = (route) =>
		items().find((row) => same(route, row[3]))?.[1] ||
		TITLES[String(route[1] || route[0] || "")] ||
		"ConstruControl";

	function installMetadata() {
		[
			["manifest", "/assets/erpnext/construcontrol/manifest.webmanifest"],
			["apple-touch-icon", "/assets/erpnext/construcontrol/apple-touch-icon-180.png"],
			["icon", "/assets/erpnext/construcontrol/favicon-32.png"],
		].forEach(([rel, href]) => {
			let node = document.querySelector(`link[rel="${rel}"][data-cc]`);
			if (!node) {
				node = document.createElement("link");
				node.rel = rel;
				node.dataset.cc = "1";
				document.head.appendChild(node);
			}
			node.href = href;
		});
		const meta = {
			"theme-color": "#175c4c",
			"apple-mobile-web-app-capable": "yes",
			"apple-mobile-web-app-title": "ConstruControl",
		};
		Object.entries(meta).forEach(([name, content]) => {
			let node = document.querySelector(`meta[name="${name}"][data-cc]`);
			if (!node) {
				node = document.createElement("meta");
				node.name = name;
				node.dataset.cc = "1";
				document.head.appendChild(node);
			}
			node.content = content;
		});
	}

	function button(row, className) {
		const node = document.createElement("button");
		node.type = "button";
		node.className = className;
		node.dataset.route = JSON.stringify(row[3]);
		node.dataset.code = row[0];
		node.innerHTML = `<span class="cc-shell-icon" aria-hidden="true">${row[2]}</span><span class="cc-shell-label"></span>`;
		node.querySelector(".cc-shell-label").textContent = row[1];
		node.addEventListener("click", () => go(row[3]));
		return node;
	}

	function ensureSidebar() {
		if (document.querySelector(".cc-desktop-sidebar")) return;
		const aside = document.createElement("aside");
		aside.className = "cc-desktop-sidebar";
		aside.innerHTML = `<button class="cc-brand" type="button"><span class="cc-brand-mark">CC</span><span class="cc-brand-words"><strong>ConstruControl</strong><small>Gestión residencial</small></span></button>`;
		aside.querySelector(".cc-brand").addEventListener("click", () => go(["construcontrol-dashboard"]));
		[...new Set(items().map((row) => row[4]))].forEach((group) => {
			const section = document.createElement("section");
			section.className = "cc-sidebar-group";
			section.innerHTML = `<div class="cc-sidebar-heading"></div>`;
			section.querySelector(".cc-sidebar-heading").textContent = group;
			items()
				.filter((row) => row[4] === group)
				.forEach((row) => section.appendChild(button(row, "cc-sidebar-link")));
			aside.appendChild(section);
		});
		document.body.appendChild(aside);
	}

	function ensureTopbar() {
		if (document.querySelector(".cc-app-topbar")) return;
		const bar = document.createElement("header");
		bar.className = "cc-app-topbar";
		bar.innerHTML = `<button class="cc-topbar-button cc-topbar-back" type="button" aria-label="Regresar">‹</button><div class="cc-topbar-title-wrap"><small>CONSTRUCONTROL</small><strong class="cc-topbar-title">Inicio</strong></div><button class="cc-topbar-button cc-topbar-home" type="button" aria-label="Inicio">⌂</button><button class="cc-profile-button" type="button"><span class="cc-profile-role">${roleLabel()}</span><span class="cc-profile-name"></span></button>`;
		bar.querySelector(".cc-profile-name").textContent = window.frappe?.boot?.user?.full_name || "Usuario";
		bar.querySelector(".cc-topbar-home").onclick = () => go(["construcontrol-dashboard"]);
		bar.querySelector(".cc-profile-button").onclick = () => go(["construcontrol-profile"]);
		bar.querySelector(".cc-topbar-back").onclick = () => {
			const current = getRoute();
			if (current[0] === "Form" && current[1]) frappe.set_route("List", current[1]);
			else if (history.length > 1) history.back();
			else go(["construcontrol-dashboard"]);
		};
		document.body.appendChild(bar);
	}

	function ensureMobile() {
		if (document.querySelector(".cc-mobile-nav")) return;
		const nav = document.createElement("nav");
		nav.className = "cc-mobile-nav";
		nav.setAttribute("aria-label", "Navegación principal");
		items()
			.filter((row) => MOBILE.has(row[0]))
			.forEach((row) => nav.appendChild(button(row, "cc-mobile-link")));
		const more = document.createElement("button");
		more.type = "button";
		more.className = "cc-mobile-link cc-more-toggle";
		more.innerHTML = `<span class="cc-shell-icon">•••</span><span class="cc-shell-label">Más</span>`;
		more.onclick = toggleMore;
		nav.appendChild(more);
		document.body.appendChild(nav);
	}

	function ensureMore() {
		if (document.querySelector(".cc-more-sheet")) return;
		const backdrop = document.createElement("button");
		backdrop.type = "button";
		backdrop.className = "cc-more-backdrop";
		backdrop.hidden = true;
		backdrop.onclick = closeMore;
		const sheet = document.createElement("section");
		sheet.className = "cc-more-sheet";
		sheet.hidden = true;
		sheet.innerHTML = `<div class="cc-more-header"><strong>Todos los módulos</strong><button type="button" class="cc-more-close" aria-label="Cerrar">×</button></div><div class="cc-more-grid"></div>`;
		sheet.querySelector(".cc-more-close").onclick = closeMore;
		items().forEach((row) =>
			sheet.querySelector(".cc-more-grid").appendChild(button(row, "cc-more-module"))
		);
		document.body.append(backdrop, sheet);
	}

	function closeMore() {
		const backdrop = document.querySelector(".cc-more-backdrop"),
			sheet = document.querySelector(".cc-more-sheet");
		if (backdrop) backdrop.hidden = true;
		if (sheet) sheet.hidden = true;
		document.body.classList.remove("cc-more-open");
	}
	function toggleMore() {
		ensureMore();
		const backdrop = document.querySelector(".cc-more-backdrop"),
			sheet = document.querySelector(".cc-more-sheet");
		const open = !sheet || sheet.hidden;
		if (backdrop) backdrop.hidden = !open;
		if (sheet) sheet.hidden = !open;
		document.body.classList.toggle("cc-more-open", open);
	}

	function updateNativePage(current) {
		const doctype = String(current[1] || "");
		const friendly = TITLES[doctype];
		if (!friendly) return;
		if (current[0] === "List") {
			document.querySelectorAll(".page-title .title-text, .page-head .title-text").forEach((node) => {
				node.textContent = friendly;
			});
			const primary = document.querySelector(".page-actions .primary-action");
			const singular = SINGULAR[doctype];
			if (primary && singular) {
				primary.textContent = `Nuevo ${singular}`;
				primary.setAttribute("aria-label", `Nuevo ${singular}`);
				primary.title = `Nuevo ${singular}`;
			}
		}
		document.title = `${friendly} · ConstruControl`;
	}

	function update(current) {
		document.querySelectorAll("[data-route]").forEach((node) => {
			let target = [];
			try {
				target = JSON.parse(node.dataset.route || "[]");
			} catch {
				target = [];
			}
			const active = same(current, target);
			node.classList.toggle("is-active", active);
			node.setAttribute("aria-current", active ? "page" : "false");
		});
		const heading = document.querySelector(".cc-topbar-title");
		if (heading) heading.textContent = title(current);
		const role = document.querySelector(".cc-profile-role");
		if (role) role.textContent = roleLabel();
		updateNativePage(current);
		const actions = document.querySelector(".page-actions");
		if (actions) {
			let close = actions.querySelector(".cc-close-view");
			if (!close) {
				close = document.createElement("button");
				close.className = "btn btn-default btn-sm cc-close-view";
				close.type = "button";
				actions.prepend(close);
			}
			close.textContent = current[0] === "Form" ? "Cerrar" : "Inicio";
			close.onclick = () =>
				current[0] === "Form" && current[1]
					? frappe.set_route("List", current[1])
					: go(["construcontrol-dashboard"]);
		}
	}

	function remove() {
		[
			".cc-desktop-sidebar",
			".cc-app-topbar",
			".cc-mobile-nav",
			".cc-more-backdrop",
			".cc-more-sheet",
		].forEach((selector) => document.querySelector(selector)?.remove());
		document.body.classList.remove("cc-construcontrol-route", "cc-more-open");
	}

	function apply() {
		const current = getRoute();
		if (!isCC(current)) {
			remove();
			return;
		}
		document.body.classList.add("cc-construcontrol-route");
		ensureSidebar();
		ensureTopbar();
		ensureMobile();
		ensureMore();
		update(current);
		closeMore();
		setTimeout(() => update(current), 80);
	}

	installMetadata();
	window.addEventListener("load", apply);
	window.addEventListener("keydown", (event) => {
		if (event.key === "Escape") closeMore();
	});
	frappe.router?.on?.("change", apply);
})();
