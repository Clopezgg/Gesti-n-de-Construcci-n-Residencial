// NEXORA · Recepciones
//
// Hallazgo real de auditoría (sesión 2026-08-16, Bloque 50): `nexora.
// purchases.receipt_service` (create/transition/get/list_receipts) no tenía
// ninguna página NEXORA — la única forma de registrar una recepción real
// era llamar la API a mano. Rompía GP-04 (solicitud → cotización → orden →
// recepción → pago) justo en el paso "recepción". Las cantidades por línea
// (ordenado/recibido previo/aceptado) y la tolerancia se calculan y
// validan siempre en el servidor (`receipt_core.validate_receipt_lines`);
// esta página solo envía cantidad recibida/rechazada por línea de orden.
frappe.pages["nexora-receipts"].on_page_load = function (wrapper) {
	const page = frappe.ui.make_app_page({
		parent: wrapper,
		title: __("Recepciones"),
		single_column: true,
	});
	const controls = {};
	const add = (definition) => {
		controls[definition.fieldname] = page.add_field(definition);
		return controls[definition.fieldname];
	};
	const statusLabels = { Draft: __("Borrador"), Completed: __("Completada"), Cancelled: __("Cancelada") };
	// Mismo grafo que `nexora.purchases.receipt_core.GOODS_RECEIPT_TRANSITIONS`.
	const transitions = { Draft: ["Completed", "Cancelled"], Completed: [], Cancelled: [] };

	add({
		fieldname: "purchase_order",
		label: __("Orden de compra"),
		fieldtype: "Link",
		options: "NXR Purchase Order",
	});
	add({
		fieldname: "status",
		label: __("Estado"),
		fieldtype: "Select",
		options: ["", ...Object.keys(statusLabels)],
	});

	$(page.body).append(`
		<div class="nxr-finance-grid nxr-receipt-grid">
			<section class="nxr-card"><h3>${__("Recepciones")}</h3><div class="nxr-receipt-results"></div></section>
			<section class="nxr-card"><h3>${__("Detalle")}</h3><div class="nxr-receipt-detail nxr-empty">${__(
		"Seleccione una recepción."
	)}</div></section>
			<section class="nxr-card"><h3>${__("Acciones")}</h3><div class="nxr-receipt-actions"></div></section>
		</div>
	`);

	page.add_button(__("Buscar"), refresh, "primary");
	page.add_button(__("Nueva recepción"), startNewReceipt);

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
			"nexora.purchases.receipt_service.list_receipts",
			{
				purchase_order: controls.purchase_order.get_value(),
				status: controls.status.get_value(),
				limit: 100,
			},
			"GET"
		);
		const target = $(page.body).find(".nxr-receipt-results").empty();
		if (!rows.length) {
			target.append(`<p class="nxr-empty">${__("No hay recepciones para los filtros indicados.")}</p>`);
			return;
		}
		rows.forEach((row) => {
			const button = $(
				`<button class="nxr-ds-btn nxr-ds-btn--secondary nxr-ds-btn--sm nxr-result-row"><strong>${escape(
					row.document_number
				)}</strong> · ${escape(statusLabels[row.status] || row.status)} · ${escape(
					row.purchase_order
				)} · ${escape(money(row.total_amount, row.currency))}</button>`
			);
			button.on("click", () => load(row.name));
			target.append(button);
		});
	}

	async function load(receipt) {
		const row = await call("nexora.purchases.receipt_service.get_receipt", { receipt }, "GET");
		const lineRows = row.lines
			.map(
				(line) => `<tr>
					<td>${escape(line.description)}</td>
					<td>${escape(line.ordered_quantity)}</td>
					<td>${escape(line.previously_received)}</td>
					<td>${escape(line.quantity)}</td>
					<td>${escape(line.rejected_quantity)}</td>
					<td>${escape(line.accepted_quantity)}</td>
					<td>${escape(money(line.amount, row.currency))}</td>
				</tr>`
			)
			.join("");
		$(page.body).find(".nxr-receipt-detail").removeClass("nxr-empty").html(`
			<p><strong>${escape(row.document_number)}</strong></p>
			<p>${__("Estado")}: ${escape(statusLabels[row.status] || row.status)}</p>
			<p>${__("Orden de compra")}: ${escape(row.purchase_order)}</p>
			<p>${__("Proveedor")}: ${escape(row.supplier_entity)}</p>
			<p>${__("Bodega")}: ${escape(row.warehouse)}</p>
			<p>${__("Fecha")}: ${escape(row.receipt_date)}</p>
			<div class="table-responsive"><table class="table table-bordered table-sm">
				<thead><tr><th>${__("Descripción")}</th><th>${__("Ordenado")}</th><th>${__("Recibido antes")}</th><th>${__(
			"Recibido"
		)}</th><th>${__("Rechazado")}</th><th>${__("Aceptado")}</th><th>${__("Importe")}</th></tr></thead>
				<tbody>${lineRows}</tbody>
			</table></div>
			<p><strong>${__("Total")}: ${escape(money(row.total_amount, row.currency))}</strong></p>
		`);
		renderActions(row);
	}

	function renderActions(row) {
		const target = $(page.body).find(".nxr-receipt-actions").empty();
		(transitions[row.status] || []).forEach((status) => {
			const button = $(
				`<button class="nxr-ds-btn nxr-ds-btn--secondary nxr-ds-btn--sm mr-2 mb-2">${escape(
					statusLabels[status] || status
				)}</button>`
			);
			button.on("click", async () => {
				const needsReason = status === "Cancelled";
				const reason = needsReason ? await askReason(statusLabels[status]) : null;
				if (needsReason && !reason) return;
				try {
					await call("nexora.purchases.receipt_service.transition_receipt", {
						receipt: row.name,
						status,
						reason,
						idempotency_key: uuid(),
					});
					frappe.show_alert({ message: __("Estado actualizado"), indicator: "green" });
					await refresh();
					await load(row.name);
				} catch (error) {
					window.nexora.ui.showError(error, { title: __("No se pudo actualizar la recepción") });
				}
			});
			target.append(button);
		});
		if (!(transitions[row.status] || []).length) {
			target.append(`<p class="nxr-empty">${__("La recepción no admite más acciones.")}</p>`);
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

	// La orden de compra se elige primero, en un diálogo aparte, porque las líneas
	// que se muestran después dependen por completo de esa orden — no hay forma
	// de pedir ambas cosas en un único paso sin inventar una jerarquía que
	// `frappe.ui.Dialog` no ofrece de forma nativa para un `Link` que filtra las
	// filas de otro campo.
	async function startNewReceipt() {
		const values = await new Promise((resolve) =>
			frappe.prompt(
				[
					{
						fieldname: "purchase_order",
						label: __("Orden de compra"),
						fieldtype: "Link",
						options: "NXR Purchase Order",
						reqd: 1,
					},
				],
				resolve,
				__("Recibir orden de compra")
			)
		);
		if (!values) return;
		try {
			const order = await call(
				"nexora.purchases.order_service.get_order",
				{ order: values.purchase_order },
				"GET"
			);
			openReceiptLinesDialog(order);
		} catch (error) {
			window.nexora.ui.showError(error, { title: __("No se pudo cargar la orden de compra") });
		}
	}

	// Las líneas se piden con una tabla HTML propia, no un campo `Table` de
	// `frappe.ui.Dialog`: cada fila representa una línea real de la orden (con su
	// `purchase_order_line`, fijo) y solo pide dos números por fila — un campo
	// `Table` genérico obligaría a que el usuario reescribiera artículo/descripción
	// que el servidor ya deriva de `purchase_order_line`.
	function openReceiptLinesDialog(order) {
		const rowsHtml = order.lines
			.map(
				(line, index) => `
				<tr data-line="${escape(line.name)}">
					<td>${escape(line.description)}</td>
					<td>${escape(line.quantity)} ${escape(line.uom)}</td>
					<td><input type="number" min="0" step="0.01" class="form-control input-sm nxr-receipt-qty" data-index="${index}" value="0"></td>
					<td><input type="number" min="0" step="0.01" class="form-control input-sm nxr-receipt-rejected" data-index="${index}" value="0"></td>
				</tr>`
			)
			.join("");
		const dialog = new frappe.ui.Dialog({
			title: __("Recibir {0}", [order.document_number]),
			size: "extra-large",
			fields: [
				{
					fieldname: "warehouse",
					label: __("Bodega destino"),
					fieldtype: "Link",
					options: "NXR Warehouse",
					reqd: 1,
				},
				{
					fieldname: "receipt_date",
					label: __("Fecha de recepción"),
					fieldtype: "Date",
					default: frappe.datetime.get_today(),
					reqd: 1,
				},
				{ fieldname: "notes", label: __("Notas"), fieldtype: "Small Text" },
				{
					fieldname: "lines_html",
					fieldtype: "HTML",
					options: `
						<div class="table-responsive"><table class="table table-bordered table-sm">
							<thead><tr><th>${__("Descripción")}</th><th>${__("Ordenado")}</th><th>${__("Recibido")}</th><th>${__(
						"Rechazado"
					)}</th></tr></thead>
							<tbody class="nxr-receipt-lines-body">${rowsHtml}</tbody>
						</table></div>
					`,
				},
			],
			primary_action_label: __("Registrar recepción"),
			primary_action: async () => {
				const values = dialog.get_values();
				if (!values) return;
				const lines = [];
				dialog.fields_dict.lines_html.$wrapper.find(".nxr-receipt-lines-body tr").each(function () {
					const poLine = $(this).attr("data-line");
					const qty = parseFloat($(this).find(".nxr-receipt-qty").val() || "0");
					const rejected = parseFloat($(this).find(".nxr-receipt-rejected").val() || "0");
					if (qty > 0) {
						lines.push({
							purchase_order_line: poLine,
							quantity: qty,
							rejected_quantity: rejected || 0,
						});
					}
				});
				if (!lines.length) {
					frappe.msgprint(__("Indique la cantidad recibida de al menos una línea."));
					return;
				}
				try {
					const result = await call("nexora.purchases.receipt_service.create_receipt", {
						payload: {
							purchase_order: order.name,
							warehouse: values.warehouse,
							receipt_date: values.receipt_date,
							notes: values.notes,
							lines,
							idempotency_key: uuid(),
						},
					});
					dialog.hide();
					frappe.show_alert({
						message: __("Recepción {0} registrada", [result.document_number]),
						indicator: "green",
					});
					await refresh();
					await load(result.name);
				} catch (error) {
					window.nexora.ui.showError(error, { title: __("No se pudo registrar la recepción") });
				}
			},
		});
		dialog.show();
	}

	refresh();
};
