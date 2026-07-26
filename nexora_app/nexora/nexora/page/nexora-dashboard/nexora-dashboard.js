frappe.pages["nexora-dashboard"].on_page_load = function (wrapper) {
	const page = frappe.ui.make_app_page({
		parent: wrapper,
		title: __("NEXORA — Control de obras"),
		single_column: true,
	});

	const operationLabels = {
		Inflow: __("Ingreso"),
		Outflow: __("Egreso"),
		Transfer: __("Transferencia"),
		Return: __("Devolución"),
		"Commitment Reserve": __("Reserva de compromiso"),
	};
	const statusLabels = {
		Draft: __("Borrador"),
		Submitted: __("Enviado"),
		"In Review": __("En revisión"),
		"Pending Approval": __("Pendiente de aprobación"),
		Approved: __("Aprobado"),
		Executed: __("Ejecutado"),
		Cancelled: __("Anulado"),
		Reversed: __("Revertido"),
	};

	const projectControl = page.add_field({
		fieldname: "project",
		label: __("Proyecto"),
		fieldtype: "Link",
		options: "Project",
		change: () => loadDashboard(),
	});

	$(page.body).append(`
		<div class="nxr-dashboard-shell">
			<section class="nxr-dashboard-welcome nxr-card">
				<div>
					<p class="nxr-eyebrow">${__("GESTIÓN INTEGRAL")}</p>
					<h2>${__("Resumen operativo")}</h2>
					<p>${__("Fondos, presupuesto, contratos y operaciones en una sola vista.")}</p>
				</div>
				<div class="nxr-dashboard-primary-actions">
					<button class="btn btn-primary nxr-action-btn" data-route="nexora-finance" data-operation="Inflow">${__(
						"Registrar ingreso"
					)}</button>
					<button class="btn btn-default nxr-action-btn" data-route="nexora-finance" data-operation="Outflow">${__(
						"Registrar egreso"
					)}</button>
				</div>
			</section>

			<div class="nxr-dashboard-grid">
				<section class="nxr-card nxr-dashboard-budgets">
					<div class="nxr-section-heading">
						<div><p class="nxr-eyebrow">${__("CONTROL FINANCIERO")}</p><h3>${__("Presupuesto")}</h3></div>
						<span class="nxr-muted nxr-active-budget-count">—</span>
					</div>
					<div class="nxr-card-grid">
						<div class="nxr-stat-card"><span class="nxr-stat-label">${__("Aprobado")}</span><span class="nxr-stat-value" data-field="budgets.total_approved_hnl" data-currency="1">—</span></div>
						<div class="nxr-stat-card"><span class="nxr-stat-label">${__("Comprometido")}</span><span class="nxr-stat-value" data-field="budgets.total_committed_hnl" data-currency="1">—</span></div>
						<div class="nxr-stat-card"><span class="nxr-stat-label">${__("Ejecutado")}</span><span class="nxr-stat-value" data-field="budgets.total_executed_hnl" data-currency="1">—</span></div>
						<div class="nxr-stat-card"><span class="nxr-stat-label">${__("Disponible")}</span><span class="nxr-stat-value" data-field="budgets.total_available_hnl" data-currency="1">—</span></div>
					</div>
				</section>

				<section class="nxr-card nxr-dashboard-counts">
					<div class="nxr-section-heading"><div><p class="nxr-eyebrow">${__("ACTIVIDAD")}</p><h3>${__("Indicadores")}</h3></div></div>
					<div class="nxr-card-grid">
						<div class="nxr-stat-card"><span class="nxr-stat-label">${__("Contratos activos")}</span><span class="nxr-stat-value" data-field="contracts.active_count">—</span></div>
						<div class="nxr-stat-card"><span class="nxr-stat-label">${__("Solicitudes pendientes")}</span><span class="nxr-stat-value" data-field="purchase_requests.pending_count">—</span></div>
						<div class="nxr-stat-card"><span class="nxr-stat-label">${__("Proveedores activos")}</span><span class="nxr-stat-value" data-field="suppliers.active_count">—</span></div>
						<div class="nxr-stat-card"><span class="nxr-stat-label">${__("Entidades activas")}</span><span class="nxr-stat-value" data-field="entities.active_count">—</span></div>
					</div>
				</section>

				<section class="nxr-card nxr-dashboard-recent">
					<div class="nxr-section-heading"><div><p class="nxr-eyebrow">${__("LIBRO CENTRAL")}</p><h3>${__("Operaciones recientes")}</h3></div></div>
					<div class="nxr-dashboard-recent-rows nxr-empty">${__("Cargando…")}</div>
				</section>

				<section class="nxr-card nxr-dashboard-actions">
					<div class="nxr-section-heading"><div><p class="nxr-eyebrow">${__("ACCESOS")}</p><h3>${__("Gestión diaria")}</h3></div></div>
					<div class="nxr-action-buttons">
						<button class="btn btn-default nxr-action-btn" data-route="nexora-finance">${__("Fondos y operaciones")}</button>
						<button class="btn btn-default nxr-action-btn" data-route="nexora-contracts">${__("Contratos")}</button>
						<button class="btn btn-default nxr-action-btn" data-route="nexora-suppliers">${__("Proveedores")}</button>
						<button class="btn btn-default nxr-action-btn" data-route="nexora-purchase-requests">${__("Solicitudes de compra")}</button>
						<button class="btn btn-default nxr-action-btn" data-route="nexora-search">${__("Buscar en NEXORA")}</button>
					</div>
				</section>
			</div>
		</div>
	`);

	$(page.body).on("click", ".nxr-action-btn", function () {
		const operationType = $(this).data("operation");
		if (operationType) {
			frappe.route_options = { operation_type: operationType };
		}
		frappe.set_route($(this).data("route"));
	});

	page.add_button(__("Actualizar"), loadDashboard, "primary");
	loadDashboard();

	async function loadDashboard() {
		try {
			const response = await frappe.call({
				method: "nexora.dashboard.service.get_dashboard_summary",
				type: "POST",
				args: { payload: { project: projectControl.get_value() || null } },
				freeze: true,
				freeze_message: __("Actualizando resumen operativo…"),
			});
			renderValues(response.message || {});
		} catch (error) {
			$(page.body)
				.find(".nxr-dashboard-recent-rows")
				.addClass("nxr-empty")
				.text(__("No fue posible cargar el dashboard."));
			frappe.msgprint({
				title: __("Dashboard no disponible"),
				message: __("Revise su conexión o permisos e intente nuevamente."),
				indicator: "red",
			});
			throw error;
		}
	}

	function readPath(data, path) {
		return path.split(".").reduce((value, key) => (value ? value[key] : undefined), data);
	}

	function renderValues(data) {
		$(page.body)
			.find("[data-field]")
			.each(function () {
				const value = readPath(data, $(this).data("field"));
				if (value !== undefined && value !== null) {
					$(this).text($(this).data("currency") ? frappe.format(value, { fieldtype: "Currency" }) : value);
				}
			});

		const activeBudgetCount = readPath(data, "budgets.active_budget_count") || 0;
		$(page.body)
			.find(".nxr-active-budget-count")
			.text(__({ singular: "{0} presupuesto activo", plural: "{0} presupuestos activos", count: activeBudgetCount }, [activeBudgetCount]));

		const recentTarget = $(page.body).find(".nxr-dashboard-recent-rows").empty();
		const operations = data.recent_operations || [];
		if (!operations.length) {
			recentTarget.addClass("nxr-empty").text(__("No hay operaciones recientes para este proyecto."));
			return;
		}

		recentTarget.removeClass("nxr-empty");
		recentTarget.append(`<div class="table-responsive"><table class="table table-bordered">
			<thead><tr><th>${__("Documento")}</th><th>${__("Movimiento")}</th><th>${__("Monto")}</th><th>${__("Estado")}</th></tr></thead>
			<tbody></tbody></table></div>`);
		const body = recentTarget.find("tbody");
		operations.forEach((operation) => {
			const link = frappe.utils.get_form_link("NXR Operation", operation.name);
			const operationType = operationLabels[operation.operation_type] || operation.operation_type || "—";
			const status = statusLabels[operation.status] || operation.status || "—";
			$(`<tr>
				<td><a href="${link}">${frappe.utils.escape_html(operation.document_number || operation.name)}</a></td>
				<td>${frappe.utils.escape_html(operationType)}</td>
				<td>${frappe.format(operation.amount_hnl || 0, { fieldtype: "Currency" })}</td>
				<td>${frappe.utils.escape_html(status)}</td>
			</tr>`).appendTo(body);
		});
	}
};
