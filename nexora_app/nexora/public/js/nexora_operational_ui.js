(() => {
	let dashboardRequest = 0;
	let dashboardTimer = null;
	let dashboardSignature = "";
	const CORRECTION_FIELDS = [
		"project",
		"source_name",
		"document_date",
		"channel",
		"currency",
		"original_amount",
		"exchange_rate",
		"amount_hnl",
		"origin_or_sender",
		"institution",
		"account_reference",
		"external_reference",
		"evidence",
		"reason",
		"preview_html",
	];

	function routeName() {
		return (frappe.get_route?.() || []).join("/").toLowerCase();
	}

	function dashboardProject() {
		return (
			document.querySelector('#page-nexora-dashboard [data-fieldname="project"] input')?.value ||
			frappe.route_options?.project ||
			null
		);
	}

	function canCorrectDocuments() {
		return ["System Manager", "NEXORA Administrator", "NEXORA Finance Manager"].some((role) =>
			frappe.user.has_role(role)
		);
	}

	function openOperationalConsole(movementCode, project = null, showLedger = false) {
		frappe.route_options = {
			movement_code: movementCode || "101",
			project: project || null,
			show_ledger: showLedger ? 1 : null,
		};
		frappe.set_route("nexora-operations");
	}

	document.addEventListener(
		"click",
		(event) => {
			const correctionTarget = event.target.closest?.(
				'.nxr-movement-chip[data-code="304"], [data-nexora-correct-document]'
			);
			if (correctionTarget && routeName().includes("nexora-operations")) {
				event.preventDefault();
				event.stopPropagation();
				event.stopImmediatePropagation();
				openCorrectionDialog();
				return;
			}
			const target = event.target.closest?.(
				'[data-action="income"], [data-launch-income], [data-action="expense"], [data-operation="CONSTRUCTION_PAYMENT"], [data-nexora-operational-ledger]'
			);
			if (!target) return;
			const route = routeName();
			if (!route.includes("nexora-dashboard") && !route.includes("nexora-finance")) return;
			event.preventDefault();
			event.stopPropagation();
			event.stopImmediatePropagation();
			const showLedger = target.hasAttribute("data-nexora-operational-ledger");
			const movementCode =
				target.dataset.action === "expense" || target.dataset.operation === "CONSTRUCTION_PAYMENT"
					? "102"
					: "101";
			openOperationalConsole(movementCode, dashboardProject(), showLedger);
		},
		true
	);

	document.addEventListener(
		"keydown",
		(event) => {
			if (event.key !== "Enter" || !routeName().includes("nexora-operations")) return;
			const input = event.target.closest?.(
				'#page-nexora-operations [data-field="movement_code"] input'
			);
			if (!input || String(input.value || "").trim() !== "304") return;
			event.preventDefault();
			event.stopPropagation();
			event.stopImmediatePropagation();
			openCorrectionDialog();
		},
		true
	);

	async function refreshDashboardOperationalRows() {
		if (!routeName().includes("nexora-dashboard")) return;
		const shell = document.querySelector(
			'#page-nexora-dashboard .nxr-dashboard-shell[data-state="ready"]'
		);
		if (!shell) return;
		const serial = ++dashboardRequest;
		try {
			const response = await frappe.call({
				method: "nexora.financial.service.list_operational_ledger",
				type: "POST",
				args: { project: dashboardProject(), limit: 20 },
			});
			if (serial !== dashboardRequest) return;
			const rows = response.message || [];
			const signature = JSON.stringify([
				dashboardProject(),
				rows.map((row) => [
					row.name,
					row.document_date,
					row.movement_code,
					row.amount_hnl,
					row.status,
				]),
			]);
			if (signature === dashboardSignature && operationalTableIsSynchronized(rows)) return;
			dashboardSignature = signature;
			renderActivity(rows);
			renderRecent(rows);
		} catch (error) {
			console.warn("NEXORA operational dashboard extension failed", error);
		}
	}

	function operationalTableIsSynchronized(rows) {
		const table = document.querySelector("#page-nexora-dashboard .nxr-dashboard-recent-rows");
		if (!table || table.dataset.operationalLedger !== "ready") return false;
		const headerCount = table.querySelectorAll("thead th").length;
		const bodyRows = [...table.querySelectorAll("tbody tr")];
		return (
			headerCount === 11 &&
			bodyRows.length === Math.min(rows.length, 8) &&
			bodyRows.every((row) => row.children.length === 11)
		);
	}

	function renderActivity(rows) {
		const target = document.querySelector("#page-nexora-dashboard .nxr-activity-list");
		if (!target) return;
		const visible = rows.slice(0, 3);
		target.innerHTML = visible.length
			? `${visible.map(activityRow).join("")}
				<button type="button" class="nxr-activity-more" data-nexora-operational-ledger="1">${__(
					"Ver más actividad"
				)}</button>`
			: `<p class="nxr-executive-empty">${__("No hay actividad reciente.")}</p>`;
	}

	function activityRow(row) {
		const amount = row.struck ? `<s>${money(row.amount_hnl)}</s>` : money(row.amount_hnl);
		return `<a class="nxr-executive-row nxr-operational-activity-row" data-tone="${escape(
			row.tone
		)}" href="${frappe.utils.get_form_link("NXR Operation", row.name)}">
			<span><strong>${escape(row.document_number || row.name)} · ${escape(row.movement_code)}</strong>
			<small>${escape(row.day)} ${date(row.document_date)} · ${escape(row.movement_label)}</small></span>
			<b data-tone="${escape(row.tone)}">${amount}</b>
		</a>`;
	}

	function renderRecent(rows) {
		const table = document.querySelector("#page-nexora-dashboard .nxr-dashboard-recent-rows");
		if (!table) return;
		table.querySelector("thead").innerHTML = `<tr>
			<th>${__("Día")}</th><th>${__("Fecha documento")}</th><th>${__("Documento")}</th>
			<th>${__("Mov.")}</th><th>${__("Movimiento")}</th><th>${__("Remitente / beneficiario")}</th>
			<th>${__("Institución")}</th><th>${__("Cuenta")}</th><th>${__("Moneda")}</th>
			<th class="text-right">${__("Importe")}</th><th>${__("Estado")}</th>
		</tr>`;
		table.querySelector("tbody").innerHTML = rows.slice(0, 8).map(recentRow).join("");
		table.dataset.operationalLedger = "ready";
		table.closest(".nxr-executive-card")?.classList.add("nxr-operational-ledger-card");
	}

	function recentRow(row) {
		const amount = row.struck ? `<s>${money(row.amount_hnl)}</s>` : money(row.amount_hnl);
		return `<tr data-tone="${escape(row.tone)}" data-movement="${escape(row.movement_code)}">
			<td>${escape(row.day)}</td><td>${date(row.document_date)}</td>
			<td><a href="${frappe.utils.get_form_link("NXR Operation", row.name)}">${escape(
			row.document_number || row.name
		)}</a></td>
			<td><b>${escape(row.movement_code)}</b></td><td>${escape(row.movement_label)}</td>
			<td>${escape(row.counterparty)}</td><td>${escape(row.institution)}</td><td>${escape(row.account)}</td>
			<td>${escape(row.currency)}</td><td class="text-right"><span data-tone="${escape(
			row.tone
		)}">${amount}</span></td><td>${escape(row.status)}</td>
		</tr>`;
	}

	function ensureCorrectionLauncher() {
		if (!routeName().includes("nexora-operations") || !canCorrectDocuments()) return;
		const header = document.querySelector("#page-nexora-operations .nxr-operational-header");
		if (!header || header.querySelector("[data-nexora-correct-document]")) return;
		const button = document.createElement("button");
		button.type = "button";
		button.className = "btn btn-default btn-sm";
		button.dataset.nexoraCorrectDocument = "1";
		button.textContent = __("Corregir documento");
		header.appendChild(button);
	}

	function hideCorrectionFields(dialog, hidden) {
		for (const fieldname of CORRECTION_FIELDS) {
			dialog.set_df_property(fieldname, "hidden", hidden ? 1 : 0);
		}
	}

	function correctionPayload(dialog) {
		const values = dialog.get_values();
		if (!values) return null;
		return {
			document: values.document_number,
			document_date: values.document_date,
			source_name: values.source_name,
			channel: values.channel,
			currency: values.currency,
			original_amount: values.original_amount,
			exchange_rate: values.exchange_rate,
			origin_or_sender: values.origin_or_sender,
			institution: values.institution,
			account_reference: values.account_reference,
			external_reference: values.external_reference,
			evidence: values.evidence,
			reason: values.reason,
		};
	}

	function syncCorrectionAmount(dialog) {
		const original = Number(dialog.get_value("original_amount") || 0);
		const exchange = Number(dialog.get_value("exchange_rate") || 0);
		dialog.set_value("amount_hnl", original * exchange);
	}

	function syncCorrectionChannel(dialog) {
		const channel = dialog.get_value("channel");
		const cash = channel === "Cash";
		const bank = ["Remittance", "Deposit", "Transfer"].includes(channel);
		for (const fieldname of ["institution", "account_reference", "external_reference"]) {
			dialog.set_df_property(fieldname, "hidden", cash ? 1 : 0);
			dialog.set_df_property(fieldname, "reqd", bank ? 1 : 0);
			if (cash) dialog.set_value(fieldname, "");
		}
	}

	function correctionPreviewHtml(preview) {
		const labels = {
			document_date: __("Fecha"),
			source_name: __("Nombre de remesa"),
			channel: __("Tipo de ingreso"),
			currency: __("Moneda"),
			original_amount: __("Valor original"),
			exchange_rate: __("Tasa"),
			amount_hnl: __("Importe HNL"),
			origin_or_sender: __("Remitente"),
			institution: __("Banco o remesadora"),
			account_reference: __("Cuenta"),
			external_reference: __("Referencia"),
			evidence: __("Comprobante"),
		};
		const rows = (preview.changed_fields || [])
			.map(
				(field) =>
					`<tr><td>${escape(labels[field] || field)}</td><td>${escape(
						preview.before?.[field] || "—"
					)}</td><td>${escape(preview.after?.[field] || "—")}</td></tr>`
			)
			.join("");
		return `<div class="alert alert-info"><strong>${__("Corrección 304 sin borrado físico")}</strong><br>
			${__(
				"La evidencia es opcional. Se generará un documento nuevo y quedará el antes y después en auditoría."
			)}</div>
			<div class="table-responsive"><table class="table table-bordered"><thead><tr><th>${__("Campo")}</th><th>${__(
			"Antes"
		)}</th><th>${__("Después")}</th></tr></thead><tbody>${rows}</tbody></table></div>
			<p><strong>${__("Diferencia financiera")}:</strong> ${money(preview.financial_delta_hnl)}</p>`;
	}

	function openCorrectionDialog(documentNumber = "", frm = null) {
		if (!canCorrectDocuments()) {
			frappe.msgprint({
				title: __("Corrección no autorizada"),
				message: __("Se requiere Gerente financiero o Administrador."),
				indicator: "red",
			});
			return;
		}
		const state = { loadedDocument: "", preview: null, loading: false };
		let dialog;
		const invalidate = () => {
			if (!dialog || state.loading) return;
			state.preview = null;
			dialog.fields_dict.preview_html.$wrapper.empty();
			dialog.set_primary_action(__("Vista previa"), previewCorrection);
		};
		dialog = new frappe.ui.Dialog({
			title: __("Corregir operación contabilizada"),
			size: "extra-large",
			fields: [
				{
					fieldname: "document_number",
					label: __("Número de documento"),
					fieldtype: "Data",
					reqd: 1,
					description: __(
						"Escriba los 12 dígitos. NEXORA cargará la fecha, remesa, importe y demás datos."
					),
				},
				{ fieldname: "lookup_html", fieldtype: "HTML" },
				{
					fieldname: "correction_section",
					fieldtype: "Section Break",
					label: __("Datos corregidos"),
				},
				{
					fieldname: "project",
					label: __("Proyecto"),
					fieldtype: "Link",
					options: "Project",
					read_only: 1,
				},
				{
					fieldname: "source_name",
					label: __("Nombre de la remesa o fuente"),
					fieldtype: "Data",
					reqd: 1,
					onchange: invalidate,
				},
				{ fieldname: "column_1", fieldtype: "Column Break" },
				{
					fieldname: "document_date",
					label: __("Fecha del documento"),
					fieldtype: "Date",
					reqd: 1,
					onchange: invalidate,
				},
				{ fieldname: "money_section", fieldtype: "Section Break", label: __("Importe") },
				{
					fieldname: "currency",
					label: __("Moneda"),
					fieldtype: "Link",
					options: "Currency",
					reqd: 1,
					onchange: invalidate,
				},
				{
					fieldname: "original_amount",
					label: __("Valor original"),
					fieldtype: "Currency",
					reqd: 1,
					onchange: () => {
						syncCorrectionAmount(dialog);
						invalidate();
					},
				},
				{ fieldname: "column_2", fieldtype: "Column Break" },
				{
					fieldname: "exchange_rate",
					label: __("Tasa a HNL"),
					fieldtype: "Float",
					reqd: 1,
					onchange: () => {
						syncCorrectionAmount(dialog);
						invalidate();
					},
				},
				{
					fieldname: "amount_hnl",
					label: __("Importe HNL"),
					fieldtype: "Currency",
					read_only: 1,
				},
				{ fieldname: "remittance_section", fieldtype: "Section Break", label: __("Remesa y cuenta") },
				{
					fieldname: "channel",
					label: __("Tipo de ingreso"),
					fieldtype: "Select",
					options: [
						{ label: __("Remesa"), value: "Remittance" },
						{ label: __("Efectivo"), value: "Cash" },
						{ label: __("Depósito"), value: "Deposit" },
						{ label: __("Transferencia"), value: "Transfer" },
						{ label: __("Otro"), value: "Other" },
					],
					reqd: 1,
					onchange: () => {
						syncCorrectionChannel(dialog);
						invalidate();
					},
				},
				{
					fieldname: "origin_or_sender",
					label: __("Remitente u origen"),
					fieldtype: "Data",
					reqd: 1,
					onchange: invalidate,
				},
				{ fieldname: "column_3", fieldtype: "Column Break" },
				{
					fieldname: "institution",
					label: __("Banco o remesadora"),
					fieldtype: "Link",
					options: "Bank",
					onchange: invalidate,
				},
				{
					fieldname: "account_reference",
					label: __("Cuenta destino"),
					fieldtype: "Data",
					onchange: invalidate,
				},
				{
					fieldname: "external_reference",
					label: __("Número de referencia"),
					fieldtype: "Data",
					onchange: invalidate,
				},
				{
					fieldname: "reason_section",
					fieldtype: "Section Break",
					label: __("Motivo y comprobante"),
				},
				{
					fieldname: "reason",
					label: __("Motivo de la corrección"),
					fieldtype: "Small Text",
					reqd: 1,
					onchange: invalidate,
				},
				{ fieldname: "column_4", fieldtype: "Column Break" },
				{
					fieldname: "evidence",
					label: __("Comprobante opcional"),
					fieldtype: "Attach",
					description: __("No es obligatorio para corregir fecha o datos."),
					onchange: invalidate,
				},
				{ fieldname: "preview_section", fieldtype: "Section Break" },
				{ fieldname: "preview_html", fieldtype: "HTML" },
			],
		});

		async function loadDocument() {
			const number = String(dialog.get_value("document_number") || "").trim();
			if (!number) return;
			state.loading = true;
			try {
				const response = await frappe.call({
					method: "nexora.financial.service.get_operation_for_correction",
					type: "POST",
					args: { document: number },
					freeze: true,
					freeze_message: __("Buscando el documento y sus datos efectivos…"),
				});
				const row = response.message || {};
				state.loadedDocument = row.document_number;
				state.preview = null;
				await dialog.set_value("document_number", row.document_number);
				for (const fieldname of [
					"project",
					"source_name",
					"document_date",
					"channel",
					"currency",
					"original_amount",
					"exchange_rate",
					"amount_hnl",
					"origin_or_sender",
					"institution",
					"account_reference",
					"external_reference",
					"evidence",
				]) {
					await dialog.set_value(fieldname, row[fieldname] || "");
				}
				for (const fieldname of ["currency", "original_amount", "exchange_rate"]) {
					dialog.set_df_property(fieldname, "read_only", row.amount_editable ? 0 : 1);
				}
				dialog.fields_dict.lookup_html.$wrapper.html(
					`<div class="alert alert-${row.amount_editable ? "success" : "warning"}"><strong>${escape(
						row.document_number
					)}</strong> · ${escape(row.channel_label)} · ${money(row.amount_hnl)}<br>${escape(
						row.amount_editable
							? __("Puede corregir todos los campos mostrados.")
							: row.amount_block_reason
					)}</div>`
				);
				hideCorrectionFields(dialog, false);
				syncCorrectionChannel(dialog);
				dialog.set_primary_action(__("Vista previa"), previewCorrection);
			} finally {
				state.loading = false;
			}
		}

		async function previewCorrection() {
			if (String(dialog.get_value("document_number") || "").trim() !== state.loadedDocument) {
				await loadDocument();
				return;
			}
			const payload = correctionPayload(dialog);
			if (!payload) return;
			const response = await frappe.call({
				method: "nexora.financial.service.preview_operation_correction",
				type: "POST",
				args: { payload },
				freeze: true,
				freeze_message: __("Validando períodos, uso del fondo y auditoría…"),
			});
			state.preview = response.message;
			dialog.fields_dict.preview_html.$wrapper.html(correctionPreviewHtml(state.preview));
			dialog.set_primary_action(__("Aplicar corrección"), executeCorrection);
		}

		async function executeCorrection() {
			if (!state.preview) return previewCorrection();
			const payload = correctionPayload(dialog);
			if (!payload) return;
			const response = await frappe.call({
				method: "nexora.financial.service.execute_operation_correction",
				type: "POST",
				args: {
					payload: {
						...payload,
						preview_hash: state.preview.preview_hash,
						idempotency_key: uuid(),
					},
				},
				freeze: true,
				freeze_message: __("Creando la corrección y preservando el antes y después…"),
			});
			dialog.hide();
			frappe.show_alert({
				message: __("Documento {0} corregido mediante {1}", [
					response.message.document_number,
					response.message.correction_document_number,
				]),
				indicator: "green",
			});
			document.dispatchEvent(
				new CustomEvent("nexora:data-changed", { detail: { area: "finance", type: "304" } })
			);
			await frm?.reload_doc?.();
		}

		dialog.show();
		hideCorrectionFields(dialog, true);
		dialog.set_primary_action(__("Buscar documento"), loadDocument);
		dialog.fields_dict.document_number.$input.on("keydown", (event) => {
			if (event.key !== "Enter") return;
			event.preventDefault();
			void loadDocument();
		});
		if (documentNumber) {
			dialog.set_value("document_number", documentNumber);
			void loadDocument();
		}
	}

	window.nexora_open_operation_correction = openCorrectionDialog;

	if (frappe.ui?.form?.on) {
		frappe.ui.form.on("NXR Operation", {
			refresh(frm) {
				const executed = ["Executed", "Compensated Partial", "Compensated Total"].includes(
					frm.doc.status
				);
				if (!executed) return;
				for (const fieldname of [
					"operation_date",
					"amount",
					"exchange_rate",
					"project",
					"beneficiary_doctype",
					"beneficiary",
					"external_reference",
					"evidence",
				]) {
					frm.set_df_property(fieldname, "read_only", 1);
				}
				frm.disable_save();
				frm.set_intro(
					__(
						"Esta operación está contabilizada. No edite sus campos directamente; use Corregir documento para preservar auditoría."
					),
					"blue"
				);
				if (
					frm.doc.status === "Executed" &&
					frm.doc.operation_type === "Inflow" &&
					frm.doc.operation_code !== "DOCUMENT_SUBSTITUTION" &&
					canCorrectDocuments()
				) {
					frm.add_custom_button(
						__("Corregir documento"),
						() => openCorrectionDialog(frm.doc.document_number, frm),
						__("Correcciones")
					);
				}
			},
		});
	}

	function scheduleDashboardRefresh() {
		ensureCorrectionLauncher();
		if (dashboardTimer) window.clearTimeout(dashboardTimer);
		dashboardTimer = window.setTimeout(() => {
			dashboardTimer = null;
			void refreshDashboardOperationalRows();
		}, 250);
	}

	frappe.router?.on?.("change", scheduleDashboardRefresh);
	document.addEventListener("nexora:data-changed", scheduleDashboardRefresh);
	const observer = new MutationObserver(() => {
		ensureCorrectionLauncher();
		if (document.querySelector('#page-nexora-dashboard .nxr-dashboard-shell[data-state="ready"]')) {
			scheduleDashboardRefresh();
		}
	});
	observer.observe(document.documentElement, { childList: true, subtree: true, attributes: true });

	function uuid() {
		return window.nexora.ui.generateId();
	}
	function money(value) {
		return window.nexora.ui.formatMoney(value);
	}
	function date(value) {
		return window.nexora.ui.formatDate(value);
	}
	function escape(value) {
		return window.nexora.ui.escapeHtml(value);
	}
})();
