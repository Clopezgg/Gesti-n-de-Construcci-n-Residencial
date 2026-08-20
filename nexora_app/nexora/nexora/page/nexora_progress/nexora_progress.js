frappe.pages["nexora-progress"].on_page_load = function (wrapper) {
	const page = frappe.ui.make_app_page({
		parent: wrapper,
		title: __("Avance del proyecto"),
		single_column: true,
	});
	const ui = window.nexora.ui;
	const controls = {};
	const field = (definition) => {
		const control = page.add_field(definition);
		controls[definition.fieldname] = control;
		return control;
	};
	field({
		fieldname: "project",
		label: __("Proyecto"),
		fieldtype: "Link",
		options: "Project",
		reqd: 1,
		change: () => contextChanged(),
	});
	field({ fieldname: "phase", label: __("Fase o frente de trabajo"), fieldtype: "Data" });
	field({
		fieldname: "description",
		label: __("Descripción del avance"),
		fieldtype: "Small Text",
		reqd: 1,
	});
	field({
		fieldname: "progress_percent",
		label: __("Avance físico (%)"),
		fieldtype: "Percent",
		reqd: 1,
	});
	field({
		fieldname: "recorded_date",
		label: __("Fecha del registro"),
		fieldtype: "Date",
		reqd: 1,
		default: frappe.datetime.get_today(),
	});
	field({ fieldname: "responsible", label: __("Responsable"), fieldtype: "Link", options: "User" });
	field({ fieldname: "photos", label: __("Fotografía"), fieldtype: "Attach" });
	field({ fieldname: "notes", label: __("Notas"), fieldtype: "Small Text" });

	$(page.body).append(`
		<div class="nxr-finance-grid nxr-progress-grid">
			<section class="nxr-card">
				<h3>${__("Registrar avance")}</h3>
				<p class="text-muted">${__(
					"La cámara o galería del teléfono se abre directamente desde el campo Fotografía."
				)}</p>
				<div class="nxr-progress-result nxr-ds-empty" aria-live="polite">${__(
					"Complete los datos y registre el avance."
				)}</div>
			</section>
			<section class="nxr-card nxr-progress-review">
				<h3>${__("Revisión")}</h3>
				<div class="nxr-review-fields"></div>
			</section>
			<section class="nxr-card nxr-progress-feed">
				<h3>${__("Avance reciente")}</h3>
				<div class="nxr-progress-rows"></div>
			</section>
		</div>
	`);

	const reviewControls = buildReviewControls(page.body);
	page.add_button(__("Registrar avance"), createRecord, "primary");
	page.add_button(__("Actualizar avance"), loadRecords);

	let syncingProject = false;
	let releaseContext = null;
	$(wrapper).on("remove", () => releaseContext?.());
	initialize().catch((error) => console.error("NEXORA progress failed to adopt the active project", error));

	// El proyecto llega por la ruta si se navegó desde otra pantalla; si no, se hereda
	// del contexto activo en lugar de pedirlo otra vez — mismo patrón que nexora-evidence.
	async function initialize() {
		const launchOptions = frappe.route_options || {};
		frappe.route_options = null;
		const launchProject =
			launchOptions.project || (await window.nexora.context?.activeProject?.()) || null;
		if (launchProject) {
			syncingProject = true;
			try {
				await controls.project.set_value(launchProject);
			} finally {
				syncingProject = false;
			}
		}
		await loadRecords();
		releaseContext = window.nexora.context?.onContextChange?.(async (context) => {
			const desired = context?.project || "";
			if ((controls.project.get_value() || "") === desired) return;
			syncingProject = true;
			try {
				await controls.project.set_value(desired);
			} finally {
				syncingProject = false;
			}
			await loadRecords();
		});
	}

	async function contextChanged() {
		if (syncingProject) return;
		try {
			await window.nexora.context?.setActiveProject?.(controls.project.get_value() || null);
		} catch (error) {
			console.error("NEXORA progress failed to publish the active project", error);
		}
		await loadRecords();
	}

	function uuid() {
		return window.nexora.ui.generateId();
	}

	function payload() {
		return Object.fromEntries(
			Object.entries(controls).map(([name, control]) => [name, control.get_value()])
		);
	}

	async function createRecord() {
		const data = { ...payload(), idempotency_key: uuid() };
		try {
			const response = await frappe.call({
				method: "nexora.progress.service.create_progress_record",
				type: "POST",
				args: { payload: data },
				freeze: true,
				freeze_message: __("Registrando el avance…"),
			});
			const result = response.message;
			$(page.body)
				.find(".nxr-progress-result")
				.removeClass("nxr-ds-empty")
				.html(
					`<p><strong>${__("Documento")}:</strong> ${frappe.utils.escape_html(
						result.document_number
					)}</p>
					<p><strong>${__("Estado")}:</strong> ${frappe.utils.escape_html(ui.label("status", result.status))}</p>`
				);
			reviewControls.record.set_value(result.name);
			ui.showSuccess({
				message: __("Avance registrado correctamente"),
				documentNumber: result.document_number,
			});
			await loadRecords();
		} catch (error) {
			console.error("NEXORA progress registration failed", error);
			ui.showError(error, {
				title: __("No fue posible registrar el avance"),
				fallback: __("No se registró ningún cambio. Revise los datos obligatorios."),
			});
		}
	}

	async function transition(targetStatus) {
		const record = reviewControls.record.get_value();
		if (!record) {
			frappe.msgprint({
				title: __("Seleccione un registro"),
				message: __("Elija el avance que desea actualizar antes de continuar."),
				indicator: "orange",
			});
			return;
		}
		try {
			const response = await frappe.call({
				method: "nexora.progress.service.transition_progress_record",
				type: "POST",
				args: { payload: { record, target_status: targetStatus } },
				freeze: true,
				freeze_message: __("Actualizando el estado…"),
			});
			ui.showSuccess({
				message: __("Avance actualizado: {0}", [ui.label("status", response.message.status)]),
				documentNumber: response.message.document_number,
			});
			await loadRecords();
		} catch (error) {
			ui.showError(error, { title: __("No fue posible actualizar el avance") });
		}
	}

	async function loadRecords() {
		try {
			const response = await frappe.call({
				method: "nexora.progress.service.list_progress_records",
				type: "POST",
				args: { payload: { project: controls.project.get_value(), limit: 50 } },
			});
			renderRecords(response.message || []);
		} catch (error) {
			console.error("NEXORA progress list failed", error);
			ui.showError(error, { title: __("No fue posible consultar el avance") });
		}
	}

	function firstPhoto(value) {
		if (!value) return null;
		try {
			const decoded = JSON.parse(value);
			if (Array.isArray(decoded) && decoded.length) return decoded[0];
		} catch (error) {
			// No era JSON: es una URL de archivo directa (el caso normal de esta página).
		}
		return String(value).split(/[\n,]/)[0].trim() || null;
	}

	function renderRecords(rows) {
		const target = $(page.body).find(".nxr-progress-rows").empty();
		if (!rows.length) {
			target.text(__("Aún no hay avance registrado para este proyecto."));
			return;
		}
		rows.forEach((row) => {
			const photo = firstPhoto(row.photos);
			const card = $(`<article class="nxr-progress-card" role="button" tabindex="0">
				${photo ? `<img class="nxr-progress-photo" src="${frappe.utils.escape_html(photo)}" alt="">` : ""}
				<div class="nxr-progress-card-body">
					<p><strong>${frappe.utils.escape_html(row.document_number)}</strong> · ${frappe.utils.escape_html(
				ui.label("status", row.status)
			)}</p>
					<p>${frappe.utils.escape_html(row.phase || "")}</p>
					<p>${frappe.utils.escape_html(row.description || "")}</p>
					<p>${ui.formatDate(row.recorded_date)} · ${frappe.utils.escape_html(String(row.progress_percent ?? 0))}%</p>
				</div>
			</article>`).appendTo(target);
			const select = () => reviewControls.record.set_value(row.name);
			card.on("click", select);
			card.on("keydown", (event) => {
				if (event.key === "Enter" || event.key === " ") {
					event.preventDefault();
					select();
				}
			});
		});
	}

	function buildReviewControls(body) {
		const parent = $(body).find(".nxr-review-fields");
		const record = frappe.ui.form.make_control({
			parent,
			df: {
				fieldname: "record",
				label: __("Registro de avance"),
				fieldtype: "Link",
				options: "NXR Progress Record",
				reqd: 1,
			},
			render_input: true,
		});
		$(`<button class="nxr-ds-btn nxr-ds-btn--sm mr-2">${__("Enviar a revisión")}</button>`)
			.appendTo(parent)
			.on("click", () => transition("Submitted"));
		$(`<button class="nxr-ds-btn nxr-ds-btn--success nxr-ds-btn--sm mr-2">${__("Aprobar")}</button>`)
			.appendTo(parent)
			.on("click", () => transition("Approved"));
		$(`<button class="nxr-ds-btn nxr-ds-btn--danger nxr-ds-btn--sm">${__("Rechazar")}</button>`)
			.appendTo(parent)
			.on("click", () => transition("Rejected"));
		return { record };
	}
};
