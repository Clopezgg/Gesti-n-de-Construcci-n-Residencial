// prettier-ignore
frappe.pages["nexora-closing"].on_page_load = function (wrapper) {
	const page = frappe.ui.make_app_page({ parent: wrapper, title: __("Cierres NEXORA"), single_column: true });
	const body = $(page.body);
	let calculation = null;
	let historyRows = new Map();
	let monthlyHistoryRows = new Map();
	let suppressReload = false;
	let releaseContext = null;
	const lastValues = { project: "", week_start: "", week_end: "" };
	const controls = {
		project: page.add_field({ fieldname: "project", label: __("Proyecto"), fieldtype: "Link", options: "Project", change: () => { if (fieldChanged("project")) contextChanged(); } }),
		week_start: page.add_field({ fieldname: "week_start", label: __("Inicio"), fieldtype: "Date", reqd: 1, change: () => { if (fieldChanged("week_start")) calculationChanged("field:week_start"); } }),
		week_end: page.add_field({ fieldname: "week_end", label: __("Final"), fieldtype: "Date", reqd: 1, change: () => { if (fieldChanged("week_end")) calculationChanged("field:week_end"); } }),
		close_month: page.add_field({ fieldname: "close_month", label: __("Mes de cierre (AAAA-MM)"), fieldtype: "Data", default: frappe.datetime.get_today().slice(0, 7) }),
	};

	// Los controles de Frappe emiten `change` también al perder el foco, con el mismo
	// valor de siempre. Pulsar «Calcular» quita el foco del proyecto: el cálculo recién
	// pedido se descartaba solo. Un cálculo se descarta cuando cambia un dato que lo
	// alimenta, no cuando el usuario pasa por encima del campo.
	function fieldChanged(fieldname) {
		const current = String(controls[fieldname]?.get_value() ?? "");
		if (lastValues[fieldname] === current) return false;
		lastValues[fieldname] = current;
		return true;
	}

	body.html(`<main class="nxr-product-shell nxr-bi-shell nxr-closing-shell" data-state="loading" aria-busy="true"><section class="nxr-bi-hero"><div><p class="nxr-eyebrow">CL01 · ${__("CIERRE SEMANAL")}</p><h2>${__("Fotografía financiera inmutable")}</h2><p>${__("Saldos históricos as-of, trazabilidad de 12 dígitos, idempotencia, auditoría y correcciones compensatorias.")}</p></div><div class="nxr-bi-actions"><button class="nxr-ds-btn nxr-ds-btn--primary nxr-ds-btn--sm nxr-calculate">${__("Calcular")}</button><button class="nxr-ds-btn nxr-ds-btn--secondary nxr-ds-btn--sm nxr-save">${__("Guardar cierre")}</button></div></section><section class="nxr-close-notice"></section><section class="nxr-bi-kpis nxr-close-kpis"></section><section class="nxr-ds-card nxr-bi-table-card"><header><div><h3>${__("Resumen calculado")}</h3><small class="nxr-close-hash"></small></div></header><div class="nxr-close-summary"></div></section><section class="nxr-ds-card nxr-bi-table-card"><header><div><h3>${__("Historial de cierres semanales")}</h3><small>${__("Los cierres no se eliminan ni se sobrescriben")}</small></div></header><div class="nxr-close-history"></div></section><section class="nxr-bi-hero"><div><p class="nxr-eyebrow">CIE-M · ${__("CIERRE MENSUAL")}</p><h2>${__("Cierre mensual con aprobación")}</h2><p>${__("Crear un cierre calcula y guarda la fotografía del mes de inmediato — no hay una vista previa separada. Solo un cierre Aprobado puede corregirse.")}</p></div><div class="nxr-bi-actions"><button class="nxr-ds-btn nxr-ds-btn--primary nxr-ds-btn--sm nxr-monthly-create">${__("Crear cierre mensual")}</button></div></section><section class="nxr-ds-card nxr-bi-table-card"><header><div><h3>${__("Historial de cierres mensuales")}</h3></div></header><div class="nxr-monthly-history"></div></section></main>`);
	page.add_button(__("Actualizar historial"), () => { loadHistory(true); loadMonthlyHistory(true); });
	body.on("click", ".nxr-calculate", calculate);
	body.on("click", ".nxr-save", save);
	body.on("click", "[data-correct]", function () { correct(String($(this).data("correct"))); });
	body.on("click", ".nxr-monthly-create", monthlyCreate);
	body.on("click", "[data-monthly-transition]", function () { monthlyTransition(String($(this).data("monthly-transition")), String($(this).data("status"))); });
	body.on("click", "[data-monthly-correct]", function () { monthlyCorrect(String($(this).data("monthly-correct"))); });
	$(wrapper).on("remove", () => releaseContext?.());
	initialize().catch((error) => console.error("NEXORA closing failed to adopt the active project", error));

	// El proyecto llega por la ruta si se navegó desde otra pantalla; si no, se hereda
	// del contexto activo en lugar de pedirlo otra vez.
	async function initialize() {
		const launchOptions = frappe.route_options || {};
		frappe.route_options = null;
		suppressReload = true;
		try {
			const today = frappe.datetime.get_today();
			await controls.week_end.set_value(today);
			await controls.week_start.set_value(frappe.datetime.add_days(today, -6));
			const launchProject = launchOptions.project || (await window.nexora.context?.activeProject?.()) || null;
			if (launchProject) await controls.project.set_value(launchProject);
		} finally {
			suppressReload = false;
		}
		if (requiresProjectSelection() && !controls.project.get_value()) renderProjectPrompt();
		else { await loadHistory(false); await loadMonthlyHistory(false); }
		releaseContext = window.nexora.context?.onContextChange?.(async (context) => {
			// Bloque 108: mismo defecto real corregido en `nexora_operations.js` (Bloque
			// 107) — Frappe no destruye de forma fiable el wrapper al navegar, así que
			// este suscriptor puede seguir vivo después de que el usuario se fue.
			if ((frappe.get_route ? frappe.get_route() : [])[0] !== "nexora-closing") return;
			const desired = context?.project || "";
			if ((controls.project.get_value() || "") === desired) return;
			suppressReload = true;
			try {
				await controls.project.set_value(desired);
			} finally {
				suppressReload = false;
			}
			calculationChanged("context:external");
			if (requiresProjectSelection() && !controls.project.get_value()) renderProjectPrompt();
			else { await loadHistory(false); await loadMonthlyHistory(false); }
		});
	}

	function requiresProjectSelection() {
		return frappe.user.has_role("NEXORA Project Viewer") && !["System Manager", "NEXORA Administrator", "NEXORA Finance Manager", "NEXORA Finance Operator", "NEXORA Auditor"].some((role) => frappe.user.has_role(role));
	}

	function contextChanged() {
		calculationChanged("field:project");
		if (suppressReload) return;
		// El proyecto elegido aquí pasa a ser el contexto activo: la barra global y el
		// resto de módulos no pueden quedar contradiciendo esta pantalla.
		Promise.resolve(window.nexora.context?.setActiveProject?.(controls.project.get_value() || null)).catch(
			(error) => console.error("NEXORA closing failed to publish the active project", error)
		);
		if (requiresProjectSelection() && !controls.project.get_value()) renderProjectPrompt();
		else { void loadHistory(false); void loadMonthlyHistory(false); }
	}

	// El motivo queda escrito en la pantalla: cuando un cálculo desaparece, el diagnóstico
	// tiene que decir quién lo borró en vez de dejar una tarjeta vacía sin explicación.
	function calculationChanged(reason = "unknown") {
		calculation = null;
		body.find(".nxr-closing-shell").attr("data-calculation-cleared-by", reason);
		body.find(".nxr-close-kpis").empty();
		body.find(".nxr-close-hash").empty();
		body.find(".nxr-close-summary").html(empty(__("Calcule nuevamente para este proyecto y período.")));
	}

	function payload(overrides = {}) {
		return {
			project: controls.project.get_value() || null,
			week_start: controls.week_start.get_value(),
			week_end: controls.week_end.get_value(),
			...overrides,
		};
	}

	function validateContext(values = payload()) {
		if (requiresProjectSelection() && !values.project) frappe.throw(__("Seleccione un proyecto autorizado para continuar."));
		if (!values.week_start || !values.week_end) frappe.throw(__("Seleccione el inicio y el final de la semana."));
		if (String(values.week_end) < String(values.week_start)) frappe.throw(__("La semana termina antes de su fecha inicial."));
		return values;
	}

	async function calculate() {
		const values = validateContext();
		setState("loading");
		try {
			const response = await frappe.call({ method: "nexora.close.service.calculate_weekly_close", type: "POST", args: { payload: values }, freeze: true, freeze_message: __("Calculando cierre…") });
			calculation = response.message || {};
			renderCalculation();
			setState("ready");
			return true;
		} catch (error) {
			console.error("NEXORA weekly close calculation failed", error);
			setState("error");
			window.nexora.ui.showError(error, {
				title: __("No fue posible calcular el cierre"),
				fallback: __("Revise el período, el proyecto y sus permisos."),
			});
			return false;
		}
	}

	async function save() {
		const values = validateContext();
		if (!calculation && !(await calculate())) return;
		const comments = await promptValues([{ fieldname: "comments", label: __("Comentarios"), fieldtype: "Small Text" }], __("Guardar cierre semanal"));
		if (!comments) return;
		try {
			const response = await frappe.call({ method: "nexora.close.service.save_weekly_close", type: "POST", args: { payload: { ...values, comments: comments.comments || "", idempotency_key: `weekly-close-${frappe.session.user}-${Date.now()}` } }, freeze: true, freeze_message: __("Guardando cierre inmutable…") });
			frappe.show_alert({ message: __("Cierre {0} guardado.", [response.message?.document_number]), indicator: "green" });
			calculationChanged("saved");
			await loadHistory(false);
		} catch (error) {
			console.error("NEXORA weekly close save failed", error);
			window.nexora.ui.showError(error, {
				title: __("No fue posible guardar el cierre"),
				fallback: __("El período puede estar cerrado o sus permisos pueden haber cambiado."),
			});
		}
	}

	async function correct(name) {
		const row = historyRows.get(name);
		if (!row) { frappe.msgprint(__("El cierre seleccionado ya no está disponible. Actualice el historial.")); return; }
		const values = await promptValues([{ fieldname: "correction_reason", label: __("Motivo de corrección"), fieldtype: "Small Text", reqd: 1 }, { fieldname: "comments", label: __("Comentarios"), fieldtype: "Small Text" }], __("Corrección compensatoria"));
		if (!values) return;
		const reason = String(values.correction_reason || "").trim();
		if (reason.length < 10) { frappe.msgprint(__("Explique la corrección con al menos 10 caracteres.")); return; }
		const correctionPayload = validateContext({ project: row.project || null, week_start: row.week_start, week_end: row.week_end });
		try {
			await frappe.call({ method: "nexora.close.service.correct_weekly_close", type: "POST", args: { payload: { ...correctionPayload, weekly_close: name, correction_reason: reason, comments: values.comments || "", idempotency_key: `weekly-correction-${name}-${Date.now()}` } }, freeze: true, freeze_message: __("Registrando corrección…") });
			frappe.show_alert({ message: __("Corrección registrada sin sobrescribir el cierre original."), indicator: "green" });
			await loadHistory(false);
		} catch (error) {
			console.error("NEXORA weekly close correction failed", error);
			window.nexora.ui.showError(error, {
				title: __("No fue posible registrar la corrección"),
				fallback: __("Revise el cierre original, el motivo y sus permisos."),
			});
		}
	}

	async function loadHistory(freeze) {
		if (requiresProjectSelection() && !controls.project.get_value()) { renderProjectPrompt(); return; }
		setState("loading");
		try {
			const response = await frappe.call({ method: "nexora.close.service.list_weekly_closes", type: "POST", args: { payload: { project: controls.project.get_value() || null, page: 1, page_size: 50 } }, freeze: Boolean(freeze), freeze_message: __("Actualizando historial…") });
			const rows = response.message?.rows || [];
			historyRows = new Map(rows.map((row) => [String(row.name), row]));
			const rendered = rows.map((row) => [`<a href="${frappe.utils.get_form_link("NXR Weekly Close", row.name)}">${escape(row.document_number)}</a>`, `${date(row.week_start)} — ${date(row.week_end)}`, status(row.status), money(row.received_hnl), money(row.spent_hnl), money(row.available_hnl), `${Number(row.physical_progress || 0).toFixed(1)}%`, `<code>${escape(String(row.snapshot_hash || "").slice(0, 12))}</code>`, row.status === "Closed" ? `<button class="nxr-ds-btn nxr-ds-btn--secondary nxr-ds-btn--sm" data-correct="${escape(row.name)}">${__("Corregir")}</button>` : ""]);
			body.find(".nxr-close-history").html(rows.length ? table([__("Número"), __("Período"), __("Estado"), __("Recibido"), __("Gastado"), __("Disponible"), __("Avance"), __("Huella"), __("Acción")], rendered) : empty(__("No hay cierres guardados.")));
			body.find(".nxr-close-notice").empty();
			setState("ready");
		} catch (error) {
			console.error("NEXORA weekly close history failed", error);
			historyRows = new Map();
			body.find(".nxr-close-history").html(empty(__("No fue posible cargar el historial.")));
			setState("error");
		}
	}

	function renderProjectPrompt() {
		historyRows = new Map();
		monthlyHistoryRows = new Map();
		body.find(".nxr-close-notice").html(`<article class="nxr-executive-alert" data-level="info"><i></i><span><strong>${__("Proyecto requerido")}</strong><small>${__("Seleccione un proyecto autorizado para calcular y consultar cierres.")}</small></span></article>`);
		body.find(".nxr-close-history").html(empty(__("Seleccione un proyecto.")));
		body.find(".nxr-monthly-history").html(empty(__("Seleccione un proyecto.")));
		setState("ready");
	}

	// Cierre mensual (`nexora.close.service.*` → redirigido en tiempo de ejecución a
	// `nexora.close.monthly_canonical`, ver `hooks.py::override_whitelisted_methods`).
	// A diferencia del cierre semanal, no hay una vista previa separada: crear el
	// cierre calcula la fotografía real (misma fuente que el dashboard ejecutivo,
	// `get_executive_snapshot`) y la guarda de inmediato como Borrador. Solo un
	// cierre Aprobado admite corrección; ningún estado terminal (Aprobado/Cancelado)
	// puede transicionarse de nuevo.
	async function monthlyCreate() {
		const closeMonth = String(controls.close_month.get_value() || "").trim();
		if (!/^\d{4}-\d{2}$/.test(closeMonth)) { frappe.throw(__("El mes de cierre debe tener formato AAAA-MM.")); return; }
		if (requiresProjectSelection() && !controls.project.get_value()) { frappe.throw(__("Seleccione un proyecto autorizado.")); return; }
		const values = await promptValues([{ fieldname: "comments", label: __("Comentarios"), fieldtype: "Small Text" }], __("Crear cierre mensual"));
		if (!values) return;
		try {
			const response = await frappe.call({ method: "nexora.close.service.create_monthly_close", type: "POST", args: { payload: { project: controls.project.get_value() || null, close_month: closeMonth, comments: values.comments || "", idempotency_key: `monthly-close-${frappe.session.user}-${closeMonth}-${Date.now()}` } }, freeze: true, freeze_message: __("Calculando y guardando cierre mensual…") });
			frappe.show_alert({ message: __("Cierre mensual {0} creado.", [response.message?.document_number]), indicator: "green" });
			await loadMonthlyHistory(false);
		} catch (error) {
			console.error("NEXORA monthly close create failed", error);
			window.nexora.ui.showError(error, {
				title: __("No fue posible crear el cierre mensual"),
				fallback: __("Revise el proyecto, el período y sus permisos — puede que ya exista un cierre aprobado para ese mes."),
			});
		}
	}

	async function monthlyTransition(name, targetStatus) {
		// `monthly_canonical.transition_monthly_close` no lee ni guarda un motivo —
		// a diferencia de compras/inventario, la cancelación mensual no lo exige.
		// Se confirma la acción, sin pedir un dato que el servidor descartaría.
		const confirmed = await new Promise((resolve) => frappe.confirm(__("¿Cambiar el cierre mensual a {0}?", [monthlyStatus(targetStatus)]), () => resolve(true), () => resolve(false)));
		if (!confirmed) return;
		try {
			const response = await frappe.call({ method: "nexora.close.service.transition_monthly_close", type: "POST", args: { payload: { monthly_close: name, status: targetStatus } }, freeze: true, freeze_message: __("Actualizando cierre mensual…") });
			frappe.show_alert({ message: __("Cierre mensual actualizado a {0}.", [monthlyStatus(response.message?.status)]), indicator: "green" });
			await loadMonthlyHistory(false);
		} catch (error) {
			console.error("NEXORA monthly close transition failed", error);
			window.nexora.ui.showError(error, {
				title: __("No fue posible actualizar el cierre mensual"),
				fallback: __("Si el destino es Aprobado, la fotografía pudo cambiar desde que se creó: genere un nuevo cierre."),
			});
		}
	}

	async function monthlyCorrect(name) {
		const row = monthlyHistoryRows.get(name);
		if (!row) { frappe.msgprint(__("El cierre seleccionado ya no está disponible. Actualice el historial.")); return; }
		const values = await promptValues([{ fieldname: "correction_reason", label: __("Motivo de corrección"), fieldtype: "Small Text", reqd: 1 }, { fieldname: "comments", label: __("Comentarios"), fieldtype: "Small Text" }], __("Corrección de cierre mensual"));
		if (!values) return;
		const reason = String(values.correction_reason || "").trim();
		if (reason.length < 10) { frappe.msgprint(__("Explique la corrección con al menos 10 caracteres.")); return; }
		try {
			await frappe.call({ method: "nexora.close.service.correct_monthly_close", type: "POST", args: { payload: { monthly_close: name, correction_reason: reason, comments: values.comments || "", idempotency_key: `monthly-correction-${name}-${Date.now()}` } }, freeze: true, freeze_message: __("Registrando corrección…") });
			frappe.show_alert({ message: __("Corrección registrada sin sobrescribir el cierre original."), indicator: "green" });
			await loadMonthlyHistory(false);
		} catch (error) {
			console.error("NEXORA monthly close correction failed", error);
			window.nexora.ui.showError(error, {
				title: __("No fue posible registrar la corrección"),
				fallback: __("Revise el cierre original, el motivo y sus permisos."),
			});
		}
	}

	async function loadMonthlyHistory(freeze) {
		if (requiresProjectSelection() && !controls.project.get_value()) { body.find(".nxr-monthly-history").html(empty(__("Seleccione un proyecto."))); return; }
		try {
			const response = await frappe.call({ method: "nexora.close.service.list_monthly_closes", type: "POST", args: { payload: { project: controls.project.get_value() || null, page_size: 50 } }, freeze: Boolean(freeze), freeze_message: __("Actualizando historial mensual…") });
			const rows = response.message?.rows || [];
			monthlyHistoryRows = new Map(rows.map((row) => [String(row.name), row]));
			const nonTerminal = ["In Review", "Approved", "Cancelled"];
			const rendered = rows.map((row) => {
				const actions = [];
				if (!["Approved", "Cancelled"].includes(row.status)) {
					nonTerminal.filter((target) => target !== row.status).forEach((target) => {
						actions.push(`<button class="nxr-ds-btn nxr-ds-btn--secondary nxr-ds-btn--sm" data-monthly-transition="${escape(row.name)}" data-status="${escape(target)}">${monthlyStatus(target)}</button>`);
					});
				}
				if (row.status === "Approved") actions.push(`<button class="nxr-ds-btn nxr-ds-btn--secondary nxr-ds-btn--sm" data-monthly-correct="${escape(row.name)}">${__("Corregir")}</button>`);
				return [`<a href="${frappe.utils.get_form_link("NXR Monthly Close", row.name)}">${escape(row.document_number)}</a>`, escape(row.close_month), monthlyStatus(row.status), money(row.net_flow_hnl), money(row.total_available_hnl), `<code>${escape(String(row.snapshot_hash || "").slice(0, 12))}</code>`, row.correction_of ? escape(row.correction_of) : "—", actions.join(" ")];
			});
			body.find(".nxr-monthly-history").html(rows.length ? table([__("Número"), __("Mes"), __("Estado"), __("Flujo neto"), __("Disponible"), __("Huella"), __("Corrige a"), __("Acciones")], rendered) : empty(__("No hay cierres mensuales guardados.")));
		} catch (error) {
			console.error("NEXORA monthly close history failed", error);
			monthlyHistoryRows = new Map();
			body.find(".nxr-monthly-history").html(empty(__("No fue posible cargar el historial mensual.")));
		}
	}

	function monthlyStatus(value) {
		return escape({ Draft: __("Borrador"), "In Review": __("En revisión"), Approved: __("Aprobado"), Rejected: __("Rechazado"), Cancelled: __("Cancelado") }[value] || value);
	}

	function renderCalculation() {
		body.find(".nxr-closing-shell").removeAttr("data-calculation-cleared-by");
		const totals = calculation.totals || {};
		const counts = calculation.counts || {};
		body.find(".nxr-close-kpis").html([[__("Recibido"), money(totals.received_hnl)], [__("Gastado"), money(totals.spent_hnl)], [__("Pendiente"), money(totals.pending_hnl)], [__("Disponible"), money(totals.available_hnl)], [__("Comprometido"), money(totals.committed_hnl)], [__("Avance"), `${Number(calculation.physical_progress || 0).toFixed(1)}%`]].map((row) => `<article class="nxr-bi-kpi"><span>${escape(row[0])}</span><strong>${row[1]}</strong></article>`).join(""));
		body.find(".nxr-close-hash").text(`${calculation.engine_version || ""} · ${String(calculation.snapshot_hash || "").slice(0, 20)}`);
		body.find(".nxr-close-summary").html(table([__("Fondos"), __("Gastos"), __("Contratos"), __("Sin conciliar"), __("Saldo inicial"), __("Saldo cierre")], [[counts.income_count || 0, counts.expense_count || 0, counts.contract_count || 0, calculation.unreconciled_incomes || 0, money(totals.opening_funds_hnl), money(totals.closing_funds_hnl)]]));
	}

	function setState(state) { body.find(".nxr-closing-shell").attr({ "data-state": state, "aria-busy": state === "loading" ? "true" : "false" }); }
	function promptValues(fields, title) { return new Promise((resolve) => frappe.prompt(fields, resolve, title)); }
	function status(value) { return escape({ Closed: __("Cerrado"), Correction: __("Corrección") }[value] || value); }
	function table(headers, rows) { return `<div class="nxr-ds-table-wrap"><table class="nxr-ds-table"><thead><tr>${headers.map((header) => `<th>${escape(header)}</th>`).join("")}</tr></thead><tbody>${rows.map((row) => `<tr>${row.map((cell) => `<td>${cell ?? ""}</td>`).join("")}</tr>`).join("")}</tbody></table></div>`; }
	function money(value) { return window.nexora.ui.formatMoney(value); }
	function date(value) { return window.nexora.ui.formatDate(value); }
	function escape(value) { return window.nexora.ui.escapeHtml(value); }
	function empty(message) { return `<p class="nxr-executive-empty">${escape(message)}</p>`; }
};
