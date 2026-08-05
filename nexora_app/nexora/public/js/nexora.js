frappe.provide("nexora");

window.nexora.identity = Object.freeze({
	product: "NEXORA",
	version: "0.2",
	description: "Gestión Integral de Fondos, Proyectos y Operaciones",
});

// Espejo exacto de `evaluate_evidence_policy` (financial/evidence_core.py). Vive aquí,
// en el primer bundle que carga NEXORA, para que la regla exista en un solo lugar del
// cliente: la consola operativa y el gasto rápido la consumen, en vez de repetirla.
// Sin este espejo el usuario llena el formulario completo y el servidor lo rechaza al
// final, que es trabajo perdido causado por la interfaz.
window.nexora.rules = Object.freeze({
	EVIDENCE_PAYMENT_METHODS: Object.freeze(["Deposit", "Transfer"]),
	CASH_EVIDENCE_THRESHOLD_HNL: 2000,
	// `BANK_CHANNELS` en financial/operational_common.py: el servidor exige banco y
	// referencia de cuenta para todo gasto pagado por estos medios.
	BANK_CHANNELS: Object.freeze(["Remittance", "Deposit", "Transfer"]),
	requiresBankAccountDetails(paymentMethod) {
		return window.nexora.rules.BANK_CHANNELS.includes(String(paymentMethod || "").trim());
	},
	evidencePolicy(paymentMethod, amountHnl) {
		const method = String(paymentMethod || "").trim();
		if (window.nexora.rules.EVIDENCE_PAYMENT_METHODS.includes(method)) {
			return {
				required: true,
				reason: __("Los depósitos y transferencias requieren comprobante."),
			};
		}
		if (method === "Cash" && Number(amountHnl || 0) > window.nexora.rules.CASH_EVIDENCE_THRESHOLD_HNL) {
			return {
				required: true,
				reason: __("Un pago en efectivo mayor de L2,000 requiere comprobante."),
			};
		}
		return { required: false, reason: "" };
	},
});

