// NEXORA · Control de calidad
//
// `nexora.quality.service` existe desde el Bloque 13 (ver el comentario al
// inicio de quality/service.py) pero nunca tuvo ningún punto de entrada
// real: ni un Administrador podía crear o transicionar un control de
// calidad desde afuera del propio doctype. `list_quality_checks` ya
// devuelve todos los campos por fila, así que esta página no necesita un
// `get` aparte — el detalle se pinta con la misma fila que ya trajo la
// lista.
frappe.pages["nexora-quality"].on_page_load = function (wrapper) {
	const page = frappe.ui.make_app_page({
		parent: wrapper,
		title: __("Control de calidad"),
		single_column: true,
	});
	const controls = {};
	const add = (definition) => {
		controls[definition.fieldname] = page.add_field(definition);
		return controls[definition.fieldname];
	};
	const statusLabels = {
		Open: __("Abierto"),
		Passed: __("Aprobado"),
		Failed: __("Rechazado"),
		Corrected: __("Corregido"),
		Closed: __("Cerrado"),
	};
	const resultLabels = { Pass: __("Aprueba"), Fail: __("Rechaza"), "Not Tested": __("Sin probar") };
	// Mismo grafo que `nexora.quality.core.QUALITY_TRANSITIONS`.
	const transitions = {
		Open: ["Passed", "Failed"],
		Failed: ["Corrected"],
		Corrected: ["Passed", "Failed"],
		Passed: ["Closed"],
		Closed: [],
	};
	let currentRows = new Map();

	add({ fieldname: "project", label: __("Proyecto"), fieldtype: "Link", options: "Project" });
	add({
		fieldname: "status",
		label: __("Estado"),
		fieldtype: "Select",
		options: ["", ...Object.keys(statusLabels)],
	});

	$(page.body).append(`
		<div class="nxr-finance-grid nxr-quality-grid">
			<section class="nxr-card"><h3>${__("Controles")}</h3><div class="nxr-quality-results"></div></section>
			<section class="nxr-card"><h3>${__("Detalle")}</h3><div class="nxr-quality-detail nxr-ds-empty">${__(
		"Seleccione un control."
	)}</div></section>
			<section class="nxr-card"><h3>${__("Acciones")}</h3><div class="nxr-quality-actions"></div></section>
		</div>
	`);

	page.add_button(__("Buscar"), refresh, "primary");
	page.add_button(__("Nuevo control"), createCheck);

	function uuid() {
		return window.nexora.ui.generateId();
	}

	async function call(method, args) {
		return (await frappe.call({ method, type: "POST", args, freeze: true })).message;
	}

	function escape(value) {
		return window.nexora.ui.escapeHtml(value);
	}

	async function refresh() {
		const rows = await call("nexora.quality.service.list_quality_checks", {
			payload: {
				project: controls.project.get_value() || null,
				status: controls.status.get_value() || null,
				limit: 100,
			},
		});
		currentRows = new Map((rows || []).map((row) => [String(row.name), row]));
		const target = $(page.body).find(".nxr-quality-results").empty();
		if (!rows || !rows.length) {
			target.append(
				`<p class="nxr-ds-empty">${__("No hay controles para los filtros indicados.")}</p>`
			);
			return;
		}
		rows.forEach((row) => {
			const button = $(
				`<button class="nxr-ds-btn nxr-ds-btn--secondary nxr-ds-btn--sm nxr-result-row"><strong>${escape(
					row.document_number
				)}</strong> · ${escape(statusLabels[row.status] || row.status)} · ${escape(
					row.description
				)}</button>`
			);
			button.on("click", () => load(row.name));
			target.append(button);
		});
	}

	function load(name) {
		const row = currentRows.get(name);
		if (!row) return;
		$(page.body).find(".nxr-quality-detail").removeClass("nxr-ds-empty").html(`
			<p><strong>${escape(row.document_number)}</strong></p>
			<p>${__("Estado")}: ${escape(statusLabels[row.status] || row.status)}</p>
			<p>${__("Proyecto")}: ${escape(row.project)}</p>
			<p>${__("Fase")}: ${escape(row.phase || "—")}</p>
			<p>${__("Descripción")}: ${escape(row.description)}</p>
			<p>${__("Resultado")}: ${escape(resultLabels[row.result] || row.result || "—")}</p>
			<p>${__("Observaciones")}: ${escape(row.observations || "—")}</p>
			<p>${__("Verificado por")}: ${escape(row.checked_by)}</p>
			<p>${__("Fecha")}: ${escape(row.check_date)}</p>
			<p>${__("Acciones correctivas")}: ${escape(row.corrective_actions || "—")}</p>
		`);
		renderActions(row);
	}

	function renderActions(row) {
		const target = $(page.body).find(".nxr-quality-actions").empty();
		(transitions[row.status] || []).forEach((status) => {
			const button = $(
				`<button class="nxr-ds-btn nxr-ds-btn--secondary nxr-ds-btn--sm mr-2 mb-2">${escape(
					statusLabels[status] || status
				)}</button>`
			);
			button.on("click", () => transition(row, status));
			target.append(button);
		});
		if (!(transitions[row.status] || []).length) {
			target.append(`<p class="nxr-ds-empty">${__("El control no admite más transiciones.")}</p>`);
		}
	}

	async function transition(row, targetStatus) {
		const needsResult = ["Passed", "Failed"].includes(targetStatus);
		const needsCorrectiveActions = targetStatus === "Corrected";
		const fields = [];
		if (needsResult) {
			fields.push({
				fieldname: "result",
				label: __("Resultado"),
				fieldtype: "Select",
				options: Object.keys(resultLabels),
				default: targetStatus === "Passed" ? "Pass" : "Fail",
				reqd: 1,
			});
		}
		if (needsCorrectiveActions) {
			fields.push({
				fieldname: "corrective_actions",
				label: __("Acciones correctivas"),
				fieldtype: "Small Text",
				reqd: 1,
			});
		}
		let values = {};
		if (fields.length) {
			const prompted = await new Promise((resolve) =>
				frappe.prompt(fields, resolve, statusLabels[targetStatus] || targetStatus)
			);
			if (!prompted) return;
			values = prompted;
		}
		try {
			await call("nexora.quality.service.transition_quality_check", {
				payload: { record: row.name, target_status: targetStatus, ...values },
			});
			frappe.show_alert({ message: __("Estado actualizado"), indicator: "green" });
			await refresh();
			load(row.name);
		} catch (error) {
			window.nexora.ui.showError(error, { title: __("No se pudo actualizar el control") });
		}
	}

	function createCheck() {
		const dialog = new frappe.ui.Dialog({
			title: __("Nuevo control de calidad"),
			fields: [
				{
					fieldname: "project",
					label: __("Proyecto"),
					fieldtype: "Link",
					options: "Project",
					reqd: 1,
				},
				{ fieldname: "phase", label: __("Fase"), fieldtype: "Data" },
				{
					fieldname: "progress_record",
					label: __("Registro de avance"),
					fieldtype: "Link",
					options: "NXR Progress Record",
				},
				{ fieldname: "description", label: __("Descripción"), fieldtype: "Small Text", reqd: 1 },
				{
					fieldname: "checked_by",
					label: __("Verificado por"),
					fieldtype: "Link",
					options: "User",
					default: frappe.session.user,
					reqd: 1,
				},
				{
					fieldname: "check_date",
					label: __("Fecha"),
					fieldtype: "Date",
					default: frappe.datetime.get_today(),
					reqd: 1,
				},
				{ fieldname: "observations", label: __("Observaciones"), fieldtype: "Small Text" },
			],
			primary_action_label: __("Crear"),
			primary_action: async () => {
				const values = dialog.get_values();
				if (!values) return;
				try {
					await call("nexora.quality.service.create_quality_check", {
						payload: { ...values, idempotency_key: uuid() },
					});
					dialog.hide();
					frappe.show_alert({ message: __("Control de calidad creado."), indicator: "green" });
					await refresh();
				} catch (error) {
					window.nexora.ui.showError(error, { title: __("No se pudo crear el control") });
				}
			},
		});
		dialog.show();
	}

	refresh();
};
