// NEXORA · Integraciones (bloque posterior al 58, NXR-INT-001)
//
// Registro genérico de integraciones REST/SOAP/Webhook/Custom
// (`integrations.service`), con prueba de conectividad explícita y separada
// del registro, mismo principio que
// `conversation.channels.whatsapp.connect_credential` vs.
// `test_channel_connection`.
//
// Cierre de producción, Paso 2: las conexiones SAP reales vivían aquí,
// compartiendo esta misma tabla genérica con REST/SOAP/Webhook — sin
// experiencia propia, sin pestañas de salud/documentos/auditoría. Se movieron
// a `nexora-sap`, su propia página, con el mismo backend real
// (`integrations.sap`) detrás; esta pantalla ya no las gestiona, solo apunta
// a dónde viven ahora.
frappe.pages["nexora-integrations"].on_page_load = function (wrapper) {
	const page = frappe.ui.make_app_page({
		parent: wrapper,
		title: __("Integraciones"),
		single_column: true,
	});
	const ui = window.nexora.ui;
	const escape = ui.escapeHtml;
	const isManager = () =>
		(frappe.user_roles || []).some((role) =>
			["System Manager", "NEXORA Administrator", "NEXORA Finance Manager"].includes(role)
		);

	$(page.body).append(`
		<div class="nxr-integrations">
			<p class="nxr-ds-text-secondary">${__(
				"Registro genérico de integraciones externas REST/SOAP/Webhook/Custom, con prueba de conectividad explícita — nunca se marca una conexión como exitosa sin haberla probado."
			)}</p>
			<p class="nxr-ds-notice nxr-ds-notice--info">${__(
				"Las conexiones SAP tienen su propia superficie completa (resumen, conexiones, salud, documentos, sincronización, errores, auditoría y configuración) en"
			)} <a href="/app/nexora-sap">${__("SAP")}</a>.</p>
			<section class="nxr-ds-card">
				<h3>${__("Integraciones")}</h3>
				<div class="nxr-integrations-table"></div>
			</section>
		</div>
	`);

	if (isManager()) {
		page.add_button(__("Registrar integración"), openRegisterIntegrationDialog, "primary");
	}
	page.add_button(__("Actualizar"), () => loadAll());

	let integrations = [];

	loadAll().catch((error) => console.error("NEXORA integrations panel failed to load", error));

	async function loadAll() {
		integrations = (await call("nexora.integrations.service.list_integrations", {})) || [];
		renderIntegrations();
	}

	function renderIntegrations() {
		const box = $(page.body).find(".nxr-integrations-table");
		box.html(`
			<div class="nxr-ds-table-wrap"><table class="nxr-ds-table">
				<thead><tr>
					<th>${__("Nombre")}</th><th>${__("Tipo")}</th><th>${__("Endpoint")}</th><th>${__("Estado")}</th><th>${__(
			"Última prueba"
		)}</th><th>${__("Resultado")}</th><th></th>
				</tr></thead>
				<tbody>${
					integrations.length
						? integrations.map(integrationRowHtml).join("")
						: `<tr><td class="nxr-ds-table__empty" colspan="7">${__(
								"Ninguna integración registrada todavía."
						  )}</td></tr>`
				}</tbody>
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
						? `<button type="button" class="nxr-ds-btn nxr-ds-btn--secondary nxr-ds-btn--sm" data-test-integration="${escape(
								row.name
						  )}">${__("Probar conexión")}</button>`
						: ""
				}</td>
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

	function call(method, args) {
		return frappe
			.call({ method, type: "POST", args: { payload: args } })
			.then((response) => response.message);
	}
};
