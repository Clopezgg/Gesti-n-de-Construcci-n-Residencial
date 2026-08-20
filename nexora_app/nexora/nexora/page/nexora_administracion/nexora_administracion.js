// NEXORA · Administración (enmienda del propietario, 2026-08-16, Constitución Cap. 14)
//
// Zona propia de NEXORA para administrar usuarios, roles, activación y
// desactivación — separada de la cuenta técnica `Administrator`, que queda
// excluida a propósito de esta pantalla (nexora.administration.service).
// Solo envuelve `User`/`Has Role`, ya maduros en Frappe; nunca reimplementa
// gestión de usuarios propia. Restringida a `NEXORA Administrator` tanto en
// el `roles` de esta página (Desk) como en cada llamada al servidor
// (`require_action("manage_users"/"view_users")`, permissions.py).
frappe.pages["nexora-administracion"].on_page_load = function (wrapper) {
	const page = frappe.ui.make_app_page({
		parent: wrapper,
		title: __("Administración"),
		single_column: true,
	});
	const escape = (value) => window.nexora.ui.escapeHtml(value);
	const ROLE_LABELS = {};
	let currentStatusFilter = "";

	$(page.body).append(`
		<div class="nxr-admin">
			<p class="text-muted">${__(
				"Usuarios y roles de NEXORA. La cuenta técnica Administrator no se administra desde aquí."
			)}</p>
			<section class="nxr-ds-card">
				<h3>${__("Usuarios")}</h3>
				<div class="nxr-admin-users"></div>
			</section>
			<section class="nxr-ds-card">
				<h3>${__("Actividad reciente")}</h3>
				<div class="nxr-admin-activity"></div>
			</section>
		</div>
	`);

	page.add_field({
		fieldname: "status",
		label: __("Estado"),
		fieldtype: "Select",
		options: [
			{ label: __("Todos"), value: "" },
			{ label: __("Activos"), value: "Active" },
			{ label: __("Inactivos"), value: "Inactive" },
		],
		change() {
			currentStatusFilter = this.get_value() || "";
			loadUsers();
		},
	});
	page.add_button(__("Actualizar"), () => loadAll());

	loadAll().catch((error) => console.error("NEXORA administration panel failed to load", error));

	async function loadAll() {
		await Promise.all([loadRoles().then(loadUsers), loadActivity()]);
	}

	async function loadRoles() {
		const roles = await call("nexora.administration.service.list_nexora_roles", {});
		(roles || []).forEach((row) => {
			ROLE_LABELS[row.role] = row.label;
		});
	}

	async function loadUsers() {
		const users = await call("nexora.administration.service.list_users", {
			payload: { status: currentStatusFilter },
		});
		renderUsers(users || []);
	}

	async function loadActivity() {
		const rows = await call("nexora.administration.service.list_recent_activity", {
			payload: { limit: 30 },
		});
		renderActivity(rows || []);
	}

	function renderUsers(users) {
		const box = $(page.body).find(".nxr-admin-users");
		if (!users.length) {
			box.html(`<p class="text-muted">${__("Ningún usuario encontrado.")}</p>`);
			return;
		}
		box.html(`
			<div class="nxr-ds-table-wrap"><table class="nxr-ds-table">
				<thead><tr>
					<th>${__("Usuario")}</th><th>${__("Correo")}</th><th>${__("Roles NEXORA")}</th>
					<th>${__("Estado")}</th><th>${__("Último acceso")}</th><th></th>
				</tr></thead>
				<tbody>${users
					.map(
						(row) => `
					<tr>
						<td>${escape(row.full_name || row.name)}</td>
						<td>${escape(row.email || row.name)}</td>
						<td>${(row.nexora_roles || []).map((role) => escape(ROLE_LABELS[role] || role)).join(", ") || "—"}</td>
						<td>${row.enabled ? __("Activo") : __("Inactivo")}</td>
						<td>${escape(row.last_login || "—")}</td>
						<td>
							<button type="button" class="nxr-ds-btn nxr-ds-btn--secondary nxr-ds-btn--sm" data-roles="${escape(
								row.name
							)}">${__("Roles")}</button>
							<button type="button" class="nxr-ds-btn nxr-ds-btn--secondary nxr-ds-btn--sm" data-toggle-status="${escape(
								row.name
							)}" data-enabled="${row.enabled ? 1 : 0}">${
							row.enabled ? __("Desactivar") : __("Activar")
						}</button>
						</td>
					</tr>`
					)
					.join("")}</tbody>
			</table></div>
		`);
	}

	function renderActivity(rows) {
		const box = $(page.body).find(".nxr-admin-activity");
		if (!rows.length) {
			box.html(`<p class="text-muted">${__("Sin actividad registrada todavía.")}</p>`);
			return;
		}
		box.html(`
			<div class="nxr-ds-table-wrap"><table class="nxr-ds-table">
				<thead><tr>
					<th>${__("Evento")}</th><th>${__("Usuario afectado")}</th><th>${__("Por")}</th><th>${__("Fecha")}</th>
				</tr></thead>
				<tbody>${rows
					.map(
						(row) => `
					<tr>
						<td>${escape(row.event_type)}</td>
						<td>${escape(row.reference_name)}</td>
						<td>${escape(row.actor)}</td>
						<td>${escape(row.creation)}</td>
					</tr>`
					)
					.join("")}</tbody>
			</table></div>
		`);
	}

	$(page.body).on("click", "[data-toggle-status]", async function () {
		const user = $(this).attr("data-toggle-status");
		const currentlyEnabled = $(this).attr("data-enabled") === "1";
		const nextEnabled = !currentlyEnabled;
		const confirmMessage = nextEnabled
			? __("¿Activar a {0}?", [user])
			: __("¿Desactivar a {0}? Perderá acceso a NEXORA de inmediato.", [user]);
		frappe.confirm(confirmMessage, async () => {
			try {
				await call("nexora.administration.service.set_user_status", {
					payload: { user, enabled: nextEnabled },
				});
				await loadUsers();
			} catch (error) {
				window.nexora.ui.showError(error, { title: __("No se pudo cambiar el estado") });
			}
		});
	});

	$(page.body).on("click", "[data-roles]", async function () {
		const user = $(this).attr("data-roles");
		await openRolesDialog(user);
	});

	// Un campo `Check` por rol en vez de un único `MultiCheck`: cinco booleanos
	// son un tipo de campo que `frappe.prompt` resuelve sin ambigüedad; no hay
	// forma de verificar en este entorno (sin bench/navegador real) la forma
	// exacta del valor que devolvería un `MultiCheck`, así que se evita esa
	// incertidumbre en vez de arriesgar una pantalla que se ve bien pero no
	// funciona.
	async function openRolesDialog(user) {
		const users = await call("nexora.administration.service.list_users", { payload: {} });
		const current = (users || []).find((row) => row.name === user);
		const currentRoles = new Set((current && current.nexora_roles) || []);
		const roleOrder = Object.keys(ROLE_LABELS).length
			? Object.keys(ROLE_LABELS)
			: [
					"NEXORA Administrator",
					"NEXORA Finance Manager",
					"NEXORA Finance Operator",
					"NEXORA Auditor",
					"NEXORA Project Viewer",
			  ];
		const fieldnameOf = (role) => `role__${role.replace(/[^a-zA-Z0-9]/g, "_")}`;
		const fields = roleOrder.map((role) => ({
			fieldname: fieldnameOf(role),
			label: ROLE_LABELS[role] || role,
			fieldtype: "Check",
			default: currentRoles.has(role) ? 1 : 0,
		}));
		const values = await new Promise((resolve) =>
			frappe.prompt(fields, resolve, __("Roles de {0}", [user]))
		);
		if (!values) return;
		const roles = roleOrder.filter((role) => values[fieldnameOf(role)]);
		try {
			await call("nexora.administration.service.set_user_roles", {
				payload: { user, roles },
			});
			await loadUsers();
		} catch (error) {
			window.nexora.ui.showError(error, { title: __("No se pudieron actualizar los roles") });
		}
	}

	function call(method, args) {
		return frappe
			.call({ method, type: "POST", args, freeze: false })
			.then((response) => response.message);
	}
};
