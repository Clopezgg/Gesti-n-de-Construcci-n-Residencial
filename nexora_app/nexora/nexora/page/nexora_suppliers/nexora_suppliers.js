frappe.pages["nexora-suppliers"].on_page_load = function (wrapper) {
	const page = frappe.ui.make_app_page({
		parent: wrapper,
		title: __("Compras y proveedores"),
		single_column: true,
	});
	const ui = window.nexora.ui;
	const controls = {};
	const add = (definition) => {
		controls[definition.fieldname] = page.add_field(definition);
		return controls[definition.fieldname];
	};

	add({ fieldname: "entity", label: __("Entidad"), fieldtype: "Link", options: "NXR Entity" });
	add({
		fieldname: "classification",
		label: __("Tipo de proveedor"),
		fieldtype: "Select",
		options: ui.selectOptions("supplierClassification", { blank: true }),
	});
	add({
		fieldname: "status",
		label: __("Estado"),
		fieldtype: "Select",
		options: ["", "Draft", "Active", "Suspended", "Expired", "Inactive"].map((value) => ({
			label: value ? ui.label("status", value) : "",
			value,
		})),
	});

	$(page.body).append(`
		<div class="nxr-finance-grid nxr-supplier-grid">
			<section class="nxr-card"><h3>${__("Proveedores")}</h3><div class="nxr-supplier-results"></div></section>
			<section class="nxr-card"><h3>${__("Expediente")}</h3><div class="nxr-supplier-detail nxr-empty">${__(
		"Seleccione un proveedor para revisar su información."
	)}</div></section>
			<section class="nxr-card"><h3>${__(
				"Acciones disponibles"
			)}</h3><div class="nxr-supplier-actions"></div></section>
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
		try {
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
			const filtered = classification
				? rows.filter((row) => row.classification === classification)
				: rows;
			renderRows(filtered);
		} catch (error) {
			console.error("NEXORA supplier list failed", error);
			ui.showError(error, {
				title: __("No fue posible consultar proveedores"),
				fallback: __("No se modificó ningún expediente. Revise los filtros o sus permisos."),
			});
		}
	}

	function renderRows(rows) {
		const target = $(page.body).find(".nxr-supplier-results").empty();
		if (!rows.length) {
			target.append(
				`<p class="nxr-empty">${__("No hay proveedores para los filtros seleccionados.")}</p>`
			);
			return;
		}
		rows.forEach((row) => {
			const button = $(
				`<button class="btn btn-default btn-sm nxr-result-row"><strong>${escape(
					row.document_number
				)}</strong> · ${escape(ui.label("status", row.status))} · ${escape(
					ui.label("supplierClassification", row.classification)
				)} · ${escape(row.entity)}</button>`
			);
			button.on("click", () => load(row.profile));
			target.append(button);
		});
	}

	async function load(profile) {
		selected = profile;
		try {
			const row = await call("nexora.purchases.service.get_supplier_profile", { profile }, "GET");
			$(page.body).find(".nxr-supplier-detail").removeClass("nxr-empty").html(`
				<p><strong>${escape(row.document_number)}</strong></p>
				<p>${__("Entidad")}: ${escape(row.entity)}</p>
				<p>${__("Estado")}: ${escape(ui.label("status", row.status))}</p>
				<p>${__("Tipo de proveedor")}: ${escape(ui.label("supplierClassification", row.classification))}</p>
				<p>${__("Vigencia")}: ${escape(row.valid_from)} — ${escape(row.valid_until || __("Sin fecha final"))}</p>
				<p>${__("Cumplimiento")}: ${escape(ui.label("status", row.compliance_status))}</p>
				<p>${__("Expediente de cumplimiento")}: ${escape(row.compliance || __("Pendiente"))}</p>
			`);
			renderActions(row);
		} catch (error) {
			console.error("NEXORA supplier detail failed", error);
			ui.showError(error, { title: __("No fue posible abrir el proveedor") });
		}
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
			const button = $(
				`<button class="btn btn-default btn-sm mr-2 mb-2">${escape(
					ui.label("status", status)
				)}</button>`
			);
			button.on("click", async () => {
				try {
					await call("nexora.purchases.service.transition_supplier_profile", {
						profile: row.profile,
						status,
						idempotency_key: uuid(),
					});
					ui.showSuccess({ message: __("Estado actualizado correctamente.") });
					await refresh();
					await load(row.profile);
				} catch (error) {
					ui.showError(error, { title: __("No fue posible cambiar el estado") });
				}
			});
			target.append(button);
		});
		if (!(transitions[row.status] || []).length) {
			target.append(
				`<p class="nxr-empty">${__("Este expediente no tiene más acciones disponibles.")}</p>`
			);
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
					label: __("Tipo de proveedor"),
					fieldtype: "Select",
					options: ui.selectOptions("supplierClassification"),
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
					label: __("Expediente de cumplimiento"),
					fieldtype: "Link",
					options: "NXR Entity Compliance",
				},
				{ fieldname: "notes", label: __("Notas"), fieldtype: "Small Text" },
			],
			primary_action_label: __("Crear proveedor"),
			primary_action: async () => {
				const values = dialog.get_values();
				if (!values) return;
				try {
					const result = await call("nexora.purchases.service.create_supplier_profile", {
						payload: { ...values, idempotency_key: uuid() },
					});
					dialog.hide();
					controls.entity.set_value(result.entity);
					ui.showSuccess({
						message: __("Proveedor creado correctamente"),
						documentNumber: result.document_number,
					});
					await refresh();
					await load(result.profile);
				} catch (error) {
					ui.showError(error, { title: __("No fue posible crear el proveedor") });
				}
			},
		});
		dialog.show();
	}

	void refresh();
};
