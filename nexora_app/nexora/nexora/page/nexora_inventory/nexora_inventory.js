// NEXORA · Inventario
//
// Hallazgo real de auditoría (subagente en background, sesión 2026-08-16):
// `nexora.inventory.service` (create_warehouse/create_stock_transaction/
// transition_stock_transaction/get_stock_transaction/list_stock_transactions)
// tenía servicio completo — creación, transición, consulta y listado, con
// el mismo invariante de saldo no negativo que protege los fondos
// (`_assert_no_negative_balance`, corregido en el Bloque 45) — pero ninguna
// página NEXORA lo llamaba. La única lectura existente era el panel
// "inventario crítico" del dashboard, que solo reporta después del hecho;
// no había forma de registrar una entrada o salida sin salir de NEXORA por
// completo. Mismo patrón de página que `nexora-quotations`/
// `nexora-purchase-orders`.
frappe.pages["nexora-inventory"].on_page_load = function (wrapper) {
	const page = frappe.ui.make_app_page({
		parent: wrapper,
		title: __("Inventario"),
		single_column: true,
	});
	const controls = {};
	const add = (definition) => {
		controls[definition.fieldname] = page.add_field(definition);
		return controls[definition.fieldname];
	};
	const typeLabels = {
		Receipt: __("Recepción"),
		"Receipt Reversal": __("Reversión de recepción"),
		"Transfer In": __("Traslado (entrada)"),
		"Transfer Out": __("Traslado (salida)"),
		"Issue to Contractor": __("Entrega a contratista"),
		Consumption: __("Consumo"),
		Return: __("Devolución"),
		Damage: __("Daño"),
		Loss: __("Pérdida"),
		Adjustment: __("Ajuste"),
		"Physical Count": __("Conteo físico"),
	};
	const statusLabels = { Draft: __("Borrador"), Completed: __("Completado"), Cancelled: __("Cancelado") };
	// Mismo grafo que `nexora.inventory.core.STOCK_TRANSACTION_TRANSITIONS` —
	// el servidor decide de verdad vía `assert_stock_transition`, incluyendo
	// el bloqueo de saldo negativo al completar una salida.
	const transitions = { Draft: ["Completed", "Cancelled"], Completed: [], Cancelled: [] };
	const isManager = () =>
		(frappe.user_roles || []).some((role) =>
			["System Manager", "NEXORA Administrator", "NEXORA Finance Manager"].includes(role)
		);

	add({ fieldname: "project", label: __("Proyecto"), fieldtype: "Link", options: "Project" });
	add({
		fieldname: "transaction_type",
		label: __("Tipo de movimiento"),
		fieldtype: "Select",
		options: ["", ...Object.keys(typeLabels)],
	});

	$(page.body).append(`
		<div class="nxr-finance-grid nxr-inventory-grid">
			<section class="nxr-card"><h3>${__("Movimientos")}</h3><div class="nxr-inventory-results"></div></section>
			<section class="nxr-card"><h3>${__("Detalle")}</h3><div class="nxr-inventory-detail nxr-empty">${__(
				"Seleccione un movimiento."
			)}</div></section>
			<section class="nxr-card"><h3>${__("Acciones")}</h3><div class="nxr-inventory-actions"></div></section>
		</div>
	`);

	page.add_button(__("Buscar"), refresh, "primary");
	page.add_button(__("Nuevo movimiento"), createTransaction);
	if (isManager()) {
		page.add_button(__("Nueva bodega"), createWarehouse);
	}

	function uuid() {
		return window.nexora.ui.generateId();
	}

	async function call(method, args, type = "POST") {
		return (await frappe.call({ method, type, args, freeze: true })).message;
	}

	function escape(value) {
		return window.nexora.ui.escapeHtml(value);
	}

	function money(value) {
		return format_currency(value || 0, "HNL");
	}

	async function refresh() {
		const rows = await call(
			"nexora.inventory.service.list_stock_transactions",
			{
				project: controls.project.get_value(),
				transaction_type: controls.transaction_type.get_value(),
				limit: 100,
			},
			"GET"
		);
		const target = $(page.body).find(".nxr-inventory-results").empty();
		if (!rows.length) {
			target.append(`<p class="nxr-empty">${__("No hay movimientos para los filtros indicados.")}</p>`);
			return;
		}
		rows.forEach((row) => {
			const button = $(
				`<button class="nxr-ds-btn nxr-ds-btn--secondary nxr-ds-btn--sm nxr-result-row"><strong>${escape(
					row.document_number
				)}</strong> · ${escape(typeLabels[row.transaction_type] || row.transaction_type)} · ${escape(
					statusLabels[row.status] || row.status
				)} · ${escape(money(row.total_amount))}</button>`
			);
			button.on("click", () => load(row.name));
			target.append(button);
		});
	}

	async function load(transaction) {
		const row = await call("nexora.inventory.service.get_stock_transaction", { transaction }, "GET");
		const lineRows = row.lines
			.map(
				(line) => `<tr>
					<td>${escape(line.line_code)}</td>
					<td>${escape(line.item)}</td>
					<td>${escape(line.warehouse)}</td>
					<td>${escape(line.quantity)}</td>
					<td>${escape(money(line.amount))}</td>
				</tr>`
			)
			.join("");
		$(page.body).find(".nxr-inventory-detail").removeClass("nxr-empty").html(`
			<p><strong>${escape(row.document_number)}</strong></p>
			<p>${__("Tipo")}: ${escape(typeLabels[row.transaction_type] || row.transaction_type)}</p>
			<p>${__("Estado")}: ${escape(statusLabels[row.status] || row.status)}</p>
			<p>${__("Proyecto")}: ${escape(row.project || "—")}</p>
			<p>${__("Fecha")}: ${escape(row.transaction_date)}</p>
			<div class="table-responsive"><table class="table table-bordered table-sm">
				<thead><tr><th>${__("Línea")}</th><th>${__("Artículo")}</th><th>${__("Bodega")}</th><th>${__(
					"Cantidad"
				)}</th><th>${__("Importe")}</th></tr></thead>
				<tbody>${lineRows}</tbody>
			</table></div>
			<p><strong>${__("Total")}: ${escape(money(row.total_amount))}</strong></p>
		`);
		renderActions(row);
	}

	function renderActions(row) {
		const target = $(page.body).find(".nxr-inventory-actions").empty();
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
					await call("nexora.inventory.service.transition_stock_transaction", {
						transaction: row.name,
						status,
						reason,
						idempotency_key: uuid(),
					});
					frappe.show_alert({ message: __("Estado actualizado"), indicator: "green" });
					await refresh();
					await load(row.name);
				} catch (error) {
					window.nexora.ui.showError(error, { title: __("No se pudo actualizar el movimiento") });
				}
			});
			target.append(button);
		});
		if (!(transitions[row.status] || []).length) {
			target.append(`<p class="nxr-empty">${__("El movimiento no admite más acciones.")}</p>`);
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

	function createTransaction() {
		const dialog = new frappe.ui.Dialog({
			title: __("Nuevo movimiento de inventario"),
			size: "extra-large",
			fields: [
				{
					fieldname: "transaction_type",
					label: __("Tipo de movimiento"),
					fieldtype: "Select",
					options: Object.keys(typeLabels),
					reqd: 1,
				},
				{ fieldname: "project", label: __("Proyecto"), fieldtype: "Link", options: "Project" },
				{
					fieldname: "warehouse",
					label: __("Bodega principal"),
					fieldtype: "Link",
					options: "NXR Warehouse",
				},
				{
					fieldname: "transaction_date",
					label: __("Fecha"),
					fieldtype: "Date",
					default: frappe.datetime.get_today(),
					reqd: 1,
				},
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
							fieldname: "item",
							label: __("Artículo"),
							fieldtype: "Link",
							options: "Item",
							in_list_view: 1,
							reqd: 1,
						},
						{
							fieldname: "warehouse",
							label: __("Bodega"),
							fieldtype: "Link",
							options: "NXR Warehouse",
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
							fieldname: "unit_rate",
							label: __("Precio unitario"),
							fieldtype: "Currency",
							in_list_view: 1,
						},
						{ fieldname: "batch_no", label: __("Lote"), fieldtype: "Data" },
					],
				},
			],
			primary_action_label: __("Crear"),
			primary_action: async () => {
				const values = dialog.get_values();
				if (!values) return;
				try {
					const result = await call("nexora.inventory.service.create_stock_transaction", {
						payload: { ...values, idempotency_key: uuid() },
					});
					dialog.hide();
					frappe.show_alert({
						message: __("Movimiento {0} creado", [result.document_number]),
						indicator: "green",
					});
					await refresh();
					await load(result.name);
				} catch (error) {
					window.nexora.ui.showError(error, { title: __("No se pudo crear el movimiento") });
				}
			},
		});
		dialog.show();
	}

	function createWarehouse() {
		const dialog = new frappe.ui.Dialog({
			title: __("Nueva bodega"),
			fields: [
				{ fieldname: "warehouse_name", label: __("Nombre"), fieldtype: "Data", reqd: 1 },
				{ fieldname: "project", label: __("Proyecto"), fieldtype: "Link", options: "Project" },
				{ fieldname: "location", label: __("Ubicación"), fieldtype: "Data" },
				{ fieldname: "notes", label: __("Notas"), fieldtype: "Small Text" },
			],
			primary_action_label: __("Crear"),
			primary_action: async (values) => {
				try {
					await call("nexora.inventory.service.create_warehouse", { payload: values });
					dialog.hide();
					frappe.show_alert({ message: __("Bodega creada."), indicator: "green" });
				} catch (error) {
					window.nexora.ui.showError(error, { title: __("No se pudo crear la bodega") });
				}
			},
		});
		dialog.show();
	}

	refresh();
};
