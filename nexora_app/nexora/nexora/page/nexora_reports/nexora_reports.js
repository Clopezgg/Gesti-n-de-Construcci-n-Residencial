// prettier-ignore
frappe.pages["nexora-reports"].on_page_load = function (wrapper) {
	const page = frappe.ui.make_app_page({ parent: wrapper, title: __("Reportes NEXORA"), single_column: true });
	const body = $(page.body);
	let suppressControlReload = false;
	const controls = {
		project: page.add_field({ fieldname: "project", label: __("Proyecto"), fieldtype: "Link", options: "Project", change: onProjectChange }),
		from_date: page.add_field({ fieldname: "from_date", label: __("Desde"), fieldtype: "Date", change: onFilterChange }),
		to_date: page.add_field({ fieldname: "to_date", label: __("Hasta"), fieldtype: "Date", change: onFilterChange }),
		source: page.add_field({ fieldname: "source", label: __("Fuente"), fieldtype: "Link", options: "NXR Fund Source", change: onFilterChange }),
		economic_category: page.add_field({ fieldname: "economic_category", label: __("Categoría"), fieldtype: "Link", options: "NXR Economic Category", change: onFilterChange }),
		cost_center: page.add_field({ fieldname: "cost_center", label: __("Centro de costo"), fieldtype: "Link", options: "Cost Center", change: onFilterChange }),
		entity: page.add_field({ fieldname: "entity", label: __("Entidad"), fieldtype: "Link", options: "NXR Entity", change: onFilterChange }),
		payment_method: page.add_field({ fieldname: "payment_method", label: __("Medio de pago"), fieldtype: "Select", options: "\nCash\nDeposit\nTransfer\nOther", change: onFilterChange }),
		contractor: page.add_field({ fieldname: "contractor", label: __("Contratista"), fieldtype: "Link", options: "NXR Entity", change: onFilterChange }),
		contract_status: page.add_field({ fieldname: "contract_status", label: __("Estado contractual"), fieldtype: "Select", options: "\nDraft\nIn Review\nApproved\nActive\nSuspended\nCompleted\nIn Liquidation\nLiquidated\nEarly Terminated\nCancelled Before Active", change: onFilterChange }),
	};
	let activeView = "FI01";
	let currentPage = 1;
	let snapshot = {};
	let currentRows = [];
	let currentPagination = { page: 1, page_size: 25, total: 0 };
	let requestSerial = 0;
	let viewSerial = 0;
	const channelLabels = { Remittance: __("Remesa"), Cash: __("Efectivo"), Deposit: __("Depósito"), Transfer: __("Transferencia"), Other: __("Otro") };

	body.html(`
		<main class="nxr-product-shell nxr-bi-shell" data-state="loading" aria-busy="true">
			<section class="nxr-bi-hero"><div><p class="nxr-eyebrow">BI01 · ${__("REPORTES Y CONTROL")}</p><h2>${__("Centro ejecutivo NEXORA")}</h2><p>${__("El panel, los estados de cuenta, los contratos y los cierres consumen el mismo motor analítico canónico.")}</p></div><div class="nxr-bi-actions"><button class="btn btn-primary btn-sm nxr-refresh">${__("Actualizar")}</button><button class="btn btn-default btn-sm nxr-save">${__("Guardar reporte")}</button><button class="btn btn-default btn-sm nxr-export-xlsx">${__("Excel")}</button><button class="btn btn-default btn-sm nxr-export-pdf">${__("PDF")}</button></div></section>
			<section class="nxr-bi-kpis"></section>
			<section class="nxr-bi-report-links">
				${reportCard("BI01", __("BI01 · Centro ejecutivo"), __("KPIs, control, proveedores y alertas"))}
				${reportCard("FI01", __("FI01 · Ingresos y remesas"), __("Saldos históricos, transferencias y conciliación"))}
				${reportCard("FI02", __("FI02 · Gastos"), __("Fuente, categoría, entidad y centro de costo"))}
				${reportCard("FI03", __("FI03 · Cuentas por pagar"), __("Vencimientos y obligaciones pendientes"))}
				${reportCard("CO01", __("CO01 · Estado contractual"), __("Adendas, anticipos, pagos, retenciones y saldo"))}
				${reportCard("PR02", __("PR02 · Presupuesto"), __("Aprobado, comprometido, ejecutado y disponible"))}
				${reportCard("PR03", __("PR03 · Fases y avance"), __("Avance físico, financiero y control operativo"))}
				${reportCard("MM03", __("MM03 · Inventario crítico"), __("Saldos agotados o negativos"))}
			</section>
			<section class="nxr-bi-grid"><article class="nxr-bi-card"><h3>${__("Gastos por categoría")}</h3><div class="nxr-report-expenses nxr-bars"></div></article><article class="nxr-bi-card"><h3>${__("Principales proveedores")}</h3><div class="nxr-report-providers nxr-bars"></div></article><article class="nxr-bi-card"><h3>${__("Ingresos por canal")}</h3><div class="nxr-report-income-channels nxr-bars"></div></article><article class="nxr-bi-card"><h3>${__("Control operativo")}</h3><div class="nxr-control-summary"></div></article></section>
			<section class="nxr-bi-table-card"><header><div><h3 class="nxr-report-title">FI01 · ${__("Ingresos y remesas")}</h3><small class="nxr-report-status"></small></div><div class="nxr-pagination-actions"><button class="btn btn-xs btn-default nxr-prev">${__("Anterior")}</button><button class="btn btn-xs btn-default nxr-next">${__("Siguiente")}</button></div></header><div class="nxr-report-table"></div></section>
			<section class="nxr-bi-table-card"><header><div><h3>${__("Reportes guardados")}</h3><small>${__("Filtros persistentes y trazables por usuario")}</small></div><button class="btn btn-xs btn-default nxr-closing" data-route="nexora-closing">${__("Cierre semanal")}</button></header><div class="nxr-saved-reports"></div></section>
		</main>
	`);

	page.add_button(__("Actualizar datos"), () => load(true), "primary");
	body.on("click", ".nxr-refresh", () => load(true));
	body.on("click", "[data-view]", function () { activeView = String($(this).data("view")); currentPage = 1; body.find("[data-view]").removeClass("is-active"); $(this).addClass("is-active"); loadView(false); });
	body.on("click", ".nxr-prev", () => { if (currentPage > 1) { currentPage -= 1; loadView(false); } });
	body.on("click", ".nxr-next", () => { if (currentPage * currentPagination.page_size < currentPagination.total) { currentPage += 1; loadView(false); } });
	body.on("click", ".nxr-export-xlsx", () => exportReport("xlsx"));
	body.on("click", ".nxr-export-pdf", () => exportReport("pdf"));
	body.on("click", ".nxr-save", saveReport);
	body.on("click", "[data-saved]", function () { applySaved($(this).data("saved")); });
	body.on("click", "[data-reconcile]", function () { openReconciliation($(this).data("reconcile")); });
	body.on("click", "[data-cancel-source]", function () { openCancellation($(this).data("cancel-source")); });
	body.on("click", "[data-route]", function () { frappe.route_options = { project: controls.project.get_value() || null }; frappe.set_route($(this).data("route")); });
	$(document).on("nexora:data-changed.nexora-reports", () => load(false));
	$(wrapper).on("remove", () => $(document).off("nexora:data-changed.nexora-reports"));

	const launchOptions = frappe.route_options || {};
	frappe.route_options = null;
	activeView = String(launchOptions.nexora_report || "FI01").toUpperCase();
	body.find(`[data-view="${activeView}"]`).addClass("is-active");
	// Un rechazo descartado dejaría el centro de reportes a medio inicializar y sin
	// rastro más allá de un "unhandledrejection" en consola.
	startWithActiveProject().catch((error) =>
		console.error("NEXORA reports failed to adopt the active project", error)
	);

	// El proyecto llega por la ruta si se navegó desde otra pantalla; si no, se hereda
	// del contexto activo en lugar de pedirlo otra vez.
	async function startWithActiveProject() {
		const project = launchOptions.project || (await window.nexora.context?.activeProject?.()) || null;
		if (project) {
			await setProjectSilently(project);
			load(false);
		} else if (requiresProjectSelection() && !controls.project.get_value()) {
			renderProjectPrompt();
		} else {
			load(false);
		}
		const release = window.nexora.context?.onContextChange?.(async (context) => {
			if ((controls.project.get_value() || "") === (context?.project || "")) return;
			await setProjectSilently(context?.project || "");
			resetAndLoad();
		});
		$(wrapper).on("remove", () => release?.());
	}

	async function setProjectSilently(project) {
		suppressControlReload = true;
		try {
			await controls.project.set_value(project || "");
		} finally {
			suppressControlReload = false;
		}
	}

	function payload() {
		return {
			project: controls.project.get_value() || null,
			from_date: controls.from_date.get_value() || null,
			to_date: controls.to_date.get_value() || null,
			source: controls.source.get_value() || null,
			economic_category: controls.economic_category.get_value() || null,
			cost_center: controls.cost_center.get_value() || null,
			entity: controls.entity.get_value() || null,
			payment_method: controls.payment_method.get_value() || null,
			contractor: controls.contractor.get_value() || null,
			contract_status: controls.contract_status.get_value() || null,
			page: currentPage,
			page_size: 25,
		};
	}

	function onFilterChange() { if (!suppressControlReload) resetAndLoad(); }
	function onProjectChange() { if (suppressControlReload) return; Promise.resolve(window.nexora.context?.setActiveProject?.(controls.project.get_value() || null)).catch((error) => console.error("NEXORA reports failed to publish the active project", error)); resetAndLoad(); }
	function resetAndLoad() { currentPage = 1; if (requiresProjectSelection() && !controls.project.get_value()) renderProjectPrompt(); else load(false); }
	function requiresProjectSelection() { return frappe.user.has_role("NEXORA Project Viewer") && !["System Manager", "NEXORA Administrator", "NEXORA Finance Manager", "NEXORA Finance Operator", "NEXORA Auditor"].some((role) => frappe.user.has_role(role)); }
	function renderProjectPrompt() { body.find(".nxr-bi-shell").attr({ "data-state": "ready", "aria-busy": "false" }); body.find(".nxr-report-table").html(empty(__("Seleccione un proyecto autorizado para consultar reportes."))); }

	async function load(freeze) {
		const serial = ++requestSerial;
		body.find(".nxr-bi-shell").attr({ "data-state": "loading", "aria-busy": "true" });
		try {
			const response = await frappe.call({ method: "nexora.dashboard.executive.get_executive_snapshot", type: "POST", args: { payload: payload() }, freeze: Boolean(freeze), freeze_message: __("Actualizando reportes…") });
			if (serial !== requestSerial) return;
			snapshot = response.message || {};
			renderSummary();
			await Promise.all([loadView(false), loadSavedReports()]);
			if (serial !== requestSerial) return;
			body.find(".nxr-bi-shell").attr({ "data-state": "ready", "aria-busy": "false" });
		} catch (error) {
			if (serial !== requestSerial) return;
			console.error("NEXORA reports failed", error);
			body.find(".nxr-bi-shell").attr({ "data-state": "error", "aria-busy": "false" });
			frappe.msgprint({ title: __("Reportes no disponibles"), message: __("Revise los filtros, el proyecto o sus permisos."), indicator: "red" });
		}
	}

	async function loadView(freeze) {
		const serial = ++viewSerial;
		if (["FI01", "FI02", "CO01"].includes(activeView)) {
			const methods = { FI01: "nexora.dashboard.executive.get_source_statement_page", FI02: "nexora.dashboard.executive.get_expense_page", CO01: "nexora.dashboard.executive.get_contract_page" };
			const response = await frappe.call({ method: methods[activeView], type: "POST", args: { payload: payload() }, freeze: Boolean(freeze) });
			if (serial !== viewSerial) return;
			currentRows = response.message?.rows || [];
			currentPagination = response.message?.pagination || { page: 1, page_size: 25, total: currentRows.length };
		} else {
			currentRows = rowsFromSnapshot(activeView);
			currentPagination = { page: 1, page_size: Math.max(currentRows.length, 1), total: currentRows.length };
		}
		if (serial === viewSerial) renderTable();
	}

	function rowsFromSnapshot(code) {
		if (code === "FI03") return snapshot.pending_accounts?.items || [];
		if (code === "PR02") return snapshot.budgets?.lines || [];
		if (code === "PR03") return [snapshot.progress || {}];
		if (code === "MM03") return snapshot.analytics?.critical_inventory || [];
		return [];
	}

	function renderSummary() {
		const e = snapshot.executive || {};
		const p = snapshot.progress || {};
		const kpis = [[__("Recibido"), money(e.received_hnl)], [__("Gastado"), money(e.spent_hnl)], [__("Pendiente"), money(snapshot.pending_accounts?.total_hnl)], [__("Disponible"), money(e.cash_available_hnl)], [__("Comprometido"), money(e.committed_hnl)], [__("Proyectado"), money(e.projected_available_hnl)], [__("Avance"), `${Number(p.physical_percent || 0).toFixed(1)}%`]];
		body.find(".nxr-bi-kpis").html(kpis.map((row) => `<article class="nxr-bi-kpi"><span>${escape(row[0])}</span><strong>${row[1]}</strong></article>`).join(""));
		renderBars(".nxr-report-expenses", snapshot.analytics?.expenses_by_category || [], (row) => row.label);
		renderBars(".nxr-report-providers", snapshot.analytics?.providers || [], (row) => row.label);
		renderBars(".nxr-report-income-channels", snapshot.analytics?.income_by_channel || [], (row) => channelLabels[row.label] || row.label);
		body.find(".nxr-control-summary").html(`<div class="nxr-progress-counts"><span><small>${__("Ingresos")}</small><strong>${snapshot.analytics?.source_pagination?.total || 0}</strong></span><span><small>${__("Sin conciliar")}</small><strong>${snapshot.analytics?.unreconciled_count || 0}</strong></span><span><small>${__("Contratos")}</small><strong>${snapshot.analytics?.contract_count || 0}</strong></span></div>`);
	}

	function renderTable() {
		const titles = { BI01: __("BI01 · Centro ejecutivo"), FI01: __("FI01 · Ingresos y remesas"), FI02: __("FI02 · Consolidado de gastos"), FI03: __("FI03 · Cuentas por pagar"), CO01: __("CO01 · Estado contractual"), PR02: __("PR02 · Presupuesto vs ejecución"), PR03: __("PR03 · Fases y avance"), MM03: __("MM03 · Inventario crítico") };
		const filterCount = Object.keys(snapshot.filter_context?.active || {}).length;
		body.find(".nxr-report-title").text(titles[activeView] || activeView);
		body.find(".nxr-report-status").text(__("Página {0} · {1} registro(s) · {2} filtro(s) activo(s)", [currentPagination.page || 1, currentPagination.total || 0, filterCount]));
		body.find(".nxr-prev").prop("disabled", currentPage <= 1);
		body.find(".nxr-next").prop("disabled", currentPage * currentPagination.page_size >= currentPagination.total);
		if (activeView === "FI01") return renderIncome(currentRows);
		if (activeView === "FI02") return renderExpenses(currentRows);
		if (activeView === "CO01") return renderContracts(currentRows);
		if (activeView === "FI03") return renderPayables(currentRows);
		if (activeView === "PR02") return renderBudget(currentRows);
		if (activeView === "PR03") return renderProgress(currentRows[0] || {});
		if (activeView === "MM03") return renderInventory(currentRows);
		renderExecutive();
	}

	function renderIncome(rows) { renderRows([__("Fuente"), __("Fecha"), __("Remitente"), __("Moneda"), __("Recibido"), __("Gastado"), __("Transferencias"), __("Reservado"), __("Saldo inicial"), __("Saldo cierre"), __("Disponible"), __("Conciliación"), __("Acciones")], rows.map((row) => [`<a href="${frappe.utils.get_form_link("NXR Fund Source", row.name)}">${escape(row.source_code || row.name)}</a>`, date(row.source_date), escape(row.origin_or_sender), escape(row.currency), money(row.received_hnl), money(row.spent_hnl), `${money(row.transfer_in_hnl)} / ${money(row.transfer_out_hnl)}`, money(row.closing_reserved_hnl), money(row.opening_funds_hnl), money(row.closing_funds_hnl), money(row.closing_available_hnl), badge(row.reconciliation_status), incomeActions(row)])); }
	function renderExpenses(rows) { renderRows([__("Documento"), __("Fecha"), __("Proveedor"), __("Categoría"), __("Centro de costo"), __("Fuentes"), __("Medio"), __("Referencia"), __("Importe"), __("Proyecto")], rows.map((row) => [`<a href="${frappe.utils.get_form_link("NXR Operation", row.name)}">${escape(row.document_number || row.name)}</a>`, date(row.operation_date), escape(row.beneficiary_label), escape(row.economic_category), escape(row.cost_center), escape(row.sources), escape(row.payment_method), escape(row.external_reference), money(row.amount_hnl), escape(row.project)])); }
	function renderContracts(rows) { renderRows([__("Contrato"), __("Contratista"), __("Estado"), __("Inicio"), __("Fin"), __("Valor"), __("Ejecutado"), __("Pagado"), __("Saldo"), __("Anticipo"), __("Retención"), __("Proyecto")], rows.map((row) => [`<a href="${frappe.utils.get_form_link("NXR Contract", row.name)}">${escape(row.document_number || row.name)}</a>`, escape(row.contractor_label), escape(row.status), date(row.start_date), date(row.current_end_date), money(row.contract_value_hnl), money(row.executed_hnl), money(row.paid_hnl), money(row.balance_hnl), money(row.advance_balance), money(row.retention_balance), escape(row.project)])); }
	function renderPayables(rows) { renderRows([__("Documento"), __("Beneficiario"), __("Vencimiento"), __("Importe"), __("Situación")], rows.map((row) => [escape(row.document_number || row.name), escape(row.beneficiary || row.title), date(row.due_date), money(row.amount_hnl), escape(row.due_state)])); }
	function renderBudget(rows) { renderRows([__("Categoría"), __("Aprobado"), __("Comprometido"), __("Ejecutado"), __("Disponible")], rows.map((row) => [escape(row.label || row.category), money(row.approved_hnl), money(row.committed_hnl), money(row.executed_hnl), money(row.available_hnl)])); }
	function renderProgress(row) { const operational = row.operational || {}; renderRows([__("Métrica"), __("Valor")], [[__("Avance físico"), `${Number(row.physical_percent || 0).toFixed(1)}%`], [__("Contratos activos"), operational.active_contracts || 0], [__("Solicitudes pendientes"), operational.pending_requests || 0], [__("Órdenes abiertas"), operational.open_orders || 0], [__("Calidad pendiente"), operational.open_quality_issues || 0]]); }
	function renderInventory(rows) { renderRows([__("Artículo"), __("Bodega"), __("Saldo")], rows.map((row) => [escape(row.item), escape(row.warehouse), number(row.balance_qty)])); }
	function renderExecutive() { const e = snapshot.executive || {}; renderRows([__("Indicador"), __("Valor")], [[__("Recibido"), money(e.received_hnl)], [__("Gastado"), money(e.spent_hnl)], [__("Pagado"), money(e.paid_hnl)], [__("Caja disponible"), money(e.cash_available_hnl)], [__("Comprometido"), money(e.committed_hnl)], [__("Presupuesto disponible"), money(e.budget_available_hnl)], [__("Disponible proyectado"), money(e.projected_available_hnl)]]); }

	function incomeActions(row) {
		const actions = [`<button class="btn btn-xs btn-default" data-reconcile="${escape(row.name)}">${__("Conciliar")}</button>`];
		if (["Active", "Exhausted"].includes(row.status)) actions.push(`<button class="btn btn-xs btn-danger" data-cancel-source="${escape(row.name)}">${__("Anular")}</button>`);
		return `<div class="nxr-inline-actions">${actions.join("")}</div>`;
	}
	function renderRows(headers, rows) { body.find(".nxr-report-table").html(rows.length ? table(headers, rows) : empty(__("No hay información para los filtros seleccionados."))); }
	function renderBars(selector, rows, label) { const visible = rows.slice(0, 6); const maximum = Math.max(...visible.map((row) => Number(row.amount_hnl || 0)), 1); body.find(selector).html(visible.length ? visible.map((row) => `<div class="nxr-bar-row"><span>${escape(label(row))}</span><b><i style="width:${Math.max((Number(row.amount_hnl || 0) / maximum) * 100, 2)}%"></i></b><strong>${money(row.amount_hnl)}</strong></div>`).join("") : empty(__("Sin datos."))); }

	function exportReport(format) {
		const form = document.createElement("form");
		form.method = "POST";
		form.target = "_blank";
		form.action = "/api/method/nexora.reports.service.export_report";
		const exportPayload = { ...payload(), report_code: activeView, format };
		[["payload", JSON.stringify(exportPayload)], ["csrf_token", frappe.csrf_token || ""]].forEach(([name, value]) => { const input = document.createElement("input"); input.type = "hidden"; input.name = name; input.value = value; form.appendChild(input); });
		document.body.appendChild(form);
		form.submit();
		form.remove();
	}

	async function saveReport() {
		const values = await promptValues([{ fieldname: "title", label: __("Título"), fieldtype: "Data", reqd: 1 }], __("Guardar reporte"));
		if (!values) return;
		await frappe.call({ method: "nexora.reports.service.save_report_definition", type: "POST", args: { payload: { title: values.title, report_code: activeView, project: controls.project.get_value() || null, filters: payload(), idempotency_key: `saved-report-${frappe.session.user}-${Date.now()}` } }, freeze: true, freeze_message: __("Guardando reporte…") });
		frappe.show_alert({ message: __("Reporte guardado."), indicator: "green" });
		await loadSavedReports();
	}

	async function loadSavedReports() {
		const response = await frappe.call({ method: "nexora.reports.service.list_saved_reports", type: "POST", args: { payload: { project: controls.project.get_value() || null } } });
		const rows = response.message || [];
		body.find(".nxr-saved-reports").html(rows.length ? rows.map((row) => `<button class="nxr-saved-report" data-saved="${escape(row.name)}" data-payload="${escape(JSON.stringify(row))}"><span><strong>${escape(row.title)}</strong><small>${escape(row.document_number)} · ${escape(row.report_code)} · ${date(row.modified)}</small></span><b>${__("Abrir")}</b></button>`).join("") : empty(__("No hay reportes guardados.")));
	}

	async function applySaved(name) {
		const element = body.find(`[data-saved="${CSS.escape(String(name))}"]`);
		const saved = JSON.parse(element.attr("data-payload") || "{}");
		activeView = saved.report_code || "FI01";
		suppressControlReload = true;
		try {
			for (const [key, value] of Object.entries(saved.filters || {})) if (controls[key]) await controls[key].set_value(value || null);
		} finally {
			suppressControlReload = false;
		}
		body.find("[data-view]").removeClass("is-active"); body.find(`[data-view="${activeView}"]`).addClass("is-active"); currentPage = 1; load(false);
	}

	function openReconciliation(source) {
		const dialog = new frappe.ui.Dialog({ title: __("Conciliar ingreso"), fields: [{ fieldname: "status", label: __("Estado"), fieldtype: "Select", options: "Reconciled\nDisputed\nPending", default: "Reconciled", reqd: 1 }, { fieldname: "method", label: __("Método"), fieldtype: "Select", options: "Bank Statement\nRemittance Statement\nReceipt\nManual" }, { fieldname: "difference_hnl", label: __("Diferencia HNL"), fieldtype: "Currency", default: 0 }, { fieldname: "evidence", label: __("Evidencia"), fieldtype: "Attach" }, { fieldname: "note", label: __("Observación"), fieldtype: "Small Text" }], primary_action_label: __("Guardar conciliación"), primary_action: async (values) => { await frappe.call({ method: "nexora.reports.service.reconcile_fund_source", type: "POST", args: { payload: { source, ...values, idempotency_key: `reconcile-${source}-${Date.now()}` } }, freeze: true, freeze_message: __("Guardando conciliación…") }); dialog.hide(); $(document).trigger("nexora:data-changed"); } });
		dialog.show();
	}

	function openCancellation(source) {
		const dialog = new frappe.ui.Dialog({ title: __("Anular ingreso"), fields: [{ fieldname: "reason", label: __("Motivo de anulación"), fieldtype: "Small Text", reqd: 1, description: __("La anulación no elimina el registro: crea una operación compensatoria y conserva la auditoría.") }], primary_action_label: __("Anular mediante compensación"), primary_action: async (values) => { const reason = String(values.reason || "").trim(); if (reason.length < 10) { frappe.msgprint(__("Explique el motivo con al menos 10 caracteres.")); return; } await frappe.call({ method: "nexora.financial.sources.cancel_fund_source", type: "POST", args: { source, reason, idempotency_key: `cancel-source-${source}` }, freeze: true, freeze_message: __("Registrando anulación compensatoria…") }); dialog.hide(); frappe.show_alert({ message: __("Ingreso anulado sin eliminar su historial."), indicator: "green" }); $(document).trigger("nexora:data-changed"); } });
		dialog.show();
	}

	function promptValues(fields, title) { return new Promise((resolve) => frappe.prompt(fields, resolve, title)); }
	function reportCard(code, title, description) { return `<button class="nxr-bi-report-card" data-view="${code}"><strong>${title}</strong><span>${description}</span></button>`; }
	function table(headers, rows) { return `<div class="table-responsive"><table class="table table-bordered"><thead><tr>${headers.map((header) => `<th>${escape(header)}</th>`).join("")}</tr></thead><tbody>${rows.map((row) => `<tr>${row.map((cell) => `<td>${cell ?? ""}</td>`).join("")}</tr>`).join("")}</tbody></table></div>`; }
	function badge(value) { const label = { Pending: __("Pendiente"), Reconciled: __("Conciliado"), Disputed: __("En disputa") }[value] || value; return `<span class="nxr-bi-badge ${value === "Reconciled" ? "" : "warning"}">${escape(label)}</span>`; }
	function money(value) { return window.nexora.ui.formatMoney(value); }
	function number(value) { return new Intl.NumberFormat("es-HN", { maximumFractionDigits: 6 }).format(Number(value || 0)); }
	function date(value) { return window.nexora.ui.formatDate(value); }
	function escape(value) { return window.nexora.ui.escapeHtml(value); }
	function empty(message) { return `<p class="nxr-executive-empty">${escape(message)}</p>`; }
};
