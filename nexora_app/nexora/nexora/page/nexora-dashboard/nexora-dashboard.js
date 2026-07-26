frappe.pages["nexora-dashboard"].on_page_load = function (wrapper) {
	const page = frappe.ui.make_app_page({
		parent: wrapper,
		title: __("NEXORA"),
		single_column: true,
	});

	const operationLabels = {
		Inflow: __("Ingreso"),
		Outflow: __("Egreso"),
		"Internal Transfer": __("Transferencia interna"),
		"Real Return": __("Devolución real"),
		Reclassification: __("Reclasificación"),
		"Analytic Adjustment": __("Ajuste analítico"),
		"Commitment Reserve": __("Reserva de compromiso"),
		"Commitment Execution": __("Pago de compromiso"),
		"Commitment Release": __("Liberación de compromiso"),
	};
	const statusLabels = {
		Draft: __("Borrador"),
		Submitted: __("Enviado"),
		"In Review": __("En revisión"),
		"Pending Approval": __("Pendiente de aprobación"),
		Approved: __("Aprobado"),
		Active: __("Activo"),
		Executed: __("Ejecutado"),
		Uploaded: __("Por revisar"),
		Validated: __("Validada"),
		Rejected: __("Rechazada"),
		Cancelled: __("Anulado"),
		Reversed: __("Revertido"),
	};
	const channelLabels = {
		Remittance: __("Remesa"),
		Cash: __("Efectivo"),
		Deposit: __("Depósito"),
		Transfer: __("Transferencia"),
		Other: __("Otro"),
	};
	let requestSerial = 0;

	const projectControl = page.add_field({
		fieldname: "project",
		label: __("Proyecto"),
		fieldtype: "Link",
		options: "Project",
		change: () => loadDashboard(false),
	});

	$(page.body).append(`
		<div class="nxr-dashboard-shell" data-state="loading">
			<section class="nxr-dashboard-welcome nxr-card">
				<div>
					<p class="nxr-eyebrow">${__("GESTIÓN INTEGRAL")}</p>
					<h2>${__("Resumen operativo")}</h2>
					<p>${__("Gestión Integral de Fondos, Proyectos y Operaciones")}</p>
					<p class="nxr-dashboard-context">${__("Todos los proyectos")}</p>
				</div>
				<div class="nxr-dashboard-primary-actions">
					<button class="btn btn-primary nxr-action-btn" data-route="nexora-finance" data-action="income">${__(
						"Registrar ingreso"
					)}</button>
					<button class="btn btn-default nxr-action-btn" data-route="nexora-finance" data-action="expense">${__(
						"Registrar gasto"
					)}</button>
					<button class="btn btn-default nxr-action-btn" data-route="nexora-evidence">${__("Subir evidencia")}</button>
				</div>
			</section>

			<div class="nxr-dashboard-grid">
				<section class="nxr-card nxr-dashboard-finance nxr-span-full">
					<div class="nxr-section-heading">
						<div><p class="nxr-eyebrow">${__("SALDOS REALES")}</p><h3>${__("Fondos disponibles")}</h3></div>
						<span class="nxr-muted nxr-source-count">—</span>
					</div>
					<div class="nxr-card-grid nxr-financial-kpis">
						<div class="nxr-stat-card nxr-stat-primary"><span class="nxr-stat-label">${__(
							"Saldo disponible"
						)}</span><span class="nxr-stat-value" data-field="finance.total_available_hnl" data-currency="1">—</span></div>
						<div class="nxr-stat-card"><span class="nxr-stat-label">${__(
							"Saldo en fondos"
						)}</span><span class="nxr-stat-value" data-field="finance.total_balance_hnl" data-currency="1">—</span></div>
						<div class="nxr-stat-card"><span class="nxr-stat-label">${__(
							"Reservado"
						)}</span><span class="nxr-stat-value" data-field="finance.total_reserved_hnl" data-currency="1">—</span></div>
						<div class="nxr-stat-card"><span class="nxr-stat-label">${__(
							"Ingresos"
						)}</span><span class="nxr-stat-value" data-field="finance.inflows_hnl" data-currency="1">—</span></div>
						<div class="nxr-stat-card"><span class="nxr-stat-label">${__(
							"Egresos"
						)}</span><span class="nxr-stat-value" data-field="finance.outflows_hnl" data-currency="1">—</span></div>
					</div>
				</section>

				<section class="nxr-card nxr-dashboard-sources nxr-span-full">
					<div class="nxr-section-heading">
						<div><p class="nxr-eyebrow">${__("ORIGEN DE LOS RECURSOS")}</p><h3>${__("Saldos por fondo")}</h3></div>
					</div>
					<div class="nxr-dashboard-source-rows nxr-dashboard-dynamic nxr-empty">${__("Cargando…")}</div>
				</section>

				<section class="nxr-card nxr-dashboard-budgets nxr-span-full">
					<div class="nxr-section-heading">
						<div><p class="nxr-eyebrow">${__("CONTROL FINANCIERO")}</p><h3>${__(
		"Presupuesto frente a ejecución"
	)}</h3></div>
						<span class="nxr-muted nxr-active-budget-count">—</span>
					</div>
					<div class="nxr-card-grid">
						<div class="nxr-stat-card"><span class="nxr-stat-label">${__(
							"Aprobado"
						)}</span><span class="nxr-stat-value" data-field="budgets.total_approved_hnl" data-currency="1">—</span></div>
						<div class="nxr-stat-card"><span class="nxr-stat-label">${__(
							"Comprometido"
						)}</span><span class="nxr-stat-value" data-field="budgets.total_committed_hnl" data-currency="1">—</span></div>
						<div class="nxr-stat-card"><span class="nxr-stat-label">${__(
							"Ejecutado"
						)}</span><span class="nxr-stat-value" data-field="budgets.total_executed_hnl" data-currency="1">—</span></div>
						<div class="nxr-stat-card"><span class="nxr-stat-label">${__(
							"Disponible"
						)}</span><span class="nxr-stat-value" data-field="budgets.total_available_hnl" data-currency="1">—</span></div>
					</div>
					<div class="nxr-budget-meter" aria-label="${__("Uso del presupuesto")}">
						<div class="nxr-budget-meter-copy"><span>${__(
							"Uso total"
						)}</span><strong class="nxr-budget-percent">0%</strong></div>
						<div class="nxr-progress-track"><span class="nxr-budget-bar" style="width:0%"></span></div>
					</div>
					<div class="nxr-budget-lines nxr-dashboard-dynamic nxr-empty">${__("Cargando…")}</div>
				</section>

				<section class="nxr-card nxr-dashboard-pending">
					<div class="nxr-section-heading">
						<div><p class="nxr-eyebrow">${__("OBLIGACIONES")}</p><h3>${__("Cuentas pendientes")}</h3></div>
						<strong class="nxr-pending-total">—</strong>
					</div>
					<div class="nxr-pending-rows nxr-dashboard-dynamic nxr-empty">${__("Cargando…")}</div>
				</section>

				<section class="nxr-card nxr-dashboard-upcoming">
					<div class="nxr-section-heading">
						<div><p class="nxr-eyebrow">${__("AGENDA FINANCIERA")}</p><h3>${__("Pagos próximos")}</h3></div>
					</div>
					<div class="nxr-upcoming-rows nxr-dashboard-dynamic nxr-empty">${__("Cargando…")}</div>
				</section>

				<section class="nxr-card nxr-dashboard-progress">
					<div class="nxr-section-heading">
						<div><p class="nxr-eyebrow">${__("OBRA")}</p><h3>${__("Avance físico")}</h3></div>
						<strong class="nxr-physical-percent">0%</strong>
					</div>
					<div class="nxr-progress-track nxr-progress-track-large">
						<span class="nxr-physical-bar" style="width:0%"></span>
					</div>
					<div class="nxr-progress-detail nxr-dashboard-dynamic nxr-empty">${__("Cargando…")}</div>
				</section>

				<section class="nxr-card nxr-dashboard-operational">
					<div class="nxr-section-heading">
						<div><p class="nxr-eyebrow">${__("OPERACIÓN")}</p><h3>${__("Estado operativo")}</h3></div>
					</div>
					<div class="nxr-card-grid nxr-operational-kpis">
						<div class="nxr-mini-stat"><span data-field="progress.operational.active_contracts">—</span><small>${__(
							"Contratos activos"
						)}</small></div>
						<div class="nxr-mini-stat"><span data-field="progress.operational.pending_requests">—</span><small>${__(
							"Solicitudes pendientes"
						)}</small></div>
						<div class="nxr-mini-stat"><span data-field="progress.operational.open_orders">—</span><small>${__(
							"Órdenes abiertas"
						)}</small></div>
						<div class="nxr-mini-stat"><span data-field="progress.operational.open_quality_issues">—</span><small>${__(
							"Revisiones de calidad"
						)}</small></div>
					</div>
				</section>

				<section class="nxr-card nxr-dashboard-evidence nxr-span-full">
					<div class="nxr-section-heading">
						<div><p class="nxr-eyebrow">${__("EXPEDIENTE VISUAL")}</p><h3>${__(
		"Evidencias y fotografías recientes"
	)}</h3></div>
						<button class="btn btn-xs btn-default nxr-action-btn" data-route="nexora-evidence">${__(
							"Ver evidencias"
						)}</button>
					</div>
					<div class="nxr-evidence-gallery nxr-dashboard-dynamic nxr-empty">${__("Cargando…")}</div>
				</section>

				<section class="nxr-card nxr-dashboard-alerts">
					<div class="nxr-section-heading">
						<div><p class="nxr-eyebrow">${__("ATENCIÓN")}</p><h3>${__("Alertas")}</h3></div>
					</div>
					<div class="nxr-alert-rows nxr-dashboard-dynamic nxr-empty">${__("Cargando…")}</div>
				</section>

				<section class="nxr-card nxr-dashboard-contracts">
					<div class="nxr-section-heading">
						<div><p class="nxr-eyebrow">${__("CONTRATACIÓN")}</p><h3>${__("Contratos relevantes")}</h3></div>
						<button class="btn btn-xs btn-default nxr-action-btn" data-route="nexora-contracts">${__(
							"Ver contratos"
						)}</button>
					</div>
					<div class="nxr-contract-rows nxr-dashboard-dynamic nxr-empty">${__("Cargando…")}</div>
				</section>

				<section class="nxr-card nxr-dashboard-recent nxr-span-full">
					<div class="nxr-section-heading">
						<div><p class="nxr-eyebrow">${__("LIBRO CENTRAL")}</p><h3>${__("Actividad reciente")}</h3></div>
					</div>
					<div class="nxr-dashboard-recent-rows nxr-dashboard-dynamic nxr-empty">${__("Cargando…")}</div>
				</section>

				<section class="nxr-card nxr-dashboard-actions nxr-span-full">
					<div class="nxr-section-heading">
						<div><p class="nxr-eyebrow">${__("ACCESOS")}</p><h3>${__("Gestión diaria")}</h3></div>
					</div>
					<div class="nxr-action-buttons">
						<button class="btn btn-default nxr-action-btn" data-route="nexora-finance">${__(
							"Fondos y operaciones"
						)}</button>
						<button class="btn btn-default nxr-action-btn" data-route="nexora-contracts">${__("Contratos")}</button>
						<button class="btn btn-default nxr-action-btn" data-route="nexora-suppliers">${__("Proveedores")}</button>
						<button class="btn btn-default nxr-action-btn" data-route="nexora-purchase-requests">${__(
							"Solicitudes de compra"
						)}</button>
						<button class="btn btn-default nxr-action-btn" data-route="nexora-evidence">${__("Evidencias")}</button>
						<button class="btn btn-default nxr-action-btn" data-route="nexora-reports">${__("Reportes")}</button>
						<button class="btn btn-default nxr-action-btn" data-route="nexora-search">${__("Buscar en NEXORA")}</button>
					</div>
				</section>
			</div>
		</div>
	`);

	$(page.body).on("click", ".nxr-action-btn", function () {
		const action = $(this).data("action");
		frappe.route_options = {
			project: projectControl.get_value() || null,
			nexora_action: action || null,
		};
		frappe.set_route($(this).data("route"));
	});

	page.add_button(__("Actualizar"), () => loadDashboard(true), "primary");
	const launchOptions = frappe.route_options || {};
	frappe.route_options = null;
	if (launchOptions.project) projectControl.set_value(launchOptions.project);
	loadDashboard(false);

	async function loadDashboard(showFreeze) {
		const serial = ++requestSerial;
		$(page.body).find(".nxr-dashboard-shell").attr("data-state", "loading");
		try {
			const response = await frappe.call({
				method: "nexora.dashboard.service.get_dashboard_summary",
				type: "POST",
				args: { payload: { project: projectControl.get_value() || null } },
				freeze: Boolean(showFreeze),
				freeze_message: __("Actualizando resumen operativo…"),
			});
			if (serial !== requestSerial) return;
			renderDashboard(response.message || {});
			$(page.body).find(".nxr-dashboard-shell").attr("data-state", "ready");
		} catch (error) {
			if (serial !== requestSerial) return;
			$(page.body)
				.find(".nxr-dashboard-dynamic")
				.addClass("nxr-empty")
				.text(__("No fue posible cargar esta información."));
			$(page.body).find(".nxr-dashboard-shell").attr("data-state", "failed");
			frappe.msgprint({
				title: __("Dashboard no disponible"),
				message: __("Revise su conexión o permisos e intente nuevamente."),
				indicator: "red",
			});
			console.error("NEXORA dashboard request failed", error);
		}
	}

	function readPath(data, path) {
		return path
			.split(".")
			.reduce((value, key) => (value !== null && value !== undefined ? value[key] : undefined), data);
	}

	function escape(value) {
		return frappe.utils.escape_html(String(value ?? ""));
	}

	function currency(value) {
		return frappe.format(Number(value || 0), { fieldtype: "Currency", options: "HNL" });
	}

	function userDate(value) {
		return value ? frappe.datetime.str_to_user(String(value).slice(0, 10)) : __("Sin fecha");
	}

	function formLink(doctype, name) {
		return frappe.utils.get_form_link(doctype, name);
	}

	function setEmpty(target, message) {
		target.empty().addClass("nxr-empty").text(message);
	}

	function renderDashboard(data) {
		$(page.body)
			.find("[data-field]")
			.each(function () {
				const value = readPath(data, $(this).data("field"));
				if (value !== undefined && value !== null) {
					$(this).text($(this).data("currency") ? currency(value) : value);
				}
			});
		$(page.body)
			.find(".nxr-dashboard-context")
			.text(data.context?.project_label || __("Todos los proyectos"));
		$(page.body)
			.find(".nxr-source-count")
			.text(
				data.finance?.source_count === 1
					? __("1 fondo")
					: __("{0} fondos", [data.finance?.source_count || 0])
			);
		const activeBudgetCount = data.budgets?.active_budget_count || 0;
		$(page.body)
			.find(".nxr-active-budget-count")
			.text(
				activeBudgetCount === 1
					? __("1 presupuesto activo")
					: __("{0} presupuestos activos", [activeBudgetCount])
			);
		$(page.body).find(".nxr-pending-total").text(currency(data.pending_accounts?.total_hnl));

		renderSources(data.finance?.sources || []);
		renderBudget(data.budgets || {});
		renderAccounts(
			".nxr-pending-rows",
			data.pending_accounts?.items || [],
			__("No hay cuentas pendientes.")
		);
		renderAccounts(
			".nxr-upcoming-rows",
			data.pending_accounts?.upcoming || [],
			__("No hay pagos con vencimiento próximo.")
		);
		renderProgress(data.progress || {});
		renderEvidence(data.evidence || {}, data.progress?.photos || []);
		renderAlerts(data.alerts || []);
		renderContracts(data.contracts?.items || []);
		renderOperations(data.recent_operations || []);
	}

	function renderSources(sources) {
		const target = $(page.body).find(".nxr-dashboard-source-rows").empty();
		if (!sources.length) {
			setEmpty(target, __("Aún no hay fondos registrados en este contexto."));
			return;
		}
		target.removeClass("nxr-empty");
		sources.forEach((source) => {
			$(`<article class="nxr-balance-row">
				<div class="nxr-balance-main">
					<a href="${formLink("NXR Fund Source", source.name)}"><strong>${escape(
				source.source_name || source.source_code
			)}</strong></a>
					<span>${escape(channelLabels[source.channel] || source.channel || __("Sin canal"))}</span>
				</div>
				<div><small>${__("Saldo")}</small><strong>${currency(source.balance_hnl)}</strong></div>
				<div><small>${__("Reservado")}</small><strong>${currency(source.reserved_hnl)}</strong></div>
				<div class="nxr-balance-available"><small>${__("Disponible")}</small><strong>${currency(
				source.available_hnl
			)}</strong></div>
			</article>`).appendTo(target);
		});
	}

	function renderBudget(budget) {
		const percent = Math.min(100, Math.max(0, Number(budget.utilization_percent || 0)));
		$(page.body)
			.find(".nxr-budget-percent")
			.text(`${Number(budget.utilization_percent || 0).toFixed(1)}%`);
		$(page.body).find(".nxr-budget-bar").css("width", `${percent}%`).attr("aria-valuenow", percent);
		const target = $(page.body).find(".nxr-budget-lines").empty();
		const lines = budget.lines || [];
		if (!lines.length) {
			setEmpty(target, __("No hay líneas presupuestarias para mostrar."));
			return;
		}
		target.removeClass("nxr-empty")
			.append(`<div class="table-responsive"><table class="table table-bordered">
			<thead><tr><th>${__("Categoría")}</th><th>${__("Aprobado")}</th><th>${__("Comprometido")}</th><th>${__(
			"Ejecutado"
		)}</th><th>${__("Disponible")}</th></tr></thead>
			<tbody></tbody></table></div>`);
		const body = target.find("tbody");
		lines.forEach((line) => {
			$(`<tr>
				<td>${escape(line.label)}</td>
				<td>${currency(line.approved_hnl)}</td>
				<td>${currency(line.committed_hnl)}</td>
				<td>${currency(line.executed_hnl)}</td>
				<td class="${Number(line.available_hnl) < 0 ? "text-danger" : ""}">${currency(line.available_hnl)}</td>
			</tr>`).appendTo(body);
		});
	}

	function dueBadge(account) {
		const labels = {
			overdue: __("Vencido"),
			today: __("Vence hoy"),
			upcoming: __("Próximo"),
			later: __("Programado"),
			undated: __("Sin fecha"),
		};
		return `<span class="nxr-due-badge nxr-due-${escape(account.due_state)}">${escape(
			labels[account.due_state] || labels.undated
		)}</span>`;
	}

	function renderAccounts(selector, accounts, emptyMessage) {
		const target = $(page.body).find(selector).empty();
		if (!accounts.length) {
			setEmpty(target, emptyMessage);
			return;
		}
		target.removeClass("nxr-empty");
		accounts.forEach((account) => {
			$(`<article class="nxr-list-row">
				<div>
					<a href="${formLink(account.doctype, account.name)}"><strong>${escape(account.document_number)}</strong></a>
					<span>${escape(account.title)}</span>
					<small>${escape(account.beneficiary || __("Sin beneficiario"))}</small>
				</div>
				<div class="nxr-list-row-value">
					<strong>${currency(account.amount_hnl)}</strong>
					<small>${userDate(account.due_date)}</small>
					${dueBadge(account)}
				</div>
			</article>`).appendTo(target);
		});
	}

	function renderProgress(progress) {
		const percent = Math.min(100, Math.max(0, Number(progress.physical_percent || 0)));
		$(page.body)
			.find(".nxr-physical-percent")
			.text(`${percent.toFixed(1)}%`);
		$(page.body).find(".nxr-physical-bar").css("width", `${percent}%`).attr("aria-valuenow", percent);
		const target = $(page.body).find(".nxr-progress-detail").empty();
		if (!progress.latest) {
			setEmpty(target, __("Todavía no hay un avance físico aprobado."));
			return;
		}
		target.removeClass("nxr-empty").html(`
			<a href="${formLink("NXR Progress Record", progress.latest.name)}"><strong>${escape(
			progress.latest.phase || __("Avance general")
		)}</strong></a>
			<p>${escape(progress.latest.description)}</p>
			<small>${__("Actualizado el {0}", [userDate(progress.latest.recorded_date)])}</small>
		`);
	}

	function renderEvidence(evidence, progressPhotos) {
		const target = $(page.body).find(".nxr-evidence-gallery").empty();
		const seen = new Set();
		const items = [];
		(evidence.items || []).forEach((item) => {
			if (!item.file_url || seen.has(item.file_url)) return;
			seen.add(item.file_url);
			items.push({
				...item,
				title: item.file_name || item.document_number,
				is_image: String(item.mime_type || "").startsWith("image/"),
			});
		});
		progressPhotos.forEach((url, index) => {
			if (!url || seen.has(url)) return;
			seen.add(url);
			items.push({
				file_url: url,
				title: __("Fotografía de avance {0}", [index + 1]),
				status: "Validated",
				is_image: /\.(png|jpe?g|webp|gif)(\?|$)/i.test(url),
			});
		});
		if (!items.length) {
			setEmpty(target, __("Aún no hay fotografías ni evidencias en este contexto."));
			return;
		}
		target.removeClass("nxr-empty");
		items.slice(0, 10).forEach((item) => {
			const preview = item.is_image
				? `<img src="${escape(item.file_url)}" alt="${escape(item.title)}" loading="lazy">`
				: `<div class="nxr-file-preview" aria-hidden="true">PDF</div>`;
			$(`<a class="nxr-evidence-tile" href="${escape(item.file_url)}" target="_blank" rel="noopener">
				${preview}
				<span><strong>${escape(item.title)}</strong><small>${escape(
				statusLabels[item.status] || item.status || __("Evidencia")
			)}</small></span>
			</a>`).appendTo(target);
		});
	}

	function renderAlerts(alerts) {
		const target = $(page.body).find(".nxr-alert-rows").empty();
		if (!alerts.length) {
			target
				.removeClass("nxr-empty")
				.append(
					`<div class="nxr-alert nxr-alert-success"><strong>${__(
						"Sin alertas críticas"
					)}</strong><span>${__(
						"La operación visible no requiere atención inmediata."
					)}</span></div>`
				);
			return;
		}
		target.removeClass("nxr-empty");
		alerts.forEach((alert) => {
			$(`<div class="nxr-alert nxr-alert-${escape(alert.level || "info")}">
				<strong>${escape(alert.title)}</strong><span>${escape(alert.message)}</span>
			</div>`).appendTo(target);
		});
	}

	function renderContracts(contracts) {
		const target = $(page.body).find(".nxr-contract-rows").empty();
		if (!contracts.length) {
			setEmpty(target, __("No hay contratos activos en este contexto."));
			return;
		}
		target.removeClass("nxr-empty");
		contracts.forEach((contract) => {
			$(`<article class="nxr-list-row">
				<div>
					<a href="${formLink("NXR Contract", contract.name)}"><strong>${escape(contract.document_number)}</strong></a>
					<span>${escape(contract.contractor_label || __("Sin contratista"))}</span>
					<small>${escape(statusLabels[contract.status] || contract.status)}</small>
				</div>
				<div class="nxr-list-row-value">
					<strong>${currency(contract.pending_amount_hnl)}</strong>
					<small>${__("Pendiente · fin {0}", [userDate(contract.current_end_date)])}</small>
				</div>
			</article>`).appendTo(target);
		});
	}

	function renderOperations(operations) {
		const target = $(page.body).find(".nxr-dashboard-recent-rows").empty();
		if (!operations.length) {
			setEmpty(target, __("No hay operaciones recientes para este contexto."));
			return;
		}
		target.removeClass("nxr-empty");
		target.append(`<div class="table-responsive"><table class="table table-bordered">
			<thead><tr><th>${__("Documento")}</th><th>${__("Fecha")}</th><th>${__("Movimiento")}</th><th>${__(
			"Monto"
		)}</th><th>${__("Estado")}</th></tr></thead>
			<tbody></tbody></table></div>`);
		const body = target.find("tbody");
		operations.forEach((operation) => {
			const link = formLink("NXR Operation", operation.name);
			const operationType =
				operationLabels[operation.operation_type] || operation.operation_type || "—";
			const status = statusLabels[operation.status] || operation.status || "—";
			$(`<tr>
				<td><a href="${link}">${escape(operation.document_number || operation.name)}</a></td>
				<td>${userDate(operation.operation_date)}</td>
				<td>${escape(operationType)}</td>
				<td>${currency(operation.amount_hnl)}</td>
				<td>${escape(status)}</td>
			</tr>`).appendTo(body);
		});
	}
};
