frappe.pages["construcontrol-reporting-center"].on_page_load = function (wrapper) {
	"use strict";

	frappe.ui.make_app_page({
		parent: wrapper,
		title: "BI01 · Reportes y notificaciones",
		single_column: true,
	});

	const body = $(wrapper).find(".layout-main-section");
	const today = frappe.datetime.get_today();
	const monthStart = `${today.slice(0, 8)}01`;
	let lastNotificationLog = null;
	let reportingRequest = 0;
	let context = { projects: [], contacts: [], can_export: false, can_generate: false };

	const executiveReports = {
		FI03: {
			label: "FI03 Cuentas por Pagar",
			route: ["List", "CC Payable Control"],
			detail: "Vencimientos, pagos y saldos pendientes",
		},
		PR02: {
			label: "PR02 Presupuesto vs Ejecución",
			route: ["construcontrol-project-center"],
			detail: "Presupuesto, comprometido, ejecutado y disponible",
		},
		PR03: {
			label: "PR03 Fases y Desviaciones",
			route: ["List", "CC Construction Phase"],
			detail: "Avance, retrasos y variaciones por fase",
		},
		MM03: {
			label: "MM03 Inventario Crítico",
			route: ["List", "CC Material Ledger"],
			detail: "Existencias bajas, costo y trazabilidad",
		},
		FI04: {
			label: "FI04 Ingresos y Conciliación",
			route: ["List", "CC Funding Source"],
			detail: "Fondos reconocidos, referencias y conciliación",
		},
	};

	body.html(`
    <style>
      .cc-bi[data-cc-page="reporting"]{max-width:1200px}.cc-bi[data-cc-page="reporting"] .cc-bi-toolbar{display:grid;grid-template-columns:repeat(4,minmax(150px,1fr));gap:10px;align-items:end;padding:14px;border:1px solid var(--border-color);border-radius:12px;background:var(--card-bg)}
      .cc-bi[data-cc-page="reporting"] label{display:block;font-weight:600}.cc-bi[data-cc-page="reporting"] input,.cc-bi[data-cc-page="reporting"] select,.cc-bi[data-cc-page="reporting"] textarea{width:100%;min-height:42px;margin-top:5px;border:1px solid var(--border-color);border-radius:8px;padding:8px;background:var(--control-bg);color:var(--text-color)}
      .cc-bi[data-cc-page="reporting"] .cc-bi-actions{display:flex;gap:8px;flex-wrap:wrap;margin:12px 0}.cc-bi[data-cc-page="reporting"] .cc-bi-metrics{display:grid;grid-template-columns:repeat(auto-fit,minmax(155px,1fr));gap:10px;margin:12px 0}.cc-bi[data-cc-page="reporting"] .cc-bi-metric{padding:14px;border:1px solid var(--border-color);border-radius:12px;background:var(--card-bg)}.cc-bi[data-cc-page="reporting"] .cc-bi-metric strong{display:block;margin-top:4px;font-size:20px}
      .cc-bi[data-cc-page="reporting"] .cc-bi-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px}.cc-bi[data-cc-page="reporting"] .cc-bi-card{padding:14px;border:1px solid var(--border-color);border-radius:12px;background:var(--card-bg)}.cc-bi[data-cc-page="reporting"] .cc-bi-wide{grid-column:1/-1}.cc-bi[data-cc-page="reporting"] .cc-bi-row,.cc-bi[data-cc-page="reporting"] .cc-bi-phase{width:100%;display:flex;justify-content:space-between;gap:10px;padding:8px 0;border:0;border-bottom:1px solid var(--border-color);background:transparent;color:inherit;text-align:left}.cc-bi[data-cc-page="reporting"] .cc-bi-row:last-child{border-bottom:0}.cc-bi[data-cc-page="reporting"] .cc-bi-empty{color:var(--text-muted);padding:12px 0}.cc-bi[data-cc-page="reporting"] .cc-bi-result{margin-top:10px;padding:10px;border-radius:8px;background:var(--subtle-fg)}
      .cc-bi[data-cc-page="reporting"] .cc-bi-phase{display:grid;grid-template-columns:1fr auto;position:relative;padding-bottom:16px}.cc-bi[data-cc-page="reporting"] .cc-bi-phase span:first-child{display:flex;flex-direction:column}.cc-bi[data-cc-page="reporting"] .cc-bi-phase i{position:absolute;left:0;right:0;bottom:6px;height:6px;background:var(--control-bg);border-radius:99px;overflow:hidden}.cc-bi[data-cc-page="reporting"] .cc-bi-phase i b{display:block;height:100%;background:var(--primary)}
      .cc-bi[data-cc-page="reporting"] .cc-executive-reports{display:grid;grid-template-columns:repeat(auto-fit,minmax(205px,1fr));gap:9px}.cc-bi[data-cc-page="reporting"] .cc-executive-report{display:flex;flex-direction:column;gap:4px;min-height:82px;padding:12px;border:1px solid var(--border-color);border-radius:11px;background:var(--card-bg);color:var(--text-color);text-align:left}.cc-bi[data-cc-page="reporting"] .cc-executive-report:hover{border-color:var(--primary);background:var(--subtle-fg)}.cc-bi[data-cc-page="reporting"] .cc-executive-report small{color:var(--text-muted)}
      @media(max-width:767px){.cc-bi[data-cc-page="reporting"] .cc-bi-toolbar,.cc-bi[data-cc-page="reporting"] .cc-bi-grid{grid-template-columns:1fr}.cc-bi[data-cc-page="reporting"] .cc-bi-actions .btn{flex:1 1 100%}.cc-bi[data-cc-page="reporting"] .cc-bi-wide{grid-column:auto}}
    </style>
    <div class="cc-bi" data-cc-page="reporting">
      <div class="cc-bi-toolbar">
        <label>Desde<input id="cc-bi-from" type="date" value="${monthStart}"></label>
        <label>Hasta<input id="cc-bi-to" type="date" value="${today}"></label>
        <label>Proyecto<select id="cc-bi-project"><option value="">Seleccione un proyecto</option></select></label>
        <label>Tipo<select id="cc-bi-type"><option value="financial">Financiero integral</option><option value="expenses">Gastos</option><option value="contracts">Contratos y CxP</option><option value="phases">Fases y desviaciones</option><option value="inventory">Inventario crítico</option><option value="quality">Calidad</option><option value="weekly">Cierre semanal</option></select></label>
      </div>
      <div class="cc-bi-actions">
        <button class="btn btn-primary" id="cc-bi-refresh">Actualizar datos</button>
        <button class="btn btn-default" id="cc-bi-generate">Guardar reporte</button>
        <button class="btn btn-default" id="cc-bi-export">Exportar CSV privado</button>
        <button class="btn btn-default" id="cc-bi-reports">Historial</button>
      </div>
      <div id="cc-bi-status" class="text-muted" role="status" aria-live="polite">Cargando datos vivos...</div>
      <div id="cc-bi-metrics" class="cc-bi-metrics"></div>
      <div class="cc-bi-grid">
        <section class="cc-bi-card cc-bi-wide"><h3>Reportes ejecutivos</h3><div id="cc-bi-executive-reports" class="cc-executive-reports"></div></section>
        <section class="cc-bi-card"><h3>Gastos por categoría</h3><div id="cc-bi-categories"></div></section>
        <section class="cc-bi-card"><h3>Principales proveedores</h3><div id="cc-bi-providers"></div></section>
        <section class="cc-bi-card"><h3>Avance por fase</h3><div id="cc-bi-phases"></div></section>
        <section class="cc-bi-card"><h3>Control operativo</h3><div id="cc-bi-operational"></div></section>
        <section class="cc-bi-card cc-bi-wide"><h3>Notificación manual autorizada</h3><p class="text-muted">El envío se confirma manualmente y no utiliza secretos externos.</p><label>Contacto<select id="cc-bi-contact"><option value="">Seleccione un contacto</option></select></label><label>Evento<select id="cc-bi-event"><option value="income">Ingreso/remesa</option><option value="expense">Gasto</option><option value="material">Material</option><option value="inventory">Inventario</option><option value="progress">Avance</option><option value="weekly">Cierre semanal</option><option value="report">Reporte</option><option value="manual">Manual</option></select></label><label>Mensaje opcional<textarea id="cc-bi-message" rows="4" maxlength="1500" placeholder="Vacío usa la plantilla segura"></textarea></label><div class="cc-bi-actions"><button class="btn btn-primary" id="cc-bi-prepare">Preparar WhatsApp</button><button class="btn btn-default" id="cc-bi-contacts">Contactos</button><button class="btn btn-default" id="cc-bi-logs">Historial</button></div><div id="cc-bi-notification-result"></div></section>
      </div>
    </div>
  `);

	const esc = (value) => frappe.utils.escape_html(String(value ?? ""));
	const money = (value) => format_currency(Number(value) || 0, "HNL");
	const params = () => ({
		date_from: body.find("#cc-bi-from").val(),
		date_to: body.find("#cc-bi-to").val(),
		project: body.find("#cc-bi-project").val() || null,
	});
	const selectedProject = () => params().project;

	body.find("#cc-bi-executive-reports").html(
		Object.entries(executiveReports)
			.map(
				([code, report]) =>
					`<button type="button" class="cc-executive-report" data-executive-report="${code}"><strong>${esc(
						report.label
					)}</strong><small>${esc(report.detail)}</small></button>`
			)
			.join("")
	);

	function requireProject() {
		if (selectedProject()) return true;
		frappe.msgprint(__("Seleccione un proyecto para generar, exportar o notificar."));
		return false;
	}

	function setBusy(busy) {
		body.find("button").prop("disabled", Boolean(busy));
		body.find(".cc-bi").attr("aria-busy", busy ? "true" : "false");
	}

	function renderRows(rows, target, emptyText) {
		body.find(target).html(
			(rows || []).length
				? rows
						.map(
							(row) =>
								`<div class="cc-bi-row"><span>${esc(row.label)}</span><strong>${money(
									row.amount_hnl
								)}</strong></div>`
						)
						.join("")
				: `<div class="cc-bi-empty">${esc(emptyText)}</div>`
		);
	}

	function renderSummary(summary) {
		const totals = summary.totals || {};
		const counts = summary.counts || {};
		const metrics = [
			["Recibido", money(totals.received_hnl)],
			["Gastado", money(totals.spent_hnl)],
			["Pendiente", money(totals.pending_hnl)],
			["Disponible", money(totals.available_hnl)],
			["Comprometido", money(totals.phase_committed_hnl)],
			["Inventario", money(totals.inventory_value_hnl)],
			["Avance", `${Number(totals.overall_progress || 0).toFixed(2)}%`],
		];
		body.find("#cc-bi-metrics").html(
			metrics
				.map(
					(row) =>
						`<div class="cc-bi-metric"><span class="text-muted">${esc(row[0])}</span><strong>${
							row[1]
						}</strong></div>`
				)
				.join("")
		);
		renderRows(summary.expense_categories, "#cc-bi-categories", "Sin gastos reconocidos en el período.");
		renderRows(summary.providers, "#cc-bi-providers", "Sin proveedores con gasto reconocido.");
		body.find("#cc-bi-phases").html(
			(summary.phases || []).length
				? summary.phases
						.map((row) => {
							const progress = Math.max(0, Math.min(100, Number(row.progress_percent || 0)));
							return `<button type="button" class="cc-bi-phase" data-doctype="CC Construction Phase" data-name="${esc(
								row.name
							)}"><span><strong>${esc(row.phase_name || row.name)}</strong><small>${esc(
								row.schedule_status || row.status || ""
							)}</small></span><span>${progress.toFixed(
								2
							)}%</span><i><b style="width:${progress}%"></b></i></button>`;
						})
						.join("")
				: `<div class="cc-bi-empty">Sin fases para mostrar.</div>`
		);
		body.find("#cc-bi-operational").html(`
      <button class="cc-bi-row" data-list="CC Material Ledger"><span>Materiales críticos</span><strong>${Number(
			counts.low_stock || 0
		)}</strong></button>
      <button class="cc-bi-row" data-list="CC Progress Update"><span>Hallazgos de calidad</span><strong>${Number(
			counts.quality_issues || 0
		)}</strong></button>
      <button class="cc-bi-row" data-list="CC Weekly Closing"><span>Cierres semanales</span><strong>${Number(
			counts.closings || 0
		)}</strong></button>
    `);
		body.find("#cc-bi-status").text(
			`${summary.period.date_from} a ${summary.period.date_to} · ${counts.funds || 0} ingresos · ${
				counts.expenses || 0
			} gastos · ${counts.materials || 0} materiales`
		);
	}

	async function loadContext() {
		context = await frappe.xcall("erpnext.construcontrol.reporting.get_reporting_context");
		body.find("#cc-bi-project").append(
			(context.projects || [])
				.map(
					(row) =>
						`<option value="${esc(row.project)}">${esc(row.project_name || row.project)}</option>`
				)
				.join("")
		);
		body.find("#cc-bi-contact").append(
			(context.contacts || [])
				.map(
					(row) =>
						`<option value="${esc(row.name)}">${esc(
							row.contact_name || row.title || row.name
						)} · ${esc(row.phone || "sin teléfono")}</option>`
				)
				.join("")
		);
		body.find("#cc-bi-generate").toggle(Boolean(context.can_generate));
		body.find("#cc-bi-export").toggle(Boolean(context.can_export));
	}

	async function refresh() {
		const requestId = ++reportingRequest;
		body.find("#cc-bi-status").text("Consultando datos vivos...");
		try {
			const summary = await frappe.xcall(
				"erpnext.construcontrol.reporting.get_reporting_summary",
				params()
			);
			if (requestId !== reportingRequest) return;
			renderSummary(summary || {});
		} catch (error) {
			if (requestId !== reportingRequest) return;
			body.find("#cc-bi-status").html(
				`<span class="text-danger">${esc(
					error?.message || "No se pudo consultar el reporte."
				)}</span>`
			);
		}
	}

	async function runAction(callback) {
		setBusy(true);
		try {
			await callback();
		} finally {
			setBusy(false);
		}
	}

	body.find("#cc-bi-refresh").on("click", refresh);
	body.find("#cc-bi-reports").on("click", () => frappe.set_route("List", "CC Generated Report"));
	body.find("#cc-bi-contacts").on("click", () => frappe.set_route("List", "CC Notification Contact"));
	body.find("#cc-bi-logs").on("click", () => frappe.set_route("List", "CC Notification Log"));
	body.on("click", "[data-list]", (event) => frappe.set_route("List", event.currentTarget.dataset.list));
	body.on("click", "[data-doctype][data-name]", (event) =>
		frappe.set_route("Form", event.currentTarget.dataset.doctype, event.currentTarget.dataset.name)
	);
	body.on("click", "[data-executive-report]", (event) => {
		const report = executiveReports[event.currentTarget.dataset.executiveReport];
		if (report) frappe.set_route(...report.route);
	});

	body.find("#cc-bi-generate").on("click", () => {
		if (!requireProject()) return;
		runAction(async () => {
			const result = await frappe.xcall("erpnext.construcontrol.reporting.generate_report_record", {
				...params(),
				report_type: body.find("#cc-bi-type").val(),
			});
			frappe.show_alert({
				message: result.reused ? "Reporte existente reutilizado" : "Reporte guardado",
				indicator: "green",
			});
			frappe.set_route("Form", "CC Generated Report", result.name);
		});
	});

	body.find("#cc-bi-export").on("click", () => {
		if (!requireProject()) return;
		runAction(async () => {
			const result = await frappe.xcall("erpnext.construcontrol.reporting.export_report_csv", {
				...params(),
				report_type: body.find("#cc-bi-type").val(),
			});
			frappe.show_alert({
				message: result.reused ? "Exportación privada reutilizada" : "Exportación privada creada",
				indicator: "green",
			});
			window.open(result.file_url, "_blank", "noopener,noreferrer");
		});
	});

	body.find("#cc-bi-prepare").on("click", () => {
		if (!requireProject()) return;
		const contact = body.find("#cc-bi-contact").val();
		if (!contact) {
			frappe.msgprint("Seleccione un contacto activo y autorizado.");
			return;
		}
		runAction(async () => {
			const result = await frappe.xcall("erpnext.construcontrol.reporting.prepare_notification", {
				...params(),
				contact,
				event_type: body.find("#cc-bi-event").val(),
				message: body.find("#cc-bi-message").val() || null,
			});
			lastNotificationLog = result.log;
			body.find("#cc-bi-notification-result").html(
				`<div class="cc-bi-result"><p>${esc(
					result.message
				)}</p><div class="cc-bi-actions"><a class="btn btn-primary" target="_blank" rel="noopener noreferrer" href="${esc(
					result.whatsapp_url
				)}">Abrir WhatsApp</a><button class="btn btn-default" id="cc-bi-sent">Marcar envío manual</button></div></div>`
			);
		});
	});

	body.on("click", "#cc-bi-sent", () => {
		if (!lastNotificationLog) return;
		runAction(async () => {
			await frappe.xcall("erpnext.construcontrol.reporting.mark_notification_sent", {
				log_name: lastNotificationLog,
			});
			frappe.show_alert({ message: "Envío manual confirmado", indicator: "green" });
			body.find("#cc-bi-sent").prop("disabled", true);
		});
	});

	runAction(async () => {
		await loadContext();
		await refresh();
	});
};
