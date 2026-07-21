(() => {
	"use strict";

	const API = {
		status: "erpnext.construcontrol.admin_corrections.get_security_status",
		authorize: "erpnext.construcontrol.admin_corrections.authorize_correction",
		expensePreview: "erpnext.construcontrol.admin_corrections.preview_expense_correction",
		expenseExecute: "erpnext.construcontrol.admin_expense_operations.execute_expense_correction",
		batchPreview: "erpnext.construcontrol.admin_expense_operations.preview_expense_batch",
		batchExecute: "erpnext.construcontrol.admin_expense_operations.execute_expense_batch",
		supplierPreview: "erpnext.construcontrol.admin_supplier_corrections.preview_supplier_consolidation",
		supplierExecute: "erpnext.construcontrol.admin_supplier_corrections.execute_supplier_consolidation",
		recordPreview: "erpnext.construcontrol.admin_record_corrections.preview_record_correction",
		recordExecute: "erpnext.construcontrol.admin_record_corrections.execute_record_correction",
		payablePreview: "erpnext.construcontrol.admin_record_corrections.preview_payable_rebuild",
		payableExecute: "erpnext.construcontrol.admin_record_corrections.execute_payable_rebuild",
		userPreview: "erpnext.construcontrol.admin_user_corrections.preview_user_correction",
		userExecute: "erpnext.construcontrol.admin_user_corrections.execute_user_correction",
	};
	let authorization = null;
	let security = null;
	let root = null;
	const escape = (value) => frappe.utils.escape_html(String(value ?? ""));
	const money = (value) => format_currency(Number(value || 0), "HNL");
	const tokenValid = () =>
		Boolean(
			authorization?.token &&
				authorization?.expires_at &&
				new Date(authorization.expires_at).getTime() > Date.now()
		);
	const authArgs = () => ({ authorization_token: authorization.token });
	const privateAttach = (fieldname = "evidence") => ({
		fieldname,
		fieldtype: "Attach",
		label: "Evidencia privada",
		is_private: 1,
	});
	const reasonField = () => ({
		fieldname: "reason",
		fieldtype: "Small Text",
		label: "Motivo detallado (obligatorio)",
		reqd: 1,
	});
	const lines = (value) =>
		String(value || "")
			.split(/\r?\n/)
			.map((item) => item.trim())
			.filter(Boolean);

	function updateState() {
		if (!root) return;
		if (!tokenValid()) authorization = null;
		const badge = root.find("#cc-admin-auth-state");
		if (authorization) {
			badge.addClass("is-open").text(`Autorizado · ${authorization.authorization_id}`);
			root.find("#cc-admin-authorize").text("Renovar autorización");
		} else {
			badge.removeClass("is-open").text("Bloqueado");
			root.find("#cc-admin-authorize").text("Autorizar por 10 minutos");
		}
	}

	function loadStatus() {
		return frappe.xcall(API.status).then((result) => {
			security = result || {};
			root.find("#cc-admin-authorize").prop(
				"disabled",
				!security.configured || !security.enabled || security.locked
			);
			if (!security.configured)
				root.find("#cc-admin-auth-state").text("Configure la clave en Mi perfil");
			else if (security.locked) root.find("#cc-admin-auth-state").text("Bloqueado temporalmente");
		});
	}

	function authorize(callback) {
		if (tokenValid()) {
			callback();
			return;
		}
		if (!security?.configured || !security?.enabled) {
			frappe.msgprint({
				title: __("Autorización no configurada"),
				message: __("Abra Mi perfil y configure la clave de corrección crítica."),
				indicator: "orange",
			});
			return;
		}
		const dialog = new frappe.ui.Dialog({
			title: "Autorizar correcciones críticas",
			fields: [
				{
					fieldname: "current_password",
					fieldtype: "Password",
					label: "Contraseña actual de Administrator",
					reqd: 1,
				},
				{ fieldname: "pin", fieldtype: "Password", label: "Clave de corrección", reqd: 1 },
				{
					fieldname: "notice",
					fieldtype: "HTML",
					options:
						"<p class='text-muted'>La autorización vive únicamente en esta pestaña y expira automáticamente.</p>",
				},
			],
			primary_action_label: "Autorizar",
			primary_action(values) {
				dialog.get_primary_btn().prop("disabled", true);
				frappe
					.xcall(API.authorize, values)
					.then((result) => {
						authorization = result;
						dialog.hide();
						updateState();
						callback?.();
					})
					.finally(() => dialog.get_primary_btn().prop("disabled", false));
			},
		});
		dialog.show();
	}

	function previewThenExecute({ previewMethod, executeMethod, args, html, done }) {
		frappe.xcall(previewMethod, { ...args, ...authArgs() }).then((preview) => {
			frappe.confirm(html(preview), () => {
				frappe
					.xcall(executeMethod, {
						...args,
						...authArgs(),
						preview_hash: preview.preview_hash,
					})
					.then(done);
			});
		});
	}

	function expenseChanges(values) {
		const result = {};
		for (const field of [
			"supplier",
			"project",
			"phase",
			"funding_source",
			"labor_contract",
			"category",
			"posting_date",
			"subtotal_hnl",
			"paid_amount_hnl",
			"payment_status",
		]) {
			if (values[field] !== undefined && values[field] !== null && values[field] !== "") {
				result[field] = values[field];
			}
		}
		if (values.clear_phase) result.phase = "";
		if (values.clear_funding_source) result.funding_source = "";
		if (values.clear_labor_contract) result.labor_contract = "";
		return result;
	}

	function openExpense() {
		const dialog = new frappe.ui.Dialog({
			title: "Corregir gasto migrado o vigente",
			size: "extra-large",
			fields: [
				{
					fieldname: "expense_name",
					fieldtype: "Link",
					options: "CC Expense Control",
					label: "Gasto",
					reqd: 1,
				},
				{
					fieldname: "operation",
					fieldtype: "Select",
					label: "Operación",
					options: "correct\nannul_migrated\nreverse_imported_payment\nregister_reimbursement",
					default: "correct",
					reqd: 1,
				},
				{
					fieldname: "supplier",
					fieldtype: "Link",
					options: "Supplier",
					label: "Proveedor correcto",
				},
				{ fieldname: "project", fieldtype: "Link", options: "Project", label: "Proyecto correcto" },
				{
					fieldname: "phase",
					fieldtype: "Link",
					options: "CC Construction Phase",
					label: "Fase correcta",
				},
				{ fieldname: "clear_phase", fieldtype: "Check", label: "Quitar fase incorrecta" },
				{
					fieldname: "funding_source",
					fieldtype: "Link",
					options: "CC Funding Source",
					label: "Fuente de fondos correcta",
				},
				{
					fieldname: "clear_funding_source",
					fieldtype: "Check",
					label: "Quitar fuente de fondos incorrecta",
				},
				{
					fieldname: "labor_contract",
					fieldtype: "Link",
					options: "CC Labor Contract",
					label: "Contrato correcto",
				},
				{
					fieldname: "clear_labor_contract",
					fieldtype: "Check",
					label: "Quitar contrato incorrecto",
				},
				{ fieldname: "category", fieldtype: "Data", label: "Categoría correcta" },
				{ fieldname: "posting_date", fieldtype: "Date", label: "Fecha correcta" },
				{
					fieldname: "subtotal_hnl",
					fieldtype: "Currency",
					options: "HNL",
					label: "Subtotal correcto",
				},
				{
					fieldname: "paid_amount_hnl",
					fieldtype: "Currency",
					options: "HNL",
					label: "Monto pagado correcto",
				},
				{
					fieldname: "payment_status",
					fieldtype: "Select",
					label: "Estado de pago correcto",
					options:
						"\ndraft\npending_approval\napproved\npartially_paid\npaid\noverdue\ncancelled\nreimbursed",
				},
				reasonField(),
				privateAttach(),
			],
			primary_action_label: "Simular corrección",
			primary_action(values) {
				const args = {
					expense_name: values.expense_name,
					operation: values.operation,
					changes: expenseChanges(values),
					reason: values.reason,
					evidence: values.evidence || "",
				};
				previewThenExecute({
					previewMethod: API.expensePreview,
					executeMethod: API.expenseExecute,
					args,
					html: (preview) =>
						`<p><b>Revise el impacto.</b></p><div class="cc-admin-impact"><div>Reconocido<br><b>${money(
							preview.impact.recognized_hnl.before
						)} → ${money(preview.impact.recognized_hnl.after)}</b></div><div>Pagado<br><b>${money(
							preview.impact.paid_hnl.before
						)} → ${money(preview.impact.paid_hnl.after)}</b></div><div>Pendiente<br><b>${money(
							preview.impact.pending_hnl.before
						)} → ${money(
							preview.impact.pending_hnl.after
						)}</b></div></div><p>El registro histórico original no será modificado.</p>`,
					done: (result) => {
						dialog.hide();
						frappe.msgprint({
							title: "Corrección aplicada",
							indicator: "green",
							message: `Gasto: <b>${escape(result.expense)}</b><br>Autorización: <code>${escape(
								result.authorization_id
							)}</code>`,
						});
					},
				});
			},
		});
		dialog.show();
	}

	function openBatch() {
		const dialog = new frappe.ui.Dialog({
			title: "Corrección masiva de gastos",
			fields: [
				{ fieldname: "expenses", fieldtype: "Small Text", label: "Gastos, uno por línea", reqd: 1 },
				{
					fieldname: "operation",
					fieldtype: "Select",
					label: "Operación común",
					options: "annul_migrated\nreverse_imported_payment\nregister_reimbursement",
					reqd: 1,
				},
				{
					fieldname: "paid_amount_hnl",
					fieldtype: "Currency",
					options: "HNL",
					label: "Monto pagado correcto",
				},
				reasonField(),
				{ ...privateAttach(), reqd: 1 },
			],
			primary_action_label: "Simular lote",
			primary_action(values) {
				const changes =
					values.operation === "reverse_imported_payment"
						? { paid_amount_hnl: values.paid_amount_hnl || 0 }
						: {};
				const args = {
					items: lines(values.expenses).map((expense_name) => ({
						expense_name,
						operation: values.operation,
						changes,
					})),
					reason: values.reason,
					evidence: values.evidence,
				};
				previewThenExecute({
					previewMethod: API.batchPreview,
					executeMethod: API.batchExecute,
					args,
					html: (preview) =>
						`<p>Registros: <b>${preview.count}</b></p><p>Cambio reconocido: <b>${money(
							preview.totals.recognized_delta_hnl
						)}</b><br>Cambio pagado: <b>${money(
							preview.totals.paid_delta_hnl
						)}</b><br>Cambio pendiente: <b>${money(preview.totals.pending_delta_hnl)}</b></p>`,
					done: (result) => {
						dialog.hide();
						frappe.msgprint(`${result.count} gastos fueron corregidos en una sola transacción.`);
					},
				});
			},
		});
		dialog.show();
	}

	function openSupplier() {
		const dialog = new frappe.ui.Dialog({
			title: "Consolidar proveedores duplicados",
			fields: [
				{
					fieldname: "canonical_supplier",
					fieldtype: "Link",
					options: "Supplier",
					label: "Proveedor oficial",
					reqd: 1,
				},
				{
					fieldname: "duplicate_suppliers",
					fieldtype: "Small Text",
					label: "Duplicados, uno por línea",
					reqd: 1,
				},
				reasonField(),
				{ ...privateAttach(), reqd: 1 },
			],
			primary_action_label: "Analizar referencias",
			primary_action(values) {
				const args = {
					canonical_supplier: values.canonical_supplier,
					duplicate_suppliers: lines(values.duplicate_suppliers),
					reason: values.reason,
					evidence: values.evidence,
				};
				previewThenExecute({
					previewMethod: API.supplierPreview,
					executeMethod: API.supplierExecute,
					args,
					html: (preview) =>
						`<p>Documentos a reasignar: <b>${
							preview.total_documents
						}</b></p><p>Duplicados a archivar: <b>${preview.duplicates.length}</b></p>${
							preview.blocked
								? "<p class='text-danger'>Existen referencias no compatibles y no se ejecutará.</p>"
								: ""
						}`,
					done: (result) => {
						dialog.hide();
						frappe.msgprint(`Proveedor oficial: ${escape(result.canonical_supplier)}.`);
					},
				});
			},
		});
		dialog.show();
	}

	const RECORDS = {
		funding: {
			title: "Corregir fuente de fondos FI01",
			doctype: "CC Funding Source",
			fields: [
				["project", "Link", "Project"],
				["status", "Select", "pending\nreceived\nheld\ncancelled"],
				["reconciliation_status", "Select", "pending\nverified\nreconciled\nrejected"],
				["gross_amount", "Currency", "HNL"],
				["fee_amount", "Currency", "HNL"],
				["treasury_exchange_rate", "Float", ""],
			],
		},
		phase: {
			title: "Corregir fase PR01",
			doctype: "CC Construction Phase",
			fields: [
				["project", "Link", "Project"],
				["budget_hnl", "Currency", "HNL"],
				["progress_percent", "Percent", ""],
				["responsible_user", "Link", "User"],
				["target_start_date", "Date", ""],
				["target_end_date", "Date", ""],
			],
		},
		contract: {
			title: "Corregir contrato CO01",
			doctype: "CC Labor Contract",
			fields: [
				["project", "Link", "Project"],
				["phase", "Link", "CC Construction Phase"],
				["supplier", "Link", "Supplier"],
				["project_value_hnl", "Currency", "HNL"],
				["labor_value_hnl", "Currency", "HNL"],
				["start_date", "Date", ""],
				["target_end_date", "Date", ""],
			],
		},
	};

	function openRecord(kind) {
		const config = RECORDS[kind];
		const fields = [
			{ fieldname: "name", fieldtype: "Link", options: config.doctype, label: "Registro", reqd: 1 },
		];
		for (const [fieldname, fieldtype, options] of config.fields) {
			fields.push({ fieldname, fieldtype, options, label: fieldname.replaceAll("_", " ") });
		}
		fields.push(reasonField(), privateAttach());
		const dialog = new frappe.ui.Dialog({
			title: config.title,
			size: "large",
			fields,
			primary_action_label: "Simular corrección",
			primary_action(values) {
				const changes = {};
				for (const [fieldname] of config.fields) {
					if (
						values[fieldname] !== undefined &&
						values[fieldname] !== null &&
						values[fieldname] !== ""
					) {
						changes[fieldname] = values[fieldname];
					}
				}
				const args = {
					doctype: config.doctype,
					name: values.name,
					changes,
					reason: values.reason,
					evidence: values.evidence || "",
				};
				previewThenExecute({
					previewMethod: API.recordPreview,
					executeMethod: API.recordExecute,
					args,
					html: (preview) =>
						`<p>Campos que cambiarán: <b>${preview.impact.changed_fields
							.map(escape)
							.join(", ")}</b></p>`,
					done: (result) => {
						dialog.hide();
						frappe.msgprint(`${escape(result.doctype)} · ${escape(result.name)} fue corregido.`);
					},
				});
			},
		});
		dialog.show();
	}

	function openPayable() {
		const dialog = new frappe.ui.Dialog({
			title: "Reconstruir cuenta por pagar",
			fields: [
				{
					fieldname: "expense_name",
					fieldtype: "Link",
					options: "CC Expense Control",
					label: "Gasto",
					reqd: 1,
				},
				reasonField(),
			],
			primary_action_label: "Analizar",
			primary_action(values) {
				previewThenExecute({
					previewMethod: API.payablePreview,
					executeMethod: API.payableExecute,
					args: values,
					html: (preview) =>
						`<p>Cuentas encontradas: <b>${preview.payables.length}</b><br>Duplicadas: <b>${preview.duplicate_count}</b></p>`,
					done: () => {
						dialog.hide();
						frappe.msgprint(__("La cuenta por pagar fue reconstruida desde el gasto canónico."));
					},
				});
			},
		});
		dialog.show();
	}

	function openUser() {
		const dialog = new frappe.ui.Dialog({
			title: "Archivar o consolidar usuario",
			fields: [
				{ fieldname: "user", fieldtype: "Link", options: "User", label: "Usuario origen", reqd: 1 },
				{
					fieldname: "operation",
					fieldtype: "Select",
					label: "Operación",
					options: "archive\nconsolidate\nanonymize_profile",
					default: "archive",
					reqd: 1,
				},
				{
					fieldname: "replacement_user",
					fieldtype: "Link",
					options: "User",
					label: "Cuenta sustituta",
				},
				reasonField(),
			],
			primary_action_label: "Simular",
			primary_action(values) {
				const args = { ...values, replacement_user: values.replacement_user || "" };
				previewThenExecute({
					previewMethod: API.userPreview,
					executeMethod: API.userExecute,
					args,
					html: (preview) =>
						`<p>Permisos: <b>${preview.assignments.user_permissions.length}</b><br>Fases responsables: <b>${preview.assignments.responsible_phases.length}</b></p><p>La autoría histórica permanecerá intacta.</p>`,
					done: (result) => {
						dialog.hide();
						frappe.msgprint(
							`Usuario ${escape(result.user)} procesado como ${escape(result.operation)}.`
						);
					},
				});
			},
		});
		dialog.show();
	}

	function mount(body) {
		if (frappe.session.user !== "Administrator" || body.find("#cc-admin-corrections").length) return;
		root = $(
			`<section id="cc-admin-corrections" class="cc-step cc-admin-corrections"><div class="cc-admin-head"><div><h3>Centro de Correcciones Administrativas</h3><p>Corrige datos heredados mediante vista previa, transacción, recálculo y auditoría inmutable.</p></div><span id="cc-admin-auth-state" class="cc-admin-auth-state">Bloqueado</span></div><div class="cc-actions"><button id="cc-admin-authorize" class="btn btn-primary">Autorizar por 10 minutos</button><button id="cc-admin-profile" class="btn btn-default">Seguridad del perfil</button><button id="cc-admin-audit" class="btn btn-default">Trazabilidad</button></div><div class="cc-admin-tools">${[
				["expense", "Corregir gasto", "Proveedor, fase, fondo, contrato, monto, pago o anulación."],
				["batch", "Corrección masiva", "Hasta 50 gastos en una transacción atómica."],
				["supplier", "Consolidar proveedores", "Reasigna referencias y archiva duplicados."],
				["funding", "Corregir FI01", "Remesas, montos, tasas y conciliación."],
				["phase", "Corregir fase", "Presupuesto, progreso, fechas y responsable."],
				["contract", "Corregir contrato", "Proveedor, valor, fase y fechas."],
				["payable", "Reconstruir cuenta por pagar", "Sincroniza desde el gasto canónico."],
				["user", "Archivar usuario", "Conserva la autoría histórica y reasigna permisos."],
			]
				.map(
					([action, title, description]) =>
						`<button class="cc-admin-tool" data-admin-action="${action}"><strong>${title}</strong><span>${description}</span></button>`
				)
				.join("")}</div></section>`
		);
		body.find(".cc-mig").append(root);
		$("<style>")
			.text(
				`.cc-admin-corrections{border-color:rgba(23,92,76,.4);background:linear-gradient(145deg,var(--card-bg),rgba(23,92,76,.05))}.cc-admin-head{display:flex;justify-content:space-between;gap:12px}.cc-admin-auth-state{height:max-content;padding:5px 10px;border-radius:999px;background:var(--subtle-fg);font-size:12px;font-weight:800}.cc-admin-auth-state.is-open{background:rgba(23,92,76,.12);color:#175c4c}.cc-admin-tools{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:10px;margin-top:14px}.cc-admin-tool{min-height:96px;padding:12px;border:1px solid var(--border-color);border-radius:12px;background:var(--card-bg);text-align:left}.cc-admin-tool strong,.cc-admin-tool span{display:block}.cc-admin-tool span{margin-top:5px;color:var(--text-muted);font-size:12px}.cc-admin-impact{display:grid;grid-template-columns:repeat(3,1fr);gap:8px}.cc-admin-impact div{padding:8px;border:1px solid var(--border-color);border-radius:8px}@media(max-width:767px){.cc-admin-head{flex-direction:column}.cc-admin-tools{grid-template-columns:1fr}.cc-admin-tool{min-height:auto}.cc-admin-impact{grid-template-columns:1fr}}`
			)
			.appendTo(document.head);
		root.find("#cc-admin-profile").on("click", () => frappe.set_route("construcontrol-profile"));
		root.find("#cc-admin-audit").on("click", () =>
			frappe.set_route("List", "CC Audit Log", { origin: "ADMIN_CORRECTION" })
		);
		root.find("#cc-admin-authorize").on("click", () => authorize(() => {}));
		root.on("click", "[data-admin-action]", function () {
			const action = String($(this).data("admin-action"));
			authorize(() => {
				if (action === "expense") openExpense();
				else if (action === "batch") openBatch();
				else if (action === "supplier") openSupplier();
				else if (RECORDS[action]) openRecord(action);
				else if (action === "payable") openPayable();
				else if (action === "user") openUser();
			});
		});
		loadStatus();
		window.setInterval(updateState, 15000);
	}

	window.ConstruControlAdminCorrections = { mount };
})();
