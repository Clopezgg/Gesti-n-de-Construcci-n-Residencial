frappe.pages["nexora-reports"].on_page_load = function (wrapper) {
	const page = frappe.ui.make_app_page({
		parent: wrapper,
		title: __("Reportes"),
		single_column: true,
	});
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
	let currentView = "executive";
	let state = { executive: null, income: null, contracts: null };

	const project = page.add_field({
		fieldname: "project",
		label: __("Proyecto"),
		fieldtype: "Link",
		options: "Project",
		change: () => refreshCurrent(),
	});
	const launchOptions = frappe.route_options || {};
	frappe.route_options = null;
	if (launchOptions.project) project.set_value(launchOptions.project);

	body.append(`
		<style>
			.nxr-bi{display:grid;gap:16px;padding:2px 0 30px}.nxr-bi-hero{display:flex;justify-content:space-between;gap:20px;align-items:flex-start;padding:22px 24px;border:1px solid var(--border-color);border-radius:18px;background:linear-gradient(120deg,var(--card-bg),var(--subtle-fg));box-shadow:0 10px 30px rgba(15,23,42,.06)}.nxr-bi-hero h2{margin:3px 0 4px;font-size:25px}.nxr-bi-eyebrow{font-size:11px;font-weight:800;letter-spacing:.08em;color:var(--text-muted);margin:0}.nxr-bi-actions{display:flex;flex-wrap:wrap;gap:8px}.nxr-bi-tabs{display:flex;gap:8px;flex-wrap:wrap}.nxr-bi-tabs .is-active{background:var(--primary);color:#fff;border-color:var(--primary)}.nxr-bi-metrics{display:grid;grid-template-columns:repeat(6,minmax(0,1fr));gap:10px}.nxr-bi-metric{padding:15px;border:1px solid var(--border-color);border-radius:14px;background:var(--card-bg)}.nxr-bi-metric span{display:block;color:var(--text-muted);font-size:12px}.nxr-bi-metric strong{display:block;margin-top:6px;font-size:19px}.nxr-bi-metric.is-negative strong{color:var(--red-500)}.nxr-bi-grid{display:grid;grid-template-columns:1fr 1fr;gap:14px}.nxr-bi-card{border:1px solid var(--border-color);border-radius:16px;background:var(--card-bg);padding:18px;min-width:0}.nxr-bi-card h3{margin:0 0 14px;font-size:16px}.nxr-bi-bars{display:grid;gap:10px}.nxr-bi-bar{display:grid;grid-template-columns:minmax(105px,1fr) 2fr auto;gap:10px;align-items:center;font-size:12px}.nxr-bi-track{height:8px;border-radius:999px;background:var(--subtle-fg);overflow:hidden}.nxr-bi-track i{display:block;height:100%;border-radius:inherit;background:var(--primary)}.nxr-bi-table{width:100%;border-collapse:separate;border-spacing:0;font-size:12px}.nxr-bi-table th{position:sticky;top:0;background:var(--subtle-fg);text-align:left;padding:10px;white-space:nowrap}.nxr-bi-table td{padding:10px;border-bottom:1px solid var(--border-color);vertical-align:top}.nxr-bi-table-wrap{overflow:auto;max-height:520px;border:1px solid var(--border-color);border-radius:12px}.nxr-bi-badge{display:inline-flex;padding:4px 8px;border-radius:999px;background:var(--subtle-fg);font-size:11px;font-weight:700}.nxr-bi-badge.warning{background:var(--yellow-100);color:var(--yellow-700)}.nxr-bi-empty{padding:28px;text-align:center;color:var(--text-muted)}.nxr-bi-span{grid-column:1/-1}@media(max-width:1100px){.nxr-bi-metrics{grid-template-columns:repeat(3,1fr)}}@media(max-width:760px){.nxr-bi-hero{display:block}.nxr-bi-actions{margin-top:14px}.nxr-bi-metrics{grid-template-columns:repeat(2,1fr)}.nxr-bi-grid{grid-template-columns:1fr}.nxr-bi-bar{grid-template-columns:100px 1fr}.nxr-bi-bar strong{grid-column:2}.nxr-bi-span{grid-column:auto}}
		</style>
		<main class="nxr-bi">
			<section class="nxr-bi-hero">
				<div><p class="nxr-bi-eyebrow">BI01 · ${__("REPORTES Y CONTROL")}</p><h2>${__("Centro ejecutivo")}</h2><p class="text-muted nxr-bi-context">${__("Todos los proyectos")}</p></div>
				<div class="nxr-bi-actions"><button class="btn btn-primary" data-refresh>${__("Actualizar datos")}</button><button class="btn btn-default" data-route="nexora-finance">${__("Registrar movimiento")}</button></div>
			</section>
			<nav class="nxr-bi-tabs">
				<button class="btn btn-default is-active" data-view="executive">${__("Resumen ejecutivo")}</button>
				<button class="btn btn-default" data-view="income">${__("Ingresos y remesas")}</button>
				<button class="btn btn-default" data-view="contracts">${__("Estado contractual")}</button>
				<button class="btn btn-default" data-view="financial">${__("Estados de cuenta")}</button>
			</nav>
			<section class="nxr-report-result"><div class="nxr-bi-empty">${__("Cargando reportes…")}</div></section>
		</main>
	`);

	const money = (value) => format_currency(Number(value || 0), "HNL");
	const esc = (value) => frappe.utils.escape_html(String(value ?? ""));
	const date = (value) => (value ? frappe.datetime.str_to_user(String(value).slice(0, 10)) : "—");
	const projectValue = () => project.get_value() || null;

	body.on("click", "[data-view]", function () {
		currentView = $(this).data("view");
		body.find("[data-view]").removeClass("is-active");
		$(this).addClass("is-active");
		refreshCurrent();
	});
	body.on("click", "[data-refresh]", () => refreshCurrent(true));
	body.on("click", "[data-route]", function () {
		frappe.route_options = { project: projectValue() };
		frappe.set_route($(this).data("route"));
	});
	body.on("click", "[data-form]", function () {
		frappe.set_route("Form", $(this).data("form"), $(this).data("name"));
	});
	page.add_button(__("Generar reporte"), () => refreshCurrent(true), "primary");

	async function call(method) {
		const response = await frappe.call({
			method,
			type: "POST",
			args: { payload: { project: projectValue() } },
			freeze: true,
			freeze_message: __("Actualizando información…"),
		});
		return response.message || {};
	}

	async function refreshCurrent(force = false) {
		body.find(".nxr-bi-context").text(projectValue() || __("Todos los proyectos"));
		const target = body.find(".nxr-report-result").html(`<div class="nxr-bi-empty">${__("Cargando…")}</div>`);
		try {
			if (currentView === "executive") {
				if (force || !state.executive) state.executive = await call("nexora.reports.executive.get_executive_report");
				renderExecutive(target, state.executive);
			} else if (currentView === "income") {
				if (force || !state.income) state.income = await call("nexora.reports.executive.get_income_register");
				renderIncome(target, state.income);
			} else if (currentView === "contracts") {
				if (force || !state.contracts) state.contracts = await call("nexora.reports.executive.get_contract_register");
				renderContracts(target, state.contracts);
			} else {
				renderStatements(target);
			}
		} catch (error) {
			target.html(`<div class="nxr-bi-empty text-danger">${esc(error?.message || error)}</div>`);
		}
	}

	function metric(label, value, negative = false) {
		return `<div class="nxr-bi-metric ${negative ? "is-negative" : ""}"><span>${esc(label)}</span><strong>${value}</strong></div>`;
	}

	function bars(rows, labelKey = "code") {
		const visible = (rows || []).slice(0, 8);
		const max = Math.max(...visible.map((row) => Number(row.amount_hnl || 0)), 1);
		if (!visible.length) return `<div class="nxr-bi-empty">${__("Sin datos para mostrar.")}</div>`;
		return `<div class="nxr-bi-bars">${visible
			.map((row) => {
				const raw = row[labelKey] || row.name || __("Sin clasificar");
				const label = categoryLabels[raw] || raw;
				return `<div class="nxr-bi-bar"><span title="${esc(label)}">${esc(label)}</span><span class="nxr-bi-track"><i style="width:${Math.max((Number(row.amount_hnl || 0) / max) * 100, 2)}%"></i></span><strong>${money(row.amount_hnl)}</strong></div>`;
			})
			.join("")}</div>`;
	}

	function renderExecutive(target, data) {
		const income = data.income || {};
		const totals = income.totals || {};
		const contractRows = data.contracts?.rows || [];
		const committed = contractRows.reduce((sum, row) => sum + Number(row.value_hnl || 0), 0);
		const paid = contractRows.reduce((sum, row) => sum + Number(row.paid_hnl || 0), 0);
		target.html(`
			<div class="nxr-bi-metrics">
				${metric(__("Recibido"), money(totals.received_hnl))}
				${metric(__("Gastado"), money(totals.spent_hnl))}
				${metric(__("Reservado"), money(totals.reserved_hnl))}
				${metric(__("Disponible"), money(totals.available_hnl), Number(totals.available_hnl) < 0)}
				${metric(__("Comprometido en contratos"), money(committed))}
				${metric(__("Pagado a contratos"), money(paid))}
			</div>
			<div class="nxr-bi-grid">
				<section class="nxr-bi-card"><h3>${__("Gastos por categoría")}</h3>${bars(data.costs || [])}</section>
				<section class="nxr-bi-card"><h3>${__("Principales proveedores y contratistas")}</h3>${bars(data.providers || [], "name")}</section>
				<section class="nxr-bi-card nxr-bi-span"><h3>${__("Control operativo")}</h3><div class="nxr-bi-metrics">${metric(__("Ingresos"), income.count || 0)}${metric(__("Sin conciliar"), income.unreconciled_count || 0)}${metric(__("Contratos"), data.contracts?.count || 0)}${metric(__("Operaciones"), data.operation_count || 0)}</div></section>
			</div>
		`);
	}

	function renderIncome(target, data) {
		const t = data.totals || {};
		target.html(`<div class="nxr-bi-metrics">${metric(__("Recibido"), money(t.received_hnl))}${metric(__("Gastado"), money(t.spent_hnl))}${metric(__("Reservado"), money(t.reserved_hnl))}${metric(__("Disponible"), money(t.available_hnl))}${metric(__("Ingresos"), data.count || 0)}${metric(__("Sin conciliar"), data.unreconciled_count || 0)}</div><section class="nxr-bi-card"><h3>FI01 · ${__("Estado de cuenta de ingresos")}</h3><div class="nxr-bi-table-wrap"><table class="nxr-bi-table"><thead><tr><th>${__("Fuente")}</th><th>${__("Fecha")}</th><th>${__("Remitente")}</th><th>${__("Canal")}</th><th>${__("Remesadora / banco")}</th><th>${__("Referencia")}</th><th>${__("Recibido")}</th><th>${__("Gastado")}</th><th>${__("Reservado")}</th><th>${__("Disponible")}</th><th>${__("Proyecto")}</th><th>${__("Conciliación")}</th></tr></thead><tbody>${(data.rows || []).map((row) => `<tr data-form="NXR Fund Source" data-name="${esc(row.name)}"><td><strong>${esc(row.source_code || row.source_name || row.name)}</strong></td><td>${date(row.source_date)}</td><td>${esc(row.origin_or_sender || "—")}</td><td>${esc(channelLabels[row.channel] || row.channel || "—")}</td><td>${esc(row.institution || row.account_reference || "—")}</td><td>${esc(row.external_reference || "—")}</td><td>${money(row.received_hnl)}</td><td>${money(row.spent_hnl)}</td><td>${money(row.reserved_hnl)}</td><td>${money(row.available_hnl)}</td><td>${esc(row.project || "—")}</td><td><span class="nxr-bi-badge ${row.reconciliation_status === "Pendiente" ? "warning" : ""}">${esc(row.reconciliation_status)}</span></td></tr>`).join("")}</tbody></table></div></section>`);
	}

	function renderContracts(target, data) {
		target.html(`<section class="nxr-bi-card"><h3>CO01 · ${__("Estado contractual")}</h3><div class="nxr-bi-table-wrap"><table class="nxr-bi-table"><thead><tr><th>${__("Contrato")}</th><th>${__("Contratista")}</th><th>${__("Estado")}</th><th>${__("Inicio")}</th><th>${__("Fin previsto")}</th><th>${__("Valor contractual")}</th><th>${__("Pagado")}</th><th>${__("Saldo")}</th><th>${__("Proyecto")}</th></tr></thead><tbody>${(data.rows || []).map((row) => `<tr data-form="NXR Contract" data-name="${esc(row.name)}"><td><strong>${esc(row.document_number || row.name)}</strong></td><td>${esc(row.contractor_label || row.contractor || "—")}</td><td><span class="nxr-bi-badge">${esc(row.status || "—")}</span></td><td>${date(row.current_start_date)}</td><td>${date(row.current_end_date)}</td><td>${money(row.value_hnl)}</td><td>${money(row.paid_hnl)}</td><td>${money(row.balance_hnl)}</td><td>${esc(row.project || "—")}</td></tr>`).join("")}</tbody></table></div></section>`);
	}

	function renderStatements(target) {
		target.html(`<div class="nxr-bi-grid"><section class="nxr-bi-card"><h3>${__("Estado de cuenta por fondo")}</h3><p class="text-muted">${__("Consulte movimientos, saldo corrido y trazabilidad desde cada ingreso registrado.")}</p><button class="btn btn-primary" data-route="nexora-finance">${__("Abrir fondos y operaciones")}</button></section><section class="nxr-bi-card"><h3>${__("Conciliación de totales")}</h3><p class="text-muted">${__("Los indicadores ejecutivos se calculan desde el libro financiero y los efectos de cada fuente, evitando cifras duplicadas.")}</p><button class="btn btn-default" data-view="executive">${__("Ver resumen conciliado")}</button></section></div>`);
	}

	refreshCurrent();
};
