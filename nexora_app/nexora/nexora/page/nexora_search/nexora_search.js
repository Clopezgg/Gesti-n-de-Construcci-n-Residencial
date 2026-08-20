frappe.pages["nexora-search"].on_page_load = function (wrapper) {
	const page = frappe.ui.make_app_page({
		parent: wrapper,
		title: __("Buscador universal"),
		single_column: true,
	});
	const ui = window.nexora.ui;
	const controls = {};
	let searchAssistantBusy = false;
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

	async function askAssistant(query) {
		const detail = $(page.body).find(".nxr-search-detail-body").removeClass("nxr-empty");
		detail.html(`<p class="text-muted">${__("Consultando al asistente…")}</p>`);
		try {
			const response = await frappe.call({
				method: "nexora.conversation.dispatch.send_message",
				type: "POST",
				args: { payload: { text: query } },
				freeze: false,
			});
			renderAssistantReply(detail, response.message || {}, query);
		} catch (error) {
			ui.showError(error, {
				title: __("El asistente no pudo responder"),
				fallback: __("No se modificó ningún dato. Revise la conexión o sus permisos."),
			});
			detail.addClass("nxr-empty").text(__("No encontramos resultados con esos datos."));
		}
	}

	function renderAssistantReply(detail, result, query) {
		const openInAssistant = `<p><a href="#" data-search-open-assistant>${__(
			"Continuar esta conversación en el Asistente →"
		)}</a></p>`;
		let actions = "";
		if (result.state === "AwaitingConfirmation" && result.data && result.data.name) {
			actions = `
				<div class="nxr-search-assistant-pending" data-search-pending-intent="${frappe.utils.escape_html(
					result.data.name
				)}">
					<button type="button" class="nxr-ds-btn nxr-ds-btn--primary" data-search-assistant-confirm>${__(
						"Confirmar"
					)}</button>
					<button type="button" class="nxr-ds-btn nxr-ds-btn--secondary" data-search-assistant-cancel>${__(
						"Cancelar"
					)}</button>
				</div>`;
		}
		detail.html(`
			<p class="nxr-assistant-bubble nxr-assistant-bubble--assistant">${frappe.utils.escape_html(
				result.message || __("No entendí qué necesitas.")
			)}</p>
			${actions}
			${openInAssistant}
		`);
		detail.data("search-assistant-query", query);
	}

	$(page.body).on("click", "[data-search-open-assistant]", function (event) {
		event.preventDefault();
		frappe.set_route("nexora-assistant");
	});

	$(page.body).on(
		"click",
		"[data-search-assistant-confirm], [data-search-assistant-cancel]",
		async function () {
			if (searchAssistantBusy) return;
			const button = $(this);
			const pendingBox = button.closest("[data-search-pending-intent]");
			const name = pendingBox.attr("data-search-pending-intent");
			if (!name) return;
			const method = button.is("[data-search-assistant-confirm]")
				? "confirm_pending_intent"
				: "cancel_pending_intent";
			searchAssistantBusy = true;
			pendingBox.find("button").prop("disabled", true);
			try {
				const response = await frappe.call({
					method: `nexora.conversation.dispatch.${method}`,
					type: "POST",
					args: { payload: { pending_intent: name } },
					freeze: false,
				});
				const result = response.message || {};
				pendingBox.replaceWith(
					`<p class="nxr-assistant-bubble nxr-assistant-bubble--assistant">${frappe.utils.escape_html(
						result.message || ""
					)}</p>`
				);
			} catch (error) {
				ui.showError(error, { title: __("No se pudo completar la acción") });
				pendingBox.find("button").prop("disabled", false);
			} finally {
				searchAssistantBusy = false;
			}
		}
	);

	function renderResults(results) {
		const target = $(page.body).find(".nxr-search-results").empty();
		if (!results.length) {
			target.addClass("nxr-empty").text(__("No encontramos resultados con esos datos."));
			void askAssistant(controls.query.get_value());
			return;
		}
		$(page.body)
			.find(".nxr-search-detail-body")
			.addClass("nxr-empty")
			.html(__("Seleccione un resultado para revisar sus datos, efecto financiero y relaciones."));
		target.removeClass("nxr-empty").append(`<div class="nxr-ds-table-wrap"><table class="nxr-ds-table">
			<thead><tr><th>${__("Tipo")}</th><th>${__("Título")}</th><th>${__("Documento")}</th><th>${__(
			"Proyecto"
		)}</th><th>${__("Estado")}</th><th>${__("Acción")}</th></tr></thead><tbody></tbody></table></div>`);
		const body = target.find("tbody");
		results.forEach((row) => {
			const button = `<button type="button" class="nxr-ds-btn nxr-ds-btn--secondary nxr-ds-btn--sm" data-search-doctype="${frappe.utils.escape_html(
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
						ui.label("dimension", effect.dimension)
					)}</td><td>${escape(
						ui.label("effectType", effect.effect_type)
					)}</td><td data-numeric="true">${ui.formatMoney(effect.amount_hnl)}</td></tr>`
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
					  )}</h4><div class="nxr-ds-table-wrap"><table class="nxr-ds-table"><thead><tr><th>${__(
							"Fondo"
					  )}</th><th>${__("Dimensión")}</th><th>${__("Efecto")}</th><th data-numeric="true">${__(
							"Importe"
					  )}</th></tr></thead><tbody>${effects}</tbody></table></div>`
					: ""
			}
			<a class="nxr-ds-btn nxr-ds-btn--primary" href="${frappe.utils.get_form_link(row.doctype, row.name)}">${__(
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
