frappe.pages["nexora-finance"].on_page_load = function (wrapper) {
	const page = frappe.ui.make_app_page({
		parent: wrapper,
		title: __("Núcleo de Fondos"),
		single_column: true,
	});

	const state = {
		preview: null,
		sources: [],
		profiles: new Map(),
		categories: new Map(),
		profile: null,
	};
	const controls = {};
	const addField = (definition) => {
		const control = page.add_field({ ...definition, change: definition.change || invalidatePreview });
		controls[definition.fieldname] = control;
		return control;
	};

	const project = addField({
		label: __("Proyecto"),
		fieldname: "project",
		fieldtype: "Link",
		options: "Project",
		reqd: 1,
		change: () => loadSources(),
	});
	const operationCode = addField({
		fieldname: "operation_code",
		label: __("Tipo oficial de operación"),
		fieldtype: "Link",
		options: "NXR Operation Type",
		reqd: 1,
		change: applySelectedProfile,
	});
	const kernelService = addField({
		fieldname: "kernel_service",
		label: __("Servicio canónico derivado"),
		fieldtype: "Data",
		read_only: 1,
	});
	const economicCategory = addField({
		fieldname: "economic_category",
		label: __("Clasificación económica"),
		fieldtype: "Link",
		options: "NXR Economic Category",
		reqd: 1,
		get_query: () => ({
			filters: [["NXR Economic Category", "name", "in", state.profile?.allowed || []]],
		}),
		change: applyCategoryVisibility,
	});
	const amount = addField({
		label: __("Importe HNL"),
		fieldname: "amount_hnl",
		fieldtype: "Currency",
	});
	const dueDate = addField({
		label: __("Vencimiento"),
		fieldname: "due_date",
		fieldtype: "Date",
	});
	const costCenter = addField({
		label: __("Centro de costo"),
		fieldname: "cost_center",
		fieldtype: "Link",
		options: "Cost Center",
	});
	const secondCostCenter = addField({
		fieldname: "second_cost_center",
		label: __("Segundo centro de costo"),
		fieldtype: "Link",
		options: "Cost Center",
	});
	const secondCostAmount = addField({
		fieldname: "second_cost_amount",
		label: __("Importe segundo centro"),
		fieldtype: "Currency",
	});
	const targetProject = addField({
		fieldname: "target_project",
		label: __("Proyecto destino"),
		fieldtype: "Link",
		options: "Project",
	});
	const destinationSource = addField({
		fieldname: "destination_source",
		label: __("Fuente destino"),
		fieldtype: "Link",
		options: "NXR Fund Source",
	});
	const beneficiaryDoctype = addField({
		fieldname: "beneficiary_doctype",
		label: __("Tipo de beneficiario o responsable"),
		fieldtype: "Link",
		options: "DocType",
	});
	const beneficiary = addField({
		fieldname: "beneficiary",
		label: __("Beneficiario o responsable"),
		fieldtype: "Dynamic Link",
		options: "beneficiary_doctype",
	});
	const referenceName = addField({
		fieldname: "reference_name",
		label: __("Operación original"),
		fieldtype: "Link",
		options: "NXR Operation",
		change: referenceChanged,
	});
	const returnOriginalSource = addField({
		fieldname: "return_original_source",
		label: __("Fuente original relacionada"),
		fieldtype: "Link",
		options: "NXR Fund Source",
	});
	const paymentMethod = addField({
		fieldname: "payment_method",
		label: __("Medio de pago"),
		fieldtype: "Select",
		options: ["Cash", "Deposit", "Transfer", "Other"],
	});
	const externalReference = addField({
		fieldname: "external_reference",
		label: __("Referencia externa"),
		fieldtype: "Data",
	});
	const requester = addField({
		label: __("Solicitante"),
		fieldname: "requester",
		fieldtype: "Link",
		options: "User",
		reqd: 1,
	});
	const approvedBy = addField({
		label: __("Aprobador"),
		fieldname: "approved_by",
		fieldtype: "Link",
		options: "User",
		reqd: 1,
	});
	const commitment = addField({
		label: __("Compromiso"),
		fieldname: "commitment",
		fieldtype: "Link",
		options: "NXR Commitment",
	});
	const evidence = addField({
		label: __("Evidencia"),
		fieldname: "evidence",
		fieldtype: "Attach",
	});

	$(page.body).append(`
    <div class="nxr-finance-grid">
      <section class="nxr-card nxr-source-allocation"><h3>${__(
			"Asignaciones por fuente"
		)}</h3><div class="nxr-source-list"></div></section>
      <section class="nxr-card"><h3>${__(
			"Vista previa antes de ejecutar"
		)}</h3><div class="nxr-preview nxr-empty">${__(
		"Genere una vista previa para continuar."
	)}</div></section>
      <section class="nxr-card nxr-source-create"><h3>${__(
			"Alta rápida de fuente"
		)}</h3><div class="nxr-source-fields"></div></section>
      <section class="nxr-card nxr-ledger"><h3>${__(
			"Libro Central reciente"
		)}</h3><div class="nxr-ledger-list"></div></section>
    </div>
  `);

	buildSourceFields(page.body);
	page.add_button(__("Vista previa"), previewOperation, "primary");
	const executeButton = page.add_button(__("Ejecutar operación"), executeOperation);
	executeButton.prop("disabled", true);

	loadCatalogs();

	function uuid() {
		return (
			globalThis.crypto?.randomUUID?.() || `nxr-${Date.now()}-${Math.random().toString(16).slice(2)}`
		);
	}

	function toggle(control, visible, required = false) {
		control.toggle(Boolean(visible));
		control.df.reqd = Boolean(required);
		control.refresh();
	}

	function invalidatePreview() {
		state.preview = null;
		executeButton.prop("disabled", true);
		$(page.body)
			.find(".nxr-preview")
			.addClass("nxr-empty")
			.text(__("La información cambió; genere otra vista previa."));
	}

	async function loadCatalogs() {
		const response = await frappe.call({
			method: "nexora.financial.service.list_analytic_catalogs",
			type: "POST",
		});
		(response.message?.operation_types || []).forEach((row) => {
			state.profiles.set(row.code, {
				...row,
				allowed: String(row.allowed_categories || "")
					.split("\n")
					.filter(Boolean),
			});
		});
		(response.message?.economic_categories || []).forEach((row) => {
			state.categories.set(row.code, row);
		});
		applySelectedProfile();
	}

	function applySelectedProfile() {
		state.profile = state.profiles.get(operationCode.get_value()) || null;
		kernelService.set_value(state.profile?.kernel_type || "");
		if (state.profile && !state.profile.allowed.includes(economicCategory.get_value())) {
			economicCategory.set_value("");
		}
		const profile = state.profile || {};
		const noFunds = ["Reclassification", "Analytic Adjustment"].includes(profile.kernel_type);
		const documentary = profile.code === "DOCUMENT_SUBSTITUTION";
		toggle(amount, !documentary, !["RECLASSIFICATION", "REVERSAL_NO_CASH"].includes(profile.code));
		toggle(dueDate, profile.requires_due_date, profile.requires_due_date);
		toggle(targetProject, profile.requires_target_project, profile.requires_target_project);
		toggle(destinationSource, profile.requires_destination, profile.requires_destination);
		toggle(beneficiaryDoctype, profile.requires_beneficiary, profile.requires_beneficiary);
		toggle(beneficiary, profile.requires_beneficiary, profile.requires_beneficiary);
		toggle(referenceName, profile.requires_reference, profile.requires_reference);
		toggle(returnOriginalSource, profile.code === "REAL_RETURN");
		toggle(paymentMethod, profile.requires_payment_reference, profile.requires_payment_reference);
		toggle(externalReference, profile.requires_payment_reference, profile.requires_payment_reference);
		toggle(evidence, profile.requires_evidence, profile.requires_evidence);
		toggle(
			commitment,
			["Commitment Execution", "Commitment Release"].includes(profile.kernel_type),
			["Commitment Execution", "Commitment Release"].includes(profile.kernel_type)
		);
		$(page.body)
			.find(".nxr-source-allocation")
			.toggle(!noFunds && !documentary);
		applyCategoryVisibility();
		invalidatePreview();
	}

	function applyCategoryVisibility() {
		const category = state.categories.get(economicCategory.get_value());
		const profile = state.profile || {};
		const derivedCorrection = ["RECLASSIFICATION", "REVERSAL_NO_CASH"].includes(profile.code);
		const needsCostCenter = Boolean(category?.requires_cost_center) || derivedCorrection;
		toggle(costCenter, needsCostCenter, Boolean(category?.requires_cost_center));
		toggle(secondCostCenter, needsCostCenter);
		toggle(secondCostAmount, needsCostCenter);
		invalidatePreview();
	}

	async function referenceChanged() {
		invalidatePreview();
		if (state.profile?.code !== "ADVANCE_SETTLEMENT" || !referenceName.get_value()) return;
		const response = await frappe.call({
			method: "nexora.financial.service.get_advance_status",
			type: "POST",
			args: { operation: referenceName.get_value() },
		});
		const status = response.message;
		frappe.show_alert({
			message: __("Anticipo: entregado L{0}, liquidado L{1}, pendiente L{2}", [
				status.total_disbursed_hnl,
				status.total_settled_hnl,
				status.outstanding_hnl,
			]),
			indicator: "blue",
		});
	}

	function allocations() {
		if (["Reclassification", "Analytic Adjustment"].includes(state.profile?.kernel_type)) return [];
		const rows = $(page.body)
			.find(".nxr-source-amount")
			.toArray()
			.map((input) => ({ source: input.dataset.source, amount_hnl: input.value }))
			.filter((row) => Number(row.amount_hnl) > 0);
		if (state.profile?.code === "REAL_RETURN" && returnOriginalSource.get_value()) {
			rows.forEach((row) => {
				row.related_source = returnOriginalSource.get_value();
			});
		}
		return rows;
	}

	function operationPayload() {
		const secondAmount = Number(secondCostAmount.get_value() || 0);
		const totalAmount = Number(amount.get_value() || 0);
		const splits = [];
		if (costCenter.get_value() && totalAmount > 0) {
			splits.push({
				cost_center: costCenter.get_value(),
				amount_hnl: totalAmount - secondAmount,
			});
		}
		if (secondCostCenter.get_value() && secondAmount > 0) {
			splits.push({
				cost_center: secondCostCenter.get_value(),
				amount_hnl: secondAmount,
			});
		}
		return {
			operation_code: operationCode.get_value(),
			economic_category: economicCategory.get_value(),
			project: project.get_value(),
			target_project: targetProject.get_value(),
			destination_source: destinationSource.get_value(),
			amount_hnl: state.profile?.code === "DOCUMENT_SUBSTITUTION" ? 0 : amount.get_value(),
			cost_center: costCenter.get_value(),
			analytic_splits: splits,
			beneficiary_doctype: beneficiaryDoctype.get_value(),
			beneficiary: beneficiary.get_value(),
			reference_doctype: state.profile?.requires_reference ? "NXR Operation" : "",
			reference_name: referenceName.get_value(),
			payment_method: paymentMethod.get_value(),
			external_reference: externalReference.get_value(),
			operation_date: frappe.datetime.get_today(),
			due_date: dueDate.get_value(),
			requester: requester.get_value(),
			approved_by: approvedBy.get_value(),
			commitment: commitment.get_value(),
			description: __("Operación registrada desde el Libro Central NEXORA"),
			evidence: evidence.get_value(),
			allocations: allocations(),
		};
	}

	async function loadSources() {
		invalidatePreview();
		const value = project.get_value();
		if (!value) return renderSources([]);
		const response = await frappe.call({
			method: "nexora.financial.service.list_source_balances",
			type: "POST",
			args: { project: value },
			freeze: true,
			freeze_message: __("Consultando saldos canónicos…"),
		});
		state.sources = response.message || [];
		renderSources(state.sources);
		await loadLedger();
	}

	function renderSources(rows) {
		const target = $(page.body).find(".nxr-source-list").empty();
		if (!rows.length) {
			target.append(`<p class="text-muted">${__("No hay fuentes activas para este proyecto.")}</p>`);
			return;
		}
		rows.forEach((row) =>
			target.append(`
      <label class="nxr-source-row">
        <span><strong>${frappe.utils.escape_html(row.source)}</strong><br>
        ${__("Saldo")}: L${row.balance_hnl} · ${__("Reservado")}: L${row.reserved_hnl} · ${__(
				"Disponible"
			)}: L${row.available_hnl}</span>
        <input class="form-control nxr-source-amount" type="number" min="0" step="0.01" value="0" data-source="${frappe.utils.escape_html(
			row.source
		)}">
      </label>`)
		);
		target.find("input").on("input", invalidatePreview);
	}

	async function previewOperation() {
		const response = await frappe.call({
			method: "nexora.financial.service.preview_central_operation",
			type: "POST",
			args: { payload: operationPayload() },
			freeze: true,
			freeze_message: __("Recalculando saldos y referencias en servidor…"),
		});
		state.preview = response.message;
		renderPreview(state.preview);
		executeButton.prop("disabled", false);
	}

	function renderPreview(preview) {
		const sourceRows = (preview.sources || [])
			.map(
				(row) => `
      <tr><td>${frappe.utils.escape_html(row.source)}</td><td>L${row.amount_hnl}</td><td>L${
					row.balance_before_hnl
				}</td><td>L${row.balance_after_hnl}</td><td>L${row.reserved_before_hnl}</td><td>L${
					row.reserved_after_hnl
				}</td></tr>`
			)
			.join("");
		const analyticRows = (preview.analytic_effects || [])
			.map(
				(row) =>
					`<tr><td>${frappe.utils.escape_html(row.dimension)}</td><td>${frappe.utils.escape_html(
						row.economic_category || preview.economic_category
					)}</td><td>${frappe.utils.escape_html(row.cost_center || "—")}</td><td>L${
						row.amount_hnl
					}</td></tr>`
			)
			.join("");
		$(page.body).find(".nxr-preview").removeClass("nxr-empty").html(`
      <table class="table table-bordered"><thead><tr><th>${__("Fuente")}</th><th>${__(
			"Importe"
		)}</th><th>${__("Saldo antes")}</th><th>${__("Saldo después")}</th><th>${__(
			"Reservado antes"
		)}</th><th>${__("Reservado después")}</th></tr></thead><tbody>${sourceRows}</tbody></table>
      <table class="table table-bordered"><thead><tr><th>${__("Dimensión")}</th><th>${__(
			"Clasificación"
		)}</th><th>${__("Centro")}</th><th>${__(
			"Efecto"
		)}</th></tr></thead><tbody>${analyticRows}</tbody></table>
      <p><strong>${__("Costo")}:</strong> L${preview.cost_effect_hnl} · <strong>${__(
			"Presupuesto"
		)}:</strong> L${preview.budget_effect_hnl} · <strong>${__("Ahorro")}:</strong> L${
			preview.savings_effect_hnl
		} · <strong>${__("Inversión")}:</strong> L${preview.investment_effect_hnl}</p>
      <p><strong>${__("Saldo referenciado")}:</strong> L${preview.reference_balance_before_hnl} → L${
			preview.reference_balance_after_hnl
		}</p>
      <p><strong>${__("Documento")}:</strong> ${frappe.utils.escape_html(preview.document_to_generate)}</p>`);
	}

	function serviceForProfile() {
		return (
			{
				"Commitment Reserve": "nexora.financial.service.create_commitment",
				"Commitment Execution": "nexora.financial.service.execute_commitment",
				"Commitment Release": "nexora.financial.service.release_commitment",
			}[state.profile?.kernel_type] || "nexora.financial.service.execute_central_operation"
		);
	}

	async function executeOperation() {
		if (!state.preview) return;
		const payload = {
			...operationPayload(),
			idempotency_key: uuid(),
			preview_hash: state.preview.preview_hash,
		};
		const response = await frappe.call({
			method: serviceForProfile(),
			type: "POST",
			args: { payload },
			freeze: true,
			freeze_message: __("Ejecutando operación atómica…"),
		});
		const number = response.message.document_number || response.message.commitment_number;
		frappe.show_alert({ message: __("Documento {0} ejecutado", [number]), indicator: "green" });
		await loadSources();
	}

	async function loadLedger() {
		const response = await frappe.call({
			method: "nexora.financial.service.list_central_operations",
			type: "POST",
			args: { project: project.get_value(), limit: 20 },
		});
		const rows = response.message || [];
		const target = $(page.body).find(".nxr-ledger-list").empty();
		if (!rows.length) return target.text(__("Aún no hay operaciones."));
		rows.forEach((row) =>
			target.append(
				`<div class="nxr-source-row"><strong>${frappe.utils.escape_html(
					row.document_number
				)}</strong> · ${frappe.utils.escape_html(row.operation_code)} · L${row.amount_hnl}</div>`
			)
		);
	}

	function buildSourceFields(body) {
		const parent = $(body).find(".nxr-source-fields");
		const fields = {};
		const definitions = [
			["channel", __("Canal"), "Select", ["Remittance", "Cash", "Deposit", "Transfer", "Other"]],
			["currency", __("Moneda"), "Link", "Currency"],
			["original_amount", __("Importe original"), "Currency"],
			["exchange_rate", __("Tasa a HNL"), "Float"],
			["origin_or_sender", __("Procedencia o remitente"), "Data"],
			["institution", __("Institución"), "Data"],
			["account_reference", __("Cuenta"), "Data"],
			["external_reference", __("Referencia"), "Data"],
		];
		definitions.forEach(([fieldname, label, fieldtype, options]) => {
			fields[fieldname] = frappe.ui.form.make_control({
				parent,
				df: { fieldname, label, fieldtype, options, change: toggleBankFields },
				render_input: true,
			});
		});
		fields.currency.set_value("HNL");
		fields.exchange_rate.set_value(1);
		const add = $(`<button class="btn btn-primary btn-sm">${__("Registrar fuente")}</button>`).appendTo(
			parent
		);
		add.on("click", async () => {
			const sourcePayload = Object.fromEntries(
				Object.entries(fields).map(([name, control]) => [name, control.get_value()])
			);
			Object.assign(sourcePayload, {
				project: project.get_value(),
				custodian: frappe.session.user,
				idempotency_key: uuid(),
			});
			const response = await frappe.call({
				method: "nexora.financial.service.create_fund_source",
				type: "POST",
				args: { payload: sourcePayload },
				freeze: true,
				freeze_message: __("Registrando fuente y efecto de ingreso…"),
			});
			frappe.show_alert({
				message: __("Fuente {0} registrada", [response.message.source_number]),
				indicator: "green",
			});
			await loadSources();
		});
		toggleBankFields();

		function toggleBankFields() {
			const bank = ["Deposit", "Transfer"].includes(fields.channel?.get_value());
			["institution", "account_reference", "external_reference"].forEach((name) =>
				fields[name]?.toggle(bank)
			);
		}
	}
};
