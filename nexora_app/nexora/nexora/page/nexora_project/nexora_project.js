// NEXORA · Contexto 360° del proyecto (NXR-UX-0010) + Timeline universal (NXR-UX-0011)
//
// Esta pantalla no calcula nada financiero por su cuenta: todo lo que muestra viene
// de `nexora.context360.service.get_project_overview` (que a su vez reutiliza
// `get_executive_snapshot`, la misma función que ya usa el panel ejecutivo — no una
// copia) y `nexora.context360.timeline.get_project_timeline`. Es una capa de
// comprensión sobre datos que ya existen, como pedía el mandato del Bloque 17.
frappe.pages["nexora-project"].on_page_load = function (wrapper) {
	const page = frappe.ui.make_app_page({ parent: wrapper, title: __("Proyecto"), single_column: true });
	const body = $(page.body);
	const state = {
		project: null,
		timelineCategory: null,
		timelineLimit: 20,
	};
	let syncingProject = false;
	let releaseContext = null;

	const CATEGORY_LABELS = {
		financiero: __("Financiero"),
		compras: __("Compras"),
		contratos: __("Contratos"),
		inventario: __("Inventario"),
		avance: __("Avance"),
		evidencia: __("Evidencia"),
	};
	const CATEGORY_ORDER = Object.keys(CATEGORY_LABELS);

	const projectControl = page.add_field({
		fieldname: "project",
		label: __("Proyecto"),
		fieldtype: "Link",
		options: "Project",
		change: () => void onProjectFieldChanged(),
	});

	body.html(`
		<main class="nxr-product-shell nxr-project-shell" data-state="empty">
			<section class="nxr-ds-card nxr-project-empty">
				<strong>${__("Seleccione un proyecto")}</strong>
				<p>${__(
					"Elija un proyecto arriba para ver su contexto completo: dinero, contratos, compras, avance y su historia."
				)}</p>
			</section>
			<section class="nxr-project-content" hidden>
				<header class="nxr-ds-card nxr-project-header">
					<div>
						<p class="nxr-ds-eyebrow">${__("PROYECTO")}</p>
						<h2 class="nxr-project-name"></h2>
						<span class="nxr-ds-badge nxr-ds-badge--neutral" data-project-status></span>
					</div>
					<div class="nxr-project-headline" data-project-headline></div>
				</header>

				<div class="nxr-project-grid">
					<section class="nxr-ds-card nxr-project-section" data-section="finance">
						<header><strong>${__("Salud financiera")}</strong></header>
						<div class="nxr-ds-money-list" data-finance-body></div>
					</section>
					<section class="nxr-ds-card nxr-project-section" data-section="funds">
						<header><strong>${__("Fondos y fuentes")}</strong></header>
						<div data-funds-body></div>
					</section>
					<section class="nxr-ds-card nxr-project-section" data-section="contracts">
						<header><strong>${__("Contratos y contratistas")}</strong></header>
						<div data-contracts-body></div>
					</section>
					<section class="nxr-ds-card nxr-project-section" data-section="purchases">
						<header><strong>${__("Compras abiertas")}</strong></header>
						<div data-purchases-body></div>
					</section>
					<section class="nxr-ds-card nxr-project-section" data-section="inventory">
						<header><strong>${__("Inventario crítico")}</strong></header>
						<div data-inventory-body></div>
					</section>
					<section class="nxr-ds-card nxr-project-section" data-section="progress">
						<header><strong>${__("Avance y evidencia")}</strong></header>
						<div data-progress-body></div>
					</section>
					<section class="nxr-ds-card nxr-project-section" data-section="alerts">
						<header><strong>${__("Necesita atención")}</strong></header>
						<div data-alerts-body></div>
					</section>
				</div>

				<section class="nxr-ds-card nxr-project-timeline">
					<header>
						<strong>${__("Historia del proyecto")}</strong>
						<div class="nxr-timeline-filters" data-timeline-filters></div>
					</header>
					<div data-timeline-body></div>
					<button type="button" class="nxr-ds-btn nxr-ds-btn--secondary nxr-ds-btn--sm" data-timeline-more hidden>
						${__("Ver más")}
					</button>
				</section>
			</section>
		</main>
	`);

	renderTimelineFilters();
	body.on("click", "[data-timeline-more]", () => {
		state.timelineLimit += 20;
		void loadTimeline();
	});

	function escape(value) {
		return window.nexora.ui.escapeHtml(value);
	}
	function money(value) {
		return window.nexora.ui.formatMoney(value);
	}
	function date(value) {
		return window.nexora.ui.formatDate(value);
	}

	function empty(message) {
		return `<p class="nxr-empty">${escape(message)}</p>`;
	}

	function formLink(doctype, name, label) {
		return `<a href="${frappe.utils.get_form_link(doctype, name)}">${escape(label)}</a>`;
	}

	function moneyRow(label, value, tone, headline = false) {
		const classes = ["nxr-ds-money-row", `nxr-ds-money-row--${tone}`];
		if (headline) classes.push("nxr-ds-money-row--headline");
		return `<div class="${classes.join(" ")}">
			<span class="nxr-ds-money-row__label">${escape(label)}</span>
			<span class="nxr-ds-money-row__value">${money(value)}</span>
		</div>`;
	}

	async function onProjectFieldChanged() {
		if (syncingProject) return;
		const project = projectControl.get_value() || null;
		await window.nexora.context?.setActiveProject?.(project);
		await setProject(project);
	}

	async function setProject(project) {
		state.project = project;
		state.timelineLimit = 20;
		const shell = body.find(".nxr-project-shell");
		if (!project) {
			shell.attr("data-state", "empty");
			body.find(".nxr-project-content").attr("hidden", true);
			return;
		}
		shell.attr("data-state", "loading");
		body.find(".nxr-project-content").removeAttr("hidden");
		try {
			await Promise.all([loadOverview(), loadTimeline()]);
			shell.attr("data-state", "ready");
		} catch (error) {
			shell.attr("data-state", "error");
			window.nexora.ui.showError(error, {
				title: __("No fue posible cargar el proyecto"),
				fallback: __("Revise el proyecto seleccionado y sus permisos."),
			});
		}
	}

	async function loadOverview() {
		const response = await frappe.call({
			method: "nexora.context360.service.get_project_overview",
			type: "POST",
			args: { payload: { project: state.project } },
			freeze: false,
		});
		renderOverview(response.message);
	}

	function renderOverview(data) {
		body.find(".nxr-project-name").text(data.project.project_name || data.project.name);
		body.find("[data-project-status]").text(data.project.status || "");

		const executive = data.executive || {};
		body.find("[data-project-headline]").html(`
			<span><small>${__("Disponible")}</small><strong>${money(executive.cash_available_hnl)}</strong></span>
			<span><small>${__("Comprometido")}</small><strong>${money(executive.committed_hnl)}</strong></span>
			<span><small>${__("Pendiente")}</small><strong>${money(executive.pending_obligations_hnl)}</strong></span>
		`);

		body.find("[data-finance-body]").html(
			[
				moneyRow(__("Presupuesto disponible"), executive.budget_available_hnl, "reference", true),
				moneyRow(__("Comprometido"), executive.committed_hnl, "pending"),
				moneyRow(__("Ejecutado (gastos)"), executive.spent_hnl, "spent"),
				moneyRow(__("Pagado a contratos"), executive.paid_hnl, "spent"),
				moneyRow(__("Disponible en fondos"), executive.cash_available_hnl, "available"),
				moneyRow(__("Obligaciones pendientes"), executive.pending_obligations_hnl, "pending"),
			].join("")
		);

		const sources = (data.finance || {}).sources || [];
		body.find("[data-funds-body]").html(
			sources.length
				? sources
						.slice(0, 5)
						.map(
							(row) =>
								`<a class="nxr-project-row" href="${frappe.utils.get_form_link(
									"NXR Fund Source",
									row.name
								)}">
									<span><strong>${escape(row.source_name)}</strong><small>${escape(row.channel)}</small></span>
									<b>${money(row.available_hnl)}</b>
								</a>`
						)
						.join("")
				: empty(__("No hay fondos registrados en este proyecto todavía."))
		);

		const contracts = (data.contracts || {}).items || [];
		body.find("[data-contracts-body]").html(
			contracts.length
				? contracts
						.slice(0, 5)
						.map(
							(row) =>
								`<a class="nxr-project-row" href="${frappe.utils.get_form_link(
									"NXR Contract",
									row.name
								)}">
									<span><strong>${escape(
										row.contractor_label || row.contractor || row.document_number
									)}</strong><small>${escape(row.status)}</small></span>
									<b>${money(row.current_amount)}</b>
								</a>`
						)
						.join("")
				: empty(__("Sin contratos activos en este proyecto."))
		);

		const requests = (data.open_purchases || {}).requests || [];
		const orders = (data.open_purchases || {}).orders || [];
		const purchases = [
			...requests.map((row) => ({ ...row, doctype: "NXR Purchase Request", kind: __("Solicitud") })),
			...orders.map((row) => ({
				...row,
				doctype: "NXR Purchase Order",
				name: row.name,
				kind: __("Orden"),
			})),
		];
		body.find("[data-purchases-body]").html(
			purchases.length
				? purchases
						.slice(0, 6)
						.map(
							(row) =>
								`<a class="nxr-project-row" href="${frappe.utils.get_form_link(
									row.doctype,
									row.name || row.request
								)}">
									<span><strong>${escape(row.document_number)}</strong><small>${escape(row.kind)} · ${escape(
									row.status
								)}</small></span>
									<b>${money(row.total_amount)}</b>
								</a>`
						)
						.join("")
				: empty(__("No hay compras abiertas. Todo está al día."))
		);

		const critical = data.critical_inventory || [];
		body.find("[data-inventory-body]").html(
			critical.length
				? critical
						.map(
							(row) =>
								`<div class="nxr-project-row"><span><strong>${escape(
									row.item
								)}</strong><small>${escape(row.warehouse)}</small></span><b>${
									row.balance_qty
								}</b></div>`
						)
						.join("")
				: empty(__("Sin artículos en estado crítico."))
		);

		const progress = data.progress || {};
		const evidence = data.evidence || {};
		body.find("[data-progress-body]").html(`
			<div class="nxr-project-row"><span>${__("Avance físico")}</span><b>${
			progress.physical_percent != null ? progress.physical_percent + "%" : "—"
		}</b></div>
			<div class="nxr-project-row"><span>${__("Evidencias registradas")}</span><b>${evidence.count || 0}</b></div>
			<div class="nxr-project-row"><span>${__("Evidencias por revisar")}</span><b>${
			evidence.pending_review_count || 0
		}</b></div>
		`);

		// Hallazgo real de auditoría visual (primer recorrido real de esta pantalla):
		// esparcir `data.compliance_alerts` directo crasheaba con «is not iterable» porque
		// el backend (`compliance_query.py::compliance_alerts`) siempre devuelve un
		// objeto `{items, expired_count, upcoming_count, ...}`, nunca un arreglo — el
		// mismo campo que el panel ya consume bien en `data.compliance_alerts?.items`.
		// Cada fila de cumplimiento tampoco trae `level`/`title`/`message`: es un
		// registro de `NXR Entity Compliance`, no una alerta genérica, y hay que
		// traducirlo a esa forma antes de mezclarlo con `data.alerts`.
		const complianceAlerts = (data.compliance_alerts?.items || []).map((item) => ({
			level: item.compliance_state === "Vencido" ? "danger" : "warning",
			title: window.nexora.ui.label("complianceType", item.compliance_type),
			message:
				item.compliance_state === "Vencido"
					? __("{0} · venció el {1}", [item.entity_name || item.entity, date(item.valid_until)])
					: __("{0} · vence el {1}", [item.entity_name || item.entity, date(item.valid_until)]),
		}));
		const alerts = [...(data.alerts || []), ...complianceAlerts];
		body.find("[data-alerts-body]").html(
			alerts.length
				? alerts
						.map(
							(alert) =>
								`<div class="nxr-ds-notice nxr-ds-notice--${
									alert.level === "danger"
										? "danger"
										: alert.level === "warning"
										? "danger"
										: "info"
								}">
									<div><strong>${escape(alert.title)}</strong><p>${escape(alert.message)}</p></div>
								</div>`
						)
						.join("")
				: empty(__("Nada requiere atención en este momento."))
		);
	}

	function renderTimelineFilters() {
		const chips = [
			`<button type="button" class="nxr-ds-badge nxr-ds-badge--brand" data-timeline-filter data-active="true">${__(
				"Todo"
			)}</button>`,
		]
			.concat(
				CATEGORY_ORDER.map(
					(category) =>
						`<button type="button" class="nxr-ds-badge nxr-ds-badge--neutral" data-timeline-filter="${category}">${CATEGORY_LABELS[category]}</button>`
				)
			)
			.join("");
		body.find("[data-timeline-filters]").html(chips);
		body.on("click", "[data-timeline-filter]", function () {
			const category = $(this).attr("data-timeline-filter") || null;
			state.timelineCategory = category || null;
			state.timelineLimit = 20;
			body.find("[data-timeline-filter]").attr("data-active", "false");
			$(this).attr("data-active", "true");
			void loadTimeline();
		});
	}

	async function loadTimeline() {
		const payload = { project: state.project, limit: state.timelineLimit };
		if (state.timelineCategory) payload.categories = [state.timelineCategory];
		const response = await frappe.call({
			method: "nexora.context360.timeline.get_project_timeline",
			type: "POST",
			args: { payload },
			freeze: false,
		});
		renderTimeline(response.message);
	}

	function renderTimeline(data) {
		const events = data.events || [];
		body.find("[data-timeline-more]").attr("hidden", !data.has_more);
		if (!events.length) {
			body.find("[data-timeline-body]").html(
				empty(
					__(
						"Sin eventos todavía para este filtro. Registre una operación, compra o avance y aparecerá aquí."
					)
				)
			);
			return;
		}
		let lastDay = null;
		const rows = events
			.map((event) => {
				const day = String(event.date).slice(0, 10);
				const heading = day !== lastDay ? `<p class="nxr-timeline-day">${date(day)}</p>` : "";
				lastDay = day;
				const amount = event.amount_hnl != null ? `<b>${money(event.amount_hnl)}</b>` : "";
				return `${heading}
					<a class="nxr-timeline-row" data-category="${escape(event.category)}" data-exception="${event.is_exception}"
						href="${frappe.utils.get_form_link(event.doctype, event.name)}">
						<span class="nxr-timeline-dot"></span>
						<span class="nxr-timeline-body">
							<strong>${escape(event.title)}</strong>
							<small>${escape(event.category_label)} · ${escape(event.document_number)}${
					event.actor ? " · " + escape(event.actor) : ""
				}${event.is_exception ? " · " + __("Excepción") : ""}</small>
						</span>
						${amount}
					</a>`;
			})
			.join("");
		body.find("[data-timeline-body]").html(rows);
	}

	$(wrapper).on("remove", () => releaseContext?.());
	initialize().catch((error) =>
		console.error("NEXORA project 360 failed to adopt the active project", error)
	);

	async function initialize() {
		const launchOptions = frappe.route_options || {};
		frappe.route_options = null;
		const launchProject =
			launchOptions.project || (await window.nexora.context?.activeProject?.()) || null;
		if (launchProject) {
			syncingProject = true;
			try {
				await projectControl.set_value(launchProject);
			} finally {
				syncingProject = false;
			}
		}
		await setProject(launchProject);
		releaseContext = window.nexora.context?.onContextChange?.(async (context) => {
			const desired = context?.project || "";
			if ((projectControl.get_value() || "") === desired) return;
			syncingProject = true;
			try {
				await projectControl.set_value(desired);
			} finally {
				syncingProject = false;
			}
			await setProject(desired || null);
		});
	}
};
