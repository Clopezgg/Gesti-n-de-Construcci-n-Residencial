// NEXORA · SAP (cierre de producción, Paso 2)
//
// Antes de este bloque, SAP vivía escondido dentro de la pantalla genérica
// `nexora-integrations`, compartiendo una sola tabla con el registro
// genérico de integraciones REST/SOAP/Webhook — ninguna experiencia propia,
// ninguna vista de salud, documentos o auditoría separada de la simple lista
// de conexiones. Esta página reutiliza exactamente el mismo backend real
// (`nexora.integrations.sap`, sin reescribir lo que ya funciona) detrás de
// nueve pestañas reales. Cuando el backend no tiene un concepto central
// todavía (mapeos de campo: cada llamador de `submit_document` decide su
// propio `endpoint_path`/`document_payload`, no hay catálogo — ver el
// docstring de `integrations/sap.py`), la pestaña lo dice explícitamente en
// vez de simular datos que no existen.
frappe.pages["nexora-sap"].on_page_load = function (wrapper) {
	const page = frappe.ui.make_app_page({
		parent: wrapper,
		title: __("SAP"),
		single_column: true,
	});
	const ui = window.nexora.ui;
	const escape = ui.escapeHtml;
	const isAdministrator = () => (frappe.user_roles || []).includes("NEXORA Administrator");
	const isManager = () =>
		(frappe.user_roles || []).some((role) =>
			["System Manager", "NEXORA Administrator", "NEXORA Finance Manager"].includes(role)
		);

	const TABS = [
		{ id: "resumen", label: __("Resumen") },
		{ id: "conexiones", label: __("Conexiones") },
		{ id: "salud", label: __("Salud") },
		{ id: "documentos", label: __("Documentos") },
		{ id: "sincronizacion", label: __("Sincronización") },
		{ id: "errores", label: __("Errores") },
		{ id: "mapeos", label: __("Mapeos") },
		{ id: "auditoria", label: __("Auditoría") },
		{ id: "configuracion", label: __("Configuración") },
	];

	$(page.body).append(`
		<div class="nxr-sap">
			<p class="nxr-ds-text-secondary">${__(
				"Integración SAP real de NEXORA: conexiones, documentos enviados, errores y auditoría — sin datos simulados. Un estado vacío significa que todavía no hay actividad real, no un error de carga."
			)}</p>
			<div class="nxr-ds-tabs" role="tablist">
				${TABS.map(
					(tab, index) => `
					<button type="button" class="nxr-ds-tabs__tab" role="tab"
						aria-selected="${index === 0 ? "true" : "false"}" data-tab="${tab.id}">${tab.label}</button>
				`
				).join("")}
			</div>
			${TABS.map(
				(tab, index) => `
				<section class="nxr-ds-tabs__panel" data-panel="${tab.id}" ${index === 0 ? "" : "hidden"}></section>
			`
			).join("")}
		</div>
	`);

	if (isManager()) {
		page.add_button(__("Enviar documento"), openSubmitDocumentDialog, "primary");
		page.add_button(__("Consultar documento"), openPullDocumentDialog);
	}
	if (isAdministrator()) {
		page.add_button(__("Conectar SAP"), openConnectSapDialog);
	}
	page.add_button(__("Actualizar"), () => loadAll());

	$(page.body).on("click", "[data-tab]", function () {
		const tab = $(this).attr("data-tab");
		$(page.body).find("[data-tab]").attr("aria-selected", "false");
		$(this).attr("aria-selected", "true");
		$(page.body).find("[data-panel]").attr("hidden", "hidden");
		$(page.body).find(`[data-panel="${tab}"]`).removeAttr("hidden");
	});

	let summary = {};
	let connections = [];
	let documentEvents = [];
	let allEvents = [];
	let mappings = [];
	let inboundRecords = [];

	loadAll().catch((error) => console.error("NEXORA SAP panel failed to load", error));

	async function loadAll() {
		const [summaryResult, connectionList, docEvents, auditEvents, mappingList, inboundList] =
			await Promise.all([
				call("nexora.integrations.sap.get_sap_summary", {}, "GET"),
				call("nexora.integrations.sap.list_connections", {}),
				call("nexora.integrations.sap.list_sap_events", {
					event_types: ["sap_document_submitted", "sap_document_submission_failed"],
				}),
				call("nexora.integrations.sap.list_sap_events", {}),
				call("nexora.integrations.sap.list_field_mappings", {}),
				call("nexora.integrations.sap.list_inbound_records", {}),
			]);
		summary = summaryResult || {};
		connections = connectionList || [];
		documentEvents = docEvents || [];
		allEvents = auditEvents || [];
		mappings = mappingList || [];
		inboundRecords = inboundList || [];
		renderResumen();
		renderConexiones();
		renderSalud();
		renderDocumentos();
		renderSincronizacion();
		renderErrores();
		renderMapeos();
		renderAuditoria();
		renderConfiguracion();
	}

	function panel(id) {
		return $(page.body).find(`[data-panel="${id}"]`);
	}

	function statCard(label, value) {
		return `
			<div class="nxr-ds-card nxr-ds-stat">
				<span class="nxr-ds-stat__label">${escape(label)}</span>
				<strong class="nxr-ds-stat__value">${escape(String(value))}</strong>
			</div>
		`;
	}

	function renderResumen() {
		if (!summary.total_connections) {
			panel("resumen").html(
				`<p class="nxr-ds-empty">${__(
					"Todavía no hay ninguna conexión SAP configurada. Use «Conectar SAP» para registrar la primera — nada de esto se simula."
				)}</p>`
			);
			return;
		}
		const byStatus = summary.connections_by_status || {};
		panel("resumen").html(`
			<div class="nxr-ds-stat-grid">
				${statCard(__("Conexiones totales"), summary.total_connections)}
				${statCard(__("Activas"), byStatus.Active || 0)}
				${statCard(__("Inactivas"), byStatus.Inactive || 0)}
				${statCard(__("Documentos enviados"), summary.documents_submitted || 0)}
				${statCard(__("Documentos con error"), summary.documents_failed || 0)}
				${statCard(__("Última prueba"), formatDateTime(summary.last_tested_at))}
			</div>
		`);
	}

	function renderConexiones() {
		panel("conexiones").html(`
			<div class="nxr-ds-table-wrap"><table class="nxr-ds-table">
				<thead><tr>
					<th>${__("Nombre")}</th><th>${__("URL base")}</th><th>${__("Autenticación")}</th>
					<th>${__("Estado")}</th><th>${__("Última prueba")}</th><th>${__("Resultado")}</th><th></th>
				</tr></thead>
				<tbody>${
					connections.length
						? connections.map(connectionRowHtml).join("")
						: `<tr><td class="nxr-ds-table__empty" colspan="7">${__(
								"Ninguna conexión SAP registrada todavía."
						  )}</td></tr>`
				}</tbody>
			</table></div>
		`);
	}

	function connectionRowHtml(row) {
		return `
			<tr>
				<td>${escape(row.connection_name)}</td>
				<td>${escape(row.base_url)}</td>
				<td>${escape(row.auth_type)}</td>
				<td>${statusBadge(row.status)}</td>
				<td>${formatDateTime(row.last_test_at)}</td>
				<td>${resultBadge(row.last_test_result)}</td>
				<td>${
					isAdministrator()
						? `<button type="button" class="nxr-ds-btn nxr-ds-btn--secondary nxr-ds-btn--sm" data-test-connection="${escape(
								row.name
						  )}">${__("Probar conexión")}</button>`
						: ""
				}</td>
			</tr>
		`;
	}

	function renderSalud() {
		if (!connections.length) {
			panel("salud").html(`<p class="nxr-ds-empty">${__("Sin conexiones que mostrar salud.")}</p>`);
			return;
		}
		panel("salud").html(`
			<div class="nxr-ds-table-wrap"><table class="nxr-ds-table">
				<thead><tr>
					<th>${__("Conexión")}</th><th>${__("Estado")}</th><th>${__("Última comprobación")}</th><th>${__(
			"Diagnóstico"
		)}</th>
				</tr></thead>
				<tbody>${connections.map(healthRowHtml).join("")}</tbody>
			</table></div>
		`);
	}

	function healthRowHtml(row) {
		let diagnosis;
		if (!row.last_test_at) {
			diagnosis = __("Nunca probada");
		} else if (row.last_test_result === "Success") {
			diagnosis = __("Última prueba exitosa");
		} else {
			diagnosis = __("Última prueba falló");
		}
		return `
			<tr>
				<td>${escape(row.connection_name)}</td>
				<td>${statusBadge(row.status)}</td>
				<td>${formatDateTime(row.last_test_at)}</td>
				<td>${escape(diagnosis)}</td>
			</tr>
		`;
	}

	function renderDocumentos() {
		if (!documentEvents.length) {
			panel("documentos").html(
				`<p class="nxr-ds-empty">${__("Ningún documento se ha enviado a SAP todavía.")}</p>`
			);
			return;
		}
		panel("documentos").html(`
			<div class="nxr-ds-table-wrap"><table class="nxr-ds-table">
				<thead><tr>
					<th>${__("Conexión")}</th><th>${__("Tipo de documento")}</th><th>${__("Resultado")}</th>
					<th>${__("Actor")}</th><th>${__("Fecha")}</th>
				</tr></thead>
				<tbody>${documentEvents.map(documentRowHtml).join("")}</tbody>
			</table></div>
		`);
	}

	function documentRowHtml(row) {
		const ok = row.event_type === "sap_document_submitted";
		return `
			<tr>
				<td>${escape(row.connection || "—")}</td>
				<td>${escape((row.detail || {}).document_type || "—")}</td>
				<td><span class="nxr-ds-badge nxr-ds-badge--${ok ? "success" : "danger"}">${
			ok ? __("Enviado") : __("Falló")
		}</span></td>
				<td>${escape(row.actor || "—")}</td>
				<td>${formatDateTime(row.timestamp)}</td>
			</tr>
		`;
	}

	function renderSincronizacion() {
		if (!connections.length) {
			panel("sincronizacion").html(
				`<p class="nxr-ds-empty">${__("Sin conexiones — no hay nada que sincronizar todavía.")}</p>`
			);
			return;
		}
		const latestByConnection = new Map();
		for (const event of documentEvents) {
			const existing = latestByConnection.get(event.connection);
			if (!existing || String(event.timestamp) > String(existing.timestamp)) {
				latestByConnection.set(event.connection, event);
			}
		}
		panel("sincronizacion").html(`
			<p class="nxr-ds-notice nxr-ds-notice--info">${__(
				'NEXORA → SAP se envía bajo demanda ("Enviar documento"); SAP → NEXORA se consulta bajo demanda ("Consultar documento") y aterriza en un área de aterrizaje real (nunca escribe directamente sobre un documento de negocio). Ninguna dirección tiene todavía una cola programada — esta pestaña resume la última sincronización real de cada sentido.'
			)}</p>
			<p class="nxr-ds-eyebrow">${__("NEXORA → SAP (envío)")}</p>
			<div class="nxr-ds-table-wrap"><table class="nxr-ds-table">
				<thead><tr>
					<th>${__("Conexión")}</th><th>${__("Última sincronización")}</th><th>${__("Resultado")}</th>
				</tr></thead>
				<tbody>${connections.map((row) => syncRowHtml(row, latestByConnection.get(row.name))).join("")}</tbody>
			</table></div>
			<p class="nxr-ds-eyebrow">${__("SAP → NEXORA (documentos entrantes)")}</p>
			<div class="nxr-ds-table-wrap"><table class="nxr-ds-table">
				<thead><tr>
					<th>${__("Conexión")}</th><th>${__("Objeto SAP")}</th><th>${__("Identificador externo")}</th>
					<th>${__("Estado")}</th><th>${__("Última sincronización")}</th>
				</tr></thead>
				<tbody>${
					inboundRecords.length
						? inboundRecords.map(inboundRowHtml).join("")
						: `<tr><td class="nxr-ds-table__empty" colspan="5">${__(
								"Ningún documento consultado desde SAP todavía."
						  )}</td></tr>`
				}</tbody>
			</table></div>
		`);
	}

	function inboundRowHtml(row) {
		const variant =
			row.status === "Error" ? "danger" : row.status === "Duplicate" ? "neutral" : "success";
		const label =
			{
				Received: __("Recibido"),
				Updated: __("Actualizado"),
				Duplicate: __("Duplicado"),
				Error: __("Error"),
			}[row.status] || row.status;
		return `
			<tr>
				<td>${escape(row.connection)}</td>
				<td>${escape(row.sap_object)}</td>
				<td>${escape(row.external_id)}</td>
				<td><span class="nxr-ds-badge nxr-ds-badge--${variant}">${escape(label)}</span></td>
				<td>${formatDateTime(row.last_synced_at)}</td>
			</tr>
		`;
	}

	function syncRowHtml(connectionRow, lastEvent) {
		if (!lastEvent) {
			return `
				<tr>
					<td>${escape(connectionRow.connection_name)}</td>
					<td colspan="2" class="nxr-ds-table__empty">${__("Sin documentos enviados todavía")}</td>
				</tr>
			`;
		}
		const ok = lastEvent.event_type === "sap_document_submitted";
		return `
			<tr>
				<td>${escape(connectionRow.connection_name)}</td>
				<td>${formatDateTime(lastEvent.timestamp)}</td>
				<td><span class="nxr-ds-badge nxr-ds-badge--${ok ? "success" : "danger"}">${
			ok ? __("Exitosa") : __("Falló")
		}</span></td>
			</tr>
		`;
	}

	function renderErrores() {
		const errors = documentEvents.filter((row) => row.event_type === "sap_document_submission_failed");
		if (!errors.length) {
			panel("errores").html(`<p class="nxr-ds-empty">${__("Sin errores registrados.")}</p>`);
			return;
		}
		panel("errores").html(`
			<div class="nxr-ds-table-wrap"><table class="nxr-ds-table">
				<thead><tr>
					<th>${__("Conexión")}</th><th>${__("Tipo de documento")}</th><th>${__("Error")}</th><th>${__("Fecha")}</th>
				</tr></thead>
				<tbody>${errors.map(errorRowHtml).join("")}</tbody>
			</table></div>
		`);
	}

	function errorRowHtml(row) {
		const detail = row.detail || {};
		return `
			<tr>
				<td>${escape(row.connection || "—")}</td>
				<td>${escape(detail.document_type || "—")}</td>
				<td>${escape(detail.error || "—")}</td>
				<td>${formatDateTime(row.timestamp)}</td>
			</tr>
		`;
	}

	async function loadMappings() {
		mappings = (await call("nexora.integrations.sap.list_field_mappings", {})) || [];
		renderMapeos();
	}

	function renderMapeos() {
		panel("mapeos").html(`
			<p class="nxr-ds-text-secondary">${__(
				"Catálogo real de mapeos de campo (objeto NEXORA → objeto SAP): quien llama a «Enviar documento» sigue decidiendo el payload exacto de cada envío — este catálogo documenta y gobierna esos mapeos, no sustituye ese envío. Un mapeo nunca se borra, solo se desactiva para conservar su historial."
			)}</p>
			${
				isManager()
					? `<button type="button" class="nxr-ds-btn nxr-ds-btn--secondary nxr-ds-btn--sm" data-add-mapping>${__(
							"Agregar mapeo"
					  )}</button>`
					: ""
			}
			<div class="nxr-ds-table-wrap"><table class="nxr-ds-table">
				<thead><tr>
					<th>${__("Conexión")}</th><th>${__("Objeto NEXORA")}</th><th>${__("Objeto SAP")}</th>
					<th>${__("Campo origen")}</th><th>${__("Campo destino")}</th><th>${__("Obligatorio")}</th>
					<th>${__("Versión")}</th><th>${__("Estado")}</th><th></th>
				</tr></thead>
				<tbody>${
					mappings.length
						? mappings.map(mappingRowHtml).join("")
						: `<tr><td class="nxr-ds-table__empty" colspan="9">${__(
								"Ningún mapeo de campo registrado todavía."
						  )}</td></tr>`
				}</tbody>
			</table></div>
		`);
	}

	function mappingRowHtml(row) {
		return `
			<tr>
				<td>${escape(row.connection)}</td>
				<td>${escape(row.nexora_object)}</td>
				<td>${escape(row.sap_object)}</td>
				<td>${escape(row.source_field)}</td>
				<td>${escape(row.target_field)}</td>
				<td>${row.required ? __("Sí") : __("No")}</td>
				<td>${escape(String(row.version))}</td>
				<td><span class="nxr-ds-badge nxr-ds-badge--${row.active ? "success" : "neutral"}">${
			row.active ? __("Activo") : __("Inactivo")
		}</span></td>
				<td>${
					isManager()
						? `
					<button type="button" class="nxr-ds-btn nxr-ds-btn--secondary nxr-ds-btn--sm" data-edit-mapping="${escape(
						row.name
					)}">${__("Editar")}</button>
					${
						row.active
							? `<button type="button" class="nxr-ds-btn nxr-ds-btn--secondary nxr-ds-btn--sm" data-deactivate-mapping="${escape(
									row.name
							  )}">${__("Desactivar")}</button>`
							: ""
					}
				`
						: ""
				}</td>
			</tr>
		`;
	}

	function mappingDialogFields(defaults = {}) {
		return [
			{
				fieldname: "connection",
				label: __("Conexión SAP"),
				fieldtype: "Select",
				options: connections.map((row) => row.name).join("\n"),
				reqd: 1,
				default: defaults.connection,
			},
			{
				fieldname: "nexora_object",
				label: __("Objeto NEXORA"),
				fieldtype: "Data",
				reqd: 1,
				default: defaults.nexora_object,
			},
			{
				fieldname: "sap_object",
				label: __("Objeto SAP"),
				fieldtype: "Data",
				reqd: 1,
				default: defaults.sap_object,
			},
			{
				fieldname: "source_field",
				label: __("Campo origen (NEXORA)"),
				fieldtype: "Data",
				reqd: 1,
				default: defaults.source_field,
			},
			{
				fieldname: "target_field",
				label: __("Campo destino (SAP)"),
				fieldtype: "Data",
				reqd: 1,
				default: defaults.target_field,
			},
			{
				fieldname: "transformation",
				label: __("Transformación (opcional, vacío = copia directa)"),
				fieldtype: "Small Text",
				default: defaults.transformation,
			},
			{
				fieldname: "required",
				label: __("Obligatorio en SAP"),
				fieldtype: "Check",
				default: defaults.required ? 1 : 0,
			},
		];
	}

	function openAddMappingDialog() {
		const dialog = new frappe.ui.Dialog({
			title: __("Agregar mapeo de campo SAP"),
			fields: mappingDialogFields(),
			primary_action_label: __("Guardar mapeo"),
			primary_action: async (values) => {
				try {
					await call("nexora.integrations.sap.create_field_mapping", values);
					ui.showSuccess({ message: __("Mapeo guardado.") });
					dialog.hide();
					loadMappings();
				} catch (error) {
					ui.showError(error, { title: __("No se pudo guardar el mapeo") });
				}
			},
		});
		dialog.show();
	}

	function openEditMappingDialog(row) {
		const dialog = new frappe.ui.Dialog({
			title: __("Editar mapeo de campo SAP"),
			fields: mappingDialogFields(row).map((field) =>
				field.fieldname === "connection" ? { ...field, read_only: 1 } : field
			),
			primary_action_label: __("Guardar cambios"),
			primary_action: async (values) => {
				try {
					await call("nexora.integrations.sap.update_field_mapping", {
						mapping: row.name,
						...values,
					});
					ui.showSuccess({ message: __("Mapeo actualizado.") });
					dialog.hide();
					loadMappings();
				} catch (error) {
					ui.showError(error, { title: __("No se pudo actualizar el mapeo") });
				}
			},
		});
		dialog.show();
	}

	$(page.body).on("click", "[data-add-mapping]", openAddMappingDialog);

	$(page.body).on("click", "[data-edit-mapping]", function () {
		const name = $(this).attr("data-edit-mapping");
		const row = mappings.find((item) => item.name === name);
		if (row) openEditMappingDialog(row);
	});

	$(page.body).on("click", "[data-deactivate-mapping]", async function () {
		const name = $(this).attr("data-deactivate-mapping");
		frappe.confirm(
			__("¿Desactivar este mapeo? Su historial se conserva, solo deja de estar activo."),
			async () => {
				try {
					await call("nexora.integrations.sap.deactivate_field_mapping", { mapping: name });
					ui.showSuccess({ message: __("Mapeo desactivado.") });
					loadMappings();
				} catch (error) {
					ui.showError(error, { title: __("No se pudo desactivar el mapeo") });
				}
			}
		);
	});

	function renderAuditoria() {
		if (!allEvents.length) {
			panel("auditoria").html(
				`<p class="nxr-ds-empty">${__("Sin eventos de auditoría SAP todavía.")}</p>`
			);
			return;
		}
		panel("auditoria").html(`
			<div class="nxr-ds-table-wrap"><table class="nxr-ds-table">
				<thead><tr>
					<th>${__("Evento")}</th><th>${__("Conexión")}</th><th>${__("Actor")}</th>
					<th>${__("Correlación")}</th><th>${__("Fecha")}</th>
				</tr></thead>
				<tbody>${allEvents.map(auditRowHtml).join("")}</tbody>
			</table></div>
		`);
	}

	const EVENT_LABELS = {
		sap_connection_saved: __("Conexión guardada"),
		sap_connection_tested: __("Conexión probada"),
		sap_document_submitted: __("Documento enviado"),
		sap_document_submission_failed: __("Documento falló"),
		sap_mapping_saved: __("Mapeo guardado"),
		sap_mapping_deactivated: __("Mapeo desactivado"),
		sap_document_pulled: __("Documento consultado"),
		sap_document_pull_failed: __("Consulta falló"),
	};

	function auditRowHtml(row) {
		return `
			<tr>
				<td>${escape(EVENT_LABELS[row.event_type] || row.event_type)}</td>
				<td>${escape(row.connection || "—")}</td>
				<td>${escape(row.actor || "—")}</td>
				<td><code class="nxr-ds-text-secondary">${escape(row.correlation_id || "—")}</code></td>
				<td>${formatDateTime(row.timestamp)}</td>
			</tr>
		`;
	}

	function renderConfiguracion() {
		panel("configuracion").html(`
			<p class="nxr-ds-text-secondary">${__(
				"Las credenciales nunca se muestran de vuelta — solo quien administra puede volver a guardarlas."
			)}</p>
			<div class="nxr-ds-table-wrap"><table class="nxr-ds-table">
				<thead><tr>
					<th>${__("Nombre")}</th><th>${__("URL base")}</th><th>${__("Autenticación")}</th><th>${__("Estado")}</th>
				</tr></thead>
				<tbody>${
					connections.length
						? connections.map(configRowHtml).join("")
						: `<tr><td class="nxr-ds-table__empty" colspan="4">${__(
								"Ninguna conexión configurada — use «Conectar SAP»."
						  )}</td></tr>`
				}</tbody>
			</table></div>
		`);
	}

	function configRowHtml(row) {
		return `
			<tr>
				<td>${escape(row.connection_name)}</td>
				<td>${escape(row.base_url)}</td>
				<td>${escape(row.auth_type)}</td>
				<td>${statusBadge(row.status)}</td>
			</tr>
		`;
	}

	function statusBadge(status) {
		const variant = status === "Active" ? "success" : status === "Error" ? "danger" : "neutral";
		return `<span class="nxr-ds-badge nxr-ds-badge--${variant}">${escape(status || "—")}</span>`;
	}

	function resultBadge(result) {
		if (!result || result === "Not Tested") {
			return `<span class="nxr-ds-badge nxr-ds-badge--neutral">${__("Sin probar")}</span>`;
		}
		const variant = result === "Success" ? "success" : "danger";
		return `<span class="nxr-ds-badge nxr-ds-badge--${variant}">${escape(result)}</span>`;
	}

	function formatDateTime(value) {
		return value ? frappe.datetime.str_to_user(String(value)) : __("Sin registro");
	}

	$(page.body).on("click", "[data-test-connection]", async function () {
		const connection = $(this).attr("data-test-connection");
		try {
			const result = await call("nexora.integrations.sap.test_sap_connection", { connection });
			frappe.show_alert({
				message:
					result.last_test_result === "Success"
						? __("SAP respondió correctamente: {0}", [result.detail || ""])
						: __("SAP rechazó la conexión: {0}", [result.detail || ""]),
				indicator: result.last_test_result === "Success" ? "green" : "red",
			});
		} catch (error) {
			ui.showError(error, { title: __("No se pudo probar la conexión SAP") });
		} finally {
			loadAll();
		}
	});

	function openConnectSapDialog() {
		const dialog = new frappe.ui.Dialog({
			title: __("Conectar SAP"),
			fields: [
				{
					fieldname: "connection_name",
					label: __("Nombre de la conexión"),
					fieldtype: "Data",
					reqd: 1,
				},
				{ fieldname: "base_url", label: __("URL base"), fieldtype: "Data", reqd: 1 },
				{
					fieldname: "default_document_endpoint",
					label: __("Endpoint por defecto para documentos (opcional)"),
					fieldtype: "Data",
				},
				{
					fieldname: "auth_type",
					label: __("Tipo de autenticación"),
					fieldtype: "Select",
					options: "Basic\nOAuth Client Credentials\nStatic Token",
					default: "Basic",
					reqd: 1,
					onchange: () => toggleSapAuthFields(dialog),
				},
				{ fieldname: "username", label: __("Usuario"), fieldtype: "Data" },
				{ fieldname: "password", label: __("Contraseña"), fieldtype: "Password" },
				{ fieldname: "token_url", label: __("URL del token OAuth"), fieldtype: "Data" },
				{ fieldname: "client_id", label: __("Client ID"), fieldtype: "Data" },
				{ fieldname: "client_secret", label: __("Client Secret"), fieldtype: "Password" },
				{ fieldname: "static_token", label: __("Token estático"), fieldtype: "Password" },
			],
			primary_action_label: __("Guardar conexión"),
			primary_action: async (values) => {
				try {
					await call("nexora.integrations.sap.connect_connection", values);
					ui.showSuccess({ message: __("Conexión SAP guardada. Pruébela para activarla.") });
					dialog.hide();
					loadAll();
				} catch (error) {
					ui.showError(error, { title: __("No se pudo guardar la conexión SAP") });
				}
			},
		});
		toggleSapAuthFields(dialog);
		dialog.show();
	}

	function toggleSapAuthFields(dialog) {
		const authType = dialog.get_value("auth_type");
		const fieldsByType = {
			Basic: ["username", "password"],
			"OAuth Client Credentials": ["token_url", "client_id", "client_secret"],
			"Static Token": ["static_token"],
		};
		const visible = new Set(fieldsByType[authType] || []);
		// `dialog.toggle_display(field, show)` no existe en `frappe.ui.Dialog` (mismo
		// hallazgo real que ya documentó `nexora_integrations.js`).
		["username", "password", "token_url", "client_id", "client_secret", "static_token"].forEach(
			(field) => {
				dialog.set_df_property(field, "hidden", visible.has(field) ? 0 : 1);
			}
		);
	}

	function openSubmitDocumentDialog() {
		const dialog = new frappe.ui.Dialog({
			title: __("Enviar documento a SAP"),
			fields: [
				{
					fieldname: "connection",
					label: __("Conexión SAP"),
					fieldtype: "Select",
					options: connections.map((row) => row.name).join("\n"),
					reqd: 1,
				},
				{ fieldname: "document_type", label: __("Tipo de documento"), fieldtype: "Data", reqd: 1 },
				{
					fieldname: "endpoint_path",
					label: __(
						"Ruta del endpoint (opcional, usa la ruta por defecto de la conexión si se omite)"
					),
					fieldtype: "Data",
				},
				{
					fieldname: "document_payload",
					label: __("Payload del documento (JSON)"),
					fieldtype: "Code",
					options: "JSON",
					reqd: 1,
				},
			],
			primary_action_label: __("Enviar"),
			primary_action: async (values) => {
				let payload;
				try {
					payload = JSON.parse(values.document_payload);
				} catch (error) {
					frappe.msgprint({ title: __("JSON inválido"), message: error.message, indicator: "red" });
					return;
				}
				try {
					const result = await call("nexora.integrations.sap.submit_document", {
						connection: values.connection,
						document_type: values.document_type,
						endpoint_path: values.endpoint_path,
						document_payload: payload,
						idempotency_key: ui.generateId(),
					});
					if (result.ok) {
						ui.showSuccess({
							message: __("Documento enviado a SAP (HTTP {0}).", [result.sap_status_code]),
						});
					} else {
						frappe.msgprint({
							title: __("SAP rechazó el documento"),
							message: escape(result.error || ""),
							indicator: "orange",
						});
					}
					dialog.hide();
					loadAll();
				} catch (error) {
					ui.showError(error, { title: __("No se pudo enviar el documento") });
				}
			},
		});
		dialog.show();
	}

	function openPullDocumentDialog() {
		const dialog = new frappe.ui.Dialog({
			title: __("Consultar documento en SAP"),
			fields: [
				{
					fieldname: "connection",
					label: __("Conexión SAP"),
					fieldtype: "Select",
					options: connections.map((row) => row.name).join("\n"),
					reqd: 1,
				},
				{ fieldname: "sap_object", label: __("Objeto SAP"), fieldtype: "Data", reqd: 1 },
				{
					fieldname: "external_id",
					label: __("Identificador externo (SAP)"),
					fieldtype: "Data",
					reqd: 1,
				},
				{
					fieldname: "endpoint_path",
					label: __("Ruta del documento en SAP"),
					fieldtype: "Data",
					reqd: 1,
				},
			],
			primary_action_label: __("Consultar"),
			primary_action: async (values) => {
				try {
					const result = await call("nexora.integrations.sap.pull_document", {
						connection: values.connection,
						sap_object: values.sap_object,
						external_id: values.external_id,
						endpoint_path: values.endpoint_path,
						idempotency_key: ui.generateId(),
					});
					if (result.ok) {
						ui.showSuccess({
							message: __("Documento traído desde SAP: {0} (HTTP {1}).", [
								result.status,
								result.sap_status_code,
							]),
						});
					} else {
						frappe.msgprint({
							title: __("SAP rechazó la consulta"),
							message: escape(result.error || ""),
							indicator: "orange",
						});
					}
					dialog.hide();
					loadAll();
				} catch (error) {
					ui.showError(error, { title: __("No se pudo consultar el documento") });
				}
			},
		});
		dialog.show();
	}

	function call(method, args, type = "POST") {
		if (type === "GET") {
			return frappe.call({ method, type: "GET" }).then((response) => response.message);
		}
		return frappe
			.call({ method, type: "POST", args: { payload: args } })
			.then((response) => response.message);
	}
};
