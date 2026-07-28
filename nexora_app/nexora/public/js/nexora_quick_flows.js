frappe.provide("nexora");

(() => {
	const escapedCurrencyMarkup = /^\s*<div\b[^>]*>\s*([^<]+?)\s*<\/div>\s*$/i;
	const guidedIncomeKey = "nexora:guided-income-context";
	let observer = null;

	function routeName() {
		return String((frappe.get_route?.() || [])[0] || "").toLowerCase();
	}

	function normalizeDashboardCurrency(root = document) {
		const nodes = root.querySelectorAll?.(
			"#page-nexora-dashboard [data-currency], #page-nexora-dashboard .nxr-pending-total"
		);
		if (!nodes) return;
		nodes.forEach((node) => {
			const raw = String(node.textContent || "").trim();
			const match = raw.match(escapedCurrencyMarkup);
			if (match) node.textContent = match[1].trim();
		});
	}

	function uuid() {
		return (
			globalThis.crypto?.randomUUID?.() || `nxr-${Date.now()}-${Math.random().toString(16).slice(2)}`
		);
	}

	function money(value) {
		return (
			window.nexora.ui?.formatMoney?.(value) ||
			new Intl.NumberFormat("es-HN", {
				style: "currency",
				currency: "HNL",
				minimumFractionDigits: 2,
			}).format(Number(value || 0))
		);
	}

	function refreshCurrentProductView() {
		const route = frappe.get_route?.() || [];
		if (route[0] === "nexora-dashboard") {
			frappe.set_route("nexora-dashboard", { refresh: Date.now() });
			return;
		}
		frappe.show_alert({ message: __("Los saldos ya fueron actualizados."), indicator: "green" });
	}

	function dashboardProject() {
		return (
			document.querySelector('#page-nexora-dashboard [data-fieldname="project"] input')?.value ||
			frappe.route_options?.project ||
			null
		);
	}

	function activeIncomeContext() {
		const globalContext = window.nexora.context?.get?.() || {};
		return {
			project: globalContext.project || dashboardProject() || null,
			period: globalContext.period || null,
			from_date: globalContext.from_date || null,
			to_date: globalContext.to_date || null,
		};
	}

	function saveGuidedIncomeContext(context) {
		try {
			window.sessionStorage?.setItem(guidedIncomeKey, JSON.stringify(context));
		} catch (error) {
			console.warn("NEXORA could not persist guided income context", error);
		}
	}

	function guidedIncomeContext() {
		try {
			return JSON.parse(window.sessionStorage?.getItem(guidedIncomeKey) || "null");
		} catch (error) {
			console.warn("NEXORA guided income context is invalid", error);
			return null;
		}
	}

	function clearGuidedIncomeContext() {
		try {
			window.sessionStorage?.removeItem(guidedIncomeKey);
		} catch (error) {
			console.warn("NEXORA could not clear guided income context", error);
		}
	}

	function openIncomeFlow() {
		const context = activeIncomeContext();
		saveGuidedIncomeContext(context);
		frappe.route_options = {
			movement_code: "101",
			guided: "income",
			project: context.project,
			from_date: context.from_date,
			to_date: context.to_date,
			nexora_period: context.period,
		};
		frappe.set_route("nexora-operations");
	}

	function replaceLegacyIncomeCard(root = document) {
		if (routeName() !== "nexora-finance") return;
		const card = root.querySelector?.("#page-nexora-finance .nxr-source-create");
		if (!card || card.dataset.unifiedIncome === "ready") return;
		card.dataset.unifiedIncome = "ready";
		card.classList.remove("nxr-card-highlight");
		card.innerHTML = `
			<h3>${__("Registrar ingreso")}</h3>
			<p class="text-muted">${__(
				"Los ingresos se registran en un único formulario con cuenta, moneda, vista previa y confirmación del efecto financiero."
			)}</p>
			<button type="button" class="btn btn-primary btn-sm" data-nexora-unified-income="1">${__(
				"Abrir formulario de ingreso"
			)}</button>`;
	}

	function revealAdvancedOperations(shell) {
		shell.removeAttribute("data-guided-income");
		shell.querySelector(".nxr-movement-help")?.removeAttribute("hidden");
		shell.querySelector('[data-field="movement_code"]')?.removeAttribute("hidden");
		shell.querySelector(".nxr-income-engine-guide")?.remove();
		clearGuidedIncomeContext();
	}

	function enhanceGuidedIncome(root = document) {
		if (routeName() !== "nexora-operations") return;
		const context = guidedIncomeContext();
		if (!context) return;
		const shell = root.querySelector?.("#page-nexora-operations .nxr-operational-shell");
		const activeIncome = shell?.querySelector(
			'.nxr-movement-chip[data-code="101"][aria-pressed="true"]'
		);
		if (!shell || !activeIncome) return;
		if (shell.dataset.guidedIncome === "ready") return;
		shell.dataset.guidedIncome = "ready";
		shell.setAttribute("data-guided-income", "true");
		shell.querySelector(".nxr-movement-help")?.setAttribute("hidden", "");
		shell.querySelector('[data-field="movement_code"]')?.setAttribute("hidden", "");
		const title = shell.querySelector(".nxr-operational-title");
		if (title) title.textContent = __("Registrar ingreso");
		const description = shell.querySelector(".nxr-operational-header .text-muted");
		if (description) {
			description.textContent = __(
				"Complete la procedencia, la cuenta y el importe. NEXORA validará el efecto antes de registrar definitivamente."
			);
		}
		const tabs = shell.querySelector(".nxr-document-tabs");
		if (tabs && !shell.querySelector(".nxr-income-engine-guide")) {
			const guide = document.createElement("div");
			guide.className = "nxr-account-hint nxr-income-engine-guide";
			const periodText = context.period
				? __("Período activo: {0}.", [context.period])
				: __("Use la fecha documental correspondiente al ingreso.");
			guide.innerHTML = `<strong>${__("Ingreso único NEXORA")}</strong><br>${periodText} ${__(
				"Primero genere la vista previa; el ingreso solo se guarda después de su confirmación."
			)} <button type="button" class="btn btn-xs btn-default" data-nexora-income-advanced="1">${__(
				"Ver operaciones avanzadas"
			)}</button>`;
			tabs.parentElement?.insertBefore(guide, tabs);
		}
		const previewButton = shell.querySelector(".nxr-preview-movement");
		const executeButton = shell.querySelector(".nxr-execute-movement");
		if (previewButton) previewButton.textContent = __("Revisar ingreso");
		if (executeButton) executeButton.textContent = __("Registrar ingreso");
	}

	function normalizeDateInput(value) {
		const text = String(value || "").trim();
		if (!text) return "";
		try {
			return String(frappe.datetime.user_to_str?.(text) || text).slice(0, 10);
		} catch (_error) {
			return text.slice(0, 10);
		}
	}

	function validateGuidedIncomePeriod(event) {
		const previewButton = event.target?.closest?.(
			"#page-nexora-operations .nxr-preview-movement"
		);
		if (!previewButton) return false;
		const context = guidedIncomeContext();
		if (!context?.from_date || !context?.to_date) return false;
		const field = document.querySelector(
			'#page-nexora-operations [data-field="document_date"] input'
		);
		const documentDate = normalizeDateInput(field?.value);
		if (!documentDate || (documentDate >= context.from_date && documentDate <= context.to_date)) {
			return false;
		}
		event.preventDefault();
		event.stopPropagation();
		event.stopImmediatePropagation();
		frappe.msgprint({
			title: __("Fecha fuera del período activo"),
			message: __(
				"Seleccione una fecha entre {0} y {1}, o cambie el período activo antes de continuar.",
				[
					frappe.datetime.str_to_user(context.from_date),
					frappe.datetime.str_to_user(context.to_date),
				]
			),
			indicator: "orange",
		});
		field?.focus();
		return true;
	}

	function refreshGuidedIncomeContext(context) {
		if (routeName() !== "nexora-operations" || !guidedIncomeContext()) return;
		const next = {
			project: context?.project || null,
			period: context?.period || null,
			from_date: context?.from_date || null,
			to_date: context?.to_date || null,
		};
		saveGuidedIncomeContext(next);
		frappe.route_options = { movement_code: "101", guided: "income", ...next };
		const wrapper = document.querySelector('[data-page-route="nexora-operations"]');
		void wrapper?.nexora_apply_operational_context?.();
		const shell = document.querySelector("#page-nexora-operations .nxr-operational-shell");
		if (shell) shell.dataset.guidedIncome = "";
		window.requestAnimationFrame(() => enhanceGuidedIncome(document));
	}

	function installSharedEnhancements() {
		const enhance = () => {
			normalizeDashboardCurrency(document);
			replaceLegacyIncomeCard(document);
			enhanceGuidedIncome(document);
		};
		if (observer) observer.disconnect();
		observer = new MutationObserver((mutations) => {
			if (
				mutations.some(
					(mutation) => mutation.type === "characterData" || mutation.addedNodes.length > 0
				)
			) {
				window.requestAnimationFrame(enhance);
			}
		});
		observer.observe(document.documentElement, {
			subtree: true,
			childList: true,
			characterData: true,
		});
		frappe.router?.on?.("change", () => window.requestAnimationFrame(enhance));
		enhance();
	}

	function setExpenseSubmitEnabled(dialog, enabled) {
		dialog.get_primary_btn()?.prop("disabled", !enabled);
	}

	function sourceOption(row) {
		return {
			label: row.source,
			value: row.source,
			description: `${__("Disponible")}: ${money(row.available_hnl)} · ${__("Saldo")}: ${money(
				row.balance_hnl
			)} · ${__("Reservado")}: ${money(row.reserved_hnl)}`,
		};
	}

	function setSourceSelectorState(dialog, { options = [], loading = false, description = "" } = {}) {
		const sourceControl = dialog.fields_dict.source;
		const placeholder = loading
			? __("Cargando fondos…")
			: options.length
			? __("Escriba o toque para seleccionar un fondo")
			: __("No hay fondos disponibles para este proyecto");

		dialog.nexoraAvailableSources = new Set(options.map((option) => option.value));
		sourceControl.set_data(options);
		sourceControl.set_value("");
		sourceControl.$input?.attr("placeholder", placeholder);
		sourceControl.$input?.prop("disabled", loading || !options.length);
		sourceControl.set_description(description);
		setExpenseSubmitEnabled(dialog, false);
	}

	async function loadExpenseSources(dialog, project) {
		if (!project) {
			setSourceSelectorState(dialog, {
				description: __("Seleccione primero el proyecto que realizará el gasto."),
			});
			return;
		}

		setSourceSelectorState(dialog, {
			loading: true,
			description: __("Consultando fondos activos y su saldo disponible…"),
		});

		try {
			const response = await frappe.call({
				method: "nexora.financial.service.list_source_balances",
				type: "POST",
				args: { project },
			});
			const options = (response.message || [])
				.filter((row) => Number(row.available_hnl) > 0)
				.map(sourceOption);

			if (!options.length) {
				setSourceSelectorState(dialog, {
					description: __(
						"El proyecto seleccionado no tiene fondos con saldo disponible. Registre un ingreso o libere una reserva antes de guardar el gasto."
					),
				});
				frappe.show_alert({
					message: __("No hay fondos disponibles para este proyecto."),
					indicator: "orange",
				});
				return;
			}

			setSourceSelectorState(dialog, {
				options,
				description: __(
					"Seleccione el fondo que financiará el gasto. La lista muestra saldo disponible, saldo total y monto reservado."
				),
			});
		} catch (error) {
			setSourceSelectorState(dialog, {
				description: __("No fue posible cargar los fondos. Cierre el diálogo e intente nuevamente."),
			});
			frappe.msgprint({
				title: __("No se pudieron cargar los fondos"),
				message: error?.message || __("Ocurrió un error al consultar los saldos del proyecto."),
				indicator: "red",
			});
		}
	}

	async function createExpense(values, dialog) {
		const amount = Number(values.amount_hnl || 0);
		const source = String(values.source || "").trim();
		if (amount <= 0) {
			frappe.msgprint(__("Ingrese un monto mayor que cero."));
			return;
		}
		if (!source || !dialog.nexoraAvailableSources?.has(source)) {
			frappe.msgprint(__("Seleccione un fondo válido con saldo disponible antes de guardar el gasto."));
			return;
		}
		const payload = {
			operation_code: "CONSTRUCTION_PAYMENT",
			economic_category: values.economic_category,
			project: values.project,
			amount_hnl: amount,
			cost_center: values.cost_center,
			analytic_splits: [{ cost_center: values.cost_center, amount_hnl: amount }],
			beneficiary_doctype: "NXR Entity",
			beneficiary: values.beneficiary,
			payment_method: values.payment_method,
			external_reference: values.external_reference || "",
			operation_date: frappe.datetime.get_today(),
			requester: frappe.session.user,
			approved_by: frappe.session.user,
			description: values.description,
			evidence: values.evidence || "",
			allocations: [{ source, amount_hnl: amount }],
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
		refreshCurrentProductView();
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
					onchange: () => void loadExpenseSources(dialog, dialog.get_value("project")),
				},
				{ fieldname: "amount_hnl", label: __("Monto pagado"), fieldtype: "Currency", reqd: 1 },
				{
					fieldname: "source",
					label: __("Fondo que pagará"),
					fieldtype: "Autocomplete",
					options: [],
					placeholder: __("Seleccione primero un proyecto"),
					reqd: 1,
					onchange: () => {
						const selected = String(dialog.get_value("source") || "").trim();
						setExpenseSubmitEnabled(
							dialog,
							Boolean(selected && dialog.nexoraAvailableSources?.has(selected))
						);
					},
				},
				{
					fieldname: "economic_category",
					label: __("Categoría del gasto"),
					fieldtype: "Link",
					options: "NXR Economic Category",
					reqd: 1,
					get_query: () => ({
						filters: [
							[
								"NXR Economic Category",
								"name",
								"in",
								["CONSTRUCTION_MATERIALS", "CONSTRUCTION_LABOR"],
							],
						],
					}),
				},
				{
					fieldname: "cost_center",
					label: __("Centro de costo"),
					fieldtype: "Link",
					options: "Cost Center",
					reqd: 1,
				},
				{
					fieldname: "beneficiary",
					label: __("Contratista o proveedor"),
					fieldtype: "Link",
					options: "NXR Entity",
					reqd: 1,
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
				},
				{ fieldname: "external_reference", label: __("Referencia de pago"), fieldtype: "Data" },
				{ fieldname: "description", label: __("Concepto"), fieldtype: "Small Text", reqd: 1 },
				{ fieldname: "evidence", label: __("Comprobante"), fieldtype: "Attach" },
			],
			primary_action_label: __("Guardar gasto"),
			primary_action: (values) => void createExpense(values, dialog),
		});
		dialog.show();
		setSourceSelectorState(dialog, {
			description: __("Seleccione primero el proyecto que realizará el gasto."),
		});
		return dialog;
	}

	window.nexora.normalizeDashboardCurrency = normalizeDashboardCurrency;
	window.nexora.loadExpenseSources = loadExpenseSources;
	window.nexora.openIncomeFlow = openIncomeFlow;
	window.nexora.openIncomeDialog = openIncomeFlow;
	window.nexora.openExpenseDialog = openExpenseDialog;

	document.addEventListener(
		"click",
		(event) => {
			if (validateGuidedIncomePeriod(event)) return;
			const advanced = event.target?.closest?.("[data-nexora-income-advanced]");
			if (advanced) {
				event.preventDefault();
				revealAdvancedOperations(advanced.closest(".nxr-operational-shell"));
				return;
			}
			const incomeTarget = event.target?.closest?.(
				'.nxr-quick-income, [data-action="income"], [data-launch-income], [data-nexora-unified-income], .nxr-source-create button'
			);
			if (incomeTarget && !incomeTarget.closest("#page-nexora-operations")) {
				event.preventDefault();
				event.stopPropagation();
				event.stopImmediatePropagation();
				openIncomeFlow();
				return;
			}
			const expenseTarget = event.target?.closest?.(".nxr-quick-expense");
			if (!expenseTarget) return;
			event.preventDefault();
			event.stopImmediatePropagation();
			openExpenseDialog();
		},
		true
	);

	document.addEventListener("nexora:context-changed", (event) => {
		refreshGuidedIncomeContext(event.detail || {});
	});
	document.addEventListener("nexora:data-changed", (event) => {
		if (String(event.detail?.type || "") === "101") clearGuidedIncomeContext();
	});

	if (typeof frappe.ready === "function") frappe.ready(installSharedEnhancements);
	else installSharedEnhancements();
})();
