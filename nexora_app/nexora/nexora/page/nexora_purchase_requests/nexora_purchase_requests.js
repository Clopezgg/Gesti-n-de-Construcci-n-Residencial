frappe.pages["nexora-purchase-requests"].on_page_load = function (wrapper) {
	const page = frappe.ui.make_app_page({
		parent: wrapper,
		title: __("Solicitudes de Compra"),
		single_column: true,
	});
	const controls = {};
	const add = (definition) => {
		controls[definition.fieldname] = page.add_field(definition);
		return controls[definition.fieldname];
	};
	const statusLabels = {
		Draft: __("Borrador"),
		"In Review": __("En revisión"),
		Approved: __("Aprobada"),
		Rejected: __("Rechazada"),
		Cancelled: __("Cancelada"),
	};

	add({ fieldname: "project", label: __("Proyecto"), fieldtype: "Link", options: "Project" });
	add({
		fieldname: "status",
		label: __("Estado"),
		fieldtype: "Select",
		options: ["", "Draft", "In Review", "Approved", "Rejected", "Cancelled"],
	});

	$(page.body).append(`
		<div class="nxr-finance-grid nxr-purchase-request-grid">
			<section class="nxr-card"><h3>${__("Solicitudes")}</h3><div class="nxr-request-results"></div></section>
			<section class="nxr-card"><h3>${__("Detalle")}</h3><div class="nxr-request-detail nxr-empty">${__(
		"Seleccione una solicitud."
	)}</div></section>
			<section class="nxr-card"><h3>${__("Acciones")}</h3><div class="nxr-request-actions"></div></section>
		</div>
	`);

	page.add_button(__("Buscar"), refresh, "primary");
	page.add_button(__("Nueva solicitud"), createRequest);
	page.add_button(__("Proveedores"), () => frappe.set_route("nexora-suppliers"));

	function uuid() {
		return (
			globalThis.crypto?.randomUUID?.() || `nxr-${Date.now()}-${Math.random().toString(16).slice(2)}`
		);
	}

	async function call(method, args, type = "POST") {
		return (await frappe.call({ method, type, args, freeze: true })).message;
	}

	function escape(value) {
		return frappe.utils.escape_html(String(value ?? ""));
	}

	function money(value, currency = "HNL") {
		return format_currency(value || 0, currency);
	}

	async function refresh() {
		const rows = await call(
			"nexora.purchases.request_service.list_purchase_requests",
			{
				project: controls.project.get_value(),
				status: controls.status.get_value(),
				limit: 100,
			},
			"GET"
		);
		const target = $(page.body).find(".nxr-request-results").empty();
		if (!rows.length) {
			target.append(`<p class="nxr-empty">${__("No hay solicitudes para los filtros indicados.")}</p>`);
			return;
		}
		rows.forEach((row) => {
			const button = $(
				`<button class="btn btn-default btn-sm nxr-result-row"><strong>${escape(
					row.document_number
				)}</strong> · ${escape(statusLabels[row.status] || row.status)} · ${escape(
					row.project
				)} · ${escape(money(row.total_amount, row.currency))}</button>`
			);
			button.on("click", () => load(row.request));
			target.append(button);
		});
	}

	async function load(request) {
		const row = await call("nexora.purchases.request_service.get_purchase_request", { request }, "GET");
		const lineRows = row.lines
			.map(
				(line) => `<tr>
					<td>${escape(line.line_code)}</td>
					<td>${escape(line.description)}</td>
					<td>${escape(line.quantity)} ${escape(line.uom)}</td>
					<td>${escape(money(line.estimated_unit_rate, row.currency))}</td>
					<td>${escape(money(line.estimated_amount, row.currency))}</td>
				</tr>`
			)
			.join("");
		$(page.body).find(".nxr-request-detail").removeClass("nxr-empty").html(`
			<p><strong>${escape(row.document_number)}</strong></p>
			<p>${__("Estado")}: ${escape(statusLabels[row.status] || row.status)}</p>
			<p>${__("Proyecto")}: ${escape(row.project)}</p>
			<p>${__("Centro de costo")}: ${escape(row.cost_center)}</p>
			<p>${__("Responsable")}: ${escape(row.responsible)}</p>
			<p>${__("Prioridad")}: ${escape(row.priority)}</p>
			<p>${__("Requerido para")}: ${escape(row.required_by)}</p>
			<p>${__("Justificación")}: ${escape(row.justification)}</p>
			<div class="table-responsive"><table class="table table-bordered table-sm">
				<thead><tr><th>${__("Línea")}</th><th>${__("Descripción")}</th><th>${__("Cantidad")}</th><th>${__(
			"Precio"
		)}</th><th>${__("Importe")}</th></tr></thead>
				<tbody>${lineRows}</tbody>
			</table></div>
			<p><strong>${__("Total estimado")}: ${escape(money(row.total_amount, row.currency))}</strong></p>
		`);
		renderActions(row);
	}

	function askReason(label) {
		return new Promise((resolve) => {
			frappe.prompt(
				[
					{
						fieldname: "reason",
						label: __("Motivo"),
						fieldtype: "Small Text",
						reqd: 1,
					},
				],
				(values) => resolve(values.reason),
				label,
				__("Confirmar")
			);
		});
	}

	function renderActions(row) {
		const target = $(page.body).find(".nxr-request-actions").empty();
		const transitions = {
			Draft: ["In Review", "Cancelled"],
			"In Review": ["Draft", "Approved", "Rejected", "Cancelled"],
			Approved: ["Cancelled"],
			Rejected: [],
			Cancelled: [],
		};
		(transitions[row.status] || []).forEach((status) => {
			const button = $(
				`<button class="btn btn-default btn-sm mr-2 mb-2">${escape(
					statusLabels[status] || status
				)}</button>`
			);
			button.on("click", async () => {
				const reason = ["Rejected", "Cancelled"].includes(status)
					? await askReason(statusLabels[status])
					: null;
				await call("nexora.purchases.request_service.transition_purchase_request", {
					request: row.request,
					status,
					reason,
					idempotency_key: uuid(),
				});
				frappe.show_alert({ message: __("Estado actualizado"), indicator: "green" });
				await refresh();
				await load(row.request);
			});
			target.append(button);
		});
		if (!(transitions[row.status] || []).length) {
			target.append(`<p class="nxr-empty">${__("La solicitud no admite más transiciones.")}</p>`);
		}
	}

	function createRequest() {
		const dialog = new frappe.ui.Dialog({
			title: __("Nueva solicitud de compra"),
			size: "extra-large",
			fields: [
				{
					fieldname: "request_date",
					label: __("Fecha de solicitud"),
					fieldtype: "Date",
					default: frappe.datetime.get_today(),
					reqd: 1,
				},
				{
					fieldname: "required_by",
					label: __("Requerido para"),
					fieldtype: "Date",
					default: frappe.datetime.add_days(frappe.datetime.get_today(), 7),
					reqd: 1,
				},
				{
					fieldname: "project",
					label: __("Proyecto"),
					fieldtype: "Link",
					options: "Project",
					default: controls.project.get_value(),
					reqd: 1,
				},
				{
					fieldname: "cost_center",
					label: __("Centro de costo"),
					fieldtype: "Link",
					options: "Cost Center",
					reqd: 1,
				},
				{
					fieldname: "fund_source",
					label: __("Fuente prevista"),
					fieldtype: "Link",
					options: "NXR Fund Source",
				},
				{
					fieldname: "responsible",
					label: __("Responsable"),
					fieldtype: "Link",
					options: "User",
					default: frappe.session.user,
					reqd: 1,
				},
				{
					fieldname: "priority",
					label: __("Prioridad"),
					fieldtype: "Select",
					options: ["Low", "Normal", "High", "Urgent"],
					default: "Normal",
					reqd: 1,
				},
				{
					fieldname: "currency",
					label: __("Moneda"),
					fieldtype: "Link",
					options: "Currency",
					default: "HNL",
					reqd: 1,
				},
				{
					fieldname: "justification",
					label: __("Justificación"),
					fieldtype: "Small Text",
					reqd: 1,
				},
				{
					fieldname: "evidence",
					label: __("Evidencia"),
					fieldtype: "Link",
					options: "NXR Evidence",
				},
				{
					fieldname: "lines",
					label: __("Líneas"),
					fieldtype: "Table",
					reqd: 1,
					cannot_add_rows: false,
					in_place_edit: true,
					fields: [
						{ fieldname: "line_code", label: __("Línea"), fieldtype: "Data", in_list_view: 1 },
						{
							fieldname: "item_type",
							label: __("Tipo"),
							fieldtype: "Select",
							options: ["Goods", "Service"],
							default: "Goods",
							in_list_view: 1,
							reqd: 1,
						},
						{
							fieldname: "catalog_item",
							label: __("Artículo"),
							fieldtype: "Link",
							options: "Item",
						},
						{
							fieldname: "description",
							label: __("Descripción"),
							fieldtype: "Data",
							in_list_view: 1,
							reqd: 1,
						},
						{
							fieldname: "quantity",
							label: __("Cantidad"),
							fieldtype: "Float",
							in_list_view: 1,
							reqd: 1,
						},
						{
							fieldname: "uom",
							label: __("Unidad"),
							fieldtype: "Link",
							options: "UOM",
							in_list_view: 1,
							reqd: 1,
						},
						{
							fieldname: "estimated_unit_rate",
							label: __("Precio estimado"),
							fieldtype: "Currency",
							in_list_view: 1,
							reqd: 1,
						},
						{
							fieldname: "economic_category",
							label: __("Clasificación económica"),
							fieldtype: "Link",
							options: "NXR Economic Category",
							in_list_view: 1,
							reqd: 1,
						},
						{
							fieldname: "cost_center",
							label: __("Centro de costo"),
							fieldtype: "Link",
							options: "Cost Center",
						},
					],
				},
			],
			primary_action_label: __("Crear"),
			primary_action: async () => {
				const values = dialog.get_values();
				if (!values) return;
				const result = await call("nexora.purchases.request_service.create_purchase_request", {
					payload: { ...values, idempotency_key: uuid() },
				});
				dialog.hide();
				controls.project.set_value(result.project);
				frappe.show_alert({
					message: __("Solicitud {0} creada", [result.document_number]),
					indicator: "green",
				});
				await refresh();
				await load(result.request);
			},
		});
		dialog.show();
	}

	refresh();
};
