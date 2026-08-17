// NEXORA · Órdenes de compra
//
// Hallazgo real de auditoría (subagente en background, sesión 2026-08-16):
// `nexora.purchases.order_service` (create_order/transition_order/get_order/
// list_orders) no tenía ninguna página NEXORA — la única forma de ver o
// mover una orden de compra era el escritorio técnico de Frappe
// (`nxr_purchase_order.js`, un `frappe.ui.form.on` puro que solo agregaba un
// botón de pago sobre el formulario nativo). Rompía el recorrido dorado
// GP-04 (solicitud → cotización → orden → recepción → pago) justo en el
// paso "orden": el usuario tenía que salir de NEXORA por completo.
//
// La creación de la orden vive en `nexora_quotations.js` (botón "Crear
// orden de compra" sobre una cotización Aceptada/seleccionada, que ya trae
// las líneas por defecto de esa cotización — `order_service.create_order`
// no exige reescribirlas). Esta página es el ciclo de vida posterior:
// listar, ver detalle, transicionar estado y registrar el pago — lo mismo
// que hacía el botón del formulario técnico, ahora dentro del shell.
frappe.pages["nexora-purchase-orders"].on_page_load = function (wrapper) {
	const page = frappe.ui.make_app_page({
		parent: wrapper,
		title: __("Órdenes de compra"),
		single_column: true,
	});
	const controls = {};
	const add = (definition) => {
		controls[definition.fieldname] = page.add_field(definition);
		return controls[definition.fieldname];
	};
	const statusLabels = {
		Draft: __("Borrador"),
		Confirmed: __("Confirmada"),
		Approved: __("Aprobada"),
		Sent: __("Enviada"),
		Completed: __("Completada"),
		Cancelled: __("Cancelada"),
	};
	// Mismo grafo que `nexora.purchases.order_core.PURCHASE_ORDER_TRANSITIONS`
	// — duplicado a propósito solo para pintar los botones disponibles; el
	// servidor es quien decide de verdad (`assert_order_transition`).
	const transitions = {
		Draft: ["Confirmed", "Cancelled"],
		Confirmed: ["Approved", "Cancelled"],
		Approved: ["Sent", "Cancelled"],
		Sent: ["Completed", "Cancelled"],
		Completed: [],
		Cancelled: [],
	};

	add({
		fieldname: "project",
		label: __("Proyecto"),
		fieldtype: "Link",
		options: "Project",
	});
	add({
		fieldname: "status",
		label: __("Estado"),
		fieldtype: "Select",
		options: ["", "Draft", "Confirmed", "Approved", "Sent", "Completed", "Cancelled"],
	});

	$(page.body).append(`
		<div class="nxr-finance-grid nxr-order-grid">
			<section class="nxr-card"><h3>${__("Órdenes")}</h3><div class="nxr-order-results"></div></section>
			<section class="nxr-card"><h3>${__("Detalle")}</h3><div class="nxr-order-detail nxr-empty">${__(
		"Seleccione una orden."
	)}</div></section>
			<section class="nxr-card"><h3>${__("Acciones")}</h3><div class="nxr-order-actions"></div></section>
		</div>
	`);

	page.add_button(__("Buscar"), refresh, "primary");

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
			"nexora.purchases.order_service.list_orders",
			{
				project: controls.project.get_value(),
				status: controls.status.get_value(),
				limit: 100,
			},
			"GET"
		);
		const target = $(page.body).find(".nxr-order-results").empty();
		if (!rows.length) {
			target.append(`<p class="nxr-empty">${__("No hay órdenes para los filtros indicados.")}</p>`);
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
			button.on("click", () => load(row.name));
			target.append(button);
		});
	}

	async function load(order) {
		const row = await call("nexora.purchases.order_service.get_order", { order }, "GET");
		const lineRows = row.lines
			.map(
				(line) => `<tr>
					<td>${escape(line.line_code)}</td>
					<td>${escape(line.description)}</td>
					<td>${escape(line.quantity)} ${escape(line.uom)}</td>
					<td>${escape(money(line.unit_rate, row.currency))}</td>
					<td>${escape(money(line.net_amount, row.currency))}</td>
				</tr>`
			)
			.join("");
		$(page.body).find(".nxr-order-detail").removeClass("nxr-empty").html(`
			<p><strong>${escape(row.document_number)}</strong></p>
			<p>${__("Estado")}: ${escape(statusLabels[row.status] || row.status)}</p>
			<p>${__("Solicitud")}: ${escape(row.purchase_request)}</p>
			<p>${__("Cotización")}: ${escape(row.supplier_quotation)}</p>
			<p>${__("Proveedor")}: ${escape(row.supplier_entity)}</p>
			<p>${__("Proyecto")}: ${escape(row.project)}</p>
			<p>${__("Moneda")}: ${escape(row.currency)}</p>
			<p>${__("Entrega")}: ${escape(row.delivery_date || "—")}</p>
			<div class="table-responsive"><table class="table table-bordered table-sm">
				<thead><tr><th>${__("Línea")}</th><th>${__("Descripción")}</th><th>${__("Cantidad")}</th><th>${__(
			"Precio"
		)}</th><th>${__("Neto")}</th></tr></thead>
				<tbody>${lineRows}</tbody>
			</table></div>
			<p><strong>${__("Total")}: ${escape(money(row.total_amount, row.currency))}</strong></p>
		`);
		renderActions(row);
	}

	function renderActions(row) {
		const target = $(page.body).find(".nxr-order-actions").empty();
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
				await call("nexora.purchases.order_service.transition_order", {
					order: row.name,
					status,
					reason,
					idempotency_key: uuid(),
				});
				frappe.show_alert({ message: __("Estado actualizado"), indicator: "green" });
				await refresh();
				await load(row.name);
			});
			target.append(button);
		});
		if (["Sent", "Completed"].includes(row.status)) {
			const payButton = $(
				`<button class="nxr-ds-btn nxr-ds-btn--primary nxr-ds-btn--sm mr-2 mb-2">${__(
					"Registrar pago"
				)}</button>`
			);
			payButton.on("click", () => openPaymentDialog(row));
			target.append(payButton);
		}
		if (!(transitions[row.status] || []).length && !["Sent", "Completed"].includes(row.status)) {
			target.append(`<p class="nxr-empty">${__("La orden no admite más acciones.")}</p>`);
		}
	}

	function openPaymentDialog(row) {
		const dialog = new frappe.ui.Dialog({
			title: __("Registrar pago de compra"),
			fields: [
				{
					fieldname: "amount_hnl",
					label: __("Importe HNL"),
					fieldtype: "Currency",
					reqd: 1,
					default: 0,
					options: "HNL",
				},
				{
					fieldname: "economic_category",
					label: __("Clasificación económica"),
					fieldtype: "Link",
					options: "NXR Economic Category",
					reqd: 1,
				},
				{ fieldname: "evidence", label: __("Evidencia"), fieldtype: "Link", options: "NXR Evidence" },
				{ fieldname: "description", label: __("Descripción"), fieldtype: "Small Text" },
			],
			primary_action_label: __("Ejecutar pago"),
			primary_action: async (values) => {
				try {
					const result = await call("nexora.purchases.financial_bridge.pay_purchase_order", {
						payload: {
							purchase_order: row.name,
							amount_hnl: values.amount_hnl,
							economic_category: values.economic_category,
							evidence: values.evidence,
							description: values.description,
							idempotency_key: `purchase-payment-${row.name}-${uuid()}`,
						},
					});
					dialog.hide();
					frappe.show_alert({ message: __("Pago registrado correctamente."), indicator: "green" });
					await refresh();
					await load(row.name);
					if (result?.name) frappe.set_route("Form", "NXR Operation", result.name);
				} catch (error) {
					window.nexora.ui.showError(error, {
						title: __("No fue posible ejecutar el pago"),
						fallback: __("Revise la recepción, compromiso, fondo y permisos."),
					});
				}
			},
		});
		dialog.show();
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

	refresh();
};
