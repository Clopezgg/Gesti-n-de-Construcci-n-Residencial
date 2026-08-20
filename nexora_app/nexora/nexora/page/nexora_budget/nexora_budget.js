// NEXORA · Presupuesto
//
// Hallazgo real de auditoría (sesión 2026-08-16, Bloque 53): `budget.service`
// tenía create/activate/amend/close/cancel/check_budget_availability, pero
// ningún `list`/`get` — a diferencia de compras/inventario/cierre, la
// consulta de presupuestos no existía en absoluto, así que tampoco había
// forma de construir esta pantalla hasta agregar `get_budget`/`list_budgets`
// (mismo patrón de solo lectura que `purchases.order_service`). Sin esto,
// crear o enmendar un presupuesto solo era posible llamando la API a mano.
frappe.pages["nexora-budget"].on_page_load = function (wrapper) {
	const page = frappe.ui.make_app_page({
		parent: wrapper,
		title: __("Presupuesto"),
		single_column: true,
	});
	const controls = {};
	const add = (definition) => {
		controls[definition.fieldname] = page.add_field(definition);
		return controls[definition.fieldname];
	};
	const statusLabels = {
		Draft: __("Borrador"),
		Active: __("Activo"),
		Amended: __("Enmendado"),
		Closed: __("Cerrado"),
		Cancelled: __("Cancelado"),
	};
	// Mismo grafo que `nexora.budget.core.BUDGET_TRANSITIONS` — el servidor
	// decide de verdad vía `assert_transition`. "Amended" no es un destino
	// directo de botón: lo produce `amend_budget`, que crea una versión nueva.
	const transitions = {
		Draft: ["Active", "Cancelled"],
		Active: ["Closed"],
		Amended: [],
		Closed: [],
		Cancelled: [],
	};

	add({ fieldname: "project", label: __("Proyecto"), fieldtype: "Link", options: "Project" });
	add({
		fieldname: "status",
		label: __("Estado"),
		fieldtype: "Select",
		options: ["", ...Object.keys(statusLabels)],
	});

	$(page.body).append(`
		<div class="nxr-finance-grid nxr-budget-grid">
			<section class="nxr-card"><h3>${__("Presupuestos")}</h3><div class="nxr-budget-results"></div></section>
			<section class="nxr-card"><h3>${__("Detalle")}</h3><div class="nxr-budget-detail nxr-empty">${__(
		"Seleccione un presupuesto."
	)}</div></section>
			<section class="nxr-card"><h3>${__("Acciones")}</h3><div class="nxr-budget-actions"></div></section>
		</div>
	`);

	page.add_button(__("Buscar"), refresh, "primary");
	page.add_button(__("Nuevo presupuesto"), () => openBudgetDialog());

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

	function lineFields() {
		return [
			{
				fieldname: "economic_category",
				label: __("Categoría económica"),
				fieldtype: "Data",
				in_list_view: 1,
				reqd: 1,
			},
			{ fieldname: "cost_center", label: __("Centro de costo"), fieldtype: "Data", in_list_view: 1 },
			{ fieldname: "description", label: __("Descripción"), fieldtype: "Data", in_list_view: 1 },
			{
				fieldname: "approved_hnl",
				label: __("Aprobado HNL"),
				fieldtype: "Currency",
				in_list_view: 1,
				reqd: 1,
			},
		];
	}

	async function refresh() {
		const rows = await call(
			"nexora.budget.service.list_budgets",
			{
				project: controls.project.get_value(),
				status: controls.status.get_value(),
				limit: 100,
			},
			"GET"
		);
		const target = $(page.body).find(".nxr-budget-results").empty();
		if (!rows.length) {
			target.append(
				`<p class="nxr-empty">${__("No hay presupuestos para los filtros indicados.")}</p>`
			);
			return;
		}
		rows.forEach((row) => {
			const button = $(
				`<button class="nxr-ds-btn nxr-ds-btn--secondary nxr-ds-btn--sm nxr-result-row"><strong>${escape(
					row.document_number
				)}</strong> · ${escape(row.title)} · v${escape(row.version)} · ${escape(
					statusLabels[row.status] || row.status
				)} · ${escape(money(row.total_available_hnl))}</button>`
			);
			button.on("click", () => load(row.name));
			target.append(button);
		});
	}

	async function load(budget) {
		const row = await call("nexora.budget.service.get_budget", { budget }, "GET");
		const lineRows = row.lines
			.map(
				(line) => `<tr>
					<td>${escape(line.economic_category)}</td>
					<td>${escape(line.cost_center || "—")}</td>
					<td data-numeric="true">${escape(money(line.approved_hnl))}</td>
					<td data-numeric="true">${escape(money(line.committed_hnl))}</td>
					<td data-numeric="true">${escape(money(line.executed_hnl))}</td>
					<td data-numeric="true">${escape(money(line.available_hnl))}</td>
				</tr>`
			)
			.join("");
		$(page.body).find(".nxr-budget-detail").removeClass("nxr-empty").html(`
			<p><strong>${escape(row.document_number)}</strong> — ${escape(row.title)}</p>
			<p>${__("Estado")}: ${escape(statusLabels[row.status] || row.status)}</p>
			<p>${__("Proyecto")}: ${escape(row.project)}</p>
			<p>${__("Versión")}: ${escape(row.version)}</p>
			<p>${__("Vigente desde")}: ${escape(row.effective_date || "—")}</p>
			<div class="nxr-ds-table-wrap"><table class="nxr-ds-table">
				<thead><tr><th>${__("Categoría")}</th><th>${__("Centro de costo")}</th><th data-numeric="true">${__(
			"Aprobado"
		)}</th><th data-numeric="true">${__("Comprometido")}</th><th data-numeric="true">${__(
			"Ejecutado"
		)}</th><th data-numeric="true">${__("Disponible")}</th></tr></thead>
				<tbody>${lineRows}</tbody>
			</table></div>
			<p><strong>${__("Total disponible")}: ${escape(money(row.total_available_hnl))}</strong></p>
		`);
		renderActions(row);
	}

	function renderActions(row) {
		const target = $(page.body).find(".nxr-budget-actions").empty();
		(transitions[row.status] || []).forEach((status) => {
			const button = $(
				`<button class="nxr-ds-btn nxr-ds-btn--secondary nxr-ds-btn--sm mr-2 mb-2">${escape(
					statusLabels[status] || status
				)}</button>`
			);
			button.on("click", async () => {
				const method = {
					Active: "activate_budget",
					Closed: "close_budget",
					Cancelled: "cancel_budget",
				}[status];
				try {
					await call(`nexora.budget.service.${method}`, { payload: { budget: row.name } });
					frappe.show_alert({ message: __("Estado actualizado"), indicator: "green" });
					await refresh();
					await load(row.name);
				} catch (error) {
					window.nexora.ui.showError(error, { title: __("No se pudo actualizar el presupuesto") });
				}
			});
			target.append(button);
		});
		if (row.status === "Active") {
			const amendButton = $(
				`<button class="nxr-ds-btn nxr-ds-btn--primary nxr-ds-btn--sm mr-2 mb-2">${__(
					"Enmendar"
				)}</button>`
			);
			amendButton.on("click", () => openBudgetDialog(row));
			target.append(amendButton);
		}
		if (!(transitions[row.status] || []).length && row.status !== "Active") {
			target.append(`<p class="nxr-empty">${__("El presupuesto no admite más acciones.")}</p>`);
		}
	}

	function openBudgetDialog(existing) {
		const isAmendment = Boolean(existing);
		const dialog = new frappe.ui.Dialog({
			title: isAmendment
				? __("Enmendar presupuesto {0}", [existing.document_number])
				: __("Nuevo presupuesto"),
			size: "extra-large",
			fields: [
				...(isAmendment
					? []
					: [
							{
								fieldname: "project",
								label: __("Proyecto"),
								fieldtype: "Link",
								options: "Project",
								reqd: 1,
							},
					  ]),
				{ fieldname: "title", label: __("Título"), fieldtype: "Data", default: existing?.title },
				{
					fieldname: "effective_date",
					label: __("Vigente desde"),
					fieldtype: "Date",
					default: frappe.datetime.get_today(),
					reqd: 1,
				},
				{ fieldname: "amendment_deadline", label: __("Plazo de enmienda"), fieldtype: "Date" },
				{
					fieldname: "lines",
					label: __("Líneas"),
					fieldtype: "Table",
					reqd: 1,
					cannot_add_rows: false,
					in_place_edit: true,
					data: isAmendment
						? existing.lines.map((line) => ({
								economic_category: line.economic_category,
								cost_center: line.cost_center,
								description: line.description,
								approved_hnl: line.approved_hnl,
						  }))
						: undefined,
					fields: lineFields(),
				},
			],
			primary_action_label: isAmendment ? __("Enmendar") : __("Crear"),
			primary_action: async () => {
				const values = dialog.get_values();
				if (!values) return;
				try {
					if (isAmendment) {
						const result = await call("nexora.budget.service.amend_budget", {
							payload: { ...values, budget: existing.name, idempotency_key: uuid() },
						});
						dialog.hide();
						frappe.show_alert({
							message: __("Presupuesto enmendado: {0}", [result.new_document_number]),
							indicator: "green",
						});
						await refresh();
						await load(result.new_budget);
					} else {
						const result = await call("nexora.budget.service.create_budget", {
							payload: { ...values, idempotency_key: uuid() },
						});
						dialog.hide();
						frappe.show_alert({
							message: __("Presupuesto {0} creado", [result.document_number]),
							indicator: "green",
						});
						await refresh();
						await load(result.budget);
					}
				} catch (error) {
					window.nexora.ui.showError(error, {
						title: isAmendment
							? __("No se pudo enmendar el presupuesto")
							: __("No se pudo crear el presupuesto"),
					});
				}
			},
		});
		dialog.show();
	}

	refresh();
};
