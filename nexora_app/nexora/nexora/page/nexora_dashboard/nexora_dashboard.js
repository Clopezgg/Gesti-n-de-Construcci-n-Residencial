// prettier-ignore
frappe.pages["nexora-dashboard"].on_page_load = function (wrapper) {
	const page = frappe.ui.make_app_page({ parent: wrapper, title: __("NEXORA"), single_column: true });
	const body = $(page.body);
	let requestSerial = 0;
	let activeContext = null;
	let synchronizingProject = false;
	const projectControl = page.add_field({
		fieldname: "project",
		label: __("Proyecto"),
		fieldtype: "Link",
		options: "Project",
		change: () => void projectChanged(),
	});
	const operationLabels = {
		Inflow: __("Ingreso"),
		Outflow: __("Gasto"),
		"Internal Transfer": __("Transferencia interna"),
		"Real Return": __("Devolución real"),
		"Commitment Reserve": __("Reserva de compromiso"),
		"Commitment Execution": __("Ejecución de compromiso"),
		"Commitment Release": __("Liberación de compromiso"),
	};
	const presentationLabels = { Cancellation: __("Anulado"), Income: __("Ingreso"), Expense: __("Gasto") };
	const statusLabels = {
		Draft: __("Borrador"),
		Executed: __("Registrado definitivamente"),
		Active: __("Activo"),
		Exhausted: __("Agotado"),
		Cancelled: __("Anulado"),
		"Compensated Partial": __("Corregido parcialmente"),
		"Compensated Total": __("Corregido totalmente"),
		Suspended: __("Suspendido"),
		"In Liquidation": __("En liquidación"),
	};
	const ledgerStatusLabels = { Posted: __("Registrado definitivamente") };
	const channelLabels = { Remittance: __("Remesas"), Cash: __("Efectivo"), Deposit: __("Depósitos"), Transfer: __("Transferencias"), Other: __("Otros") };
	const channelTypeLabels = { Remittance: __("Remesa"), Cash: __("Efectivo"), Deposit: __("Depósito"), Transfer: __("Transferencia"), Other: __("Otro") };
	const toneColors = { income: "var(--green-600, #218838)", expense: "var(--red-600, #c82333)", balance: "var(--blue-600, #0d6efd)", voided: "var(--red-600, #c82333)" };

	body.html(`
		<main class="nxr-product-shell nxr-dashboard-shell nxr-executive" data-state="loading" aria-busy="true">
			<section class="nxr-dashboard-welcome nxr-executive-hero">
				<div><p class="nxr-eyebrow">NX00 · ${__("RESUMEN EJECUTIVO")}</p><h2 class="nxr-project-name">${__("NEXORA")}</h2><p>${__("Gestión Integral de Fondos, Proyectos y Operaciones")}</p><small class="nxr-dashboard-context">${__("Preparando información canónica…")}</small><div class="nxr-dashboard-active-context"><span class="nxr-dashboard-period"></span><span class="nxr-dashboard-user"></span></div></div>
				<div class="nxr-dashboard-primary-actions"><span class="nxr-schedule-pill">${__("Actualizando")}</span><button class="btn btn-primary btn-sm" data-action="income">${__("Registrar ingreso")}</button><button class="btn btn-default btn-sm" data-action="expense">${__("Registrar gasto")}</button></div>
			</section>
			<section class="nxr-alert-rows nxr-executive-alerts"></section>
			<section class="nxr-executive-metrics"></section>
			<section class="nxr-executive-grid nxr-executive-primary">
				<article class="nxr-executive-card"><header><div><strong>${__("Avance de la obra")}</strong><span>${__("Comparación física y financiera")}</span></div><button class="btn btn-xs btn-default" data-route="nexora-reports" data-report="PR03">${__("Detalle")}</button></header><div class="nxr-progress-summary"></div></article>
				<article class="nxr-executive-card"><header><div><strong>${__("Gastos por categoría")}</strong><span>${__("Ejecución del período activo")}</span></div><button class="btn btn-xs btn-default" data-route="nexora-reports" data-report="FI02">${__("Ver gastos")}</button></header><div class="nxr-expense-bars nxr-bars"></div></article>
				<article class="nxr-executive-card"><header><div><strong>${__("Ingresos por canal")}</strong><span>${__("Remesas, depósitos y transferencias")}</span></div><button class="btn btn-xs btn-default" data-route="nexora-reports" data-report="FI01">${__("Ver ingresos")}</button></header><div class="nxr-income-bars nxr-bars"></div></article>
			</section>
			<section class="nxr-executive-grid nxr-executive-secondary">
				<article class="nxr-executive-card nxr-compact"><header><div><strong>${__("Pendiente de pagar")}</strong><span>${__("Vencido o próximo")}</span></div><button class="btn btn-xs btn-default" data-route="nexora-reports" data-report="FI03">${__("Revisar pendientes")}</button></header><div class="nxr-payables-list"></div></article>
				<article class="nxr-executive-card nxr-compact"><header><div><strong>${__("Fondos y remesas")}</strong><span>${__("Saldo independiente por fondo")}</span></div><button class="btn btn-xs btn-default" data-route="nexora-reports" data-report="FI01">${__("Estado de cuenta")}</button></header><div class="nxr-balance-row nxr-funds-list"></div></article>
				<article class="nxr-executive-card nxr-compact"><header><div><strong>${__("Inventario crítico")}</strong><span>${__("Saldos agotados o negativos")}</span></div><button class="btn btn-xs btn-default" data-route="nexora-reports" data-report="MM03">${__("Revisar inventario")}</button></header><div class="nxr-inventory-list"></div></article>
			</section>
			<section class="nxr-executive-grid nxr-executive-secondary">
				<article class="nxr-executive-card nxr-compact"><header><div><strong>${__("Actividad reciente")}</strong><span>${__("Historial financiero cronológico")}</span></div><button class="btn btn-xs btn-default" data-route="nexora-finance" data-nexora-operational-ledger="1">${__("Ver actividad")}</button></header><div class="nxr-activity-list"></div></article>
				<article class="nxr-executive-card nxr-compact"><header><div><strong>${__("Comprobantes y fotografías")}</strong><span>${__("Expediente cronológico")}</span></div><button class="btn btn-xs btn-default" data-route="nexora-evidence">${__("Ver comprobantes")}</button></header><div class="nxr-evidence-gallery"></div></article>
				<article class="nxr-executive-card nxr-compact"><header><div><strong>${__("Tareas frecuentes")}</strong><span>${__("Acciones según su contexto activo")}</span></div></header><div class="nxr-quick-links"><button data-route="nexora-purchase-requests">${__("Crear solicitud de compra")}</button><button data-route="nexora-suppliers">${__("Revisar proveedores")}</button><button data-route="nexora-search">${__("Buscar documento")}</button><button data-route="nexora-closing">${__("Revisar cierre")}</button></div></article>
			</section>
			<section class="nxr-executive-card nxr-contract-panel"><header><div><strong>${__("Estado contractual")}</strong><span>${__("Valor, ejecutado, pagado y saldo")}</span></div><button class="btn btn-xs btn-default" data-route="nexora-reports" data-report="CO01">${__("Ver contratos")}</button></header><div class="nxr-contract-rows nxr-contract-table"></div></section>
			<section class="nxr-executive-card"><header><div><strong>${__("Últimos movimientos")}</strong><span>${__("Trazabilidad financiera")}</span></div></header><div class="table-responsive"><table class="table nxr-dashboard-recent-rows"><thead><tr><th>${__("Documento")}</th><th>${__("Fecha")}</th><th>${__("Tipo")}</th><th>${__("Estado")}</th><th class="text-right">${__("Importe")}</th></tr></thead><tbody></tbody></table></div></section>
		</main>
	`);

	page.add_button(__("Actualizar datos"), () => load(true), "primary");
	body.on("click", "[data-action]", function () {
		const action = $(this).data("action");
		frappe.route_options = { ...routeContext(), nexora_action: action };
		frappe.set_route("nexora-finance");
	});
	body.on("click", "[data-route]:not([data-action])", function () {
		frappe.route_options = { ...routeContext(), nexora_report: $(this).data("report") || null };
		frappe.set_route($(this).data("route"));
	});
	$(document).on("nexora:data-changed.nexora-dashboard", () => load(false));
	const contextListener = (event) => void applyContext(event.detail || {}, true);
	document.addEventListener("nexora:context-changed", contextListener);
	$(wrapper).on("remove", () => {
		$(document).off("nexora:data-changed.nexora-dashboard");
		document.removeEventListener("nexora:context-changed", contextListener);
	});

	const launchOptions = frappe.route_options || {};
	frappe.route_options = null;
	void initialize(launchOptions);

	async function initialize(options) {
		try {
			const context = await window.nexora.context?.load?.({ silent: true });
			activeContext = context || fallbackContext(options.project);
			if (options.project && options.project !== activeContext.project) {
				activeContext = (await window.nexora.context?.update?.({ project: options.project }, { skipConfirmation: true })) || { ...activeContext, project: options.project };
			}
		} catch (error) {
			console.warn("NEXORA dashboard context fallback", error);
			activeContext = fallbackContext(options.project);
		}
		await applyContext(activeContext, true);
	}

	function fallbackContext(project = null) {
		return {
			project: project || null,
			project_label: project || __("Todos los proyectos"),
			period: "",
			from_date: null,
			to_date: null,
			user_label: frappe.session.user,
			role_label: __("Usuario NEXORA"),
			can_view_all_projects: !requiresProjectSelectionFromRoles(),
			can_view_financial_details: true,
			requires_project_selection: requiresProjectSelectionFromRoles() && !project,
		};
	}

	async function applyContext(context, reload) {
		activeContext = { ...fallbackContext(), ...(context || {}) };
		const desiredProject = activeContext.project || "";
		if ((projectControl.get_value() || "") !== desiredProject) {
			synchronizingProject = true;
			try {
				await projectControl.set_value(desiredProject);
			} finally {
				synchronizingProject = false;
			}
		}
		renderIdentity();
		if (!reload) return;
		if (requiresProjectSelection()) renderProjectPrompt();
		else await load(false);
	}

	async function projectChanged() {
		if (synchronizingProject) return;
		const project = projectControl.get_value() || null;
		if (!window.nexora.context?.update) {
			activeContext = { ...fallbackContext(project), ...(activeContext || {}), project };
			if (requiresProjectSelection()) renderProjectPrompt();
			else await load(false);
			return;
		}
		const updated = await window.nexora.context.update({ project });
		if (!updated) {
			await applyContext(activeContext, false);
			return;
		}
		await applyContext(updated, true);
	}

	function routeContext() {
		return {
			project: projectControl.get_value() || activeContext?.project || null,
			from_date: activeContext?.from_date || null,
			to_date: activeContext?.to_date || null,
			nexora_period: activeContext?.period || null,
		};
	}

	function snapshotPayload() {
		return {
			project: projectControl.get_value() || activeContext?.project || null,
			from_date: activeContext?.from_date || null,
			to_date: activeContext?.to_date || null,
		};
	}

	function requiresProjectSelectionFromRoles() {
		return frappe.user.has_role("NEXORA Project Viewer") && ![
			"System Manager",
			"NEXORA Administrator",
			"NEXORA Finance Manager",
			"NEXORA Finance Operator",
			"NEXORA Auditor",
		].some((role) => frappe.user.has_role(role));
	}

	function requiresProjectSelection() {
		return Boolean(activeContext?.requires_project_selection || (requiresProjectSelectionFromRoles() && !projectControl.get_value()));
	}

	function requestExecutiveSnapshot(payload, freeze) {
		return new Promise((resolve, reject) => {
			let settled = false;
			const finish = (callback, value) => {
				if (settled) return;
				settled = true;
				window.clearTimeout(deadline);
				callback(value);
			};
			const deadline = window.setTimeout(
				() =>
					finish(
						reject,
						new Error(
							__(
								"El resumen ejecutivo excedió 120 segundos. Revise la conexión y vuelva a intentar.",
							),
						),
				),
				120000,
			);
			try {
				frappe.call({
					method: "nexora.dashboard.executive.get_executive_snapshot",
					type: "POST",
					args: { payload },
					freeze,
					freeze_message: __("Actualizando resumen ejecutivo…"),
					callback: (response) => finish(resolve, response?.message || {}),
					error: (error) =>
						finish(
							reject,
							error instanceof Error
								? error
								: new Error(__("El servidor no pudo entregar el resumen ejecutivo.")),
						),
				});
			} catch (error) {
				finish(reject, error);
			}
		});
	}

	function renderIdentity(period = null) {
		const periodText = period?.from_date && period?.to_date ? `${date(period.from_date)} — ${date(period.to_date)}` : activeContext?.period || __("Período actual");
		body.find(".nxr-dashboard-period").text(`${__("Período")}: ${periodText}`);
		body.find(".nxr-dashboard-user").text(`${activeContext?.user_label || frappe.session.user} · ${activeContext?.role_label || __("Usuario NEXORA")}`);
	}

	function renderProjectPrompt() {
		body.find(".nxr-dashboard-shell").attr({ "data-state": "ready", "aria-busy": "false" });
		body.find(".nxr-project-name").text(__("Seleccione un proyecto"));
		body.find(".nxr-dashboard-context").text(__("Su perfil requiere un proyecto autorizado para mostrar información financiera."));
		body.find(".nxr-executive-alerts").html(alertCard("info", __("Proyecto requerido"), __("Use el selector de contexto para continuar.")));
		renderIdentity();
		renderMetrics([]);
	}

	async function load(freeze) {
		if (requiresProjectSelection()) {
			renderProjectPrompt();
			return;
		}
		const serial = ++requestSerial;
		body.find(".nxr-dashboard-shell").attr({ "data-state": "loading", "aria-busy": "true" });
		try {
			const snapshot = await requestExecutiveSnapshot(snapshotPayload(), Boolean(freeze));
			if (serial !== requestSerial) return;
			render(snapshot);
		} catch (error) {
			if (serial !== requestSerial) return;
			console.error("NEXORA dashboard failed", error);
			body.find(".nxr-dashboard-shell").attr({ "data-state": "error", "aria-busy": "false" });
			window.nexora.ui?.showError?.(error, { title: __("Resumen no disponible"), fallback: __("Revise la conexión, el proyecto o sus permisos y vuelva a intentar.") }) || frappe.msgprint({ title: __("Resumen no disponible"), message: __("Revise la conexión, el proyecto o sus permisos y vuelva a intentar."), indicator: "red" });
		}
	}

	function render(data) {
		const finance = data.finance || {};
		const budgets = data.budgets || {};
		const pendingAccounts = data.pending_accounts || {};
		const progress = data.progress || {};
		const analytics = data.analytics || {};
		const executive = data.executive || {};
		const sourceTotals = analytics.source_totals || {};
		body.find(".nxr-project-name").text(data.context?.project_label || activeContext?.project_label || __("Todos los proyectos"));
		body.find(".nxr-dashboard-context").text(`${finance.source_count || 0} ${__("fondos")} · ${analytics.contract_count || 0} ${__("contratos")} · ${pendingAccounts.count || 0} ${__("pendientes de pago")}`);
		body.find(".nxr-schedule-pill").text(Number(executive.projected_available_hnl || 0) < 0 ? __("Atención financiera") : __("Información actualizada"));
		renderIdentity(data.period || null);
		renderAlerts(data.alerts || [], analytics.unreconciled_count || 0, sourceTotals);
		const metrics = [
			{ label: __("Saldo disponible"), value: finance.total_available_hnl ?? executive.cash_available_hnl, tone: "balance" },
			{ label: __("Comprometido"), value: executive.committed_hnl ?? finance.total_reserved_hnl, tone: "balance" },
			{ label: __("Pendiente de pagar"), value: executive.pending_obligations_hnl ?? pendingAccounts.total_hnl, tone: "expense" },
			{ label: __("Ingresos netos"), value: executive.net_received_hnl ?? executive.received_hnl, tone: "income" },
			{ label: __("Gastos ejecutados"), value: executive.spent_hnl, tone: "expense" },
			{ label: __("Presupuesto disponible"), value: executive.budget_available_hnl ?? budgets.total_available_hnl, tone: "balance" },
		];
		renderMetrics(activeContext?.can_view_financial_details === false ? [] : metrics);
		renderProgress(progress.physical_percent, executive.financial_percent, progress.operational || {});
		renderBars(".nxr-expense-bars", analytics.expenses_by_category || [], (row) => row.label, "expense");
		renderBars(".nxr-income-bars", analytics.income_by_channel || [], (row) => channelLabels[row.label] || row.label, "income");
		renderPayables(pendingAccounts.items || []);
		renderFunds(analytics.rows || []);
		renderInventory(analytics.critical_inventory || []);
		renderActivity(data.recent_operations || []);
		renderEvidence(data.evidence?.items || []);
		renderContracts(analytics.contracts || data.contracts?.items || []);
		renderRecent(data.recent_operations || []);
		body.find(".nxr-dashboard-shell").attr({ "data-state": "ready", "aria-busy": "false" });
	}

	function renderAlerts(alerts, unreconciled, sourceTotals) {
		const rows = [...alerts];
		if (unreconciled) rows.push({ level: "warning", title: __("Ingresos sin conciliar"), message: __("{0} ingreso(s) requieren conciliación documental.", [unreconciled]) });
		if (Number(sourceTotals.reversed_hnl || 0) > 0) rows.push({ level: "info", title: __("Movimientos corregidos"), message: __("El período incluye anulaciones o reversos preservados en el historial financiero.") });
		if (!rows.length) rows.push({ level: "success", title: __("Operación al día"), message: __("No hay alertas críticas en este momento.") });
		body.find(".nxr-alert-rows").html(rows.slice(0, 5).map((row) => alertCard(row.level, row.title, row.message)).join(""));
	}

	function alertCard(level, title, message) { return `<article class="nxr-executive-alert" data-level="${escape(level)}"><i></i><span><strong>${escape(title)}</strong><small>${escape(message)}</small></span></article>`; }
	function renderMetrics(rows) { body.find(".nxr-executive-metrics").html(rows.length ? rows.map((row) => { const tone = row.tone === "income" && Number(row.value || 0) < 0 ? "voided" : row.tone; return `<article class="nxr-executive-metric" data-tone="${escape(tone || "neutral")}"><span>${escape(row.label)}</span><strong${toneStyle(tone)}>${money(row.value)}</strong></article>`; }).join("") : `<article class="nxr-executive-metric"><span>${__("Información financiera")}</span><strong>${requiresProjectSelection() ? __("Seleccione un proyecto") : __("No disponible para este perfil")}</strong></article>`); }
	function renderProgress(physicalValue, financialValue, operational) { const physical = Number(physicalValue || 0); const financial = Number(financialValue || 0); body.find(".nxr-progress-summary").html(`<div class="nxr-progress-pair"><div><span>${__("Avance físico")}</span><strong>${physical.toFixed(1)}%</strong><div class="nxr-progress-track"><i style="width:${clamp(physical)}%"></i></div></div><div><span>${__("Avance financiero")}</span><strong>${financial.toFixed(1)}%</strong><div class="nxr-progress-track is-financial"><i style="width:${clamp(financial)}%"></i></div></div></div><div class="nxr-progress-counts"><span><small>${__("Contratos activos")}</small><strong>${operational.active_contracts || 0}</strong></span><span><small>${__("Solicitudes")}</small><strong>${operational.pending_requests || 0}</strong></span><span><small>${__("Calidad")}</small><strong>${operational.open_quality_issues || 0}</strong></span></div>`); }
	function renderBars(selector, rows, rowLabel, tone) { const visible = rows.slice(0, 5); const maximum = Math.max(...visible.map((row) => Math.abs(Number(row.amount_hnl || 0))), 1); body.find(selector).html(visible.length ? visible.map((row) => { const rowTone = Number(row.amount_hnl || 0) < 0 ? "voided" : tone; return `<div class="nxr-bar-row" data-tone="${escape(rowTone)}"><span>${escape(rowLabel(row))}</span><b><i style="width:${Math.max((Math.abs(Number(row.amount_hnl || 0)) / maximum) * 100, 2)}%;background:${toneColor(rowTone)}"></i></b><strong${toneStyle(rowTone)}>${money(row.amount_hnl)}</strong></div>`; }).join("") : empty(__("Sin datos para mostrar."))); }
	function renderPayables(rows) { body.find(".nxr-payables-list").html(rows.length ? rows.slice(0, 4).map((row) => `<a class="nxr-executive-row" data-tone="expense" href="${frappe.utils.get_form_link(row.doctype, row.name)}"><span><strong>${escape(row.title || row.document_number)}</strong><small>${escape(row.beneficiary || date(row.due_date))}</small></span><b${toneStyle("expense")}>${money(row.amount_hnl)}</b></a>`).join("") : empty(__("No hay cuentas vencidas."))); }
	function renderFunds(rows) { body.find(".nxr-funds-list").html(rows.length ? rows.slice(0, 4).map((row) => `<a class="nxr-executive-row" data-tone="balance" href="${frappe.utils.get_form_link("NXR Fund Source", row.name)}"><span><strong>${escape(row.origin_or_sender || row.source_name)}</strong><small>${escape(channelLabels[row.channel] || row.channel)} · ${date(row.source_date)}</small></span><b${toneStyle("balance")}>${money(row.current_available_hnl)}</b></a>`).join("") : empty(__("No hay ingresos registrados."))); }
	function renderInventory(rows) { body.find(".nxr-inventory-list").html(rows.length ? rows.map((row) => `<div class="nxr-executive-row"><span><strong>${escape(row.item)}</strong><small>${escape(row.warehouse)}</small></span><b>${number(row.balance_qty)}</b></div>`).join("") : empty(__("No hay saldos críticos."))); }
	function renderActivity(rows) { body.find(".nxr-activity-list").html(rows.length ? rows.slice(0, 4).map((row) => { const tone = operationTone(row); return `<a class="nxr-executive-row" data-tone="${escape(tone)}" data-kind="${escape(row.presentation_kind || row.operation_type)}" href="${frappe.utils.get_form_link("NXR Operation", row.name)}"><span><strong>${escape(row.document_number || row.name)}</strong><small>${date(row.operation_date)} · ${ledgerValue(operationTypeLabel(row), row, "type")}</small></span><b${toneStyle(tone)}>${row.presentation_struck ? `<s>${money(row.amount_hnl)}</s>` : money(row.amount_hnl)}</b></a>`; }).join("") : empty(__("No hay actividad reciente."))); }
	function renderEvidence(rows) { body.find(".nxr-evidence-gallery").html(rows.length ? rows.slice(0, 6).map((row) => `<a class="nxr-evidence-tile" href="${escape(row.file_url)}" target="_blank" rel="noopener"><img src="${escape(row.file_url)}" alt="${escape(row.file_name || row.evidence_kind || __("Comprobante"))}" loading="eager"><span>${escape(window.nexora.ui?.label?.("evidenceKind", row.evidence_kind) || row.evidence_kind || row.file_name)}</span></a>`).join("") : empty(__("No hay comprobantes recientes."))); }
	function renderContracts(rows) { const target = body.find(".nxr-contract-rows"); if (!rows.length) { target.html(empty(__("No hay contratos registrados."))); return; } target.html(`<div class="table-responsive"><table class="table"><thead><tr><th>${__("Contrato")}</th><th>${__("Contratista")}</th><th>${__("Estado")}</th><th>${__("Inicio")}</th><th>${__("Fin")}</th><th class="text-right">${__("Valor")}</th><th class="text-right">${__("Pagado")}</th><th class="text-right">${__("Saldo")}</th></tr></thead><tbody>${rows.map((row) => `<tr><td><a href="${frappe.utils.get_form_link("NXR Contract", row.name)}">${escape(row.document_number || row.name)}</a></td><td>${escape(row.contractor_label || row.contractor)}</td><td>${escape(window.nexora.ui?.label?.("status", row.status) || statusLabels[row.status] || row.status)}</td><td>${date(row.start_date)}</td><td>${date(row.current_end_date)}</td><td class="text-right">${money(row.contract_value_hnl ?? row.current_amount)}</td><td class="text-right">${money(row.paid_hnl ?? row.paid_amount)}</td><td class="text-right">${money(row.balance_hnl ?? row.pending_amount)}</td></tr>`).join("")}</tbody></table></div>`); }
	function renderRecent(rows) { body.find(".nxr-dashboard-recent-rows tbody").html(rows.slice(0, 6).map((row) => { const tone = operationTone(row); return `<tr data-operation="${escape(row.name)}" data-kind="${escape(row.presentation_kind || row.operation_type)}" data-tone="${escape(tone)}"><td><a href="${frappe.utils.get_form_link("NXR Operation", row.name)}">${escape(row.document_number || row.name)}</a></td><td>${date(row.operation_date)}</td><td>${ledgerValue(operationTypeLabel(row), row, "type")}</td><td>${escape(operationStatusLabel(row))}</td><td class="text-right">${ledgerValue(money(row.amount_hnl), row, "amount")}</td></tr>`; }).join("")); }
	function operationTypeLabel(row) { const kind = row.presentation_kind || row.operation_type; const base = presentationLabels[kind] || operationLabels[row.operation_type] || row.operation_type; return kind === "Income" && row.source_channel ? `${base} · ${channelTypeLabels[row.source_channel] || row.source_channel}` : base; }
	function operationStatusLabel(row) { return window.nexora.ui?.label?.("status", row.presentation_status || row.status) || ledgerStatusLabels[row.presentation_status] || statusLabels[row.status] || row.status; }
	function operationTone(row) { return toneColors[row.presentation_tone] ? row.presentation_tone : "neutral"; }
	function ledgerValue(value, row, kind) { const content = escape(value); const decorated = row.presentation_struck ? `<s>${content}</s>` : content; return `<span class="nxr-ledger-${kind}" data-tone="${escape(operationTone(row))}"${toneStyle(operationTone(row))}>${decorated}</span>`; }
	function toneColor(tone) { return toneColors[tone] || "var(--blue-500, #2490ef)"; }
	function toneStyle(tone) { return toneColors[tone] ? ` style="color:${toneColors[tone]}"` : ""; }
	function money(value) { return window.nexora.ui?.formatMoney?.(value) || new Intl.NumberFormat("es-HN", { style: "currency", currency: "HNL", minimumFractionDigits: 2 }).format(Number(value || 0)); }
	function number(value) { return new Intl.NumberFormat("es-HN", { maximumFractionDigits: 6 }).format(Number(value || 0)); }
	function date(value) { return window.nexora?.ui?.formatDate?.(value) || (value ? frappe.datetime.str_to_user(String(value).slice(0, 10)) : __("Sin fecha")); }
	function clamp(value) { return Math.max(0, Math.min(Number(value || 0), 100)); }
	function escape(value) { return window.nexora?.ui?.escapeHtml?.(value) || frappe.utils.escape_html(String(value ?? "")); }
	function empty(message) { return `<p class="nxr-executive-empty">${escape(message)}</p>`; }
};
