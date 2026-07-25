frappe.pages["nexora-reports"].on_page_load = function (wrapper) {
	const page = frappe.ui.make_app_page({
		parent: wrapper,
		title: __("Reportes NEXORA"),
		single_column: true,
	});
	const controls = {};
	const field = (definition) => {
		const control = page.add_field(definition);
		controls[definition.fieldname] = control;
		return control;
	};
	field({
		fieldname: "report_type",
		label: __("Tipo de reporte"),
		fieldtype: "Select",
		options: [
			"Estado de cuenta por fuente",
			"Estado de cuenta por entidad",
			"Estado de cuenta contractual",
			"Reporte financiero",
			"Reporte de costos",
			"Conciliación de totales",
		],
		reqd: 1,
		change: toggleExtraFields,
	});
	field({ fieldname: "project", label: __("Proyecto"), fieldtype: "Link", options: "Project" });
	field({ fieldname: "source", label: __("Fuente"), fieldtype: "Link", options: "NXR Fund Source" });
	field({ fieldname: "entity", label: __("Entidad"), fieldtype: "Link", options: "NXR Entity" });
	field({ fieldname: "contract", label: __("Contrato"), fieldtype: "Link", options: "NXR Contract" });

	$(page.body).append(`
		<div class="nxr-reports-grid">
			<section class="nxr-card">
				<h3>${__("Resultados")}</h3>
				<div class="nxr-report-result nxr-empty">${__(
					"Seleccione tipo de reporte y filtros, luego presione Generar."
				)}</div>
			</section>
		</div>
	`);

	page.add_button(__("Generar reporte"), generate, "primary");

	function toggleExtraFields() {
		const type = controls.report_type.get_value();
		$(controls.source.input_area).toggle(type === "Estado de cuenta por fuente");
		$(controls.entity.input_area).toggle(
			type === "Estado de cuenta por entidad" || type === "Conciliación de totales"
		);
		$(controls.contract.input_area).toggle(type === "Estado de cuenta contractual");
	}

	function payload() {
		return Object.fromEntries(
			Object.entries(controls).map(([name, control]) => [name, control.get_value()])
		);
	}

	async function generate() {
		const type = controls.report_type.get_value();
		const methodMap = {
			"Estado de cuenta por fuente": "nexora.reports.service.get_source_statement",
			"Estado de cuenta por entidad": "nexora.reports.service.get_entity_statement",
			"Estado de cuenta contractual": "nexora.reports.service.get_contract_statement",
			"Reporte financiero": "nexora.reports.service.get_financial_report",
			"Reporte de costos": "nexora.reports.service.get_cost_report",
			"Conciliación de totales": "nexora.reports.service.reconcile_totals",
		};
		const method = methodMap[type];
		if (!method) return;
		const response = await frappe.call({
			method,
			type: "POST",
			args: { payload },
			freeze: true,
			freeze_message: __("Generando reporte…"),
		});
		const result = response.message || {};
		render(type, result);
	}

	function render(type, data) {
		const target = $(page.body).find(".nxr-report-result").removeClass("nxr-empty").empty();
		if (type === "Estado de cuenta por fuente") {
			renderRows(target, data, "source");
		} else if (type === "Estado de cuenta por entidad") {
			renderRows(target, data, "entity");
		} else if (type === "Estado de cuenta contractual") {
			renderRows(target, data, "contract");
		} else if (type === "Reporte financiero") {
			renderFinancial(target, data);
		} else if (type === "Reporte de costos") {
			renderCosts(target, data);
		} else if (type === "Conciliación de totales") {
			renderReconciliation(target, data);
		}
	}

	function renderRows(target, data, labelKey) {
		const label = data[labelKey] || "";
		const totals = data.totals || {};
		const rows = data.rows || [];
		target.append(`
			<p><strong>${__(labelKey.charAt(0).toUpperCase() + labelKey.slice(1))}:</strong> ${frappe.utils.escape_html(
			label
		)}</p>
			<p><strong>${__("Total ingresos")}:</strong> ${frappe.format(totals.total_inflows || 0, {
			fieldtype: "Currency",
		})}</p>
			<p><strong>${__("Total egresos")}:</strong> ${frappe.format(totals.total_outflows || 0, {
			fieldtype: "Currency",
		})}</p>
			<p><strong>${__("Flujo neto")}:</strong> ${frappe.format(totals.net_flow || 0, { fieldtype: "Currency" })}</p>
			<p><strong>${__("Operaciones")}:</strong> ${totals.operation_count || 0}</p>
		`);
		if (!rows.length) {
			target.append(`<p class="text-muted">${__("Sin operaciones.")}</p>`);
			return;
		}
		target.append(`<div class="table-responsive"><table class="table table-bordered">
			<thead><tr><th>${__("Número")}</th><th>${__("Fecha")}</th><th>${__("Tipo")}</th><th>${__(
			"Importe"
		)}</th><th>${__("Saldo corrido")}</th><th>${__("Estado")}</th></tr></thead>
			<tbody></tbody></table></div>`);
		const body = target.find("tbody");
		rows.forEach((row) => {
			$(`<tr>
				<td>${frappe.utils.escape_html(row.document_number || row.name || "")}</td>
				<td>${frappe.utils.escape_html(String(row.date || "").slice(0, 10))}</td>
				<td>${frappe.utils.escape_html(row.operation_type)}</td>
				<td>${frappe.format(row.amount_hnl || 0, { fieldtype: "Currency" })}</td>
				<td>${frappe.format(row.running_balance || 0, { fieldtype: "Currency" })}</td>
				<td>${frappe.utils.escape_html(row.status)}</td>
			</tr>`).appendTo(body);
		});
	}

	function renderFinancial(target, data) {
		const b = data.budgets || {};
		const c = data.commitments || {};
		target.append(`
			<h4>${__("Presupuestos activos")}</h4>
			<p>${__("Cantidad")}: ${b.active_count || 0}</p>
			<p>${__("Aprobado")}: ${frappe.format(b.total_approved_hnl || 0, { fieldtype: "Currency" })}</p>
			<p>${__("Comprometido")}: ${frappe.format(b.total_committed_hnl || 0, { fieldtype: "Currency" })}</p>
			<p>${__("Ejecutado")}: ${frappe.format(b.total_executed_hnl || 0, { fieldtype: "Currency" })}</p>
			<p>${__("Disponible")}: ${frappe.format(b.total_available_hnl || 0, { fieldtype: "Currency" })}</p>
			<h4>${__("Compromisos")}</h4>
			<p>${__("Cantidad")}: ${c.count || 0}</p>
			<p>${__("Total")}: ${frappe.format(c.total_amount_hnl || 0, { fieldtype: "Currency" })}</p>
			<h4>${__("Operaciones")}</h4>
			<p>${__("Cantidad")}: ${data.operations?.count || 0}</p>
		`);
	}

	function renderCosts(target, data) {
		const categories = data.categories || {};
		const total = data.total || 0;
		if (!Object.keys(categories).length) {
			target.append(`<p class="text-muted">${__("Sin datos de costos.")}</p>`);
			return;
		}
		target.append(`<div class="table-responsive"><table class="table table-bordered">
			<thead><tr><th>${__("Categoría")}</th><th class="text-right">${__("Total")}</th><th class="text-right">${__(
			"%"
		)}</th></tr></thead>
			<tbody></tbody></table></div>`);
		const body = target.find("tbody");
		Object.entries(categories).forEach(([cat, amount]) => {
			const pct = total > 0 ? ((amount / total) * 100).toFixed(1) : "0.0";
			$(`<tr>
				<td>${frappe.utils.escape_html(cat)}</td>
				<td class="text-right">${frappe.format(amount, { fieldtype: "Currency" })}</td>
				<td class="text-right">${pct}%</td>
			</tr>`).appendTo(body);
		});
	}

	function renderReconciliation(target, data) {
		target.append(`
			<p><strong>${__("Ingresos")}:</strong> ${frappe.format(data.inflows || 0, { fieldtype: "Currency" })}</p>
			<p><strong>${__("Egresos")}:</strong> ${frappe.format(data.outflows || 0, { fieldtype: "Currency" })}</p>
			<p><strong>${__("Neto")}:</strong> ${frappe.format(data.net || 0, { fieldtype: "Currency" })}</p>
			<p><strong>${__("Operaciones")}:</strong> ${data.operation_count || 0}</p>
		`);
	}
};
