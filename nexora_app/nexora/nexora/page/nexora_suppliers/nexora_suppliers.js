frappe.pages["nexora-suppliers"].on_page_load = function (wrapper) {
	const page = frappe.ui.make_app_page({
		parent: wrapper,
		title: __("Compras y Proveedores"),
		single_column: true,
	});
	const controls = {};
	const add = (definition) => {
		controls[definition.fieldname] = page.add_field(definition);
		return controls[definition.fieldname];
	};

	add({ fieldname: "entity", label: __("Entidad"), fieldtype: "Link", options: "NXR Entity" });
	add({
		fieldname: "classification",
		label: __("Clasificación"),
		fieldtype: "Select",
		options: ["", "Goods", "Services", "Mixed", "Consultant", "Logistics", "Other"],
	});
	add({
		fieldname: "status",
		label: __("Estado"),
		fieldtype: "Select",
		options: ["", "Draft", "Active", "Suspended", "Expired", "Inactive"],
	});

	$(page.body).append(`
		<div class="nxr-finance-grid nxr-supplier-grid">
			<section class="nxr-card"><h3>${__("Proveedores")}</h3><div class="nxr-supplier-results"></div></section>
			<section class="nxr-card"><h3>${__("Expediente")}</h3><div class="nxr-supplier-detail nxr-empty">${__(
		"Seleccione un proveedor."
	)}</div></section>
			<section class="nxr-card"><h3>${__("Acciones")}</h3><div class="nxr-supplier-actions"></div></section>
		</div>
	`);

	let selected = null;
	page.add_button(__("Buscar"), refresh, "primary");
	page.add_button(__("Crear proveedor"), createProfile);

	function uuid() {
		return (
			globalThis.crypto?.randomUUID?.() || `nxr-${Date.now()}-${Math.random().toString(16).slice(2)}`
		);
	}

	async function call(method, args, type = "POST") {
		return (await frappe.call({ method, type, args, freeze: true })).message;
	}

	function escape(value) {
		return frappe.utils.escape_html(String(value ?? ""));
	}

	async function refresh() {
		const rows = await call(
			"nexora.purchases.service.list_supplier_profiles",
			{
				entity: controls.entity.get_value(),
				status: controls.status.get_value(),
				limit: 100,
			},
			"GET"
		);
		const classification = controls.classification.get_value();
		const filtered = classification ? rows.filter((row) => row.classification === classification) : rows;
		const target = $(page.body).find(".nxr-supplier-results").empty();
		if (!filtered.length) {
			target.append(`<p class="nxr-empty">${__("No hay proveedores para los filtros indicados.")}</p>`);
			return;
		}
		filtered.forEach((row) => {
			const button = $(
				`<button class="btn btn-default btn-sm nxr-result-row"><strong>${escape(
					row.document_number
				)}</strong> · ${escape(row.status)} · ${escape(row.classification)} · ${escape(
					row.entity
				)}</button>`
			);
			button.on("click", () => load(row.profile));
			target.append(button);
		});
	}

	async function load(profile) {
		selected = profile;
		const row = await call("nexora.purchases.service.get_supplier_profile", { profile }, "GET");
		$(page.body).find(".nxr-supplier-detail").removeClass("nxr-empty").html(`
			<p><strong>${escape(row.document_number)}</strong></p>
			<p>${__("Entidad")}: ${escape(row.entity)}</p>
			<p>${__("Estado")}: ${escape(row.status)}</p>
			<p>${__("Clasificación")}: ${escape(row.classification)}</p>
			<p>${__("Vigencia")}: ${escape(row.valid_from)} — ${escape(row.valid_until || __("Sin fecha final"))}</p>
			<p>${__("Cumplimiento")}: ${escape(row.compliance_status)}</p>
			<p>${__("Expediente de cumplimiento")}: ${escape(row.compliance || __("Pendiente"))}</p>
		`);
		renderActions(row);
	}

	function renderActions(row) {
		const target = $(page.body).find(".nxr-supplier-actions").empty();
		const transitions = {
			Draft: ["Active", "Inactive"],
			Active: ["Suspended", "Expired", "Inactive"],
			Suspended: ["Active", "Expired", "Inactive"],
			Expired: ["Active", "Inactive"],
			Inactive: [],
		};
		(transitions[row.status] || []).forEach((status) => {
			const button = $(`<button class="btn btn-default btn-sm mr-2 mb-2">${escape(status)}</button>`);
			button.on("click", async () => {
				await call("nexora.purchases.service.transition_supplier_profile", {
					profile: row.profile,
					status,
					idempotency_key: uuid(),
				});
				frappe.show_alert({ message: __("Estado actualizado"), indicator: "green" });
				await refresh();
				await load(row.profile);
			});
			target.append(button);
		});
		if (!(transitions[row.status] || []).length) {
			target.append(`<p class="nxr-empty">${__("El expediente no admite más transiciones.")}</p>`);
		}
	}

	function createProfile() {
		const dialog = new frappe.ui.Dialog({
			title: __("Crear expediente de proveedor"),
			fields: [
				{
					fieldname: "entity",
					label: __("Entidad"),
					fieldtype: "Link",
					options: "NXR Entity",
					reqd: 1,
					default: controls.entity.get_value(),
				},
				{
					fieldname: "classification",
					label: __("Clasificación"),
					fieldtype: "Select",
					options: ["Goods", "Services", "Mixed", "Consultant", "Logistics", "Other"],
					default: "Goods",
					reqd: 1,
				},
				{
					fieldname: "valid_from",
					label: __("Vigente desde"),
					fieldtype: "Date",
					default: frappe.datetime.get_today(),
					reqd: 1,
				},
				{ fieldname: "valid_until", label: __("Vigente hasta"), fieldtype: "Date" },
				{
					fieldname: "compliance",
					label: __("Cumplimiento Supplier"),
					fieldtype: "Link",
					options: "NXR Entity Compliance",
				},
				{ fieldname: "notes", label: __("Notas"), fieldtype: "Small Text" },
			],
			primary_action_label: __("Crear"),
			primary_action: async () => {
				const values = dialog.get_values();
				if (!values) return;
				const result = await call("nexora.purchases.service.create_supplier_profile", {
					payload: { ...values, idempotency_key: uuid() },
				});
				dialog.hide();
				controls.entity.set_value(result.entity);
				frappe.show_alert({
					message: __("Proveedor {0} creado", [result.document_number]),
					indicator: "green",
				});
				await refresh();
				await load(result.profile);
			},
		});
		dialog.show();
	}

	refresh();
};
