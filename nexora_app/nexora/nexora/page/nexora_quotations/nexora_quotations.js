frappe.pages["nexora-quotations"].on_page_load = function (wrapper) {
	const page = frappe.ui.make_app_page({
		parent: wrapper,
		title: __("Cotizaciones de Compra"),
		single_column: true,
	});
	const controls = {};
	const add = (definition) => {
		controls[definition.fieldname] = page.add_field(definition);
		return controls[definition.fieldname];
	};
	const statusLabels = {
		Draft: __("Borrador"),
		Submitted: __("Enviada"),
		Accepted: __("Aceptada"),
		Rejected: __("Rechazada"),
		Expired: __("Vencida"),
		Cancelled: __("Cancelada"),
	};

	add({
		fieldname: "purchase_request",
		label: __("Solicitud"),
		fieldtype: "Link",
		options: "NXR Purchase Request",
	});
	add({
		fieldname: "status",
		label: __("Estado"),
		fieldtype: "Select",
		options: ["", "Draft", "Submitted", "Accepted", "Rejected", "Expired", "Cancelled"],
	});

	$(page.body).append(`
		<div class="nxr-finance-grid nxr-quotation-grid">
			<section class="nxr-card"><h3>${__("Cotizaciones")}</h3><div class="nxr-quotation-results"></div></section>
			<section class="nxr-card"><h3>${__("Detalle")}</h3><div class="nxr-quotation-detail nxr-ds-empty">${__(
		"Seleccione una cotización."
	)}</div></section>
			<section class="nxr-card"><h3>${__("Acciones")}</h3><div class="nxr-quotation-actions"></div></section>
		</div>
	`);

	page.add_button(__("Buscar"), refresh, "primary");
	page.add_button(__("Nueva cotización"), createQuotation);
	page.add_button(__("Comparar"), () => {
		const pr = controls.purchase_request.get_value();
		if (!pr) {
			frappe.msgprint(__("Seleccione una solicitud de compra para comparar cotizaciones."));
			return;
		}
		compareQuotations(pr);
	});

	function uuid() {
		return window.nexora.ui.generateId();
	}

	async function call(method, args, type = "POST") {
		return (await frappe.call({ method, type, args, freeze: true })).message;
	}

	function escape(value) {
		return window.nexora.ui.escapeHtml(value);
	}

	function money(value, currency = "HNL") {
		return format_currency(value || 0, currency);
	}

	async function refresh() {
		const rows = await call(
			"nexora.purchases.quotation_service.list_quotations",
			{
				purchase_request: controls.purchase_request.get_value(),
				status: controls.status.get_value(),
				limit: 100,
			},
			"GET"
		);
		const target = $(page.body).find(".nxr-quotation-results").empty();
		if (!rows.length) {
			target.append(
				`<p class="nxr-ds-empty">${__("No hay cotizaciones para los filtros indicados.")}</p>`
			);
			return;
		}
		rows.forEach((row) => {
			const button = $(
				`<button class="nxr-ds-btn nxr-ds-btn--secondary nxr-ds-btn--sm nxr-result-row"><strong>${escape(
					row.document_number
				)}</strong> · ${escape(statusLabels[row.status] || row.status)} · ${escape(
					row.supplier_entity
				)} · ${escape(money(row.total_amount, row.currency))}</button>`
			);
			button.on("click", () => load(row.quotation));
			target.append(button);
		});
	}

	async function load(quotation) {
		const row = await call("nexora.purchases.quotation_service.get_quotation", { quotation }, "GET");
		const lineRows = row.lines
			.map(
				(line) => `<tr>
			<td>${escape(line.line_code)}</td>
			<td>${escape(line.description)}</td>
			<td data-numeric="true">${escape(line.quantity)} ${escape(line.uom)}</td>
			<td data-numeric="true">${escape(money(line.unit_rate, row.currency))}</td>
			<td data-numeric="true">${escape(money(line.amount, row.currency))}</td>
		</tr>`
			)
			.join("");
		$(page.body).find(".nxr-quotation-detail").removeClass("nxr-ds-empty").html(`
			<p><strong>${escape(row.document_number)}</strong></p>
			<p>${__("Estado")}: ${escape(statusLabels[row.status] || row.status)}</p>
			<p>${__("Solicitud")}: ${escape(row.purchase_request)}</p>
			<p>${__("Proveedor")}: ${escape(row.supplier_entity)}</p>
			<p>${__("Moneda")}: ${escape(row.currency)}</p>
			<p>${__("Válida hasta")}: ${escape(row.valid_until)}</p>
			${row.selected ? `<p><strong>${__("SELECCIONADA")}</strong>: ${escape(row.selection_reason || "")}</p>` : ""}
			<div class="nxr-ds-table-wrap"><table class="nxr-ds-table">
				<thead><tr><th>${__("Línea")}</th><th>${__("Descripción")}</th><th data-numeric="true">${__(
			"Cantidad"
		)}</th><th data-numeric="true">${__("Precio")}</th><th data-numeric="true">${__(
			"Importe"
		)}</th></tr></thead>
				<tbody>${lineRows}</tbody>
			</table></div>
			<p><strong>${__("Total cotizado")}: ${escape(money(row.total_amount, row.currency))}</strong></p>
		`);
		renderActions(row);
	}

	function renderActions(row) {
		const target = $(page.body).find(".nxr-quotation-actions").empty();
		const transitions = {
			Draft: ["Submitted", "Cancelled"],
			Submitted: ["Accepted", "Rejected", "Expired", "Cancelled"],
			Accepted: ["Cancelled"],
			Rejected: ["Cancelled"],
			Expired: [],
			Cancelled: [],
		};
		(transitions[row.status] || []).forEach((status) => {
			const button = $(
				`<button class="nxr-ds-btn nxr-ds-btn--secondary nxr-ds-btn--sm mr-2 mb-2">${escape(
					statusLabels[status] || status
				)}</button>`
			);
			button.on("click", async () => {
				const needsReason = ["Accepted", "Rejected", "Cancelled"].includes(status);
				const reason = needsReason ? await askReason(statusLabels[status]) : null;
				await call("nexora.purchases.quotation_service.transition_quotation", {
					quotation: row.quotation,
					status,
					reason,
					idempotency_key: uuid(),
				});
				frappe.show_alert({ message: __("Estado actualizado"), indicator: "green" });
				await refresh();
				await load(row.quotation);
			});
			target.append(button);
		});
		if (!(transitions[row.status] || []).length) {
			target.append(`<p class="nxr-ds-empty">${__("La cotización no admite más transiciones.")}</p>`);
		}
		// Hallazgo real de auditoría (sesión 2026-08-16): `order_service.create_order`
		// no tenía ningún punto de entrada en NEXORA. Este es el punto natural — una
		// cotización Aceptada y seleccionada ya trae las líneas por defecto que
		// `create_order` necesita, así que crear la orden aquí es un solo llamado, sin
		// reconstruir un formulario de líneas duplicado. El resto del ciclo de vida de
		// la orden (transiciones, pago) vive en `nexora-purchase-orders`.
		if (row.status === "Accepted" && row.selected) {
			const orderButton = $(
				`<button class="nxr-ds-btn nxr-ds-btn--primary nxr-ds-btn--sm mr-2 mb-2">${__(
					"Crear orden de compra"
				)}</button>`
			);
			orderButton.on("click", async () => {
				try {
					const result = await call("nexora.purchases.order_service.create_order", {
						payload: {
							purchase_request: row.purchase_request,
							supplier_quotation: row.quotation,
							supplier_profile: row.supplier_profile,
							idempotency_key: uuid(),
						},
					});
					frappe.show_alert({
						message: __("Orden {0} creada", [result.document_number]),
						indicator: "green",
					});
					frappe.set_route("nexora-purchase-orders");
				} catch (error) {
					window.nexora.ui.showError(error, { title: __("No se pudo crear la orden de compra") });
				}
			});
			target.append(orderButton);
		}
	}

	function askReason(label) {
		return new Promise((resolve) => {
			frappe.prompt(
				[{ fieldname: "reason", label: __("Motivo"), fieldtype: "Small Text", reqd: 1 }],
				(values) => resolve(values.reason),
				label,
				__("Confirmar")
			);
		});
	}

	function createQuotation() {
		const dialog = new frappe.ui.Dialog({
			title: __("Nueva cotización"),
			size: "extra-large",
			fields: [
				{
					fieldname: "purchase_request",
					label: __("Solicitud de compra"),
					fieldtype: "Link",
					options: "NXR Purchase Request",
					reqd: 1,
				},
				{
					fieldname: "supplier_profile",
					label: __("Perfil de proveedor"),
					fieldtype: "Link",
					options: "NXR Supplier Profile",
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
					fieldname: "quotation_date",
					label: __("Fecha de cotización"),
					fieldtype: "Date",
					default: frappe.datetime.get_today(),
					reqd: 1,
				},
				{
					fieldname: "valid_until",
					label: __("Válida hasta"),
					fieldtype: "Date",
					default: frappe.datetime.add_days(frappe.datetime.get_today(), 30),
					reqd: 1,
				},
				{ fieldname: "payment_terms", label: __("Condiciones de pago"), fieldtype: "Small Text" },
				{ fieldname: "warranty", label: __("Garantía"), fieldtype: "Small Text" },
				{ fieldname: "delivery_terms", label: __("Condiciones de entrega"), fieldtype: "Small Text" },
				{ fieldname: "evidence", label: __("Evidencia"), fieldtype: "Link", options: "NXR Evidence" },
				{ fieldname: "notes", label: __("Notas"), fieldtype: "Small Text" },
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
							fieldname: "unit_rate",
							label: __("Precio"),
							fieldtype: "Currency",
							in_list_view: 1,
							reqd: 1,
						},
						{
							fieldname: "economic_category",
							label: __("Clasif. económica"),
							fieldtype: "Link",
							options: "NXR Economic Category",
						},
						{ fieldname: "delivery_date", label: __("Fecha entrega"), fieldtype: "Date" },
					],
				},
			],
			primary_action_label: __("Crear"),
			primary_action: async () => {
				const values = dialog.get_values();
				if (!values) return;
				const result = await call("nexora.purchases.quotation_service.create_quotation", {
					payload: { ...values, idempotency_key: uuid() },
				});
				dialog.hide();
				frappe.show_alert({
					message: __("Cotización {0} creada", [result.document_number]),
					indicator: "green",
				});
				await refresh();
				await load(result.quotation);
			},
		});
		dialog.show();
	}

	async function compareQuotations(purchase_request) {
		const rows = await call(
			"nexora.purchases.quotation_service.compare_quotations",
			{ purchase_request },
			"GET"
		);
		if (!rows.length) {
			frappe.msgprint(__("No hay cotizaciones enviadas o aceptadas para esta solicitud."));
			return;
		}
		let html = `<div class="nxr-ds-table-wrap"><table class="nxr-ds-table">
			<thead><tr><th>${__("Cotización")}</th><th>${__("Proveedor")}</th><th data-numeric="true">${__(
			"Total"
		)}</th><th>${__("Moneda")}</th><th>${__("Estado")}</th><th>${__("Seleccionada")}</th></tr></thead>
			<tbody>`;
		rows.forEach((r) => {
			html += `<tr>
				<td>${escape(r.document_number)}</td>
				<td>${escape(r.supplier_entity)}</td>
				<td data-numeric="true">${escape(money(r.total_amount, r.currency))}</td>
				<td>${escape(r.currency)}</td>
				<td>${escape(statusLabels[r.status] || r.status)}</td>
				<td>${r.selected ? __("Sí") : __("No")}</td>
			</tr>`;
		});
		html += `</tbody></table></div>`;
		frappe.msgprint(html, __("Comparación de cotizaciones"));
	}

	refresh();
};
