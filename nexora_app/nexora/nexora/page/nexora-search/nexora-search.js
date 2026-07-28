frappe.pages["nexora-search"].on_page_load = function (wrapper) {
	const page = frappe.ui.make_app_page({
		parent: wrapper,
		title: __("Buscador universal"),
		single_column: true,
	});
	const ui = window.nexora.ui;
	const controls = {};
	const field = (definition) => {
		const control = page.add_field(definition);
		controls[definition.fieldname] = control;
		return control;
	};
	field({
		fieldname: "query",
		label: __("¿Qué desea encontrar?"),
		fieldtype: "Data",
		reqd: 1,
		description: __("Busque por número de documento, nombre, referencia o descripción."),
	});
	field({
		fieldname: "scope",
		label: __("Filtrar por tipo"),
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
			<section class="nxr-card" aria-live="polite">
				<h3>${__("Resultados")}</h3>
				<div class="nxr-search-results nxr-empty">${__("Escriba un término para comenzar.")}</div>
			</section>
		</div>
	`);

	page.add_button(__("Buscar"), search, "primary");

	$(wrapper).on("keydown", (event) => {
		if (event.key === "Enter" && document.activeElement === controls.query.get_input().get(0)) {
			event.preventDefault();
			void search();
		}
	});

	async function search() {
		const query = String(controls.query.get_value() || "").trim();
		if (!query) {
			frappe.msgprint({
				title: __("Falta el término de búsqueda"),
				message: __("Escriba un número, nombre o referencia antes de buscar."),
				indicator: "orange",
			});
			return;
		}
		try {
			const response = await frappe.call({
				method: "nexora.dashboard.service.universal_search",
				type: "POST",
				args: { payload: { query, doctypes: controls.scope.get_value(), limit: 50 } },
				freeze: true,
				freeze_message: __("Buscando documentos y expedientes…"),
			});
			renderResults(response.message || []);
		} catch (error) {
			console.error("NEXORA universal search failed", error);
			ui.showError(error, {
				title: __("No fue posible buscar"),
				fallback: __("No se modificó ningún dato. Revise la conexión o sus permisos e intente nuevamente."),
			});
		}
	}

	function renderResults(results) {
		const target = $(page.body).find(".nxr-search-results").empty();
		if (!results.length) {
			target.addClass("nxr-empty").text(__("No encontramos resultados con esos datos."));
			return;
		}
		target.removeClass("nxr-empty");
		target.append(`<div class="table-responsive"><table class="table table-bordered">
			<thead><tr><th>${__("Tipo")}</th><th>${__("Título")}</th><th>${__("Documento")}</th><th>${__(
			"Estado"
		)}</th></tr></thead>
			<tbody></tbody></table></div>`);
		const body = target.find("tbody");
		results.forEach((row) => {
			const link = frappe.utils.get_form_link(row.doctype, row.name);
			$(`<tr>
				<td>${frappe.utils.escape_html(ui.term(row.label))}</td>
				<td><a href="${link}">${frappe.utils.escape_html(row.title)}</a></td>
				<td>${frappe.utils.escape_html(row.document_number || __("Sin número"))}</td>
				<td>${frappe.utils.escape_html(ui.label("status", row.status))}</td>
			</tr>`).appendTo(body);
		});
	}
};
