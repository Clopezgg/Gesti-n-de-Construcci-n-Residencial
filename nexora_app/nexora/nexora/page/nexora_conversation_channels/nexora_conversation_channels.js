// NEXORA · Canales de conversación (Bloque 21, NXR-INT-0008)
//
// Conecta un número real de WhatsApp Business Cloud API (App ID, App Secret,
// token de acceso, phone_number_id, WABA ID, verify token — todo ya emitido
// por Meta, nunca generado por esta pantalla) y vincula números externos a
// usuarios reales de NEXORA. Los mensajes entrantes se procesan con
// `nexora.conversation.dispatch.send_message`, el mismo motor del Bloque 18 —
// esta pantalla no interpreta ni ejecuta nada por su cuenta.
frappe.pages["nexora-conversation-channels"].on_page_load = function (wrapper) {
	const page = frappe.ui.make_app_page({
		parent: wrapper,
		title: __("Canales"),
		single_column: true,
	});
	const escape = (value) => window.nexora.ui.escapeHtml(value);
	const isAdministrator = () => (frappe.user_roles || []).includes("NEXORA Administrator");

	$(page.body).append(`
		<div class="nxr-channels">
			<p class="text-muted">${__(
				"Conexión real con WhatsApp Business Cloud API — requiere credenciales ya emitidas por Meta for Developers (App ID, App Secret, token de acceso, ID del número, WABA ID y verify token)."
			)}</p>
			<section class="nxr-ds-card nxr-channels-status"></section>
			<section class="nxr-ds-card">
				<h3>${__("Números vinculados")}</h3>
				<div class="nxr-channels-accounts"></div>
			</section>
		</div>
	`);

	if (isAdministrator()) {
		page.add_button(__("Conectar WhatsApp"), openConnectDialog, "primary");
		page.add_button(__("Probar conexión"), testConnection);
		page.add_button(__("Desactivar WhatsApp"), deactivateCredential);
		page.add_button(__("Vincular número"), openLinkDialog);
	}
	page.add_button(__("Actualizar"), () => loadAll());

	loadAll().catch((error) => console.error("NEXORA channels panel failed to load", error));

	async function loadAll() {
		const [status, accounts] = await Promise.all([
			call("nexora.conversation.channels.whatsapp.get_channel_status", {}),
			call("nexora.conversation.channels.whatsapp.list_channel_accounts", {}),
		]);
		renderStatus(status);
		renderAccounts(accounts || []);
	}

	function renderStatus(status) {
		const box = $(page.body).find(".nxr-channels-status");
		if (!status || !status.configured) {
			box.html(`<p class="text-muted">${__("Ningún canal conectado todavía.")}</p>`);
			return;
		}
		box.html(`
			<h3>${__("WhatsApp Business")}</h3>
			<dl class="nxr-channels-status-list">
				<dt>${__("Estado")}</dt><dd>${escape(window.nexora.ui.label("status", status.status))}</dd>
				<dt>${__("Número")}</dt><dd>${escape(status.display_phone_number || "—")}</dd>
				<dt>${__("Última prueba")}</dt><dd>${escape(status.last_test_at || "—")}</dd>
				<dt>${__("Resultado")}</dt><dd>${escape(status.last_test_result || "—")}</dd>
			</dl>
		`);
	}

	function renderAccounts(accounts) {
		const box = $(page.body).find(".nxr-channels-accounts");
		if (!accounts.length) {
			box.html(`<p class="text-muted">${__("Ningún número vinculado todavía.")}</p>`);
			return;
		}
		box.html(`
			<div class="nxr-ds-table-wrap"><table class="nxr-ds-table">
				<thead><tr>
					<th>${__("Número")}</th><th>${__("Usuario")}</th><th>${__("Estado")}</th><th>${__(
			"Vinculado el"
		)}</th><th></th>
				</tr></thead>
				<tbody>${accounts
					.map(
						(row) => `
					<tr>
						<td>${escape(row.external_id)}</td>
						<td>${escape(row.user)}</td>
						<td>${escape(window.nexora.ui.label("status", row.status))}</td>
						<td>${escape(row.linked_at || "—")}</td>
						<td>${
							row.status === "Active" && isAdministrator()
								? `<button type="button" class="btn btn-xs btn-default" data-revoke="${escape(
										row.name
								  )}">${__("Revocar")}</button>`
								: ""
						}</td>
					</tr>`
					)
					.join("")}</tbody>
			</table></div>
		`);
	}

	$(page.body).on("click", "[data-revoke]", async function () {
		const channel_account = $(this).attr("data-revoke");
		try {
			await call("nexora.conversation.channels.whatsapp.revoke_channel_account", {
				payload: { channel_account },
			});
			await loadAll();
		} catch (error) {
			window.nexora.ui.showError(error, { title: __("No se pudo revocar el número") });
		}
	});

	async function openConnectDialog() {
		const values = await promptValues(
			[
				{ fieldname: "app_id", label: __("App ID de Meta"), fieldtype: "Data", reqd: 1 },
				{ fieldname: "app_secret", label: __("App Secret"), fieldtype: "Password", reqd: 1 },
				{ fieldname: "access_token", label: __("Token de acceso"), fieldtype: "Password", reqd: 1 },
				{
					fieldname: "phone_number_id",
					label: __("ID del número (phone_number_id)"),
					fieldtype: "Data",
					reqd: 1,
				},
				{
					fieldname: "waba_id",
					label: __("WhatsApp Business Account ID"),
					fieldtype: "Data",
					reqd: 1,
				},
				{
					fieldname: "verify_token",
					label: __("Token de verificación del webhook"),
					fieldtype: "Password",
					reqd: 1,
				},
			],
			__("Conectar WhatsApp Business")
		);
		if (!values) return;
		try {
			await call("nexora.conversation.channels.whatsapp.connect_credential", { payload: values });
			frappe.show_alert({
				message: __("Credencial guardada. Ahora pruebe la conexión para activarla."),
				indicator: "green",
			});
			await loadAll();
		} catch (error) {
			window.nexora.ui.showError(error, { title: __("No se pudo guardar la credencial") });
		}
	}

	async function testConnection() {
		try {
			const result = await call("nexora.conversation.channels.whatsapp.test_channel_connection", {});
			frappe.show_alert({
				message: result.success
					? __("Conexión verificada: {0}", [result.display_phone_number || ""])
					: __("Meta rechazó la conexión: {0}", [result.detail || ""]),
				indicator: result.success ? "green" : "red",
			});
			await loadAll();
		} catch (error) {
			window.nexora.ui.showError(error, { title: __("No se pudo probar la conexión") });
		}
	}

	async function deactivateCredential() {
		frappe.confirm(
			__(
				"¿Desactivar WhatsApp? Se dejará de procesar mensajes entrantes hasta que vuelva a probar la conexión."
			),
			async () => {
				try {
					await call("nexora.conversation.channels.whatsapp.deactivate_credential", {});
					frappe.show_alert({ message: __("WhatsApp desactivado."), indicator: "orange" });
					await loadAll();
				} catch (error) {
					window.nexora.ui.showError(error, { title: __("No se pudo desactivar WhatsApp") });
				}
			}
		);
	}

	async function openLinkDialog() {
		const values = await promptValues(
			[
				{
					fieldname: "external_id",
					label: __("Número de WhatsApp (solo dígitos, con código de país)"),
					fieldtype: "Data",
					reqd: 1,
				},
				{
					fieldname: "user",
					label: __("Usuario NEXORA"),
					fieldtype: "Link",
					options: "User",
					reqd: 1,
				},
			],
			__("Vincular número a un usuario")
		);
		if (!values) return;
		try {
			await call("nexora.conversation.channels.whatsapp.link_channel_account", { payload: values });
			await loadAll();
		} catch (error) {
			window.nexora.ui.showError(error, { title: __("No se pudo vincular el número") });
		}
	}

	function promptValues(fields, title) {
		return new Promise((resolve) => frappe.prompt(fields, resolve, title));
	}

	function call(method, args) {
		return frappe
			.call({ method, type: "POST", args, freeze: false })
			.then((response) => response.message);
	}
};
