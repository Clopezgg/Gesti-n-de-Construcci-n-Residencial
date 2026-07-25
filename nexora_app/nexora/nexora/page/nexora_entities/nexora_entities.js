frappe.pages["nexora-entities"].on_page_load = function (wrapper) {
	const page = frappe.ui.make_app_page({
		parent: wrapper,
		title: __("Directorio Universal de Entidades"),
		single_column: true,
	});
	const controls = {};
	const field = (definition) => {
		const control = page.add_field(definition);
		controls[definition.fieldname] = control;
		return control;
	};

	field({ fieldname: "query", label: __("Búsqueda universal"), fieldtype: "Data" });
	field({
		fieldname: "entity_type",
		label: __("Tipo de entidad"),
		fieldtype: "Select",
		options: ["Individual", "Organization"],
		reqd: 1,
	});
	field({ fieldname: "display_name", label: __("Nombre visible"), fieldtype: "Data", reqd: 1 });
	field({ fieldname: "legal_name", label: __("Nombre legal"), fieldtype: "Data" });
	field({ fieldname: "linked_user", label: __("Usuario vinculado"), fieldtype: "Link", options: "User" });
	field({ fieldname: "country", label: __("País"), fieldtype: "Link", options: "Country" });
	field({
		fieldname: "identifier_type",
		label: __("Tipo de identificador"),
		fieldtype: "Select",
		options: ["", "National ID", "RTN", "Passport", "Tax ID", "Email", "Internal Code", "Other"],
	});
	field({ fieldname: "identifier_value", label: __("Identificador"), fieldtype: "Data" });
	field({
		fieldname: "contact_type",
		label: __("Tipo de contacto"),
		fieldtype: "Select",
		options: ["", "Email", "Phone", "Mobile", "WhatsApp", "Address", "Other"],
	});
	field({ fieldname: "contact_value", label: __("Contacto"), fieldtype: "Data" });

	$(page.body).append(`
		<div class="nxr-finance-grid nxr-entity-grid">
			<section class="nxr-card">
				<h3>${__("Resultados")}</h3>
				<p class="text-muted">${__(
					"Busca por número, nombre, identificador, contacto o rol. Las entidades consolidadas redirigen a su registro canónico."
				)}</p>
				<div class="nxr-entity-results"></div>
			</section>
			<section class="nxr-card">
				<h3>${__("Expediente seleccionado")}</h3>
				<div class="nxr-entity-detail nxr-empty">${__("Seleccione una entidad.")}</div>
			</section>
			<section class="nxr-card">
				<h3>${__("Roles, cumplimiento y consolidación")}</h3>
				<div class="nxr-entity-actions"></div>
			</section>
		</div>
	`);

	const actionControls = buildActionControls(page.body);
	let selectedEntity = null;
	page.add_button(__("Buscar"), searchEntities, "primary");
	page.add_button(__("Crear entidad"), createEntity);
	page.add_button(__("Detectar duplicados"), detectDuplicates);
	controls.query.$input.on("keydown", (event) => {
		if (event.key === "Enter") searchEntities();
	});
	searchEntities();

	function uuid() {
		return (
			globalThis.crypto?.randomUUID?.() || `nxr-${Date.now()}-${Math.random().toString(16).slice(2)}`
		);
	}

	function entityPayload() {
		const identifiers = [];
		if (controls.identifier_type.get_value() || controls.identifier_value.get_value()) {
			identifiers.push({
				identifier_type: controls.identifier_type.get_value(),
				identifier_value: controls.identifier_value.get_value(),
				is_primary: 1,
			});
		}
		const contacts = [];
		if (controls.contact_type.get_value() || controls.contact_value.get_value()) {
			contacts.push({
				contact_type: controls.contact_type.get_value(),
				contact_value: controls.contact_value.get_value(),
				is_primary: 1,
			});
		}
		return {
			entity_type: controls.entity_type.get_value(),
			display_name: controls.display_name.get_value(),
			legal_name: controls.legal_name.get_value(),
			linked_user: controls.linked_user.get_value(),
			country: controls.country.get_value(),
			identifiers,
			contacts,
		};
	}

	async function createEntity() {
		const payload = { ...entityPayload(), idempotency_key: uuid() };
		const response = await frappe.call({
			method: "nexora.directory.service.create_entity",
			type: "POST",
			args: { payload },
			freeze: true,
			freeze_message: __("Creando expediente de entidad…"),
		});
		selectedEntity = response.message.name;
		frappe.show_alert({
			message: __("Entidad {0} creada", [response.message.document_number]),
			indicator: "green",
		});
		await loadEntity(selectedEntity);
		await searchEntities();
	}

	async function detectDuplicates() {
		const response = await frappe.call({
			method: "nexora.directory.service.detect_entity_duplicates",
			type: "POST",
			args: { payload: entityPayload() },
		});
		const rows = response.message || [];
		if (!rows.length) {
			frappe.msgprint(__("No se detectaron candidatos duplicados."));
			return;
		}
		frappe.msgprint({
			title: __("Candidatos duplicados"),
			message: rows
				.map(
					(row) =>
						`<p><strong>${frappe.utils.escape_html(row.display_name)}</strong> — ${
							row.score
						}: ${frappe.utils.escape_html((row.reasons || []).join(", "))}</p>`
				)
				.join(""),
		});
	}

	async function searchEntities() {
		const response = await frappe.call({
			method: "nexora.directory.service.search_entities",
			type: "POST",
			args: { query: controls.query.get_value(), limit: 100 },
		});
		const rows = response.message || [];
		const target = $(page.body).find(".nxr-entity-results").empty();
		if (!rows.length) {
			target.text(__("No hay entidades para los filtros actuales."));
			return;
		}
		target.append(`<div class="table-responsive"><table class="table table-bordered">
			<thead><tr><th>${__("Número")}</th><th>${__("Nombre")}</th><th>${__("Tipo")}</th><th>${__(
			"Estado"
		)}</th><th>${__("Canónica")}</th></tr></thead><tbody></tbody></table></div>`);
		const body = target.find("tbody");
		rows.forEach((row) => {
			const tr = $(`<tr role="button">
				<td>${frappe.utils.escape_html(row.document_number)}</td>
				<td>${frappe.utils.escape_html(row.display_name)}</td>
				<td>${frappe.utils.escape_html(row.entity_type)}</td>
				<td>${frappe.utils.escape_html(row.status)}</td>
				<td>${frappe.utils.escape_html(row.canonical_entity)}</td>
			</tr>`).appendTo(body);
			tr.on("click", () => loadEntity(row.name));
		});
	}

	async function loadEntity(entity) {
		const response = await frappe.call({
			method: "nexora.directory.service.get_entity",
			type: "POST",
			args: { entity, include_sensitive: 0, resolve: 1 },
		});
		const row = response.message;
		selectedEntity = row.canonical_entity;
		actionControls.entity.set_value(selectedEntity);
		actionControls.target_entity.set_value("");
		const redirect = row.redirected
			? `<p><strong>${__("Redirección canónica")}:</strong> ${frappe.utils.escape_html(
					row.redirect_chain.join(" → ")
			  )}</p>`
			: "";
		const identifiers =
			(row.identifiers || [])
				.map((item) => `${item.identifier_type}: ${item.masked_value}`)
				.join("<br>") || __("Sin identificadores");
		const contacts =
			(row.contacts || []).map((item) => `${item.contact_type}: ${item.masked_value}`).join("<br>") ||
			__("Sin contactos");
		const roles =
			(row.roles || []).map((item) => `${item.role_type} — ${item.status}`).join("<br>") ||
			__("Sin roles");
		const compliance =
			(row.compliance || []).map((item) => `${item.compliance_type} — ${item.status}`).join("<br>") ||
			__("Sin controles");
		$(page.body).find(".nxr-entity-detail").removeClass("nxr-empty")
			.html(`<p><strong>${frappe.utils.escape_html(
			row.document_number
		)}</strong> — ${frappe.utils.escape_html(row.display_name)}</p>
				<p>${frappe.utils.escape_html(row.entity_type)} · ${frappe.utils.escape_html(row.status)}</p>
				${redirect}<p><strong>${__("Identificadores")}:</strong><br>${identifiers}</p>
				<p><strong>${__("Contactos")}:</strong><br>${contacts}</p>
				<p><strong>${__("Roles")}:</strong><br>${roles}</p>
				<p><strong>${__("Cumplimiento")}:</strong><br>${compliance}</p>`);
	}

	async function transitionEntity(status) {
		ensureSelected();
		await frappe.call({
			method: "nexora.directory.service.transition_entity",
			type: "POST",
			args: {
				entity: selectedEntity,
				status,
				idempotency_key: uuid(),
				notes: actionControls.notes.get_value(),
			},
			freeze: true,
		});
		await loadEntity(selectedEntity);
		await searchEntities();
	}

	async function assignRole() {
		ensureSelected();
		const response = await frappe.call({
			method: "nexora.directory.service.assign_entity_role",
			type: "POST",
			args: {
				payload: {
					entity: selectedEntity,
					role_type: actionControls.role_type.get_value(),
					project: actionControls.project.get_value(),
					valid_from: actionControls.valid_from.get_value(),
					valid_until: actionControls.valid_until.get_value(),
					notes: actionControls.notes.get_value(),
					idempotency_key: uuid(),
				},
			},
			freeze: true,
		});
		frappe.show_alert({
			message: __("Rol {0} creado", [response.message.document_number]),
			indicator: "green",
		});
		await loadEntity(selectedEntity);
	}

	async function createCompliance() {
		ensureSelected();
		const response = await frappe.call({
			method: "nexora.directory.service.create_entity_compliance",
			type: "POST",
			args: {
				payload: {
					entity: selectedEntity,
					compliance_type: actionControls.compliance_type.get_value(),
					valid_from: actionControls.valid_from.get_value(),
					valid_until: actionControls.valid_until.get_value(),
					evidence: actionControls.evidence.get_value(),
					notes: actionControls.notes.get_value(),
					idempotency_key: uuid(),
				},
			},
			freeze: true,
		});
		actionControls.compliance.set_value(response.message.compliance);
		frappe.show_alert({
			message: __("Control {0} creado", [response.message.document_number]),
			indicator: "green",
		});
		await loadEntity(selectedEntity);
	}

	async function validateCompliance() {
		const compliance = actionControls.compliance.get_value();
		if (!compliance) frappe.throw(__("Seleccione un control de cumplimiento."));
		await frappe.call({
			method: "nexora.directory.service.transition_entity_compliance",
			type: "POST",
			args: {
				compliance,
				status: "Current",
				idempotency_key: uuid(),
				notes: actionControls.notes.get_value(),
				evidence: actionControls.evidence.get_value(),
			},
			freeze: true,
		});
		await loadEntity(selectedEntity);
	}

	async function consolidate() {
		ensureSelected();
		const target = actionControls.target_entity.get_value();
		if (!target) frappe.throw(__("Seleccione la entidad canónica destino."));
		await frappe.call({
			method: "nexora.directory.service.consolidate_entities",
			type: "POST",
			args: {
				source: selectedEntity,
				target,
				reason: actionControls.notes.get_value(),
				idempotency_key: uuid(),
			},
			freeze: true,
			freeze_message: __("Consolidando sin eliminar referencias…"),
		});
		await loadEntity(selectedEntity);
		await searchEntities();
	}

	function ensureSelected() {
		if (!selectedEntity) frappe.throw(__("Seleccione una entidad."));
	}

	function buildActionControls(body) {
		const parent = $(body).find(".nxr-entity-actions");
		const make = (df) => frappe.ui.form.make_control({ parent, df, render_input: true });
		const entity = make({
			fieldname: "entity",
			label: __("Entidad seleccionada"),
			fieldtype: "Link",
			options: "NXR Entity",
			read_only: 1,
		});
		const roleType = make({
			fieldname: "role_type",
			label: __("Rol"),
			fieldtype: "Select",
			options: [
				"Contractor",
				"Supplier",
				"Employee",
				"Beneficiary",
				"Customer",
				"Contact",
				"Donor",
				"Owner",
				"Other",
			],
		});
		const project = make({
			fieldname: "project",
			label: __("Proyecto"),
			fieldtype: "Link",
			options: "Project",
		});
		const validFrom = make({ fieldname: "valid_from", label: __("Vigente desde"), fieldtype: "Date" });
		const validUntil = make({ fieldname: "valid_until", label: __("Vigente hasta"), fieldtype: "Date" });
		const complianceType = make({
			fieldname: "compliance_type",
			label: __("Tipo de cumplimiento"),
			fieldtype: "Select",
			options: ["Identity", "Tax", "Contractual", "Banking", "Supplier", "Labor", "Insurance", "Other"],
		});
		const compliance = make({
			fieldname: "compliance",
			label: __("Control de cumplimiento"),
			fieldtype: "Link",
			options: "NXR Entity Compliance",
		});
		const evidence = make({
			fieldname: "evidence",
			label: __("Evidencia validada"),
			fieldtype: "Link",
			options: "NXR Evidence",
		});
		const targetEntity = make({
			fieldname: "target_entity",
			label: __("Entidad canónica destino"),
			fieldtype: "Link",
			options: "NXR Entity",
		});
		const notes = make({ fieldname: "notes", label: __("Motivo o notas"), fieldtype: "Small Text" });
		const buttons = $('<div class="mt-3"></div>').appendTo(parent);
		$(`<button class="btn btn-success btn-sm mr-2">${__("Activar")}</button>`)
			.appendTo(buttons)
			.on("click", () => transitionEntity("Active"));
		$(`<button class="btn btn-warning btn-sm mr-2">${__("Bloquear")}</button>`)
			.appendTo(buttons)
			.on("click", () => transitionEntity("Blocked"));
		$(`<button class="btn btn-secondary btn-sm mr-2">${__("Inactivar")}</button>`)
			.appendTo(buttons)
			.on("click", () => transitionEntity("Inactive"));
		$(`<button class="btn btn-primary btn-sm mr-2">${__("Asignar rol")}</button>`)
			.appendTo(buttons)
			.on("click", assignRole);
		$(`<button class="btn btn-primary btn-sm mr-2">${__("Crear cumplimiento")}</button>`)
			.appendTo(buttons)
			.on("click", createCompliance);
		$(`<button class="btn btn-success btn-sm mr-2">${__("Validar cumplimiento")}</button>`)
			.appendTo(buttons)
			.on("click", validateCompliance);
		$(`<button class="btn btn-danger btn-sm">${__("Consolidar")}</button>`)
			.appendTo(buttons)
			.on("click", consolidate);
		return {
			entity,
			role_type: roleType,
			project,
			valid_from: validFrom,
			valid_until: validUntil,
			compliance_type: complianceType,
			compliance,
			evidence,
			target_entity: targetEntity,
			notes,
		};
	}
};
