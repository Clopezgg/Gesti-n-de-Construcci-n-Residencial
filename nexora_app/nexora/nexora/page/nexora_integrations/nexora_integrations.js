// NEXORA · Integraciones (bloque posterior al 58, NXR-INT-001)
//
// Registro genérico de integraciones REST/SOAP/Webhook/Custom
// (`integrations.service`) y conexiones SAP reales (`integrations.sap`) —
// ambas con prueba de conectividad explícita y separada del registro, mismo
// principio que `conversation.channels.whatsapp.connect_credential` vs.
// `test_channel_connection`. Antes de este bloque, las siete funciones reales
// detrás de esta pantalla no tenían ningún llamador en todo el repositorio.
frappe.pages["nexora-integrations"].on_page_load = function (wrapper) {
	const page = frappe.ui.make_app_page({
		parent: wrapper,
		title: __("Integraciones"),
		single_column: true,
	});
	const ui = window.nexora.ui;
	const escape = ui.escapeHtml;
	const isAdministrator = () => (frappe.user_roles || []).includes("NEXORA Administrator");
	const isManager = () =>
		(frappe.user_roles || []).some((role) =>
			["System Manager", "NEXORA Administrator", "NEXORA Finance Manager"].includes(role)
		);

	$(page.body).append(`
		<div class="nxr-integrations">
			<p class="text-muted">${__(
				"Integraciones externas de NEXORA: registro genérico REST/SOAP/Webhook y conexiones SAP reales, con prueba de conectividad explícita — nunca se marca una conexión como exitosa sin haberla probado."
			)}</p>
			<section class="nxr-ds-card">
				<h3>${__("Integraciones")}</h3>
				<div class="nxr-integrations-table"></div>
			</section>
			<section class="nxr-ds-card">
				<h3>${__("Conexiones SAP")}</h3>
				<div class="nxr-sap-connections-table"></div>
			</section>
		</div>
	`);

	if (isManager()) {
		page.add_button(__("Registrar integración"), openRegisterIntegrationDialog, "primary");
		page.add_button(__("Enviar documento a SAP"), openSubmitDocumentDialog);
	}
	if (isAdministrator()) {
		page.add_button(__("Conectar SAP"), openConnectSapDialog);
	}
	page.add_button(__("Actualizar"), () => loadAll());

	let integrations = [];
	let sapConnections = [];

	loadAll().catch((error) => console.error("NEXORA integrations panel failed to load", error));

	async function loadAll() {
		const [integrationList, connectionList] = await Promise.all([
			call("nexora.integrations.service.list_integrations", {}),
			call("nexora.integrations.sap.list_connections", {}),
		]);
		integrations = integrationList || [];
		sapConnections = connectionList || [];
		renderIntegrations();
		renderSapConnections();
	}

	function renderIntegrations() {
		const box = $(page.body).find(".nxr-integrations-table");
		if (!integrations.length) {
			box.html(`<p class="text-muted">${__("Ninguna integración registrada todavía.")}</p>`);
			return;
		}
		box.html(`
			<div class="table-responsive"><table class="table table-bordered">
				<thead><tr>
					<th>${__("Nombre")}</th><th>${__("Tipo")}</th><th>${__("Endpoint")}</th><th>${__("Estado")}</th><th>${__(
			"Última prueba"
		)}</th><th>${__("Resultado")}</th><th></th>
				</tr></thead>
				<tbody>${integrations.map(integrationRowHtml).join("")}</tbody>
			</table></div>
		`);
	}

	function integrationRowHtml(row) {
		return `
			<tr>
				<td>${escape(row.integration_name)}</td>
				<td>${escape(row.integration_type)}</td>
				<td>${escape(row.endpoint_url || "—")}</td>
				<td>${statusBadge(row.status)}</td>
				<td>${escape(row.last_test_at || "—")}</td>
				<td>${resultBadge(row.last_test_result)}</td>
				<td>${
					isManager()
						? `<button type="button" class="btn btn-xs btn-default" data-test-integration="${escape(
								row.name
						  )}">${__("Probar conexión")}</button>`
						: ""
				}</td>
			</tr>
		`;
	}

	function renderSapConnections() {
		const box = $(page.body).find(".nxr-sap-connections-table");
		if (!sapConnections.length) {
			box.html(`<p class="text-muted">${__("Ninguna conexión SAP registrada todavía.")}</p>`);
			return;
		}
		box.html(`
			<div class="table-responsive"><table class="table table-bordered">
				<thead><tr>
					<th>${__("Nombre")}</th><th>${__("URL base")}</th><th>${__("Autenticación")}</th><th>${__(
			"Estado"
		)}</th><th>${__("Última prueba")}</th><th>${__("Resultado")}</th><th></th>
				</tr></thead>
				<tbody>${sapConnections.map(sapRowHtml).join("")}</tbody>
			</table></div>
		`);
	}

	function sapRowHtml(row) {
		return `
			<tr>
				<td>${escape(row.connection_name)}</td>
				<td>${escape(row.base_url)}</td>
				<td>${escape(row.auth_type)}</td>
				<td>${statusBadge(row.status)}</td>
				<td>${escape(row.last_test_at || "—")}</td>
				<td>${resultBadge(row.last_test_result)}</td>
				<td>${
					isAdministrator()
						? `<button type="button" class="btn btn-xs btn-default" data-test-connection="${escape(
								row.name
						  )}">${__("Probar conexión")}</button>`
						: ""
				}</td>
			</tr>
		`;
	}

	function statusBadge(status) {
		const color = status === "Active" ? "green" : status === "Error" ? "red" : "grey";
		return `<span class="indicator ${color}">${escape(status || "—")}</span>`;
	}

	function resultBadge(result) {
		if (!result || result === "Not Tested") {
			return `<span class="indicator grey">${__("Sin probar")}</span>`;
		}
		const color = result === "Success" ? "green" : "red";
		return `<span class="indicator ${color}">${escape(result)}</span>`;
	}

	$(page.body).on("click", "[data-test-integration]", async function () {
		const integration = $(this).attr("data-test-integration");
		try {
			const result = await call("nexora.integrations.service.test_connection", { integration });
			frappe.show_alert({
				message:
					result.last_test_result === "Success"
						? __("Conexión exitosa: {0}", [result.detail || ""])
						: __("La conexión falló: {0}", [result.detail || ""]),
				indicator: result.last_test_result === "Success" ? "green" : "red",
			});
		} catch (error) {
			ui.showError(error, { title: __("No se pudo probar la conexión") });
		} finally {
			loadAll();
		}
	});

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

	function openRegisterIntegrationDialog() {
		const dialog = new frappe.ui.Dialog({
			title: __("Registrar integración"),
			fields: [
				{ fieldname: "integration_name", label: __("Nombre"), fieldtype: "Data", reqd: 1 },
				{
					fieldname: "integration_type",
					label: __("Tipo"),
					fieldtype: "Select",
					options: "REST\nSOAP\nWebhook\nCustom",
					default: "REST",
					reqd: 1,
				},
				{ fieldname: "endpoint_url", label: __("URL del endpoint"), fieldtype: "Data" },
				{
					fieldname: "auth_type",
					label: __("Autenticación"),
					fieldtype: "Select",
					options: "None\nBasic\nToken\nOAuth",
					default: "None",
				},
				{
					fieldname: "credentials",
					label: __("Credenciales (texto libre)"),
					fieldtype: "Small Text",
				},
				{
					fieldname: "project",
					label: __("Proyecto (opcional)"),
					fieldtype: "Link",
					options: "Project",
				},
			],
			primary_action_label: __("Registrar"),
			primary_action: async (values) => {
				try {
					await call("nexora.integrations.service.register_integration", {
						...values,
						idempotency_key: ui.generateId(),
					});
					ui.showSuccess({ message: __("Integración registrada.") });
					dialog.hide();
					loadAll();
				} catch (error) {
					ui.showError(error, { title: __("No se pudo registrar la integración") });
				}
			},
		});
		dialog.show();
	}

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
		// `dialog.toggle_display(field, show)` no existe en `frappe.ui.Dialog` —
		// nunca se había abierto este diálogo en un navegador real hasta el
		// recorrido de Bloque 101, que lo encontró de inmediato como
		// `TypeError: dialog.toggle_display is not a function`. `set_df_property`
		// es el patrón real que ya usa el resto de esta app para lo mismo
		// (`nexora_operational_ui.js`, `nexora.js`).
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
					options: sapConnections.map((row) => row.name).join("\n"),
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
				} catch (error) {
					ui.showError(error, { title: __("No se pudo enviar el documento") });
				}
			},
		});
		dialog.show();
	}

	function call(method, args) {
		return frappe
			.call({ method, type: "POST", args: { payload: args } })
			.then((response) => response.message);
	}
};
