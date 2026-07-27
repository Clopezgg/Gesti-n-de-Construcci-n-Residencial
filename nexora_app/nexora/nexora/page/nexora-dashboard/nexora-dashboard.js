// prettier-ignore
frappe.pages["nexora-dashboard"].on_page_load = function (wrapper) {
	const page = frappe.ui.make_app_page({ parent: wrapper, title: __("NEXORA"), single_column: true });
	const body = $(page.body);
	let requestSerial = 0;
	const projectControl = page.add_field({
		fieldname: "project",
		label: __("Proyecto"),
		fieldtype: "Link",
		options: "Project",
		change: () => load(false),
	});
	const operationLabels = {
		Inflow: __("Ingreso"),
		Outflow: __("Egreso"),
		"Internal Transfer": __("Transferencia interna"),
		"Real Return": __("Devolución real"),
		"Commitment Reserve": __("Reserva de compromiso"),
		"Commitment Execution": __("Ejecución de compromiso"),
		"Commitment Release": __("Liberación de compromiso"),
	};
	const statusLabels = {
		Draft: __("Borrador"),
		Executed: __("Ejecutado"),
		Active: __("Activo"),
		Exhausted: __("Agotado"),
		Cancelled: __("Anulado"),
		Suspended: __("Suspendido"),
		"In Liquidation": __("En liquidación"),
	};
	const channelLabels = {
		Remittance: __("Remesas"),
		Cash: __("Efectivo"),
		Deposit: __("Depósitos"),
		Transfer: __("Transferencias"),
		Other: __("Otros"),
	};

	body.html(`
		<main class="nxr-product-shell nxr-dashboard-shell nxr-executive" data-state="loading" aria-busy="true">
			<section class="nxr-dashboard-welcome nxr-executive-hero">
				<div><p class="nxr-eyebrow">NX00 · ${__("RESUMEN EJECUTIVO")}</p><h2 class="nxr-project-name">${__("NEXORA")}</h2><p>${__("Gestión Integral de Fondos, Proyectos y Operaciones")}</p><small class="nxr-dashboard-context">${__("Preparando información canónica…")}</small></div>
				<div class="nxr-dashboard-primary-actions"><span class="nxr-schedule-pill">${__("Actualizando")}</span><button class="btn btn-primary btn-sm" data-action="income">${__("Registrar ingreso")}</button><button class="btn btn-default btn-sm" data-action="expense">${__("Registrar gasto")}</button></div>
			</section>
			<section class="nxr-alert-rows nxr-executive-alerts"></section>
			<section class="nxr-executive-metrics"></section>
			<section class="nxr-executive-grid nxr-executive-primary">
				<article class="nxr-executive-card"><header><div><strong>${__("Avance de la obra")}</strong><span>${__("Comparación física y financiera")}</span></div><button class="btn btn-xs btn-default" data-route="nexora-projects">${__("Detalle")}</button></header><div class="nxr-progress-summary"></div></article>
				<article class="nxr-executive-card"><header><div><strong>${__("Gastos por categoría")}</strong><span>${__("Ejecución del período")}</span></div><button class="btn btn-xs btn-default" data-route="nexora-reports" data-report="FI02">${__("Ver FI02")}</button></header><div class="nxr-expense-bars nxr-bars"></div></article>
				<article class="nxr-executive-card"><header><div><strong>${__("Ingresos por canal")}</strong><span>${__("Remesas, depósitos y transferencias")}</span></div><button class="btn btn-xs btn-default" data-route="nexora-reports" data-report="FI01">${__("Ver FI01")}</button></header><div class="nxr-income-bars nxr-bars"></div></article>
			</section>
			<section class="nxr-executive-grid nxr-executive-secondary">
				<article class="nxr-executive-card nxr-compact"><header><div><strong>${__("Cuentas por pagar")}</strong><span>${__("Vencidas o próximas")}</span></div><button class="btn btn-xs btn-default" data-route="nexora-reports" data-report="FI03">${__("Ver más")}</button></header><div class="nxr-payables-list"></div></article>
				<article class="nxr-executive-card nxr-compact"><header><div><strong>${__("Fondos y remesas")}</strong><span>${__("Saldo independiente por fuente")}</span></div><button class="btn btn-xs btn-default" data-route="nexora-reports" data-report="FI01">${__("Estado de cuenta")}</button></header><div class="nxr-balance-row nxr-funds-list"></div></article>
				<article class="nxr-executive-card nxr-compact"><header><div><strong>${__("Inventario crítico")}</strong><span>${__("Saldos agotados o negativos")}</span></div><button class="btn btn-xs btn-default" data-route="nexora-reports" data-report="MM03">${__("Ver MM03")}</button></header><div class="nxr-inventory-list"></div></article>
			</section>
			<section class="nxr-executive-grid nxr-executive-secondary">
				<article class="nxr-executive-card nxr-compact"><header><div><strong>${__("Actividad reciente")}</strong><span>${__("Libro Central cronológico")}</span></div><button class="btn btn-xs btn-default" data-route="nexora-finance">${__("Ver libro")}</button></header><div class="nxr-activity-list"></div></article>
				<article class="nxr-executive-card nxr-compact"><header><div><strong>${__("Evidencias y fotografías")}</strong><span>${__("Avance fotográfico cronológico")}</span></div><button class="btn btn-xs btn-default" data-route="nexora-evidence">${__("Ver expediente")}</button></header><div class="nxr-evidence-gallery"></div></article>
				<article class="nxr-executive-card nxr-compact"><header><div><strong>${__("Accesos rápidos")}</strong><span>${__("Operación diaria")}</span></div></header><div class="nxr-quick-links"><button data-route="nexora-purchase-requests">${__("Compras")}</button><button data-route="nexora-suppliers">${__("Proveedores")}</button><button data-route="nexora-search">${__("Buscador")}</button><button data-route="nexora-closing">${__("Cierre semanal")}</button></div></article>
			</section>
			<section class="nxr-executive-card nxr-contract-panel"><header><div><strong>${__("Estado contractual")}</strong><span>${__("Valor, ejecutado, pagado y saldo")}</span></div><button class="btn btn-xs btn-default" data-route="nexora-reports" data-report="CO01">${__("Ver CO01")}</button></header><div class="nxr-contract-rows nxr-contract-table"></div></section>
			<section class="nxr-executive-card"><header><div><strong>${__("Últimas operaciones")}</strong><span>${__("Trazabilidad financiera")}</span></div></header><div class="table-responsive"><table class="table nxr-dashboard-recent-rows"><thead><tr><th>${__("Documento")}</th><th>${__("Fecha")}</th><th>${__("Tipo")}</th><th>${__("Estado")}</th><th class="text-right">${__("Importe")}</th></tr></thead><tbody></tbody></table></div></section>
		</main>
	`);

	page.add_button(__("Actualizar datos"), () => load(true), "primary");
	body.on("click", "[data-action]", function () {
		const action = $(this).data("action");
		frappe.route_options = { nexora_action: action, project: projectControl.get_value() || null };
		frappe.set_route("nexora-finance");
	});
	body.on("click", "[data-route]:not([data-action])", function () {
		frappe.route_options = {
			project: projectControl.get_value() || null,
			nexora_report: $(this).data("report") || null,
		};
		frappe.set_route($(this).data("route"));
	});
	$(document).on("nexora:data-changed.nexora-dashboard", () => load(false));
	$(wrapper).on("remove", () => $(document).off("nexora:data-changed.nexora-dashboard"));

	const launchOptions = frappe.route_options || {};
	frappe.route_options = null;
	if (launchOptions.project) {
		projectControl.set_value(launchOptions.project);
	} else if (requiresProjectSelection()) {
		renderProjectPrompt();
	} else {
		load(false);
	}

	function requiresProjectSelection() {
		return frappe.user.has_role("NEXORA Project Viewer") && ![
			"System Manager",
			"NEXORA Administrator",
			"NEXORA Finance Manager",
			"NEXORA Finance Operator",
			"NEXORA Auditor",
		].some((role) => frappe.user.has_role(role));
	}

	function renderProjectPrompt() {
		body.find(".nxr-dashboard-shell").attr({ "data-state": "ready", "aria-busy": "false" });
		body.find(".nxr-project-name").text(__("Seleccione un proyecto"));
		body.find(".nxr-dashboard-context").text(__("Su perfil requiere un proyecto autorizado para mostrar información financiera."));
		body.find(".nxr-executive-alerts").html(alertCard("info", __("Proyecto requerido"), __("Use el selector superior para continuar.")));
		renderMetrics([]);
	}

	async function load(freeze) {
		if (requiresProjectSelection() && !projectControl.get_value()) {
			renderProjectPrompt();
			return;
		}
		const serial = ++requestSerial;
		body.find(".nxr-dashboard-shell").attr({ "data-state": "loading", "aria-busy": "true" });
		try {
			const response = await frappe.call({
				method: "nexora.dashboard.executive.get_executive_snapshot",
				type: "POST",
				args: { payload: { project: projectControl.get_value() || null } },
				freeze: Boolean(freeze),
				freeze_message: __("Actualizando resumen ejecutivo…"),
			});
			if (serial !== requestSerial) return;
			render(response.message || {});
		} catch (error) {
			console.error("NEXORA dashboard failed", error);
			body.find(".nxr-dashboard-shell").attr({ "data-state": "error", "aria-busy": "false" });
			frappe.msgprint({ title: __("Dashboard no disponible"), message: __("Revise la conexión, el proyecto o sus permisos y vuelva a intentar."), indicator: "red" });
		}
	}

	function render(data) {
		const finance = data.finance || {};
		const budgets = data.budgets || {};
		const pending_accounts = data.pending_accounts || {};
		const progress = data.progress || {};
		const analytics = data.analytics || {};
		const executive = data.executive || {};
		body.find(".nxr-project-name").text(data.context?.project_label || __("Todos los proyectos"));
		body.find(".nxr-dashboard-context").text(`${finance.source_count || 0} ${__("fuentes")} · ${analytics.contract_count || 0} ${__("contratos")} · ${pending_accounts.count || 0} ${__("cuentas pendientes")}`);
		body.find(".nxr-schedule-pill").text(Number(executive.projected_available_hnl || 0) < 0 ? __("Atención financiera") : __("Operación actualizada"));
		renderAlerts(data.alerts || [], analytics.unreconciled_count || 0);
		renderMetrics([
			[__("Ingresos recibidos"), executive.received_hnl],
			[__("Gastos ejecutados"), executive.spent_hnl],
			[__("Pagado contractual"), executive.paid_hnl],
			[__("Caja disponible"), finance.total_available_hnl ?? executive.cash_available_hnl],
			[__("Reservado"), finance.total_reserved_hnl],
			[__("Presupuesto ejecutado"), budgets.total_executed_hnl],
		]);
		renderProgress(progress.physical_percent, executive.financial_percent, progress.operational || {});
		renderBars(".nxr-expense-bars", analytics.expenses_by_category || [], (row) => row.label);
		renderBars(".nxr-income-bars", analytics.income_by_channel || [], (row) => channelLabels[row.label] || row.label);
		renderPayables(pending_accounts.items || []);
		renderFunds(analytics.rows || []);
		renderInventory(analytics.critical_inventory || []);
		renderActivity(data.recent_operations || []);
		renderEvidence(data.evidence?.items || []);
		renderContracts(analytics.contracts || data.contracts?.items || []);
		renderRecent(data.recent_operations || []);
		body.find(".nxr-dashboard-shell").attr({ "data-state": "ready", "aria-busy": "false" });
	}

	function renderAlerts(alerts, unreconciled) {
		const rows = [...alerts];
		if (unreconciled) rows.push({ level: "warning", title: __("Ingresos sin conciliar"), message: __("{0} ingreso(s) requieren conciliación documental.", [unreconciled]) });
		if (!rows.length) rows.push({ level: "success", title: __("Operación al día"), message: __("No hay alertas críticas en este momento.") });
		body.find(".nxr-alert-rows").html(rows.slice(0, 5).map((row) => alertCard(row.level, row.title, row.message)).join(""));
	}

	function alertCard(level, title, message) {
		return `<article class="nxr-executive-alert" data-level="${escape(level)}"><i></i><span><strong>${escape(title)}</strong><small>${escape(message)}</small></span></article>`;
	}

	function renderMetrics(rows) {
		body.find(".nxr-executive-metrics").html(rows.length ? rows.map((row) => `<article class="nxr-executive-metric"><span>${escape(row[0])}</span><strong>${money(row[1])}</strong></article>`).join("") : `<article class="nxr-executive-metric"><span>${__("Información")}</span><strong>${__("Seleccione un proyecto")}</strong></article>`);
	}

	function renderProgress(physicalValue, financialValue, operational) {
		const physical = Number(physicalValue || 0);
		const financial = Number(financialValue || 0);
		body.find(".nxr-progress-summary").html(`<div class="nxr-progress-pair"><div><span>${__("Avance físico")}</span><strong>${physical.toFixed(1)}%</strong><div class="nxr-progress-track"><i style="width:${clamp(physical)}%"></i></div></div><div><span>${__("Avance financiero")}</span><strong>${financial.toFixed(1)}%</strong><div class="nxr-progress-track is-financial"><i style="width:${clamp(financial)}%"></i></div></div></div><div class="nxr-progress-counts"><span><small>${__("Contratos activos")}</small><strong>${operational.active_contracts || 0}</strong></span><span><small>${__("Solicitudes")}</small><strong>${operational.pending_requests || 0}</strong></span><span><small>${__("Calidad")}</small><strong>${operational.open_quality_issues || 0}</strong></span></div>`);
	}

	function renderBars(selector, rows, label) {
		const visible = rows.slice(0, 5);
		const maximum = Math.max(...visible.map((row) => Number(row.amount_hnl || 0)), 1);
		body.find(selector).html(visible.length ? visible.map((row) => `<div class="nxr-bar-row"><span>${escape(label(row))}</span><b><i style="width:${Math.max((Number(row.amount_hnl || 0) / maximum) * 100, 2)}%"></i></b><strong>${money(row.amount_hnl)}</strong></div>`).join("") : empty(__("Sin datos para mostrar.")));
	}

	function renderPayables(rows) {
		body.find(".nxr-payables-list").html(rows.length ? rows.slice(0, 4).map((row) => `<a class="nxr-executive-row" href="${frappe.utils.get_form_link(row.doctype, row.name)}"><span><strong>${escape(row.title || row.document_number)}</strong><small>${escape(row.beneficiary || date(row.due_date))}</small></span><b>${money(row.amount_hnl)}</b></a>`).join("") : empty(__("No hay cuentas vencidas.")));
	}

	function renderFunds(rows) {
		body.find(".nxr-funds-list").html(rows.length ? rows.slice(0, 4).map((row) => `<a class="nxr-executive-row" href="${frappe.utils.get_form_link("NXR Fund Source", row.name)}"><span><strong>${escape(row.origin_or_sender || row.source_name)}</strong><small>${escape(channelLabels[row.channel] || row.channel)} · ${date(row.source_date)}</small></span><b>${money(row.current_available_hnl)}</b></a>`).join("") : empty(__("No hay ingresos registrados.")));
	}

	function renderInventory(rows) {
		body.find(".nxr-inventory-list").html(rows.length ? rows.map((row) => `<div class="nxr-executive-row"><span><strong>${escape(row.item)}</strong><small>${escape(row.warehouse)}</small></span><b>${number(row.balance_qty)}</b></div>`).join("") : empty(__("No hay saldos críticos.")));
	}

	function renderActivity(rows) {
		body.find(".nxr-activity-list").html(rows.length ? rows.slice(0, 4).map((row) => `<a class="nxr-executive-row" href="${frappe.utils.get_form_link("NXR Operation", row.name)}"><span><strong>${escape(row.document_number || row.name)}</strong><small>${date(row.operation_date)} · ${escape(operationLabels[row.operation_type] || row.operation_type)}</small></span><b>${money(row.amount_hnl)}</b></a>`).join("") : empty(__("No hay actividad reciente.")));
	}

	function renderEvidence(rows) {
		body.find(".nxr-evidence-gallery").html(rows.length ? rows.slice(0, 6).map((row) => `<a class="nxr-evidence-tile" href="${escape(row.file_url)}" target="_blank" rel="noopener"><img src="${escape(row.file_url)}" alt="${escape(row.file_name || row.evidence_kind || __("Evidencia"))}"><span>${escape(row.evidence_kind || row.file_name)}</span></a>`).join("") : empty(__("No hay evidencias recientes.")));
	}

	function renderContracts(rows) {
		const target = body.find(".nxr-contract-rows");
		if (!rows.length) { target.html(empty(__("No hay contratos registrados."))); return; }
		target.html(`<div class="table-responsive"><table class="table"><thead><tr><th>${__("Contrato")}</th><th>${__("Contratista")}</th><th>${__("Estado")}</th><th>${__("Inicio")}</th><th>${__("Fin")}</th><th class="text-right">${__("Valor")}</th><th class="text-right">${__("Pagado")}</th><th class="text-right">${__("Saldo")}</th></tr></thead><tbody>${rows.map((row) => `<tr><td><a href="${frappe.utils.get_form_link("NXR Contract", row.name)}">${escape(row.document_number || row.name)}</a></td><td>${escape(row.contractor_label || row.contractor)}</td><td>${escape(statusLabels[row.status] || row.status)}</td><td>${date(row.start_date)}</td><td>${date(row.current_end_date)}</td><td class="text-right">${money(row.contract_value_hnl ?? row.current_amount)}</td><td class="text-right">${money(row.paid_hnl ?? row.paid_amount)}</td><td class="text-right">${money(row.balance_hnl ?? row.pending_amount)}</td></tr>`).join("")}</tbody></table></div>`);
	}

	function renderRecent(rows) {
		body.find(".nxr-dashboard-recent-rows tbody").html(rows.slice(0, 6).map((row) => `<tr><td><a href="${frappe.utils.get_form_link("NXR Operation", row.name)}">${escape(row.document_number || row.name)}</a></td><td>${date(row.operation_date)}</td><td>${escape(operationLabels[row.operation_type] || row.operation_type)}</td><td>${escape(statusLabels[row.status] || row.status)}</td><td class="text-right">${money(row.amount_hnl)}</td></tr>`).join(""));
	}

	function money(value) { return new Intl.NumberFormat("es-HN", { style: "currency", currency: "HNL", minimumFractionDigits: 2 }).format(Number(value || 0)); }
	function number(value) { return new Intl.NumberFormat("es-HN", { maximumFractionDigits: 6 }).format(Number(value || 0)); }
	function date(value) { return value ? frappe.datetime.str_to_user(String(value).slice(0, 10)) : __("Sin fecha"); }
	function clamp(value) { return Math.max(0, Math.min(Number(value || 0), 100)); }
	function escape(value) { return frappe.utils.escape_html(String(value ?? "")); }
	function empty(message) { return `<p class="nxr-executive-empty">${escape(message)}</p>`; }
};
