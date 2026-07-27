// prettier-ignore
frappe.pages["nexora-closing"].on_page_load = function (wrapper) {
	const page = frappe.ui.make_app_page({ parent: wrapper, title: __("Cierre semanal NEXORA"), single_column: true });
	const body = $(page.body);
	const controls = {
		project: page.add_field({ fieldname: "project", label: __("Proyecto"), fieldtype: "Link", options: "Project", change: loadHistory }),
		week_start: page.add_field({ fieldname: "week_start", label: __("Inicio"), fieldtype: "Date", reqd: 1 }),
		week_end: page.add_field({ fieldname: "week_end", label: __("Final"), fieldtype: "Date", reqd: 1 }),
	};
	let calculation = null;
	body.html(`<main class="nxr-product-shell nxr-bi-shell" data-state="ready"><section class="nxr-bi-hero"><div><p class="nxr-eyebrow">CL01 · ${__("CIERRE SEMANAL")}</p><h2>${__("Fotografía financiera inmutable")}</h2><p>${__("Saldos históricos as-of, trazabilidad de 12 dígitos, idempotencia, auditoría y correcciones compensatorias.")}</p></div><div class="nxr-bi-actions"><button class="btn btn-primary btn-sm nxr-calculate">${__("Calcular")}</button><button class="btn btn-default btn-sm nxr-save">${__("Guardar cierre")}</button></div></section><section class="nxr-bi-kpis nxr-close-kpis"></section><section class="nxr-bi-table-card"><header><div><h3>${__("Resumen calculado")}</h3><small class="nxr-close-hash"></small></div></header><div class="nxr-close-summary"></div></section><section class="nxr-bi-table-card"><header><div><h3>${__("Historial de cierres")}</h3><small>${__("Los cierres no se eliminan ni se sobrescriben")}</small></div></header><div class="nxr-close-history"></div></section></main>`);
	page.add_button(__("Actualizar historial"), loadHistory);
	body.on("click", ".nxr-calculate", calculate);
	body.on("click", ".nxr-save", save);
	body.on("click", "[data-correct]", function () { correct($(this).data("correct")); });
	const launchOptions = frappe.route_options || {};
	frappe.route_options = null;
	if (launchOptions.project) controls.project.set_value(launchOptions.project);
	setDefaultWeek();
	loadHistory();

	function payload() { return { project: controls.project.get_value() || null, week_start: controls.week_start.get_value(), week_end: controls.week_end.get_value() }; }
	function setDefaultWeek() { const today = frappe.datetime.get_today(); controls.week_end.set_value(today); controls.week_start.set_value(frappe.datetime.add_days(today, -6)); }
	async function calculate() { validateDates(); const response = await frappe.call({ method: "nexora.close.service.calculate_weekly_close", type: "POST", args: { payload: payload() }, freeze: true, freeze_message: __("Calculando cierre…") }); calculation = response.message || {}; renderCalculation(); }
	async function save() { validateDates(); if (!calculation) await calculate(); const values = await promptValues([{ fieldname: "comments", label: __("Comentarios"), fieldtype: "Small Text" }], __("Guardar cierre semanal")); if (!values) return; const response = await frappe.call({ method: "nexora.close.service.save_weekly_close", type: "POST", args: { payload: { ...payload(), comments: values.comments || "", idempotency_key: `weekly-close-${frappe.session.user}-${Date.now()}` } }, freeze: true, freeze_message: __("Guardando cierre inmutable…") }); frappe.show_alert({ message: __("Cierre {0} guardado.", [response.message?.document_number]), indicator: "green" }); calculation = null; await loadHistory(); }
	async function correct(name) { const values = await promptValues([{ fieldname: "correction_reason", label: __("Motivo de corrección"), fieldtype: "Small Text", reqd: 1 }, { fieldname: "comments", label: __("Comentarios"), fieldtype: "Small Text" }], __("Corrección compensatoria")); if (!values) return; await frappe.call({ method: "nexora.close.service.correct_weekly_close", type: "POST", args: { payload: { ...payload(), weekly_close: name, correction_reason: values.correction_reason, comments: values.comments || "", idempotency_key: `weekly-correction-${name}-${Date.now()}` } }, freeze: true, freeze_message: __("Registrando corrección…") }); frappe.show_alert({ message: __("Corrección registrada."), indicator: "green" }); await loadHistory(); }
	async function loadHistory() {
		const response = await frappe.call({
			method: "nexora.close.service.list_weekly_closes",
			type: "POST",
			args: { payload: { project: controls.project.get_value() || null, page: 1, page_size: 50 } },
		});
		const rows = response.message?.rows || [];
		const rendered = rows.map((row) => [
			`<a href="${frappe.utils.get_form_link("NXR Weekly Close", row.name)}">${escape(row.document_number)}</a>`,
			`${date(row.week_start)} — ${date(row.week_end)}`,
			escape(row.status),
			money(row.received_hnl),
			money(row.spent_hnl),
			money(row.available_hnl),
			`${Number(row.physical_progress || 0).toFixed(1)}%`,
			`<code>${escape(String(row.snapshot_hash || "").slice(0, 12))}</code>`,
			row.status === "Closed" ? `<button class="btn btn-xs btn-default" data-correct="${escape(row.name)}">${__("Corregir")}</button>` : "",
		]);
		body.find(".nxr-close-history").html(
			rows.length
				? table([__("Número"), __("Período"), __("Estado"), __("Recibido"), __("Gastado"), __("Disponible"), __("Avance"), __("Huella"), __("Acción")], rendered)
				: empty(__("No hay cierres guardados."))
		);
	}

	function renderCalculation() { const totals = calculation.totals || {}; const counts = calculation.counts || {}; body.find(".nxr-close-kpis").html([[__("Recibido"), money(totals.received_hnl)], [__("Gastado"), money(totals.spent_hnl)], [__("Pendiente"), money(totals.pending_hnl)], [__("Disponible"), money(totals.available_hnl)], [__("Comprometido"), money(totals.committed_hnl)], [__("Avance"), `${Number(calculation.physical_progress || 0).toFixed(1)}%`]].map((row) => `<article class="nxr-bi-kpi"><span>${escape(row[0])}</span><strong>${row[1]}</strong></article>`).join("")); body.find(".nxr-close-hash").text(`${calculation.engine_version || ""} · ${String(calculation.snapshot_hash || "").slice(0, 20)}`); body.find(".nxr-close-summary").html(table([__("Ingresos"), __("Gastos"), __("Contratos"), __("Sin conciliar"), __("Saldo inicial"), __("Saldo cierre")], [[counts.income_count || 0, counts.expense_count || 0, counts.contract_count || 0, calculation.unreconciled_incomes || 0, money(totals.opening_funds_hnl), money(totals.closing_funds_hnl)]])); }
	function validateDates() { if (!controls.week_start.get_value() || !controls.week_end.get_value()) frappe.throw(__("Seleccione el inicio y el final de la semana.")); }
	function promptValues(fields, title) { return new Promise((resolve) => frappe.prompt(fields, resolve, title)); }
	function table(headers, rows) { return `<div class="table-responsive"><table class="table table-bordered"><thead><tr>${headers.map((header) => `<th>${escape(header)}</th>`).join("")}</tr></thead><tbody>${rows.map((row) => `<tr>${row.map((cell) => `<td>${cell ?? ""}</td>`).join("")}</tr>`).join("")}</tbody></table></div>`; }
	function money(value) { return new Intl.NumberFormat("es-HN", { style: "currency", currency: "HNL", minimumFractionDigits: 2 }).format(Number(value || 0)); }
	function date(value) { return value ? frappe.datetime.str_to_user(String(value).slice(0, 10)) : __("Sin fecha"); }
	function escape(value) { return frappe.utils.escape_html(String(value ?? "")); }
	function empty(message) { return `<p class="nxr-executive-empty">${escape(message)}</p>`; }
};
