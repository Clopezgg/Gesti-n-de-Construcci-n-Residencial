function readOperationalLaunchContext() {
	const query = new URLSearchParams(window.location.search);
	const context = {
		movement_code: frappe.route_options?.movement_code || query.get("movement_code") || null,
		project: frappe.route_options?.project || query.get("project") || null,
		show_ledger: frappe.route_options?.show_ledger || query.get("show_ledger") || null,
	};
	frappe.route_options = null;
	return context;
}

frappe.pages["nexora-operations"].on_page_load = function (wrapper) {
	const page = frappe.ui.make_app_page({
		parent: wrapper,
		title: __("Operación diaria"),
		single_column: true,
	});
	const body = $(page.body);
	const state = {
		movements: new Map(),
		movement: null,
		preview: null,
		accounts: new Map(),
		sources: [],
		launch: readOperationalLaunchContext(),
	};
	const controls = {};

	body.html(`
		<main class="nxr-product-shell nxr-operational-shell" data-state="loading">
			<section class="nxr-operational-header nxr-card">
				<div>
					<p class="nxr-eyebrow">NX10 · ${__("OPERACIÓN DIARIA")}</p>
					<h2 class="nxr-operational-title">${__("Seleccione un código de movimiento")}</h2>
					<p class="text-muted">${__(
						"La fecha del documento define el período financiero; la fecha real de registro permanece en la auditoría."
					)}</p>
				</div>
				<div class="nxr-movement-help" aria-label="${__("Códigos disponibles")}"></div>
			</section>
			<section class="nxr-operational-form nxr-card">
				<div class="nxr-operational-fields"></div>
				<div class="nxr-account-hint" role="status"></div>
				<div class="nxr-allocation-panel">
					<header><strong>${__("Fuentes que pagarán")}</strong><span>${__("Distribuya el importe entre fondos disponibles")}</span></header>
					<div class="nxr-operational-sources"></div>
				</div>
				<div class="nxr-operational-actions">
					<button type="button" class="btn btn-default nxr-preview-movement">${__("Vista previa")}</button>
					<button type="button" class="btn btn-primary nxr-execute-movement" disabled>${__("Contabilizar")}</button>
				</div>
			</section>
			<section class="nxr-operational-preview nxr-card">
				<header><strong>${__("Vista previa verificable")}</strong><span>${__("Sin guardar hasta pulsar Contabilizar")}</span></header>
				<div class="nxr-preview-body nxr-empty">${__("Complete los datos y genere una vista previa.")}</div>
			</section>
			<section class="nxr-operational-ledger nxr-card">
				<header><div><strong>${__("Libro Central operativo")}</strong><span>${__("Fecha documental y auditoría cronológica")}</span></div><button type="button" class="btn btn-xs btn-default nxr-refresh-ledger">${__("Actualizar")}</button></header>
				<div class="nxr-operational-ledger-body"></div>
			</section>
		</main>
	`);

	const fieldDefinitions = [
		{ fieldname: "movement_code", label: __("Código de movimiento"), fieldtype: "Data", reqd: 1 },
		{ fieldname: "document_date", label: __("Fecha del documento"), fieldtype: "Date", reqd: 1 },
		{ fieldname: "project", label: __("Proyecto"), fieldtype: "Link", options: "Project", reqd: 1 },
		{ fieldname: "financial_account", label: __("Cuenta frecuente"), fieldtype: "Autocomplete" },
		{ fieldname: "save_financial_account", label: __("Guardar como cuenta frecuente"), fieldtype: "Check" },
		{ fieldname: "account_name", label: __("Nombre de la cuenta frecuente"), fieldtype: "Data" },
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
		},
		{ fieldname: "currency", label: __("Moneda"), fieldtype: "Link", options: "Currency" },
		{ fieldname: "original_amount", label: __("Importe original"), fieldtype: "Currency" },
		{ fieldname: "exchange_rate", label: __("Tasa a HNL"), fieldtype: "Float" },
		{ fieldname: "origin_or_sender", label: __("Remitente u origen"), fieldtype: "Data" },
		{ fieldname: "institution", label: __("Banco o remesadora"), fieldtype: "Data" },
		{ fieldname: "account_reference", label: __("Cuenta destino"), fieldtype: "Data" },
		{ fieldname: "external_reference", label: __("Número de referencia"), fieldtype: "Data" },
		{
			fieldname: "economic_category",
			label: __("Categoría económica"),
			fieldtype: "Link",
			options: "NXR Economic Category",
		},
		{ fieldname: "amount_hnl", label: __("Importe HNL"), fieldtype: "Currency" },
		{ fieldname: "cost_center", label: __("Centro de costo"), fieldtype: "Link", options: "Cost Center" },
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
		},
		{
			fieldname: "reference_name",
			label: __("Documento original"),
			fieldtype: "Link",
			options: "NXR Operation",
			get_query: () => ({
				filters: { project: controls.project?.get_value() || "", status: "Executed" },
			}),
		},
		{ fieldname: "description", label: __("Concepto o motivo"), fieldtype: "Small Text" },
		{ fieldname: "evidence", label: __("Comprobante"), fieldtype: "Attach" },
		{ fieldname: "requester", label: __("Solicitante"), fieldtype: "Link", options: "User" },
		{ fieldname: "approved_by", label: __("Aprobador"), fieldtype: "Link", options: "User" },
	];

	const fieldsTarget = body.find(".nxr-operational-fields");
	for (const definition of fieldDefinitions) {
		const slot = $(`<div class="nxr-operational-field" data-field="${definition.fieldname}"></div>`).appendTo(
			fieldsTarget
		);
		const control = frappe.ui.form.make_control({
			parent: slot,
			df: {
				...definition,
				change: () => void fieldChanged(definition.fieldname),
			},
			render_input: true,
		});
		controls[definition.fieldname] = control;
	}

	controls.document_date.set_value(frappe.datetime.get_today());
	controls.channel.set_value("Remittance");
	controls.currency.set_value("HNL");
	controls.exchange_rate.set_value(1);
	controls.payment_method.set_value("Transfer");

	controls.movement_code.$input.on("keydown", (event) => {
		if (event.key === "Enter") {
			event.preventDefault();
			applyMovement();
		}
	});
	body.on("click", ".nxr-movement-chip", function () {
		controls.movement_code.set_value($(this).data("code"));
		applyMovement();
	});
	body.on("click", ".nxr-preview-movement", () => void previewMovement());
	body.on("click", ".nxr-execute-movement", () => void executeMovement());
	body.on("click", ".nxr-refresh-ledger", () => void loadLedger());
	body.on("input", ".nxr-source-amount", invalidatePreview);

	wrapper.nexora_apply_operational_context = async () => {
		const launch = readOperationalLaunchContext();
		if (!launch.project && !launch.movement_code && !launch.show_ledger) return;
		if (launch.project) await controls.project.set_value(launch.project);
		if (launch.movement_code) await controls.movement_code.set_value(launch.movement_code);
		applyMovement();
		if (launch.show_ledger) body.find(".nxr-operational-ledger")[0]?.scrollIntoView({ block: "start" });
	};

	initialize();

	async function initialize() {
		const response = await frappe.call({
			method: "nexora.financial.service.movement_catalog",
			type: "POST",
		});
		for (const row of response.message || []) state.movements.set(row.code, row);
		body.find(".nxr-movement-help").html(
			[...state.movements.values()]
				.map(
					(row) =>
						`<button type="button" class="nxr-movement-chip" data-code="${escape(row.code)}"><b>${escape(
							row.code
						)}</b><span>${escape(row.label)}</span></button>`
				)
				.join("")
		);
		if (state.launch.project) await controls.project.set_value(state.launch.project);
		await controls.movement_code.set_value(state.launch.movement_code || "101");
		applyMovement();
		await loadProjectData();
		body.find(".nxr-operational-shell").attr("data-state", "ready");
		if (state.launch.show_ledger) body.find(".nxr-operational-ledger")[0]?.scrollIntoView({ block: "start" });
	}

	async function fieldChanged(fieldname) {
		invalidatePreview();
		if (fieldname === "movement_code") applyMovement();
		if (fieldname === "project") await loadProjectData();
		if (fieldname === "financial_account") await applyFinancialAccount();
		if (fieldname === "save_financial_account") applyAccountSaveVisibility();
		if (fieldname === "channel") applyBankVisibility();
	}

	function toggle(name, visible, required = false) {
		const control = controls[name];
		control.toggle(Boolean(visible));
		control.df.reqd = Boolean(required);
		control.refresh();
	}

	function applyMovement() {
		const code = String(controls.movement_code.get_value() || "").trim();
		state.movement = state.movements.get(code) || null;
		body.find(".nxr-operational-title").text(
			state.movement ? `${code} · ${state.movement.label}` : __("Código de movimiento no reconocido")
		);
		body.find(".nxr-movement-chip").attr("aria-pressed", "false");
		body.find(`.nxr-movement-chip[data-code="${code}"]`).attr("aria-pressed", "true");
		const income = code === "101";
		const expense = code === "102";
		const correction = ["303", "304", "501"].includes(code);
		for (const name of [
			"financial_account",
			"save_financial_account",
			"account_name",
			"channel",
			"currency",
			"original_amount",
			"exchange_rate",
			"origin_or_sender",
			"institution",
			"account_reference",
		]) {
			toggle(name, income, ["channel", "currency", "original_amount", "exchange_rate", "origin_or_sender"].includes(name));
		}
		toggle("economic_category", expense, expense);
		toggle("amount_hnl", expense, expense);
		toggle("cost_center", expense, false);
		toggle("beneficiary", expense, expense);
		toggle("payment_method", expense, expense);
		toggle("external_reference", income || expense, ["Deposit", "Transfer"].includes(controls.channel.get_value()));
		toggle("reference_name", correction, correction);
		toggle("description", expense || correction, expense || correction);
		toggle("evidence", expense || correction, code === "304");
		toggle("requester", expense || correction, correction);
		toggle("approved_by", expense || correction, correction);
		body.find(".nxr-allocation-panel").toggle(expense);
		body.find(".nxr-preview-movement").prop("disabled", !state.movement);
		applyAccountSaveVisibility();
		applyBankVisibility();
		invalidatePreview();
	}

	function applyAccountSaveVisibility() {
		const visible = state.movement?.code === "101" && Boolean(controls.save_financial_account.get_value());
		toggle("account_name", visible, visible);
	}

	function applyBankVisibility() {
		if (state.movement?.code !== "101") return;
		const channel = controls.channel.get_value();
		const bank = ["Remittance", "Deposit", "Transfer"].includes(channel);
		toggle("institution", bank, bank);
		toggle("account_reference", bank, bank);
		toggle("external_reference", channel !== "Cash", ["Remittance", "Deposit", "Transfer"].includes(channel));
	}

	async function loadProjectData() {
		state.preview = null;
		body.find(".nxr-execute-movement").prop("disabled", true);
		const project = controls.project.get_value();
		if (!project) {
			state.accounts.clear();
			state.sources = [];
			controls.financial_account.set_data([]);
			renderSources([]);
			await loadLedger();
			return;
		}
		const [accountsResponse, sourcesResponse] = await Promise.all([
			frappe.call({
				method: "nexora.financial.service.list_financial_accounts",
				type: "POST",
				args: { project },
			}),
			frappe.call({
				method: "nexora.financial.service.list_source_balances",
				type: "POST",
				args: { project },
			}),
		]);
		state.accounts.clear();
		const accountOptions = (accountsResponse.message || []).map((row) => {
			state.accounts.set(row.name, row);
			return { label: row.label, value: row.name };
		});
		controls.financial_account.set_data(accountOptions);
		state.sources = sourcesResponse.message || [];
		renderSources(state.sources);
		body.find(".nxr-account-hint").text(
			accountOptions.length
				? __("Seleccione una cuenta frecuente para rellenar remitente, banco, cuenta, moneda y canal.")
				: __("Todavía no hay cuentas frecuentes. Puede guardar la combinación de este ingreso.")
		);
		await loadLedger();
	}

	async function applyFinancialAccount() {
		const name = controls.financial_account.get_value();
		if (!name) return;
		const response = await frappe.call({
			method: "nexora.financial.service.get_financial_account",
			type: "POST",
			args: { account: name, project: controls.project.get_value() },
		});
		const row = response.message || {};
		for (const [field, value] of Object.entries({
			origin_or_sender: row.origin_or_sender,
			institution: row.institution,
			account_reference: row.account_reference,
			currency: row.currency,
			channel: row.default_channel,
		})) {
			await controls[field].set_value(value || "");
		}
		controls.save_financial_account.set_value(0);
		body.find(".nxr-account-hint").text(
			__("Cuenta aplicada: {0} · {1} · {2}", [
				row.account_name || name,
				row.institution || __("Sin institución"),
				row.masked_account_reference || __("Sin cuenta"),
			])
		);
		applyBankVisibility();
	}

	function renderSources(rows) {
		const target = body.find(".nxr-operational-sources").empty();
		const available = rows.filter((row) => Number(row.available_hnl) > 0);
		if (!available.length) {
			target.html(`<p class="nxr-empty">${__("El proyecto no tiene fondos disponibles.")}</p>`);
			return;
		}
		for (const row of available) {
			target.append(`
				<label class="nxr-operational-source">
					<span><strong>${escape(row.source)}</strong><small>${__("Disponible")}: ${money(
						row.available_hnl
					)}</small></span>
					<input class="form-control nxr-source-amount" type="number" min="0" step="0.01" value="0" data-source="${escape(
						row.source
					)}">
				</label>
			`);
		}
	}

	function allocations() {
		return body
			.find(".nxr-source-amount")
			.toArray()
			.map((input) => ({ source: input.dataset.source, amount_hnl: input.value }))
			.filter((row) => Number(row.amount_hnl) > 0);
	}

	function payload() {
		return {
			movement_code: String(controls.movement_code.get_value() || "").trim(),
			document_date: controls.document_date.get_value(),
			project: controls.project.get_value(),
			financial_account: controls.financial_account.get_value(),
			save_financial_account: controls.save_financial_account.get_value(),
			account_name: controls.account_name.get_value(),
			channel: controls.channel.get_value(),
			currency: controls.currency.get_value(),
			original_amount: controls.original_amount.get_value(),
			exchange_rate: controls.exchange_rate.get_value(),
			origin_or_sender: controls.origin_or_sender.get_value(),
			institution: controls.institution.get_value(),
			account_reference: controls.account_reference.get_value(),
			external_reference: controls.external_reference.get_value(),
			economic_category: controls.economic_category.get_value(),
			amount_hnl: controls.amount_hnl.get_value(),
			cost_center: controls.cost_center.get_value(),
			analytic_splits:
				controls.cost_center.get_value() && Number(controls.amount_hnl.get_value()) > 0
					? [
							{
								cost_center: controls.cost_center.get_value(),
								amount_hnl: controls.amount_hnl.get_value(),
							},
						]
					: [],
			beneficiary_doctype: controls.beneficiary.get_value() ? "NXR Entity" : "",
			beneficiary: controls.beneficiary.get_value(),
			payment_method: controls.payment_method.get_value(),
			reference_name: controls.reference_name.get_value(),
			description: controls.description.get_value(),
			reason: controls.description.get_value(),
			evidence: controls.evidence.get_value(),
			requester: controls.requester.get_value(),
			approved_by: controls.approved_by.get_value(),
			allocations: allocations(),
		};
	}

	async function previewMovement() {
		const response = await frappe.call({
			method: "nexora.financial.service.preview_operational_movement",
			type: "POST",
			args: { payload: payload() },
			freeze: true,
			freeze_message: __("Validando fecha, permisos, saldos y referencias…"),
		});
		state.preview = response.message;
		renderPreview(state.preview);
		body.find(".nxr-execute-movement").prop("disabled", false);
	}

	function renderPreview(preview) {
		const sourceRows = (preview.sources || [])
			.map(
				(row) =>
					`<tr><td>${escape(row.source)}</td><td>${money(row.amount_hnl)}</td><td>${money(
						row.balance_before_hnl
					)}</td><td>${money(row.balance_after_hnl)}</td></tr>`
			)
			.join("");
		body.find(".nxr-preview-body").removeClass("nxr-empty").html(`
			<div class="nxr-preview-summary">
				<span><small>${__("Movimiento")}</small><strong>${escape(preview.movement_code)} · ${escape(
					preview.movement_label
				)}</strong></span>
				<span><small>${__("Fecha documento")}</small><strong>${date(preview.document_date)}</strong></span>
				<span><small>${__("Importe")}</small><strong>${money(preview.amount_hnl)}</strong></span>
				<span><small>${__("Documento")}</small><strong>${escape(preview.document_to_generate || __("Operación NEXORA"))}</strong></span>
			</div>
			${
				sourceRows
					? `<div class="table-responsive"><table class="table table-bordered"><thead><tr><th>${__(
							"Fuente"
						)}</th><th>${__("Importe")}</th><th>${__("Saldo anterior")}</th><th>${__(
							"Saldo posterior"
						)}</th></tr></thead><tbody>${sourceRows}</tbody></table></div>`
					: ""
			}
		`);
	}

	async function executeMovement() {
		if (!state.preview) return;
		const data = {
			...payload(),
			idempotency_key: uuid(),
			preview_hash: state.preview.preview_hash,
		};
		const response = await frappe.call({
			method: "nexora.financial.service.execute_operational_movement",
			type: "POST",
			args: { payload: data },
			freeze: true,
			freeze_message: __("Contabilizando operación y preservando auditoría…"),
		});
		frappe.show_alert({
			message: __("Documento {0} contabilizado", [response.message.document_number || ""]),
			indicator: "green",
		});
		document.dispatchEvent(
			new CustomEvent("nexora:data-changed", { detail: { area: "finance", type: data.movement_code } })
		);
		invalidatePreview();
		await loadProjectData();
	}

	function invalidatePreview() {
		state.preview = null;
		body.find(".nxr-execute-movement").prop("disabled", true);
		body
			.find(".nxr-preview-body")
			.addClass("nxr-empty")
			.text(__("La información cambió. Genere una nueva vista previa."));
	}

	async function loadLedger() {
		const response = await frappe.call({
			method: "nexora.financial.service.list_operational_ledger",
			type: "POST",
			args: { project: controls.project.get_value() || null, limit: 100 },
		});
		renderLedger(response.message || []);
	}

	function renderLedger(rows) {
		const target = body.find(".nxr-operational-ledger-body");
		if (!rows.length) {
			target.html(`<p class="nxr-empty">${__("No hay operaciones para mostrar.")}</p>`);
			return;
		}
		target.html(`
			<div class="table-responsive">
				<table class="table nxr-ledger-table">
					<thead><tr>
						<th>${__("Día")}</th><th>${__("Fecha documento")}</th><th>${__("Documento")}</th>
						<th>${__("Mov.")}</th><th>${__("Movimiento")}</th><th>${__("Remitente / beneficiario")}</th>
						<th>${__("Institución")}</th><th>${__("Cuenta")}</th><th>${__("Moneda")}</th>
						<th class="text-right">${__("Importe")}</th><th>${__("Estado")}</th>
					</tr></thead>
					<tbody>${rows.map(ledgerRow).join("")}</tbody>
				</table>
			</div>
		`);
	}

	function ledgerRow(row) {
		const decorated = row.struck ? `<s>${money(row.amount_hnl)}</s>` : money(row.amount_hnl);
		return `<tr data-tone="${escape(row.tone)}" data-movement="${escape(row.movement_code)}">
			<td>${escape(row.day)}</td><td>${date(row.document_date)}</td>
			<td><a href="${frappe.utils.get_form_link("NXR Operation", row.name)}">${escape(
				row.document_number || row.name
			)}</a></td>
			<td><b>${escape(row.movement_code)}</b></td><td>${escape(row.movement_label)}</td>
			<td>${escape(row.counterparty)}</td><td>${escape(row.institution)}</td><td>${escape(row.account)}</td>
			<td>${escape(row.currency)}</td><td class="text-right"><span data-tone="${escape(
				row.tone
			)}">${decorated}</span></td><td>${escape(row.status)}</td>
		</tr>`;
	}

	function uuid() {
		return globalThis.crypto?.randomUUID?.() || `nxr-${Date.now()}-${Math.random().toString(16).slice(2)}`;
	}
	function money(value) {
		return new Intl.NumberFormat("es-HN", {
			style: "currency",
			currency: "HNL",
			minimumFractionDigits: 2,
		}).format(Number(value || 0));
	}
	function date(value) {
		return value ? frappe.datetime.str_to_user(String(value).slice(0, 10)) : __("Sin fecha");
	}
	function escape(value) {
		return frappe.utils.escape_html(String(value ?? ""));
	}
};

frappe.pages["nexora-operations"].on_page_show = function (wrapper) {
	void wrapper.nexora_apply_operational_context?.();
};
