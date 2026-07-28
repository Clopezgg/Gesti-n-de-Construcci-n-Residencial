frappe.provide("nexora");

(() => {
	const escapedCurrencyMarkup = /^\s*<div\b[^>]*>\s*([^<]+?)\s*<\/div>\s*$/i;

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

	function installDashboardCurrencyGuard() {
		const normalize = () => normalizeDashboardCurrency(document);
		const observer = new MutationObserver((mutations) => {
			if (
				!mutations.some(
					(mutation) => mutation.type === "characterData" || mutation.addedNodes.length > 0
				)
			) {
				return;
			}
			if (!document.querySelector("#page-nexora-dashboard")) return;
			normalize();
		});
		observer.observe(document.documentElement, {
			subtree: true,
			childList: true,
			characterData: true,
		});
		frappe.router?.on?.("change", () => window.requestAnimationFrame(normalize));
		normalize();
	}

	function uuid() {
		return (
			globalThis.crypto?.randomUUID?.() || `nxr-${Date.now()}-${Math.random().toString(16).slice(2)}`
		);
	}

	function money(value) {
		return new Intl.NumberFormat("es-HN", {
			style: "currency",
			currency: "HNL",
			minimumFractionDigits: 2,
		}).format(Number(value || 0));
	}

	function refreshCurrentProductView() {
		const route = frappe.get_route?.() || [];
		if (route[0] === "nexora-dashboard") {
			frappe.set_route("nexora-dashboard", { refresh: Date.now() });
			return;
		}
		frappe.show_alert({ message: __("Los saldos ya fueron actualizados."), indicator: "green" });
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
	window.nexora.openExpenseDialog = openExpenseDialog;
	if (typeof frappe.ready === "function") frappe.ready(installDashboardCurrencyGuard);
	else installDashboardCurrencyGuard();
	document.addEventListener(
		"click",
		(event) => {
			const target = event.target?.closest?.(".nxr-quick-expense");
			if (!target) return;
			event.preventDefault();
			event.stopImmediatePropagation();
			openExpenseDialog();
		},
		true
	);
})();
