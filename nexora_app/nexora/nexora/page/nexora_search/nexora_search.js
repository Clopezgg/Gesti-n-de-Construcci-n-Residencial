frappe.pages["nexora-search"].on_page_load = function (wrapper) {
	const page = frappe.ui.make_app_page({
		parent: wrapper,
		title: __("Buscador universal"),
		single_column: true,
	});
	const ui = window.nexora.ui;
	const controls = {};
	const field = (definition) => (controls[definition.fieldname] = page.add_field(definition));

	field({
		fieldname: "query",
		label: __("¿Qué desea encontrar?"),
		fieldtype: "Data",
		reqd: 1,
		description: __(
			"Busque por documento de 12 dígitos, nombre, cuenta, referencia, remitente o beneficiario."
		),
	});
	field({
		fieldname: "scope",
		label: __("Filtrar por tipo"),
		fieldtype: "Select",
		options: [
			"",
			"Movimiento",
			"Fondo",
			"Proyecto",
			"Cuenta guardada",
			"Entidad",
			"Contrato",
			"Perfil de contratista",
			"Perfil de proveedor",
			"Solicitud de compra",
			"Orden de compra",
			"Recepción",
			"Presupuesto",
			"Compromiso",
			"Comprobante",
			"Movimiento de inventario",
		],
	});

	$(page.body).append(`
		<div class="nxr-search-grid">
			<section class="nxr-card" aria-live="polite"><h3>${__(
				"Resultados"
			)}</h3><div class="nxr-search-results nxr-empty">${__(
		"Escriba un término para comenzar."
	)}</div></section>
			<section class="nxr-card nxr-search-detail" aria-live="polite"><h3>${__(
				"Vista consolidada"
			)}</h3><div class="nxr-search-detail-body nxr-empty">${__(
		"Seleccione un resultado para revisar sus datos, efecto financiero y relaciones."
	)}</div></section>
		</div>`);

	page.add_button(__("Buscar"), search, "primary");
	$(wrapper).on("keydown", (event) => {
		// `get_input()` no existe en los controles de Frappe: la excepción rompía el
		// manejador y la búsqueda con Enter nunca llegaba a lanzarse.
		if (event.key === "Enter" && document.activeElement === controls.query.$input?.get(0)) {
			event.preventDefault();
			void search();
		}
	});

	async function search() {
		const query = String(controls.query.get_value() || "").trim();
		if (!query) {
			frappe.msgprint({
				title: __("Falta el término de búsqueda"),
				message: __("Escriba un número, nombre, cuenta o referencia antes de buscar."),
				indicator: "orange",
			});
			return;
		}
		try {
			const response = await frappe.call({
				method: "nexora.boot.universal_search_consolidated",
				type: "POST",
				args: { payload: { query, doctypes: controls.scope.get_value(), limit: 50 } },
				freeze: true,
				freeze_message: __("Buscando documentos y relaciones autorizadas…"),
			});
			renderResults(response.message || []);
		} catch (error) {
			ui.showError(error, {
				title: __("No fue posible buscar"),
				fallback: __("No se modificó ningún dato. Revise la conexión o sus permisos."),
			});
		}
	}

	function renderResults(results) {
		const target = $(page.body).find(".nxr-search-results").empty();
		if (!results.length) {
			target.addClass("nxr-empty").text(__("No encontramos resultados con esos datos."));
			return;
		}
		target.removeClass("nxr-empty")
			.append(`<div class="table-responsive"><table class="table table-bordered">
			<thead><tr><th>${__("Tipo")}</th><th>${__("Título")}</th><th>${__("Documento")}</th><th>${__(
			"Proyecto"
		)}</th><th>${__("Estado")}</th><th>${__("Acción")}</th></tr></thead><tbody></tbody></table></div>`);
		const body = target.find("tbody");
		results.forEach((row) => {
			const button = `<button type="button" class="btn btn-xs btn-default" data-search-doctype="${frappe.utils.escape_html(
				row.doctype
			)}" data-search-name="${frappe.utils.escape_html(row.name)}">${__("Ver consolidado")}</button>`;
			$(
				`<tr><td>${frappe.utils.escape_html(
					ui.term(row.label)
				)}</td><td><a href="${frappe.utils.get_form_link(
					row.doctype,
					row.name
				)}">${frappe.utils.escape_html(row.title)}</a></td><td>${frappe.utils.escape_html(
					row.document_number || __("Sin número")
				)}</td><td>${frappe.utils.escape_html(
					row.project || __("Sin proyecto")
				)}</td><td>${frappe.utils.escape_html(
					ui.label("status", row.status)
				)}</td><td>${button}</td></tr>`
			).appendTo(body);
		});
	}

	$(page.body).on("click", "[data-search-doctype]", async function () {
		const button = $(this);
		button.prop("disabled", true).attr("aria-busy", "true");
		try {
			const response = await frappe.call({
				method: "nexora.boot.get_search_result_detail",
				type: "POST",
				args: {
					payload: { doctype: button.data("search-doctype"), name: button.data("search-name") },
				},
			});
			renderDetail(response.message || {});
		} catch (error) {
			ui.showError(error, { title: __("No fue posible abrir el consolidado") });
		} finally {
			button.prop("disabled", false).removeAttr("aria-busy");
		}
	});

	function renderDetail(row) {
		const effects = (row.effects || [])
			.map(
				(effect) =>
					`<tr><td>${escape(effect.fund_source)}</td><td>${escape(
						effect.dimension
					)}</td><td>${escape(effect.effect_type)}</td><td class="text-right">${ui.formatMoney(
						effect.amount_hnl
					)}</td></tr>`
			)
			.join("");
		const relationships = Object.entries(row.relationships || {})
			.filter(([, value]) => value)
			.map(
				([key, value]) =>
					`<li><strong>${escape(key.replaceAll("_", " "))}:</strong> ${escape(value)}</li>`
			)
			.join("");
		$(page.body).find(".nxr-search-detail-body").removeClass("nxr-empty").html(`
			<div class="nxr-preview-summary">
				<span><small>${__("Documento")}</small><strong>${escape(row.document_number || row.title)}</strong></span>
				<span><small>${__("Fecha")}</small><strong>${escape(formatDate(row.date))}</strong></span>
				<span><small>${__("Contraparte")}</small><strong>${escape(
			row.counterparty || __("Sin contraparte")
		)}</strong></span>
				<span><small>${__("Importe")}</small><strong>${
			row.amount_hnl == null ? __("No aplica") : ui.formatMoney(row.amount_hnl, row.currency || "HNL")
		}</strong></span>
			</div>
			<p><strong>${__("Proyecto")}:</strong> ${escape(row.project || __("Sin proyecto"))}</p>
			<p><strong>${__("Referencia")}:</strong> ${escape(row.reference || __("Sin referencia"))}</p>
			<p><strong>${__("Cuenta")}:</strong> ${escape(row.account || __("Sin cuenta"))}</p>
			<p><strong>${__("Comprobante")}:</strong> ${
			row.evidence
				? `<a href="${escape(row.evidence)}" target="_blank" rel="noopener">${__(
						"Abrir comprobante"
				  )}</a>`
				: __("Sin comprobante")
		}</p>
			${relationships ? `<h4>${__("Relaciones e historial")}</h4><ul>${relationships}</ul>` : ""}
			${
				effects
					? `<h4>${__(
							"Efecto financiero"
					  )}</h4><div class="table-responsive"><table class="table table-bordered"><thead><tr><th>${__(
							"Fondo"
					  )}</th><th>${__("Dimensión")}</th><th>${__("Efecto")}</th><th class="text-right">${__(
							"Importe"
					  )}</th></tr></thead><tbody>${effects}</tbody></table></div>`
					: ""
			}
			<a class="btn btn-primary" href="${frappe.utils.get_form_link(row.doctype, row.name)}">${__(
			"Abrir documento"
		)}</a>`);
	}

	function formatDate(value) {
		return window.nexora.ui.formatDate(value);
	}
	function escape(value) {
		return window.nexora.ui.escapeHtml(value);
	}
};