(() => {
	// Debe coincidir con VERSION en nexora-service-worker.js: solo sirve para
	// invalidar el <link rel="manifest"> con un querystring; el propio service
	// worker gestiona su caché con su VERSION independiente.
	const PWA_VERSION = "2026.08.05-full-shell-precache";
	const WORKER_URL = "/nexora-service-worker.js";
	const destinations = [
		{ label: __("Resumen"), href: "/app/nexora-dashboard" },
		{ label: __("Operación diaria"), href: "/app/nexora-operations" },
		{ label: __("Buscador"), href: "/app/nexora-search" },
		{ label: __("Fondos y operaciones"), href: "/app/nexora-finance" },
		{ label: __("Contratos"), href: "/app/nexora-contracts" },
		{ label: __("Entidades"), href: "/app/nexora-entities" },
		{ label: __("Proveedores"), href: "/app/nexora-suppliers" },
		{ label: __("Solicitudes de compra"), href: "/app/nexora-purchase-requests" },
		{ label: __("Cotizaciones"), href: "/app/nexora-quotations" },
		{ label: __("Evidencias"), href: "/app/nexora-evidence" },
		{ label: __("Reportes"), href: "/app/nexora-reports" },
		{ label: __("Cierre semanal"), href: "/app/nexora-closing" },
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
			(path === "/app" && frappe.boot?.home_page === "nexora-dashboard") ||
			path === "/app/nexora" ||
			path.startsWith("/app/nexora-") ||
			path.startsWith("/app/nxr-") ||
			route === "nexora" ||
			route === "nexora-finance" ||
			route.includes("nxr fund source") ||
			route.includes("nxr operation")
		);
	}

	function uuid() {
		return window.nexora.ui.generateId();
	}

	function money(value) {
		return window.nexora.ui.formatMoney(value);
	}

	function notifyDataChanged(type) {
		document.dispatchEvent(new CustomEvent("nexora:data-changed", { detail: { area: "finance", type } }));
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

	async function createIncome(values, dialog) {
		const amount = Number(values.amount_hnl || 0);
		if (amount <= 0) {
			frappe.msgprint(__("Ingrese un monto mayor que cero."));
			return;
		}
		const response = await frappe.call({
			method: "nexora.financial.service.create_fund_source",
			type: "POST",
			args: {
				payload: {
					project: values.project,
					channel: values.channel,
					currency: "HNL",
					original_amount: amount,
					exchange_rate: 1,
					origin_or_sender: values.origin_or_sender,
					institution: values.institution || "",
					account_reference: values.account_reference || "",
					external_reference: values.external_reference || "",
					custodian: frappe.session.user,
					idempotency_key: uuid(),
				},
			},
			freeze: true,
			freeze_message: __("Registrando ingreso y actualizando saldo…"),
		});
		dialog.hide();
		frappe.show_alert({
			message: __("Ingreso {0} registrado por {1}", [
				response.message?.source_number || "",
				money(amount),
			]),
			indicator: "green",
		});
		notifyDataChanged("income");
	}

	function openIncomeDialog() {
		const dialog = new frappe.ui.Dialog({
			title: __("Registrar ingreso"),
			fields: [
				{
					fieldname: "project",
					label: __("Proyecto"),
					fieldtype: "Link",
					options: "Project",
					reqd: 1,
				},
				{ fieldname: "amount_hnl", label: __("Monto recibido"), fieldtype: "Currency", reqd: 1 },
				{
					fieldname: "channel",
					label: __("Cómo se recibió"),
					fieldtype: "Select",
					options: [
						{ label: __("Remesa"), value: "Remittance" },
						{ label: __("Efectivo"), value: "Cash" },
						{ label: __("Depósito bancario"), value: "Deposit" },
						{ label: __("Transferencia"), value: "Transfer" },
						{ label: __("Otro"), value: "Other" },
					],
					default: "Remittance",
					reqd: 1,
				},
				{
					fieldname: "origin_or_sender",
					label: __("Remitente u origen"),
					fieldtype: "Data",
					reqd: 1,
				},
				{ fieldname: "institution", label: __("Banco o remesadora"), fieldtype: "Data" },
				{ fieldname: "account_reference", label: __("Cuenta destino"), fieldtype: "Data" },
				{ fieldname: "external_reference", label: __("Número de referencia"), fieldtype: "Data" },
			],
			primary_action_label: __("Guardar ingreso"),
			primary_action: (values) => void createIncome(values, dialog),
		});
		dialog.show();
	}

	async function createExpense(values, dialog) {
		const amount = Number(values.amount_hnl || 0);
		if (amount <= 0) {
			frappe.msgprint(__("Ingrese un monto mayor que cero."));
			return;
		}
		const payload = {
			operation_code: "CONSTRUCTION_PAYMENT",
			economic_category: values.economic_category,
			project: values.project,
			amount_hnl: amount,
			cost_center: values.cost_center || "",
			analytic_splits: values.cost_center
				? [{ cost_center: values.cost_center, amount_hnl: amount }]
				: [],
			beneficiary_doctype: values.beneficiary ? "NXR Entity" : "",
			beneficiary: values.beneficiary || "",
			payment_method: values.payment_method,
			external_reference: values.external_reference || "",
			operation_date: frappe.datetime.get_today(),
			requester: frappe.session.user,
			approved_by: frappe.session.user,
			description: values.description || __("Gasto registrado desde NEXORA"),
			evidence: values.evidence || "",
			allocations: [{ source: values.source, amount_hnl: amount }],
		};
		const preview = await frappe.call({
			method: "nexora.financial.service.preview_central_operation",
			type: "POST",
			args: { payload },
			freeze: true,
			freeze_message: __("Comprobando saldo y datos…"),
		});
		const result = await frappe.call({
			method: "nexora.financial.service.execute_central_operation",
			type: "POST",
			args: {
				payload: {
					...payload,
					idempotency_key: uuid(),
					preview_hash: preview.message.preview_hash,
				},
			},
			freeze: true,
			freeze_message: __("Registrando gasto y actualizando saldo…"),
		});
		dialog.hide();
		frappe.show_alert({
			message: __("Gasto {0} registrado por {1}", [
				result.message?.document_number || "",
				money(amount),
			]),
			indicator: "green",
		});
		notifyDataChanged("expense");
	}

	function openExpenseDialog() {
		const dialog = new frappe.ui.Dialog({
			title: __("Registrar gasto"),
			fields: [
				{
					fieldname: "project",
					label: __("Proyecto"),
					fieldtype: "Link",
					options: "Project",
					reqd: 1,
					onchange: async () => {
						const project = dialog.get_value("project");
						if (!project) return;
						const response = await frappe.call({
							method: "nexora.financial.service.list_source_balances",
							type: "POST",
							args: { project },
						});
						const options = (response.message || [])
							.filter((row) => Number(row.available_hnl) > 0)
							.map((row) => ({
								label: `${row.source} · ${__("Disponible")}: ${money(row.available_hnl)}`,
								value: row.source,
							}));
						dialog.set_df_property("source", "options", options);
						dialog.refresh_field("source");
						if (!options.length) {
							frappe.msgprint({
								title: __("Primero registre un ingreso"),
								message: __(
									"El proyecto seleccionado no tiene fondos disponibles. Registre un ingreso antes de guardar un gasto."
								),
								indicator: "orange",
							});
						}
					},
				},
				{
					fieldname: "amount_hnl",
					label: __("Monto pagado"),
					fieldtype: "Currency",
					reqd: 1,
					onchange: () => applyExpenseEvidencePolicy(dialog),
				},
				{ fieldname: "source", label: __("Fondo que pagará"), fieldtype: "Select", reqd: 1 },
				{
					fieldname: "economic_category",
					label: __("Categoría del gasto"),
					fieldtype: "Link",
					options: "NXR Economic Category",
					reqd: 1,
				},
				{
					fieldname: "cost_center",
					label: __("Centro de costo"),
					fieldtype: "Link",
					options: "Cost Center",
				},
				{
					fieldname: "beneficiary",
					label: __("Contratista o proveedor"),
					fieldtype: "Link",
					options: "NXR Entity",
				},
				{
					fieldname: "payment_method",
					label: __("Medio de pago"),
					fieldtype: "Select",
					options: [
						{ label: __("Efectivo"), value: "Cash" },
						{ label: __("Depósito"), value: "Deposit" },
						{ label: __("Transferencia"), value: "Transfer" },
						{ label: __("Otro"), value: "Other" },
					],
					default: "Transfer",
					reqd: 1,
					onchange: () => applyExpenseEvidencePolicy(dialog),
				},
				{ fieldname: "external_reference", label: __("Referencia de pago"), fieldtype: "Data" },
				{ fieldname: "description", label: __("Concepto"), fieldtype: "Small Text", reqd: 1 },
				{ fieldname: "evidence", label: __("Comprobante"), fieldtype: "Attach" },
			],
			primary_action_label: __("Guardar gasto"),
			primary_action: (values) => void createExpense(values, dialog),
		});
		dialog.show();
		// El medio de pago nace en «Transferencia», que siempre exige comprobante: sin
		// aplicarlo al abrir, el camino por defecto del gasto rápido termina rechazado.
		applyExpenseEvidencePolicy(dialog);
	}

	function applyExpenseEvidencePolicy(dialog) {
		const policy = window.nexora.rules.evidencePolicy(
			dialog.get_value("payment_method"),
			dialog.get_value("amount_hnl")
		);
		dialog.set_df_property("evidence", "reqd", policy.required ? 1 : 0);
		dialog.set_df_property("evidence", "description", policy.reason);
	}

	function renderNavigation() {
		const location = currentLocation();
		const existing = document.querySelector(".nxr-product-navigation");
		if (!isNexoraLocation(location)) {
			existing?.remove();
			return;
		}
		const main =
			[...document.querySelectorAll(".page-container .layout-main-section")].find(
				(element) => element.closest(".page-container")?.offsetParent !== null
			) || document.querySelector(".layout-main-section");
		if (!main) return;
		const shell = existing || document.createElement("section");
		shell.className = "nxr-product-shell nxr-product-navigation";
		shell.setAttribute("aria-label", __("Navegación principal de NEXORA"));
		shell.innerHTML = `
			<div class="nxr-product-heading">
				<div>
					<span class="nxr-product-version">NEXORA 0.2</span>
					<strong>${__("Fondos, proyectos y operaciones")}</strong>
				</div>
				<div class="nxr-capabilities" aria-label="${__("Acciones frecuentes")}">
					<button type="button" class="btn btn-primary btn-sm nxr-quick-income">${__("Registrar ingreso")}</button>
					<button type="button" class="btn btn-default btn-sm nxr-quick-expense">${__("Registrar gasto")}</button>
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
		if (shell.parentElement !== main) main.prepend(shell);
		shell.querySelector(".nxr-quick-income")?.addEventListener("click", openIncomeDialog);
		shell.querySelector(".nxr-quick-expense")?.addEventListener("click", openExpenseDialog);
	}

	window.nexora.openIncomeDialog = openIncomeDialog;
	window.nexora.openExpenseDialog = openExpenseDialog;

	const scheduleRender = () => {
		[0, 50, 150, 300, 600, 1000].forEach((delay) => {
			window.setTimeout(() => {
				window.requestAnimationFrame(() => {
					renderNavigation();
					enhancePwa();
				});
			}, delay);
		});
	};
	frappe.router?.on?.("change", scheduleRender);
	window.addEventListener("online", () => setOfflineBanner(false));
	window.addEventListener("offline", () => setOfflineBanner(true));
	if (typeof frappe.ready === "function") frappe.ready(scheduleRender);
	else scheduleRender();
})();
