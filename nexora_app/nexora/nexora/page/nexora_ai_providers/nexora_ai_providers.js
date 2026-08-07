frappe.pages["nexora-ai-providers"].on_page_load = function (wrapper) {
	const page = frappe.ui.make_app_page({
		parent: wrapper,
		title: __("Proveedores de IA"),
		single_column: true,
	});
	const ui = window.nexora.ui || {};
	const escapeHtml = (value) => frappe.utils.escape_html(String(value ?? ""));
	const isAdministrator = () => (frappe.user_roles || []).includes("NEXORA Administrator");

	$(page.body).append(`
		<div class="nxr-ai-providers">
			<p class="text-muted">${__(
				"Configuración única del motor de IA de NEXORA: estado, salud, prioridad y credenciales de los nueve proveedores oficiales."
			)}</p>
			<section class="nxr-card">
				<h3>${__("Probar la regla de oro (fallback automático)")}</h3>
				<div class="nxr-ai-fallback-controls"></div>
				<div class="nxr-ai-fallback-result text-muted">${__(
					"Elija una capacidad y ejecute la prueba para ver qué proveedor respondería ahora, con reintento automático si falla."
				)}</div>
			</section>
			<section class="nxr-card">
				<h3>${__("Proveedores")}</h3>
				<div class="nxr-ai-providers-table"></div>
			</section>
		</div>
	`);

	const fallbackControls = buildFallbackControls($(page.body).find(".nxr-ai-fallback-controls"));
	page.add_button(__("Actualizar"), () => loadAll());
	if (isAdministrator()) {
		page.add_button(__("Guardar credencial"), openCredentialDialog, "primary");
		page.add_button(__("Registrar proveedor"), openRegisterDialog);
	}

	let providers = [];
	let usageByProvider = {};

	loadAll().catch((error) => console.error("NEXORA AI providers panel failed to load", error));

	async function loadAll() {
		const [providerList, credentialStatus, usage] = await Promise.all([
			call("nexora.intelligence.service.list_providers", {}),
			call("nexora.intelligence.service.list_credential_status", {}),
			call("nexora.intelligence.service.get_provider_usage_summary", { limit: 500 }),
		]);
		const credentialByKey = Object.fromEntries(
			(credentialStatus || []).map((row) => [row.provider_key, row])
		);
		usageByProvider = Object.fromEntries((usage || []).map((row) => [row.provider_key, row]));
		providers = (providerList || []).map((row) => ({
			...row,
			credential: credentialByKey[row.provider_key],
		}));
		renderTable();
	}

	function renderTable() {
		const rows = providers
			.slice()
			.sort((a, b) => a.priority - b.priority)
			.map(rowHtml)
			.join("");
		$(page.body).find(".nxr-ai-providers-table").html(`
				<table class="table table-bordered nxr-ai-providers-grid">
					<thead>
						<tr>
							<th>${__("Proveedor")}</th>
							<th>${__("Estado")}</th>
							<th>${__("Circuito")}</th>
							<th>${__("Credencial")}</th>
							<th>${__("Prioridad")}</th>
							<th>${__("Por defecto")}</th>
							<th>${__("Modelo")}</th>
							<th>${__("Latencia prom.")}</th>
							<th>${__("Éxito")}</th>
							<th>${__("Acciones")}</th>
						</tr>
					</thead>
					<tbody>${rows}</tbody>
				</table>
			`);
		bindRowActions();
	}

	function rowHtml(row) {
		const usage = usageByProvider[row.provider_key];
		const credentialSource = row.credential?.source || "none";
		const credentialLabel =
			credentialSource === "environment"
				? __("Entorno")
				: credentialSource === "database"
				? __("Guardada")
				: __("Sin configurar");
		const latency = usage?.avg_latency_ms != null ? `${usage.avg_latency_ms} ms` : "—";
		const successRate = usage?.success_rate != null ? `${Math.round(usage.success_rate * 100)}%` : "—";
		return `
			<tr data-provider-key="${escapeHtml(row.provider_key)}">
				<td><strong>${escapeHtml(row.display_name)}</strong><br><code>${escapeHtml(row.provider_key)}</code></td>
				<td>${statusBadge(row.status)}</td>
				<td>${circuitBadge(row.circuit_state, row.last_error_kind)}</td>
				<td>${escapeHtml(credentialLabel)}</td>
				<td>${escapeHtml(row.priority)}</td>
				<td>${row.is_default ? "★" : ""}</td>
				<td>${escapeHtml(row.default_model || "—")}</td>
				<td>${escapeHtml(latency)}</td>
				<td>${escapeHtml(successRate)}</td>
				<td class="nxr-ai-actions">
					<button class="btn btn-xs btn-default nxr-ai-test">${__("Probar conexión")}</button>
					${
						isAdministrator()
							? `
						<button class="btn btn-xs btn-default nxr-ai-toggle">${
							row.status === "Active" ? __("Desactivar") : __("Activar")
						}</button>
						<button class="btn btn-xs btn-default nxr-ai-default">${__("Predeterminar")}</button>
						<button class="btn btn-xs btn-default nxr-ai-configure">${__("Configurar")}</button>
					`
							: ""
					}
				</td>
			</tr>
		`;
	}

	function statusBadge(status) {
		const color = status === "Active" ? "green" : status === "Error" ? "red" : "grey";
		return `<span class="indicator ${color}">${escapeHtml(status)}</span>`;
	}

	function circuitBadge(state, lastErrorKind) {
		const color = state === "Open" ? "red" : state === "Half-Open" ? "orange" : "green";
		const suffix = state !== "Closed" && lastErrorKind ? ` (${escapeHtml(lastErrorKind)})` : "";
		return `<span class="indicator ${color}">${escapeHtml(state || "Closed")}</span>${suffix}`;
	}

	function bindRowActions() {
		$(page.body)
			.find(".nxr-ai-test")
			.on("click", function () {
				const providerKey = $(this).closest("tr").data("provider-key");
				testConnection(providerKey);
			});
		$(page.body)
			.find(".nxr-ai-toggle")
			.on("click", function () {
				const row = $(this).closest("tr");
				const providerKey = row.data("provider-key");
				const provider = providers.find((p) => p.provider_key === providerKey);
				toggleStatus(providerKey, provider?.status === "Active" ? "Inactive" : "Active");
			});
		$(page.body)
			.find(".nxr-ai-default")
			.on("click", function () {
				setDefault($(this).closest("tr").data("provider-key"));
			});
		$(page.body)
			.find(".nxr-ai-configure")
			.on("click", function () {
				const providerKey = $(this).closest("tr").data("provider-key");
				openConfigDialog(providers.find((p) => p.provider_key === providerKey));
			});
	}

	async function testConnection(providerKey) {
		try {
			const result = await call(
				"nexora.intelligence.service.test_provider_connection",
				{ provider_key: providerKey },
				{ freeze: true, freeze_message: __("Probando conexión…") }
			);
			if (result.success) {
				ui.showSuccess?.({ message: __("Conexión exitosa con {0}", [providerKey]) });
			} else {
				frappe.msgprint({
					title: __("La conexión no fue exitosa"),
					message: escapeHtml(result.reason || ""),
					indicator: "orange",
				});
			}
		} catch (error) {
			ui.showError ? ui.showError(error) : console.error(error);
		} finally {
			loadAll();
		}
	}

	async function toggleStatus(providerKey, status) {
		try {
			await call("nexora.intelligence.service.set_provider_status", {
				provider_key: providerKey,
				status,
			});
			ui.showSuccess?.({ message: __("Estado actualizado") });
		} catch (error) {
			ui.showError ? ui.showError(error) : console.error(error);
		} finally {
			loadAll();
		}
	}

	async function setDefault(providerKey) {
		try {
			await call("nexora.intelligence.service.set_default_provider", { provider_key: providerKey });
			ui.showSuccess?.({ message: __("Proveedor por defecto actualizado") });
		} catch (error) {
			ui.showError ? ui.showError(error) : console.error(error);
		} finally {
			loadAll();
		}
	}

	function openConfigDialog(provider) {
		if (!provider) return;
		const dialog = new frappe.ui.Dialog({
			title: __("Configurar {0}", [provider.display_name]),
			fields: [
				{
					fieldname: "default_model",
					label: __("Modelo por defecto"),
					fieldtype: "Data",
					default: provider.default_model,
				},
				{
					fieldname: "priority",
					label: __("Prioridad"),
					fieldtype: "Int",
					default: provider.priority,
				},
				{
					fieldname: "cost_hint",
					label: __("Costo relativo"),
					fieldtype: "Select",
					options: "Low\nMedium\nHigh",
					default: provider.cost_hint,
				},
				{
					fieldname: "timeout_seconds",
					label: __("Tiempo de espera (s)"),
					fieldtype: "Int",
					default: provider.timeout_seconds,
				},
				{
					fieldname: "temperature",
					label: __("Temperatura"),
					fieldtype: "Float",
					default: provider.temperature,
				},
				{
					fieldname: "max_tokens",
					label: __("Máximo de tokens"),
					fieldtype: "Int",
					default: provider.max_tokens,
				},
			],
			primary_action_label: __("Guardar"),
			primary_action: async (values) => {
				try {
					await call("nexora.intelligence.service.update_provider_config", {
						provider_key: provider.provider_key,
						...values,
					});
					ui.showSuccess?.({ message: __("Configuración actualizada") });
					dialog.hide();
					loadAll();
				} catch (error) {
					ui.showError ? ui.showError(error) : console.error(error);
				}
			},
		});
		dialog.show();
	}

	function openRegisterDialog() {
		const dialog = new frappe.ui.Dialog({
			title: __("Registrar proveedor de IA"),
			fields: [
				{ fieldname: "provider_key", label: __("Clave (ej. openai)"), fieldtype: "Data", reqd: 1 },
				{ fieldname: "display_name", label: __("Nombre visible"), fieldtype: "Data", reqd: 1 },
				{
					fieldname: "capabilities",
					label: __("Capacidades (separadas por coma)"),
					fieldtype: "Data",
					reqd: 1,
					default: "text",
				},
				{ fieldname: "priority", label: __("Prioridad"), fieldtype: "Int", default: 100 },
			],
			primary_action_label: __("Registrar"),
			primary_action: async (values) => {
				try {
					await call("nexora.intelligence.service.register_provider", {
						...values,
						idempotency_key: ui.generateId ? ui.generateId() : frappe.utils.get_random(20),
					});
					ui.showSuccess?.({ message: __("Proveedor registrado") });
					dialog.hide();
					loadAll();
				} catch (error) {
					ui.showError ? ui.showError(error) : console.error(error);
				}
			},
		});
		dialog.show();
	}

	function openCredentialDialog() {
		const dialog = new frappe.ui.Dialog({
			title: __("Guardar credencial"),
			fields: [
				{
					fieldname: "provider_key",
					label: __("Proveedor"),
					fieldtype: "Select",
					options: providers.map((p) => p.provider_key).join("\n"),
					reqd: 1,
				},
				{
					fieldname: "secret",
					label: __("API Key"),
					fieldtype: "Password",
					reqd: 1,
					description: __("Se cifra en reposo. Nunca se vuelve a mostrar tras guardarla."),
				},
			],
			primary_action_label: __("Guardar"),
			primary_action: async (values) => {
				try {
					await call("nexora.intelligence.service.save_credential", values);
					ui.showSuccess?.({ message: __("Credencial guardada") });
					dialog.hide();
					loadAll();
				} catch (error) {
					ui.showError ? ui.showError(error) : console.error(error);
				}
			},
		});
		dialog.show();
	}

	function buildFallbackControls(container) {
		container.html(`
			<div class="nxr-ai-fallback-row">
				<select class="form-control nxr-ai-fallback-capability" style="max-width: 220px; display: inline-block;">
					<option value="text">text</option>
					<option value="vision">vision</option>
					<option value="audio">audio</option>
					<option value="embedding">embedding</option>
				</select>
				<button class="btn btn-default nxr-ai-fallback-run">${__("Ejecutar prueba")}</button>
			</div>
		`);
		container.find(".nxr-ai-fallback-run").on("click", runFallbackTest);
		return container;
	}

	async function runFallbackTest() {
		const capability = $(page.body).find(".nxr-ai-fallback-capability").val();
		const resultBox = $(page.body).find(".nxr-ai-fallback-result");
		resultBox.text(__("Ejecutando…"));
		try {
			const result = await call(
				"nexora.intelligence.service.run_orchestrated_request",
				{ capability, prompt: "ping" },
				{ freeze: true, freeze_message: __("Probando proveedores en orden…") }
			);
			if (result.success) {
				resultBox.html(
					`<span class="indicator green">${__("Respondió")}: <strong>${escapeHtml(
						result.provider_key
					)}</strong></span>`
				);
			} else {
				const attempts = (result.attempts || [])
					.map((a) => `${escapeHtml(a.provider_key)} (${escapeHtml(a.error_kind)})`)
					.join(", ");
				resultBox.html(
					`<span class="indicator red">${__("Ningún proveedor respondió")}</span>` +
						(attempts ? `<br><small>${__("Intentos")}: ${attempts}</small>` : "")
				);
			}
		} catch (error) {
			resultBox.text(error?.message || __("Error al ejecutar la prueba."));
		} finally {
			loadAll();
		}
	}

	async function call(method, args, options = {}) {
		const response = await frappe.call({
			method,
			type: "POST",
			args: { payload: args },
			...options,
		});
		return response.message;
	}
};
