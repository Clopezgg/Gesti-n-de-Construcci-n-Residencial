frappe.pages["nexora-search"].on_page_load = function (wrapper) {
	const page = frappe.ui.make_app_page({
		parent: wrapper,
		title: __("Buscador universal"),
		single_column: true,
	});
	const controls = {};
	const field = (definition) => {
		const control = page.add_field(definition);
		controls[definition.fieldname] = control;
		return control;
	};
	field({
		fieldname: "query",
		label: __("Buscar"),
		fieldtype: "Data",
		reqd: 1,
	});
	field({
		fieldname: "scope",
		label: __("Ámbito"),
		fieldtype: "Select",
		options: [
			"",
			"Entidad",
			"Contrato",
			"Perfil de contratista",
			"Perfil de proveedor",
			"Solicitud de compra",
			"Orden de compra",
			"Recepción",
			"Presupuesto",
			"Operación",
			"Compromiso",
			"Evidencia",
			"Fuente de fondos",
			"Movimiento de inventario",
		],
	});

	$(page.body).append(`
		<div class="nxr-search-grid">
			<section class="nxr-card">
				<h3>${__("Resultados")}</h3>
				<div class="nxr-search-results nxr-empty">${__("Ingrese un término de búsqueda.")}</div>
			</section>
		</div>
	`);

	page.add_button(__("Buscar"), search, "primary");

	$(wrapper).on("keydown", (e) => {
		if (e.key === "Enter" && document.activeElement === controls.query.get_input().get(0)) {
			search();
		}
	});

	async function search() {
		const query = controls.query.get_value();
		if (!query) return;
		const response = await frappe.call({
			method: "nexora.dashboard.service.universal_search",
			type: "POST",
			args: { payload: { query, doctypes: controls.scope.get_value(), limit: 50 } },
			freeze: true,
			freeze_message: __("Buscando…"),
		});
		const results = response.message || [];
		const target = $(page.body).find(".nxr-search-results").empty();
		if (!results.length) {
			target.addClass("nxr-empty").text(__("Sin resultados."));
			return;
		}
		target.removeClass("nxr-empty");
		target.append(`<div class="table-responsive"><table class="table table-bordered">
			<thead><tr><th>${__("Tipo")}</th><th>${__("Título")}</th><th>${__("Número")}</th><th>${__(
			"Estado"
		)}</th></tr></thead>
			<tbody></tbody></table></div>`);
		const body = target.find("tbody");
		results.forEach((row) => {
			const link = frappe.utils.get_form_link(row.doctype, row.name);
			$(`<tr>
				<td>${frappe.utils.escape_html(row.label)}</td>
				<td><a href="${link}">${frappe.utils.escape_html(row.title)}</a></td>
				<td>${frappe.utils.escape_html(row.document_number)}</td>
				<td>${frappe.utils.escape_html(row.status)}</td>
			</tr>`).appendTo(body);
		});
	}
};
