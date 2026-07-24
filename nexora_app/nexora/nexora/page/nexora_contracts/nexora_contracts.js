frappe.pages["nexora-contracts"].on_page_load = function (wrapper) {
	const page = frappe.ui.make_app_page({
		parent: wrapper,
		title: __("Contratistas y Contratos"),
		single_column: true,
	});
	const controls = {};
	const add = (definition) => {
		controls[definition.fieldname] = page.add_field(definition);
		return controls[definition.fieldname];
	};

	add({ fieldname: "project", label: __("Proyecto"), fieldtype: "Link", options: "Project" });
	add({ fieldname: "contractor", label: __("Contratista"), fieldtype: "Link", options: "NXR Entity" });
	add({ fieldname: "status", label: __("Estado"), fieldtype: "Select", options: ["", "Draft", "In Review", "Approved", "Active", "Suspended", "Completed", "In Liquidation", "Liquidated", "Early Terminated", "Cancelled Before Active"] });
	add({ fieldname: "profile", label: __("Perfil de contratista"), fieldtype: "Link", options: "NXR Contractor Profile" });
	add({ fieldname: "modality", label: __("Modalidad"), fieldtype: "Select", options: ["Lump Sum", "Unit Price", "Time and Materials", "Labor Only", "Mixed", "Other"] });
	add({ fieldname: "cost_center", label: __("Centro de costo"), fieldtype: "Link", options: "Cost Center" });
	add({ fieldname: "fund_source", label: __("Fuente principal"), fieldtype: "Link", options: "NXR Fund Source" });
	add({ fieldname: "responsible", label: __("Responsable"), fieldtype: "Link", options: "User" });
	add({ fieldname: "scope", label: __("Alcance"), fieldtype: "Small Text" });
	add({ fieldname: "start_date", label: __("Inicio"), fieldtype: "Date" });
	add({ fieldname: "end_date", label: __("Fin"), fieldtype: "Date" });
	add({ fieldname: "labor_amount", label: __("Mano de obra"), fieldtype: "Currency" });
	add({ fieldname: "material_amount", label: __("Materiales"), fieldtype: "Currency" });
	add({ fieldname: "contract_evidence", label: __("Evidencia del contrato"), fieldtype: "Link", options: "NXR Evidence" });
	add({ fieldname: "signature_evidence", label: __("Evidencia de firma"), fieldtype: "Link", options: "NXR Evidence" });
	add({ fieldname: "approval_evidence", label: __("Evidencia de aprobación"), fieldtype: "Link", options: "NXR Evidence" });

	$(page.body).append(`
		<div class="nxr-finance-grid nxr-contract-grid">
			<section class="nxr-card"><h3>${__("Contratos")}</h3><div class="nxr-contract-results"></div></section>
			<section class="nxr-card"><h3>${__("Expediente contractual")}</h3><div class="nxr-contract-detail nxr-empty">${__("Seleccione un contrato.")}</div></section>
			<section class="nxr-card"><h3>${__("Operaciones")}</h3><div class="nxr-contract-actions"></div></section>
		</div>
	`);
	let selected = null;
	page.add_button(__("Buscar"), refresh, "primary");
	page.add_button(__("Crear perfil"), createProfile);
	page.add_button(__("Crear contrato"), createContract);

	function uuid() {
		return globalThis.crypto?.randomUUID?.() || `nxr-${Date.now()}-${Math.random().toString(16).slice(2)}`;
	}

	async function call(method, args) {
		return (await frappe.call({ method, type: "POST", args, freeze: true })).message;
	}

	function values(dialog) {
		return dialog.get_values() || {};
	}

	function dialogAction(title, fields, primaryLabel, handler) {
		const dialog = new frappe.ui.Dialog({
			title,
			fields,
			primary_action_label: primaryLabel,
			primary_action: async () => {
				try {
					await handler(values(dialog));
					dialog.hide();
					await refresh();
					if (selected) await load(selected);
				} catch (error) {
					console.error(error);
				}
			},
		});
		dialog.show();
	}

	function allocation(source, amount) {
		return source && flt(amount) > 0 ? [{ source, amount_hnl: flt(amount) }] : [];
	}

	async function refresh() {
		const rows = await call("nexora.contracts.service.list_contracts", {
			project: controls.project.get_value(),
			contractor: controls.contractor.get_value(),
			status: controls.status.get_value(),
			limit: 100,
		});
		const target = $(page.body).find(".nxr-contract-results").empty();
		if (!rows.length) {
			target.append(`<p class="nxr-empty">${__("No hay contratos para los filtros indicados.")}</p>`);
			return;
		}
		rows.forEach((row) => {
			const button = $(`<button class="btn btn-default btn-sm nxr-result-row"><strong>${frappe.utils.escape_html(row.document_number)}</strong> · ${frappe.utils.escape_html(row.status)} · ${format_currency(row.current_amount)} · ${__("Pendiente")}: ${format_currency(row.pending_amount)}</button>`);
			button.on("click", () => load(row.name));
			target.append(button);
		});
	}

	function createProfile() {
		dialogAction(__("Crear perfil de contratista"), [
			{ fieldname: "entity", label: __("Entidad"), fieldtype: "Link", options: "NXR Entity", reqd: 1, default: controls.contractor.get_value() },
			{ fieldname: "classification", label: __("Clasificación"), fieldtype: "Select", options: ["Individual", "Company", "Consortium", "Specialist", "Other"], reqd: 1, default: "Company" },
			{ fieldname: "valid_from", label: __("Vigente desde"), fieldtype: "Date", reqd: 1, default: frappe.datetime.get_today() },
			{ fieldname: "valid_until", label: __("Vigente hasta"), fieldtype: "Date" },
			{ fieldname: "compliance_status", label: __("Cumplimiento"), fieldtype: "Select", options: ["Pending", "Valid", "Expired", "Rejected", "Exception Approved"], reqd: 1, default: "Pending" },
			{ fieldname: "evidence", label: __("Evidencia"), fieldtype: "Link", options: "NXR Evidence" },
			{ fieldname: "notes", label: __("Notas"), fieldtype: "Small Text" },
		], __("Crear"), async (data) => {
			const result = await call("nexora.contracts.service.create_contractor_profile", { payload: { ...data, idempotency_key: uuid() } });
			controls.profile.set_value(result.profile);
			if (["Valid", "Exception Approved"].includes(data.compliance_status)) {
				await call("nexora.contracts.service.transition_contractor_profile", { profile: result.profile, status: "Active", idempotency_key: uuid() });
			}
			frappe.show_alert({ message: __("Perfil {0} creado", [result.document_number]), indicator: "green" });
		});
	}

	async function createContract() {
		const labor = flt(controls.labor_amount.get_value());
		const materials = flt(controls.material_amount.get_value());
		const lines = [];
		if (labor > 0) lines.push({ line_code: "LAB-001", description: __("Mano de obra contractual"), cost_kind: "Labor", cost_center: controls.cost_center.get_value(), fund_source: controls.fund_source.get_value(), unit: "Contrato", quantity: 1, unit_rate: labor, amount: labor });
		if (materials > 0) lines.push({ line_code: "MAT-001", description: __("Materiales contractuales"), cost_kind: "Materials", cost_center: controls.cost_center.get_value(), fund_source: controls.fund_source.get_value(), unit: "Contrato", quantity: 1, unit_rate: materials, amount: materials });
		const evidenceRows = [
			["Contract", controls.contract_evidence.get_value()],
			["Signature", controls.signature_evidence.get_value()],
			["Approval", controls.approval_evidence.get_value()],
		].filter((row) => row[1]).map((row) => ({ evidence_type: row[0], evidence: row[1] }));
		const result = await call("nexora.contracts.service.create_contract", { payload: {
			idempotency_key: uuid(), contractor: controls.contractor.get_value(), contractor_profile: controls.profile.get_value(), modality: controls.modality.get_value(), project: controls.project.get_value(), cost_center: controls.cost_center.get_value(), fund_source: controls.fund_source.get_value(), responsible: controls.responsible.get_value(), scope: controls.scope.get_value(), currency: "HNL", exchange_rate: 1, start_date: controls.start_date.get_value(), end_date: controls.end_date.get_value(), signed_on: controls.start_date.get_value(), owner_signatory: frappe.session.user_fullname, contractor_signatory: controls.contractor.get_value(), lines, evidence_rows: evidenceRows,
		} });
		selected = result.contract;
		frappe.show_alert({ message: __("Contrato {0} creado", [result.document_number]), indicator: "green" });
		await load(selected);
		await refresh();
	}

	async function load(name) {
		selected = name;
		const doc = await call("nexora.contracts.service.get_contract", { contract: name });
		$(page.body).find(".nxr-contract-detail").removeClass("nxr-empty").html(`
			<h4>${frappe.utils.escape_html(doc.document_number)} · ${frappe.utils.escape_html(doc.status)}</h4>
			<p>${frappe.utils.escape_html(doc.current_scope || doc.scope || "")}</p>
			<dl><dt>${__("Monto vigente")}</dt><dd>${format_currency(doc.current_amount, doc.currency)}</dd><dt>${__("Ejecutado")}</dt><dd>${format_currency(doc.executed_amount, doc.currency)}</dd><dt>${__("Pendiente")}</dt><dd>${format_currency(doc.pending_amount, doc.currency)}</dd><dt>${__("Pagado")}</dt><dd>${format_currency(doc.paid_amount, doc.currency)}</dd><dt>${__("Anticipo pendiente")}</dt><dd>${format_currency(doc.advance_balance, doc.currency)}</dd><dt>${__("Retención pendiente")}</dt><dd>${format_currency(doc.retention_balance, doc.currency)}</dd></dl>
			<p class="text-muted">${__("Adendas")}: ${doc.amendments.length} · ${__("Estimaciones")}: ${doc.estimates.length} · ${__("Movimientos")}: ${doc.transactions.length}</p>
		`);
		renderActions(doc);
	}

	function actionButton(target, label, handler, primary = false) {
		const button = $(`<button class="btn ${primary ? "btn-primary" : "btn-default"} btn-sm">${label}</button>`);
		button.on("click", handler);
		target.append(button);
	}

	function renderActions(doc) {
		const target = $(page.body).find(".nxr-contract-actions").empty();
		actionButton(target, __("Imprimir contrato"), () => {
			window.open(`/printview?doctype=NXR%20Contract&name=${encodeURIComponent(selected)}&format=NEXORA%20Contract&no_letterhead=0`, "_blank", "noopener");
		});
		const transitions = { Draft: "In Review", "In Review": "Approved", Approved: "Active", Active: "Completed", Completed: "In Liquidation", "In Liquidation": "Liquidated" };
		if (transitions[doc.status]) {
			actionButton(target, __("Mover a {0}", [transitions[doc.status]]), async () => {
				await call("nexora.contracts.service.transition_contract", { contract: selected, status: transitions[doc.status], idempotency_key: uuid() });
				await load(selected);
				await refresh();
			}, true);
		}
		if (["Active", "Suspended"].includes(doc.status)) {
			actionButton(target, __("Crear adenda"), createAmendment);
			actionButton(target, __("Aplicar adenda"), applyAmendment);
		}
		if (doc.status === "Active") {
			actionButton(target, __("Crear estimación"), createEstimate);
			actionButton(target, __("Aprobar estimación"), approveEstimate);
			actionButton(target, __("Entregar anticipo"), disburseAdvance);
			actionButton(target, __("Pagar estimación"), payEstimate);
			actionButton(target, __("Devolver retención"), returnRetention);
			actionButton(target, __("Corregir movimiento"), correctTransaction);
		}
		target.append(`<p class="text-muted">${__("Todas las operaciones se validan nuevamente en servidor y generan numeración, auditoría e idempotencia.")}</p>`);
	}

	function createAmendment() {
		dialogAction(__("Crear adenda"), [
			{ fieldname: "amendment_type", label: __("Tipo"), fieldtype: "Select", options: ["Increase", "Reduction", "Extension", "Scope Change", "Suspension", "Reactivation", "Early Termination", "Other"], reqd: 1 },
			{ fieldname: "effective_date", label: __("Fecha efectiva"), fieldtype: "Date", reqd: 1, default: frappe.datetime.get_today() },
			{ fieldname: "labor_delta", label: __("Variación mano de obra"), fieldtype: "Currency", default: 0 },
			{ fieldname: "material_delta", label: __("Variación materiales"), fieldtype: "Currency", default: 0 },
			{ fieldname: "new_end_date", label: __("Nueva fecha final"), fieldtype: "Date" },
			{ fieldname: "scope_change", label: __("Nuevo alcance"), fieldtype: "Small Text" },
			{ fieldname: "reason", label: __("Motivo"), fieldtype: "Small Text", reqd: 1 },
			{ fieldname: "evidence", label: __("Evidencia validada"), fieldtype: "Link", options: "NXR Evidence", reqd: 1 },
		], __("Crear"), async (data) => {
			const result = await call("nexora.contracts.service.create_contract_amendment", { payload: { ...data, contract: selected, idempotency_key: uuid() } });
			frappe.show_alert({ message: __("Adenda {0} creada", [result.document_number]), indicator: "green" });
		});
	}

	function applyAmendment() {
		dialogAction(__("Aprobar y aplicar adenda"), [
			{ fieldname: "amendment", label: __("Adenda"), fieldtype: "Link", options: "NXR Contract Amendment", reqd: 1, get_query: () => ({ filters: { contract: selected } }) },
		], __("Aplicar"), async (data) => {
			for (const status of ["In Review", "Approved", "Active"]) {
				await call("nexora.contracts.service.transition_contract_amendment", { amendment: data.amendment, status, idempotency_key: uuid() });
			}
		});
	}

	function createEstimate() {
		dialogAction(__("Crear estimación"), [
			{ fieldname: "contract_line", label: __("Código de línea contractual"), fieldtype: "Data", reqd: 1 },
			{ fieldname: "cost_kind", label: __("Tipo de costo"), fieldtype: "Select", options: ["Labor", "Materials"], reqd: 1 },
			{ fieldname: "period_start", label: __("Inicio del período"), fieldtype: "Date", reqd: 1 },
			{ fieldname: "period_end", label: __("Fin del período"), fieldtype: "Date", reqd: 1 },
			{ fieldname: "gross_amount", label: __("Importe bruto"), fieldtype: "Currency", reqd: 1 },
			{ fieldname: "advance_amortization", label: __("Amortización"), fieldtype: "Currency", default: 0 },
			{ fieldname: "retention_amount", label: __("Retención"), fieldtype: "Currency", default: 0 },
			{ fieldname: "fine_amount", label: __("Multa"), fieldtype: "Currency", default: 0 },
			{ fieldname: "deduction_amount", label: __("Deducción"), fieldtype: "Currency", default: 0 },
			{ fieldname: "evidence", label: __("Evidencia validada"), fieldtype: "Link", options: "NXR Evidence", reqd: 1 },
			{ fieldname: "requester", label: __("Solicitante"), fieldtype: "Link", options: "User", reqd: 1, default: frappe.session.user },
		], __("Crear"), async (data) => {
			const result = await call("nexora.contracts.service.create_contract_estimate", { payload: { ...data, contract: selected, lines: [{ contract_line: data.contract_line, description: __("Avance contractual"), cost_kind: data.cost_kind, quantity: 1, amount: data.gross_amount }], idempotency_key: uuid() } });
			frappe.show_alert({ message: __("Estimación {0} creada", [result.document_number]), indicator: "green" });
		});
	}

	function approveEstimate() {
		dialogAction(__("Aprobar estimación"), [
			{ fieldname: "estimate", label: __("Estimación"), fieldtype: "Link", options: "NXR Contract Estimate", reqd: 1, get_query: () => ({ filters: { contract: selected, status: "Draft" } }) },
		], __("Aprobar"), async (data) => {
			await call("nexora.contracts.service.transition_contract_estimate", { estimate: data.estimate, status: "Pending Approval", idempotency_key: uuid() });
			await call("nexora.contracts.service.transition_contract_estimate", { estimate: data.estimate, status: "Approved", idempotency_key: uuid() });
		});
	}

	function paymentFields(includeEstimate = false) {
		const fields = [];
		if (includeEstimate) fields.push({ fieldname: "estimate", label: __("Estimación aprobada"), fieldtype: "Link", options: "NXR Contract Estimate", reqd: 1, get_query: () => ({ filters: { contract: selected, status: "Approved" } }) });
		fields.push(
			{ fieldname: "amount", label: __("Importe / asignación"), fieldtype: "Currency", reqd: 1 },
			{ fieldname: "source", label: __("Fuente"), fieldtype: "Link", options: "NXR Fund Source", reqd: 1 },
			{ fieldname: "evidence", label: __("Evidencia validada"), fieldtype: "Link", options: "NXR Evidence", reqd: 1 },
			{ fieldname: "requester", label: __("Solicitante"), fieldtype: "Link", options: "User", reqd: 1 },
			{ fieldname: "approved_by", label: __("Aprobado por"), fieldtype: "Link", options: "User", reqd: 1 },
			{ fieldname: "payment_method", label: __("Medio de pago"), fieldtype: "Select", options: ["Cash", "Transfer", "Cheque", "Other"], reqd: 1 },
			{ fieldname: "external_reference", label: __("Referencia externa"), fieldtype: "Data" },
		);
		return fields;
	}

	function disburseAdvance() {
		dialogAction(__("Entregar anticipo"), [
			...paymentFields(),
			{ fieldname: "due_date", label: __("Vencimiento"), fieldtype: "Date", reqd: 1 },
		], __("Entregar"), async (data) => {
			await call("nexora.contracts.service.disburse_contract_advance", { payload: { ...data, contract: selected, allocations: allocation(data.source, data.amount), operation_date: frappe.datetime.get_today(), idempotency_key: uuid() } });
		});
	}

	function payEstimate() {
		dialogAction(__("Pagar estimación"), [
			...paymentFields(true),
			{ fieldname: "advance_operation", label: __("Operación de anticipo para amortizar"), fieldtype: "Link", options: "NXR Operation" },
		], __("Pagar"), async (data) => {
			await call("nexora.contracts.service.execute_contract_estimate_payment", { payload: { ...data, allocations: allocation(data.source, data.amount), operation_date: frappe.datetime.get_today(), idempotency_key: uuid() } });
		});
	}

	function returnRetention() {
		dialogAction(__("Devolver retención"), paymentFields(), __("Devolver"), async (data) => {
			await call("nexora.contracts.service.return_contract_retention", { payload: { ...data, contract: selected, allocations: allocation(data.source, data.amount), operation_date: frappe.datetime.get_today(), idempotency_key: uuid() } });
		});
	}

	function correctTransaction() {
		dialogAction(__("Corregir movimiento contractual"), [
			{ fieldname: "transaction", label: __("Movimiento original"), fieldtype: "Link", options: "NXR Contract Transaction", reqd: 1, get_query: () => ({ filters: { contract: selected, status: "Executed" } }) },
			{ fieldname: "correction_operation", label: __("Corrección"), fieldtype: "Select", options: ["REAL_RETURN", "REVERSAL_NO_CASH", "DOCUMENT_SUBSTITUTION"], reqd: 1 },
			{ fieldname: "amount", label: __("Importe de devolución real"), fieldtype: "Currency", default: 0 },
			{ fieldname: "source", label: __("Fuente de devolución"), fieldtype: "Link", options: "NXR Fund Source" },
			{ fieldname: "evidence", label: __("Evidencia validada"), fieldtype: "Link", options: "NXR Evidence" },
			{ fieldname: "requester", label: __("Solicitante"), fieldtype: "Link", options: "User", reqd: 1 },
			{ fieldname: "approved_by", label: __("Aprobado por"), fieldtype: "Link", options: "User", reqd: 1 },
			{ fieldname: "payment_method", label: __("Medio"), fieldtype: "Select", options: ["Cash", "Transfer", "Cheque", "Other"] },
			{ fieldname: "external_reference", label: __("Referencia externa"), fieldtype: "Data" },
			{ fieldname: "reason", label: __("Motivo"), fieldtype: "Small Text", reqd: 1 },
		], __("Corregir"), async (data) => {
			await call("nexora.contracts.service.correct_contract_transaction", { payload: { ...data, allocations: allocation(data.source, data.amount), operation_date: frappe.datetime.get_today(), idempotency_key: uuid() } });
		});
	}

	refresh();
};
