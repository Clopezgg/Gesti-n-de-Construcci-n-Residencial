frappe.pages["nexora-dashboard"].on_page_load = function (wrapper) {
	const page = frappe.ui.make_app_page({ parent: wrapper, title: __("NEXORA"), single_column: true });
	const body = $(page.body);
	const channelLabels = {
		Remittance: __("Remesa"),
		Cash: __("Efectivo"),
		Deposit: __("Depósito"),
		Transfer: __("Transferencia"),
		Other: __("Otro"),
	};
	const categoryLabels = {
		CONSTRUCTION_MATERIALS: __("Materiales"),
		CONSTRUCTION_LABOR: __("Mano de obra"),
		MACHINERY: __("Maquinaria"),
		TRANSPORT: __("Transporte"),
		OTHER: __("Otros"),
	};
	let requestSerial = 0;
	let current = {};

	const project = page.add_field({
		fieldname: "project",
		label: __("Proyecto"),
		fieldtype: "Link",
		options: "Project",
		change: () => loadDashboard(false),
	});

	body.append(`
		<style>
			.nxr-exec{display:grid;gap:12px;padding:2px 0 30px}.nxr-exec-hero{display:flex;justify-content:space-between;align-items:flex-start;gap:20px;padding:22px 24px;border:1px solid var(--border-color);border-radius:18px;background:linear-gradient(120deg,var(--card-bg),var(--subtle-fg));box-shadow:0 10px 28px rgba(15,23,42,.06)}.nxr-exec-hero h2{font-size:27px;margin:4px 0}.nxr-exec-eyebrow{margin:0;font-size:11px;font-weight:800;letter-spacing:.08em;color:var(--text-muted)}.nxr-exec-status{display:inline-flex;padding:7px 11px;border-radius:999px;background:var(--green-100);color:var(--green-700);font-weight:800}.nxr-exec-status.warning{background:var(--yellow-100);color:var(--yellow-700)}.nxr-exec-status.danger{background:var(--red-100);color:var(--red-700)}.nxr-exec-alerts{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:10px}.nxr-exec-alert{display:flex;gap:10px;text-align:left;padding:12px 14px;border:1px solid var(--border-color);border-radius:13px;background:var(--card-bg)}.nxr-exec-alert:before{content:"";width:8px;height:8px;border-radius:50%;margin-top:5px;background:var(--blue-500)}.nxr-exec-alert.warning:before{background:var(--yellow-500)}.nxr-exec-alert.danger:before{background:var(--red-500)}.nxr-exec-alert strong,.nxr-exec-alert small{display:block}.nxr-exec-metrics{display:grid;grid-template-columns:repeat(6,minmax(0,1fr));gap:9px}.nxr-exec-metric{padding:14px;border:1px solid var(--border-color);border-radius:14px;background:var(--card-bg);min-width:0}.nxr-exec-metric span{display:block;font-size:11px;color:var(--text-muted);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.nxr-exec-metric strong{display:block;margin-top:5px;font-size:18px;white-space:nowrap}.nxr-exec-metric.negative strong{color:var(--red-500)}.nxr-exec-grid{display:grid;grid-template-columns:1.15fr 1fr 1fr;gap:12px}.nxr-exec-grid.secondary{grid-template-columns:repeat(3,1fr)}.nxr-exec-card{border:1px solid var(--border-color);border-radius:16px;background:var(--card-bg);padding:16px;min-width:0}.nxr-exec-card-head{display:flex;justify-content:space-between;gap:12px;align-items:flex-start;margin-bottom:14px}.nxr-exec-card-head strong,.nxr-exec-card-head span{display:block}.nxr-exec-card-head span{font-size:11px;color:var(--text-muted)}.nxr-progress-pair{display:grid;grid-template-columns:1fr 1fr;gap:14px}.nxr-progress-block>strong{font-size:26px}.nxr-progress-track{height:8px;border-radius:999px;background:var(--subtle-fg);overflow:hidden;margin-top:8px}.nxr-progress-track i{display:block;height:100%;border-radius:inherit;background:var(--primary)}.nxr-progress-track.financial i{background:var(--green-500)}.nxr-progress-meta{display:grid;grid-template-columns:repeat(3,1fr);gap:10px;margin-top:18px}.nxr-progress-meta span,.nxr-progress-meta strong{display:block}.nxr-progress-meta span{font-size:11px;color:var(--text-muted)}.nxr-exec-bars{display:grid;gap:10px}.nxr-exec-bar{display:grid;grid-template-columns:minmax(85px,1fr) 1.7fr auto;gap:8px;align-items:center;font-size:11px}.nxr-exec-bar>span:first-child{overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.nxr-exec-track{height:7px;border-radius:999px;background:var(--subtle-fg);overflow:hidden}.nxr-exec-track i{display:block;height:100%;border-radius:inherit;background:var(--primary)}.nxr-exec-list{display:grid}.nxr-exec-row{display:flex;justify-content:space-between;gap:12px;width:100%;padding:10px 0;border:0;border-bottom:1px solid var(--border-color);background:transparent;text-align:left}.nxr-exec-row:last-child{border-bottom:0}.nxr-exec-row strong,.nxr-exec-row small{display:block}.nxr-exec-row small{color:var(--text-muted)}.nxr-exec-row>span:last-child{text-align:right}.nxr-exec-empty{padding:18px 0;color:var(--text-muted);font-size:12px}.nxr-exec-actions{display:flex;gap:8px;flex-wrap:wrap}.nxr-exec-loading{opacity:.55;pointer-events:none}@media(max-width:1150px){.nxr-exec-metrics{grid-template-columns:repeat(3,1fr)}.nxr-exec-grid{grid-template-columns:1fr 1fr}.nxr-exec-grid .nxr-exec-card:first-child{grid-column:1/-1}}@media(max-width:760px){.nxr-exec-hero{display:block}.nxr-exec-status{margin-top:14px}.nxr-exec-alerts,.nxr-exec-grid,.nxr-exec-grid.secondary{grid-template-columns:1fr}.nxr-exec-grid .nxr-exec-card:first-child{grid-column:auto}.nxr-exec-metrics{grid-template-columns:repeat(2,1fr)}.nxr-progress-pair{grid-template-columns:1fr}.nxr-exec-bar{grid-template-columns:90px 1fr}.nxr-exec-bar strong{grid-column:2}.nxr-exec-metric strong{font-size:16px}}
		</style>
		<main class="nxr-dashboard-shell nxr-exec" data-state="loading">
			<section class="nxr-exec-hero">
				<div><p class="nxr-exec-eyebrow">NX00 · ${__("RESUMEN EJECUTIVO")}</p><h2 class="nxr-project-title">${__("Gestión de obra residencial")}</h2><p class="nxr-project-subtitle text-muted">${__("Actualizando información…")}</p></div>
				<div><span class="nxr-exec-status">${__("Cargando")}</span></div>
			</section>
			<section class="nxr-exec-alerts"></section>
			<section class="nxr-exec-metrics"></section>
			<section class="nxr-exec-grid">
				<article class="nxr-exec-card"><div class="nxr-exec-card-head"><div><strong>${__("Avance de la obra")}</strong><span>${__("Comparación física y financiera")}</span></div><button class="btn btn-xs btn-default" data-route="nexora-reports">${__("Detalle")}</button></div><div class="nxr-progress-content"></div></article>
				<article class="nxr-exec-card"><div class="nxr-exec-card-head"><div><strong>${__("Gastos por categoría")}</strong><span>${__("Distribución de la ejecución")}</span></div><button class="btn btn-xs btn-default" data-route="nexora-reports" data-report-view="executive">${__("Ver gastos")}</button></div><div class="nxr-expense-bars"></div></article>
				<article class="nxr-exec-card"><div class="nxr-exec-card-head"><div><strong>${__("Ingresos por canal")}</strong><span>${__("Remesas, depósitos y transferencias")}</span></div><button class="btn btn-xs btn-default" data-route="nexora-reports" data-report-view="income">${__("Ver ingresos")}</button></div><div class="nxr-income-bars"></div></article>
			</section>
			<section class="nxr-exec-grid secondary">
				<article class="nxr-exec-card"><div class="nxr-exec-card-head"><div><strong>${__("Cuentas por pagar")}</strong><span>${__("Vencidas o próximas")}</span></div><button class="btn btn-xs btn-default" data-route="nexora-finance">${__("Ver más")}</button></div><div class="nxr-payable-list nxr-exec-list"></div></article>
				<article class="nxr-exec-card"><div class="nxr-exec-card-head"><div><strong>${__("Contratos activos")}</strong><span>${__("Valor, pagos y saldos")}</span></div><button class="btn btn-xs btn-default" data-route="nexora-reports" data-report-view="contracts">${__("Ver más")}</button></div><div class="nxr-contract-list nxr-exec-list"></div></article>
				<article class="nxr-exec-card"><div class="nxr-exec-card-head"><div><strong>${__("Actividad reciente")}</strong><span>${__("Últimos movimientos relevantes")}</span></div><button class="btn btn-xs btn-default" data-route="nexora-finance">${__("Ver más")}</button></div><div class="nxr-activity-list nxr-exec-list"></div></article>
			</section>
			<section class="nxr-exec-card"><div class="nxr-exec-card-head"><div><strong>${__("Acciones rápidas")}</strong><span>${__("Operación diaria")}</span></div></div><div class="nxr-exec-actions"><button class="btn btn-primary" data-route="nexora-finance" data-action="income">${__("Registrar ingreso")}</button><button class="btn btn-default" data-route="nexora-finance" data-action="expense">${__("Registrar gasto")}</button><button class="btn btn-default" data-route="nexora-contracts">${__("Contratos")}</button><button class="btn btn-default" data-route="nexora-suppliers">${__("Proveedores")}</button><button class="btn btn-default" data-route="nexora-reports">${__("Reportes")}</button></div></section>
		</main>
	`);

	const money = (value) => format_currency(Number(value || 0), "HNL");
	const esc = (value) => frappe.utils.escape_html(String(value ?? ""));
	const date = (value) => (value ? frappe.datetime.str_to_user(String(value).slice(0, 10)) : __("Sin fecha"));

	body.on("click", "[data-route]", function () {
		frappe.route_options = {
			project: project.get_value() || null,
			nexora_action: $(this).data("action") || null,
			nexora_report_view: $(this).data("report-view") || null,
		};
		frappe.set_route($(this).data("route"));
	});
	body.on("click", "[data-form]", function () {
		frappe.set_route("Form", $(this).data("form"), $(this).data("name"));
	});
	page.add_button(__("Actualizar"), () => loadDashboard(true), "primary");

	function metric(label, value, negative = false) {
		return `<div class="nxr-exec-metric ${negative ? "negative" : ""}"><span>${esc(label)}</span><strong>${value}</strong></div>`;
	}

	function renderBars(selector, rows, labelResolver) {
		const visible = (rows || []).filter((row) => Number(row.amount_hnl || 0) !== 0).slice(0, 6);
		const max = Math.max(...visible.map((row) => Math.abs(Number(row.amount_hnl || 0))), 1);
		body.find(selector).html(
			visible.length
				? `<div class="nxr-exec-bars">${visible
					.map((row) => {
						const label = labelResolver(row);
						return `<div class="nxr-exec-bar"><span title="${esc(label)}">${esc(label)}</span><span class="nxr-exec-track"><i style="width:${Math.max((Math.abs(Number(row.amount_hnl || 0)) / max) * 100, 2)}%"></i></span><strong>${money(row.amount_hnl)}</strong></div>`;
					})
					.join("")}</div>`
				: `<div class="nxr-exec-empty">${__("Sin datos para mostrar.")}</div>`
		);
	}

	function renderList(selector, rows, renderer, empty) {
		body.find(selector).html((rows || []).length ? rows.slice(0, 4).map(renderer).join("") : `<div class="nxr-exec-empty">${esc(empty)}</div>`);
	}

	function render(summary, executive) {
		current = { summary, executive };
		const finance = summary.finance || {};
		const budget = summary.budgets || {};
		const progress = summary.progress || {};
		const pending = summary.pending_accounts || {};
		const contractRows = executive.contracts?.rows || [];
		const contractValue = contractRows.reduce((sum, row) => sum + Number(row.value_hnl || 0), 0);
		const paid = contractRows.reduce((sum, row) => sum + Number(row.paid_hnl || 0), 0);
		const physical = Math.min(Math.max(Number(progress.physical_percent || 0), 0), 100);
		const financial = budget.total_approved_hnl ? Math.min(Math.max((Number(budget.total_executed_hnl || 0) / Number(budget.total_approved_hnl || 1)) * 100, 0), 100) : 0;
		const status = (summary.alerts || []).some((row) => row.level === "danger") ? "danger" : (summary.alerts || []).length ? "warning" : "";
		body.find(".nxr-project-title").text(summary.context?.project_label || __("Gestión de obra residencial"));
		body.find(".nxr-project-subtitle").text(`${progress.record_count || 0} ${__("registros de avance")} · ${contractRows.length} ${__("contratos")} · ${summary.recent_operations?.length || 0} ${__("movimientos recientes")}`);
		body.find(".nxr-exec-status").attr("class", `nxr-exec-status ${status}`).text(status === "danger" ? __("Requiere atención") : status === "warning" ? __("Con alertas") : __("En control"));
		body.find(".nxr-exec-alerts").html((summary.alerts || []).slice(0, 4).map((alert) => `<button class="nxr-exec-alert ${esc(alert.level)}"><span><strong>${esc(alert.title)}</strong><small>${esc(alert.message)}</small></span></button>`).join("") || `<div class="nxr-exec-alert"><span><strong>${__("Sin alertas críticas")}</strong><small>${__("Los indicadores principales están dentro de control.")}</small></span></div>`);
		body.find(".nxr-exec-metrics").html([
			metric(__("Ingresos recibidos"), money(finance.inflows_hnl)),
			metric(__("Gastos registrados"), money(finance.outflows_hnl)),
			metric(__("Pagado"), money(paid)),
			metric(__("Caja disponible"), money(finance.total_available_hnl), Number(finance.total_available_hnl) < 0),
			metric(__("Comprometido"), money(contractValue)),
			metric(__("Presupuesto disponible"), money(budget.total_available_hnl), Number(budget.total_available_hnl) < 0),
		].join(""));
		body.find(".nxr-progress-content").html(`<div class="nxr-progress-pair"><div class="nxr-progress-block"><span class="text-muted">${__("Avance físico")}</span><strong>${physical.toFixed(0)}%</strong><div class="nxr-progress-track"><i style="width:${physical}%"></i></div></div><div class="nxr-progress-block"><span class="text-muted">${__("Avance financiero")}</span><strong>${financial.toFixed(0)}%</strong><div class="nxr-progress-track financial"><i style="width:${financial}%"></i></div></div></div><div class="nxr-progress-meta"><div><span>${__("Registros")}</span><strong>${progress.record_count || 0}</strong></div><div><span>${__("Por revisar")}</span><strong>${progress.pending_review_count || 0}</strong></div><div><span>${__("Calidad abierta")}</span><strong>${progress.operational?.open_quality_issues || 0}</strong></div></div>`);
		renderBars(".nxr-expense-bars", executive.costs || [], (row) => categoryLabels[row.code] || row.code || __("Sin clasificar"));
		const channelTotals = {};
		(executive.income?.rows || []).forEach((row) => { channelTotals[row.channel || "Other"] = (channelTotals[row.channel || "Other"] || 0) + Number(row.received_hnl || 0); });
		renderBars(".nxr-income-bars", Object.entries(channelTotals).map(([code, amount_hnl]) => ({ code, amount_hnl })), (row) => channelLabels[row.code] || row.code);
		renderList(".nxr-payable-list", pending.upcoming || pending.items || [], (row) => `<button class="nxr-exec-row" data-form="${esc(row.doctype)}" data-name="${esc(row.name)}"><span><strong>${esc(row.title || row.document_number)}</strong><small>${esc(row.beneficiary || date(row.due_date))}</small></span><span><strong>${money(row.amount_hnl)}</strong><small>${date(row.due_date)}</small></span></button>`, __("No hay cuentas vencidas o próximas."));
		renderList(".nxr-contract-list", contractRows, (row) => `<button class="nxr-exec-row" data-form="NXR Contract" data-name="${esc(row.name)}"><span><strong>${esc(row.contractor_label || row.document_number)}</strong><small>${esc(row.status || "")}</small></span><span><strong>${money(row.balance_hnl)}</strong><small>${__("Saldo")}</small></span></button>`, __("No hay contratos activos."));
		renderList(".nxr-activity-list", summary.recent_operations || [], (row) => `<button class="nxr-exec-row" data-form="NXR Operation" data-name="${esc(row.name)}"><span><strong>${esc(row.document_number || row.name)}</strong><small>${esc(row.operation_code || row.operation_type)}</small></span><span><strong>${money(row.amount_hnl)}</strong><small>${date(row.operation_date)}</small></span></button>`, __("No hay actividad reciente."));
		body.find(".nxr-dashboard-shell").attr("data-state", "ready").removeClass("nxr-exec-loading");
	}

	async function loadDashboard(showFreeze = false) {
		const serial = ++requestSerial;
		body.find(".nxr-dashboard-shell").addClass("nxr-exec-loading").attr("data-state", "loading");
		try {
			const args = { payload: { project: project.get_value() || null } };
			const [summaryResponse, executiveResponse] = await Promise.all([
				frappe.call({ method: "nexora.dashboard.service.get_dashboard_summary", type: "POST", args, freeze: showFreeze, freeze_message: __("Actualizando tablero…") }),
				frappe.call({ method: "nexora.reports.executive.get_executive_report", type: "POST", args }),
			]);
			if (serial !== requestSerial) return;
			render(summaryResponse.message || {}, executiveResponse.message || {});
		} catch (error) {
			if (serial !== requestSerial) return;
			body.find(".nxr-dashboard-shell").removeClass("nxr-exec-loading").attr("data-state", "error");
			frappe.msgprint({ title: __("No se pudo actualizar el dashboard"), message: esc(error?.message || error), indicator: "red" });
		}
	}

	document.addEventListener("nexora:data-changed", () => loadDashboard(false));
	loadDashboard(false);
};
