// NEXORA · Notificaciones (bloque posterior al 59, NXR-NOT-0006)
//
// Bandeja real: Inbox/PWA se marcan entregados al crearse (la bandeja ES el
// mecanismo de entrega); Email usa `frappe.sendmail` real, WhatsApp reutiliza
// el canal real del Bloque 21 — ninguno de los dos se marca "Delivered" sin
// que la llamada real haya tenido éxito. Antes de este bloque, las cuatro
// funciones reales de `notifications.service` no tenían ningún llamador en
// todo el repositorio: sin esta página, ni siquiera el propio destinatario
// podía ver, marcar como leída o reintentar una notificación suya.
frappe.pages["nexora-notifications"].on_page_load = function (wrapper) {
	const page = frappe.ui.make_app_page({
		parent: wrapper,
		title: __("Notificaciones"),
		single_column: true,
	});
	const ui = window.nexora.ui;
	const escape = ui.escapeHtml;
	const isManager = () =>
		(frappe.user_roles || []).some((role) =>
			["System Manager", "NEXORA Administrator", "NEXORA Finance Manager"].includes(role)
		);

	$(page.body).append(`
		<div class="nxr-notifications">
			<p class="nxr-ds-text-secondary">${__(
				"Sus notificaciones reales — Correo y WhatsApp muestran si la entrega tuvo éxito de verdad, nunca se marcan entregadas sin haberlo intentado."
			)}</p>
			<section class="nxr-ds-card">
				<div class="nxr-notifications-filters"></div>
				<div class="nxr-notifications-table"></div>
			</section>
		</div>
	`);

	const filters = buildFilters($(page.body).find(".nxr-notifications-filters"));
	if (isManager()) {
		page.add_button(__("Enviar notificación"), openCreateDialog, "primary");
	}
	page.add_button(__("Actualizar"), () => loadAll());

	let notifications = [];

	loadAll().catch((error) => console.error("NEXORA notifications panel failed to load", error));

	function buildFilters(container) {
		container.html(`
			<div class="nxr-notifications-filter-row">
				<select class="nxr-ds-select nxr-notif-filter-channel" style="max-width: 180px; display: inline-block;">
					<option value="">${__("Todos los canales")}</option>
					<option value="Inbox">Inbox</option>
					<option value="Email">Email</option>
					<option value="PWA">PWA</option>
					<option value="WhatsApp">WhatsApp</option>
				</select>
				<select class="nxr-ds-select nxr-notif-filter-status" style="max-width: 180px; display: inline-block;">
					<option value="">${__("Todos los estados")}</option>
					<option value="Created">Created</option>
					<option value="Delivered">Delivered</option>
					<option value="Failed">Failed</option>
				</select>
				<select class="nxr-ds-select nxr-notif-filter-read" style="max-width: 180px; display: inline-block;">
					<option value="">${__("Leídas y no leídas")}</option>
					<option value="0">${__("Solo no leídas")}</option>
					<option value="1">${__("Solo leídas")}</option>
				</select>
			</div>
		`);
		container.find("select").on("change", () => loadAll());
		return container;
	}

	async function loadAll() {
		const channel = $(page.body).find(".nxr-notif-filter-channel").val();
		const deliveryStatus = $(page.body).find(".nxr-notif-filter-status").val();
		const read = $(page.body).find(".nxr-notif-filter-read").val();
		const args = { limit: 100 };
		if (channel) args.channel = channel;
		if (deliveryStatus) args.delivery_status = deliveryStatus;
		if (read !== "") args.read = read === "1" ? 1 : 0;
		notifications = (await call("nexora.notifications.service.list_notifications", args)) || [];
		renderTable();
	}

	function renderTable() {
		const box = $(page.body).find(".nxr-notifications-table");
		if (!notifications.length) {
			box.html(`<p class="nxr-ds-text-secondary">${__("Ninguna notificación con estos filtros.")}</p>`);
			return;
		}
		box.html(`
			<div class="nxr-ds-table-wrap"><table class="nxr-ds-table">
				<thead><tr>
					<th></th><th>${__("Asunto")}</th><th>${__("Tipo")}</th><th>${__("Canal")}</th><th>${__(
			"Prioridad"
		)}</th><th>${__("Entrega")}</th><th>${__("Fecha")}</th><th></th>
				</tr></thead>
				<tbody>${notifications.map(rowHtml).join("")}</tbody>
			</table></div>
		`);
	}

	function rowHtml(row) {
		const canRetry =
			row.delivery_status === "Failed" && ["Email", "WhatsApp"].includes(row.channel) && isManager();
		return `
			<tr class="${row.read ? "" : "nxr-notif-unread"}">
				<td>${row.read ? "" : `<span class="indicator blue"></span>`}</td>
				<td><strong>${escape(row.subject)}</strong>${
			row.body ? `<br><small class="nxr-ds-text-secondary">${escape(row.body)}</small>` : ""
		}</td>
				<td>${typeBadge(row.notification_type)}</td>
				<td>${escape(row.channel)}</td>
				<td>${escape(row.priority)}</td>
				<td>${deliveryBadge(row.delivery_status, row.failure_reason)}</td>
				<td>${escape(row.creation || "—")}</td>
				<td>
					${
						row.read
							? ""
							: `<button type="button" class="nxr-ds-btn nxr-ds-btn--secondary nxr-ds-btn--sm" data-mark-read="${escape(
									row.name
							  )}">${__("Marcar leída")}</button>`
					}
					${
						canRetry
							? `<button type="button" class="nxr-ds-btn nxr-ds-btn--secondary nxr-ds-btn--sm" data-retry="${escape(
									row.name
							  )}">${__("Reintentar")}</button>`
							: ""
					}
				</td>
			</tr>
		`;
	}

	function typeBadge(type) {
		const color =
			type === "Error" ? "red" : type === "Warning" ? "orange" : type === "Success" ? "green" : "grey";
		return `<span class="indicator ${color}">${escape(type)}</span>`;
	}

	function deliveryBadge(status, failureReason) {
		const color = status === "Delivered" ? "green" : status === "Failed" ? "red" : "grey";
		const title = failureReason ? ` title="${escape(failureReason)}"` : "";
		return `<span class="indicator ${color}"${title}>${escape(status)}</span>`;
	}

	$(page.body).on("click", "[data-mark-read]", async function () {
		const notification = $(this).attr("data-mark-read");
		try {
			await call("nexora.notifications.service.mark_read", { notification });
			loadAll();
		} catch (error) {
			ui.showError(error, { title: __("No se pudo marcar como leída") });
		}
	});

	$(page.body).on("click", "[data-retry]", async function () {
		const notification = $(this).attr("data-retry");
		try {
			const result = await call("nexora.notifications.service.retry_notification", { notification });
			frappe.show_alert({
				message:
					result.delivery_status === "Delivered"
						? __("Entrega exitosa.")
						: __("La entrega volvió a fallar: {0}", [result.failure_reason || ""]),
				indicator: result.delivery_status === "Delivered" ? "green" : "red",
			});
			loadAll();
		} catch (error) {
			ui.showError(error, { title: __("No se pudo reintentar la entrega") });
		}
	});

	function openCreateDialog() {
		const dialog = new frappe.ui.Dialog({
			title: __("Enviar notificación"),
			fields: [
				{
					fieldname: "recipient_user",
					label: __("Destinatario"),
					fieldtype: "Link",
					options: "User",
					reqd: 1,
				},
				{ fieldname: "subject", label: __("Asunto"), fieldtype: "Data", reqd: 1 },
				{ fieldname: "body", label: __("Mensaje"), fieldtype: "Small Text" },
				{
					fieldname: "notification_type",
					label: __("Tipo"),
					fieldtype: "Select",
					options: "Info\nWarning\nError\nSuccess",
					default: "Info",
				},
				{
					fieldname: "channel",
					label: __("Canal"),
					fieldtype: "Select",
					options: "Inbox\nEmail\nPWA\nWhatsApp",
					default: "Inbox",
					reqd: 1,
				},
				{
					fieldname: "priority",
					label: __("Prioridad"),
					fieldtype: "Select",
					options: "Low\nNormal\nHigh\nCritical",
					default: "Normal",
				},
			],
			primary_action_label: __("Enviar"),
			primary_action: async (values) => {
				try {
					const result = await call("nexora.notifications.service.create_notification", {
						...values,
						idempotency_key: ui.generateId(),
					});
					ui.showSuccess({
						message:
							result.delivery_status === "Failed"
								? __("Registrada, pero la entrega falló: {0}", [result.failure_reason || ""])
								: __("Notificación enviada."),
					});
					dialog.hide();
					loadAll();
				} catch (error) {
					ui.showError(error, { title: __("No se pudo enviar la notificación") });
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
