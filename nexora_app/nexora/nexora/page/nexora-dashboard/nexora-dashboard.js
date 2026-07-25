frappe.pages["nexora-dashboard"].on_page_load = function (wrapper) {
	const page = frappe.ui.make_app_page({
		parent: wrapper,
		title: __("Dashboard NEXORA"),
		single_column: true,
	});
	const controls = {};
	page.add_field({
		fieldname: "project",
		label: __("Proyecto"),
		fieldtype: "Link",
		options: "Project",
	});

	$(page.body).append(`
		<div class="nxr-dashboard-grid">
			<section class="nxr-card nxr-dashboard-budgets">
				<h3>${__("Presupuestos")}</h3>
				<div class="nxr-card-grid">
					<div class="nxr-stat-card"><span class="nxr-stat-label">${__(
						"Aprobado"
					)}</span><span class="nxr-stat-value nxr-stat-budgets-approved" data-field="total_approved_hnl">—</span></div>
					<div class="nxr-stat-card"><span class="nxr-stat-label">${__(
						"Comprometido"
					)}</span><span class="nxr-stat-value nxr-stat-budgets-committed" data-field="total_committed_hnl">—</span></div>
					<div class="nxr-stat-card"><span class="nxr-stat-label">${__(
						"Ejecutado"
					)}</span><span class="nxr-stat-value nxr-stat-budgets-executed" data-field="total_executed_hnl">—</span></div>
					<div class="nxr-stat-card"><span class="nxr-stat-label">${__(
						"Disponible"
					)}</span><span class="nxr-stat-value nxr-stat-budgets-available" data-field="total_available_hnl">—</span></div>
				</div>
			</section>
			<section class="nxr-card nxr-dashboard-counts">
				<h3>${__("Indicadores")}</h3>
				<div class="nxr-card-grid">
					<div class="nxr-stat-card"><span class="nxr-stat-label">${__(
						"Contratos activos"
					)}</span><span class="nxr-stat-value nxr-stat-contracts" data-field="contracts.active_count">—</span></div>
					<div class="nxr-stat-card"><span class="nxr-stat-label">${__(
						"Solicitudes pendientes"
					)}</span><span class="nxr-stat-value nxr-stat-pr" data-field="purchase_requests.pending_count">—</span></div>
					<div class="nxr-stat-card"><span class="nxr-stat-label">${__(
						"Proveedores activos"
					)}</span><span class="nxr-stat-value nxr-stat-suppliers" data-field="suppliers.active_count">—</span></div>
					<div class="nxr-stat-card"><span class="nxr-stat-label">${__(
						"Entidades activas"
					)}</span><span class="nxr-stat-value nxr-stat-entities" data-field="entities.active_count">—</span></div>
				</div>
			</section>
			<section class="nxr-card nxr-dashboard-recent">
				<h3>${__("Operaciones recientes")}</h3>
				<div class="nxr-dashboard-recent-rows nxr-empty">${__("Cargando…")}</div>
			</section>
			<section class="nxr-card nxr-dashboard-actions">
				<h3>${__("Acciones rápidas")}</h3>
				<div class="nxr-action-buttons">
					<button class="btn btn-primary btn-sm nxr-action-btn" data-route="nexora-finance">${__(
						"Núcleo de Fondos"
					)}</button>
					<button class="btn btn-primary btn-sm nxr-action-btn" data-route="nexora-contracts">${__(
						"Contratos"
					)}</button>
					<button class="btn btn-primary btn-sm nxr-action-btn" data-route="nexora-suppliers">${__(
						"Proveedores"
					)}</button>
					<button class="btn btn-primary btn-sm nxr-action-btn" data-route="nexora-purchase-requests">${__(
						"Solicitudes"
					)}</button>
					<button class="btn btn-primary btn-sm nxr-action-btn" data-route="nexora-search">${__("Buscador")}</button>
				</div>
			</section>
		</div>
	`);

	$(page.body).on("click", ".nxr-action-btn", function () {
		frappe.set_route($(this).data("route"));
	});

	page.add_button(__("Actualizar"), loadDashboard, "primary");
	loadDashboard();

	async function loadDashboard() {
		const response = await frappe.call({
			method: "nexora.dashboard.service.get_dashboard_summary",
			type: "POST",
			args: { payload: { project: controls.project.get_value() } },
			freeze: true,
			freeze_message: __("Cargando dashboard…"),
		});
		const data = response.message || {};
		renderValues(data);
	}

	function renderValues(data) {
		$(page.body)
			.find("[data-field]")
			.each(function () {
				const path = $(this).data("field").split(".");
				let value = data;
				for (const key of path) {
					value = value ? value[key] : undefined;
				}
				if (value !== undefined && value !== null) {
					const isCurrency = [
						"total_approved_hnl",
						"total_committed_hnl",
						"total_executed_hnl",
						"total_available_hnl",
					].includes(path[path.length - 1]);
					$(this).text(isCurrency ? frappe.format(value, { fieldtype: "Currency" }) : value);
				}
			});
		const recentTarget = $(page.body).find(".nxr-dashboard-recent-rows").empty();
		const ops = data.recent_operations || [];
		if (!ops.length) {
			recentTarget.addClass("nxr-empty").text(__("Sin operaciones recientes."));
			return;
		}
		recentTarget.removeClass("nxr-empty");
		recentTarget.append(`<div class="table-responsive"><table class="table table-bordered">
			<thead><tr><th>${__("Número")}</th><th>${__("Tipo")}</th><th>${__("Importe")}</th><th>${__(
			"Estado"
		)}</th></tr></thead>
			<tbody></tbody></table></div>`);
		const body = recentTarget.find("tbody");
		ops.forEach((op) => {
			const link = frappe.utils.get_form_link("NXR Operation", op.name);
			$(`<tr>
				<td><a href="${link}">${frappe.utils.escape_html(op.document_number)}</a></td>
				<td>${frappe.utils.escape_html(op.operation_type)}</td>
				<td>${frappe.format(op.amount_hnl || 0, { fieldtype: "Currency" })}</td>
				<td>${frappe.utils.escape_html(op.status)}</td>
			</tr>`).appendTo(body);
		});
	}
};
