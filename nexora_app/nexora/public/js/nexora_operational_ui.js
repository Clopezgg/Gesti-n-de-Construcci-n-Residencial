(() => {
	let dashboardRequest = 0;
	let dashboardTimer = null;
	let dashboardSignature = "";

	function routeName() {
		return (frappe.get_route?.() || []).join("/").toLowerCase();
	}

	function dashboardProject() {
		return (
			document.querySelector('#page-nexora-dashboard [data-fieldname="project"] input')?.value ||
			frappe.route_options?.project ||
			null
		);
	}

	function openOperationalConsole(movementCode, project = null, showLedger = false) {
		frappe.route_options = {
			movement_code: movementCode || "101",
			project: project || null,
			show_ledger: showLedger ? 1 : null,
		};
		frappe.set_route("nexora-operations");
	}

	document.addEventListener(
		"click",
		(event) => {
			const target = event.target.closest?.(
				'[data-action="income"], [data-launch-income], [data-action="expense"], [data-operation="CONSTRUCTION_PAYMENT"], [data-nexora-operational-ledger]'
			);
			if (!target) return;
			const route = routeName();
			if (!route.includes("nexora-dashboard") && !route.includes("nexora-finance")) return;
			event.preventDefault();
			event.stopPropagation();
			event.stopImmediatePropagation();
			const showLedger = target.hasAttribute("data-nexora-operational-ledger");
			const movementCode =
				target.dataset.action === "expense" || target.dataset.operation === "CONSTRUCTION_PAYMENT"
					? "102"
					: "101";
			openOperationalConsole(movementCode, dashboardProject(), showLedger);
		},
		true
	);

	async function refreshDashboardOperationalRows() {
		if (!routeName().includes("nexora-dashboard")) return;
		const shell = document.querySelector('#page-nexora-dashboard .nxr-dashboard-shell[data-state="ready"]');
		if (!shell) return;
		const serial = ++dashboardRequest;
		try {
			const response = await frappe.call({
				method: "nexora.financial.service.list_operational_ledger",
				type: "POST",
				args: { project: dashboardProject(), limit: 20 },
			});
			if (serial !== dashboardRequest) return;
			const rows = response.message || [];
			const signature = JSON.stringify([
				dashboardProject(),
				rows.map((row) => [row.name, row.document_date, row.movement_code, row.amount_hnl, row.status]),
			]);
			if (signature === dashboardSignature) return;
			dashboardSignature = signature;
			renderActivity(rows);
			renderRecent(rows);
		} catch (error) {
			console.warn("NEXORA operational dashboard extension failed", error);
		}
	}

	function renderActivity(rows) {
		const target = document.querySelector("#page-nexora-dashboard .nxr-activity-list");
		if (!target) return;
		const visible = rows.slice(0, 3);
		target.innerHTML = visible.length
			? `${visible.map(activityRow).join("")}
				<button type="button" class="nxr-activity-more" data-nexora-operational-ledger="1">${__(
					"Ver más actividad"
				)}</button>`
			: `<p class="nxr-executive-empty">${__("No hay actividad reciente.")}</p>`;
	}

	function activityRow(row) {
		const amount = row.struck ? `<s>${money(row.amount_hnl)}</s>` : money(row.amount_hnl);
		return `<a class="nxr-executive-row nxr-operational-activity-row" data-tone="${escape(
			row.tone
		)}" href="${frappe.utils.get_form_link("NXR Operation", row.name)}">
			<span><strong>${escape(row.document_number || row.name)} · ${escape(row.movement_code)}</strong>
			<small>${escape(row.day)} ${date(row.document_date)} · ${escape(row.movement_label)}</small></span>
			<b data-tone="${escape(row.tone)}">${amount}</b>
		</a>`;
	}

	function renderRecent(rows) {
		const table = document.querySelector("#page-nexora-dashboard .nxr-dashboard-recent-rows");
		if (!table) return;
		table.querySelector("thead").innerHTML = `<tr>
			<th>${__("Día")}</th><th>${__("Fecha documento")}</th><th>${__("Documento")}</th>
			<th>${__("Mov.")}</th><th>${__("Movimiento")}</th><th>${__("Remitente / beneficiario")}</th>
			<th>${__("Institución")}</th><th>${__("Cuenta")}</th><th>${__("Moneda")}</th>
			<th class="text-right">${__("Importe")}</th><th>${__("Estado")}</th>
		</tr>`;
		table.querySelector("tbody").innerHTML = rows.slice(0, 8).map(recentRow).join("");
		table.dataset.operationalLedger = "ready";
		table.closest(".nxr-executive-card")?.classList.add("nxr-operational-ledger-card");
	}

	function recentRow(row) {
		const amount = row.struck ? `<s>${money(row.amount_hnl)}</s>` : money(row.amount_hnl);
		return `<tr data-tone="${escape(row.tone)}" data-movement="${escape(row.movement_code)}">
			<td>${escape(row.day)}</td><td>${date(row.document_date)}</td>
			<td><a href="${frappe.utils.get_form_link("NXR Operation", row.name)}">${escape(
				row.document_number || row.name
			)}</a></td>
			<td><b>${escape(row.movement_code)}</b></td><td>${escape(row.movement_label)}</td>
			<td>${escape(row.counterparty)}</td><td>${escape(row.institution)}</td><td>${escape(row.account)}</td>
			<td>${escape(row.currency)}</td><td class="text-right"><span data-tone="${escape(
				row.tone
			)}">${amount}</span></td><td>${escape(row.status)}</td>
		</tr>`;
	}

	function scheduleDashboardRefresh() {
		if (dashboardTimer) window.clearTimeout(dashboardTimer);
		dashboardTimer = window.setTimeout(() => {
			dashboardTimer = null;
			void refreshDashboardOperationalRows();
		}, 250);
	}

	frappe.router?.on?.("change", scheduleDashboardRefresh);
	document.addEventListener("nexora:data-changed", scheduleDashboardRefresh);
	const observer = new MutationObserver(() => {
		if (document.querySelector('#page-nexora-dashboard .nxr-dashboard-shell[data-state="ready"]')) {
			scheduleDashboardRefresh();
		}
	});
	observer.observe(document.documentElement, { childList: true, subtree: true, attributes: true });

	function money(value) {
		return new Intl.NumberFormat("es-HN", {
			style: "currency",
			currency: "HNL",
			minimumFractionDigits: 2,
		}).format(Number(value || 0));
	}
	function date(value) {
		return value ? frappe.datetime.str_to_user(String(value).slice(0, 10)) : __("Sin fecha");
	}
	function escape(value) {
		return frappe.utils.escape_html(String(value ?? ""));
	}
})();
