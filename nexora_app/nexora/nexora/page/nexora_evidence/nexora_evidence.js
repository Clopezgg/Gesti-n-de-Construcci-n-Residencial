frappe.pages["nexora-evidence"].on_page_load = function (wrapper) {
	const page = frappe.ui.make_app_page({
		parent: wrapper,
		title: __("Comprobantes y evidencias"),
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
	field({
		fieldname: "evidence_kind",
		label: __("Tipo de comprobante"),
		fieldtype: "Select",
		options: ui.selectOptions("evidenceKind"),
		reqd: 1,
	});
	field({
		fieldname: "channel",
		label: __("Origen del comprobante"),
		fieldtype: "Select",
		options: ["WhatsApp", "Bank Receipt", "Cash Receipt", "Email", "Other"].map((value) => ({
			label: ui.label("channel", value),
			value,
		})),
		reqd: 1,
	});
	field({ fieldname: "file_url", label: __("Archivo privado"), fieldtype: "Attach", reqd: 1 });
	field({
		fieldname: "source_message_date",
		label: __("Fecha del mensaje o comprobante"),
		fieldtype: "Datetime",
	});
	field({ fieldname: "sender", label: __("Emisor o autorizador"), fieldtype: "Data" });
	field({ fieldname: "external_reference", label: __("Número de referencia"), fieldtype: "Data" });
	field({ fieldname: "notes", label: __("Notas"), fieldtype: "Small Text" });
	field({
		fieldname: "supersedes",
		label: __("Comprobante que sustituye"),
		fieldtype: "Link",
		options: "NXR Evidence",
	});

	$(page.body).append(`
		<div class="nxr-finance-grid nxr-evidence-grid">
			<section class="nxr-card">
				<h3>${__("Registrar comprobante")}</h3>
				<p class="text-muted">${__(
					"NEXORA conservará el archivo privado, su huella digital y cada versión sin eliminar el historial."
				)}</p>
				<div class="nxr-evidence-result nxr-empty" aria-live="polite">${__(
					"Complete los datos y registre el comprobante."
				)}</div>
			</section>
			<section class="nxr-card nxr-evidence-review">
				<h3>${__("Revisión")}</h3>
				<div class="nxr-review-fields"></div>
			</section>
			<section class="nxr-card nxr-evidence-list">
				<h3>${__("Comprobantes recientes")}</h3>
				<div class="nxr-evidence-rows"></div>
			</section>
		</div>
	`);

	const reviewControls = buildReviewControls(page.body);
	page.add_button(__("Registrar comprobante"), registerEvidence, "primary");
	page.add_button(__("Actualizar lista"), loadEvidence);

	let syncingProject = false;
	let releaseContext = null;
	$(wrapper).on("remove", () => releaseContext?.());
	initialize().catch((error) => console.error("NEXORA evidence failed to adopt the active project", error));

	// El proyecto llega por la ruta si se navegó desde otra pantalla; si no, se hereda
	// del contexto activo en lugar de pedirlo otra vez.
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
		await loadEvidence();
		releaseContext = window.nexora.context?.onContextChange?.(async (context) => {
			// Bloque 108: mismo defecto real corregido en `nexora_operations.js` (Bloque
			// 107) — Frappe no destruye de forma fiable el wrapper al navegar, así que
			// este suscriptor puede seguir vivo después de que el usuario se fue.
			if ((frappe.get_route ? frappe.get_route() : [])[0] !== "nexora-evidence") return;
			const desired = context?.project || "";
			if ((controls.project.get_value() || "") === desired) return;
			syncingProject = true;
			try {
				await controls.project.set_value(desired);
			} finally {
				syncingProject = false;
			}
			await loadEvidence();
		});
	}

	async function contextChanged() {
		if (syncingProject) return;
		// El proyecto elegido aquí pasa a ser el contexto activo: la barra global y el
		// resto de módulos no pueden quedar contradiciendo esta pantalla.
		try {
			await window.nexora.context?.setActiveProject?.(controls.project.get_value() || null);
		} catch (error) {
			console.error("NEXORA evidence failed to publish the active project", error);
		}
		await loadEvidence();
	}

	function uuid() {
		return window.nexora.ui.generateId();
	}

	function payload() {
		return Object.fromEntries(
			Object.entries(controls).map(([name, control]) => [name, control.get_value()])
		);
	}

	async function registerEvidence() {
		const data = { ...payload(), idempotency_key: uuid() };
		try {
			const response = await frappe.call({
				method: "nexora.financial.service.register_evidence",
				type: "POST",
				args: { payload: data },
				freeze: true,
				freeze_message: __("Verificando el archivo y registrando el comprobante…"),
			});
			const result = response.message;
			$(page.body)
				.find(".nxr-evidence-result")
				.removeClass("nxr-empty")
				.html(
					`<p><strong>${__("Documento")}:</strong> ${frappe.utils.escape_html(
						result.document_number
					)}</p>
					<p><strong>${__("Estado")}:</strong> ${frappe.utils.escape_html(ui.label("status", result.status))}</p>
					<p><strong>${__("Versión")}:</strong> ${result.version}</p>
					<p><strong>SHA-256:</strong> <code>${frappe.utils.escape_html(result.content_sha256)}</code></p>`
				);
			reviewControls.evidence.set_value(result.evidence);
			ui.showSuccess({
				message: __("Comprobante registrado correctamente"),
				documentNumber: result.document_number,
			});
			await loadEvidence();
		} catch (error) {
			console.error("NEXORA evidence registration failed", error);
			ui.showError(error, {
				title: __("No fue posible registrar el comprobante"),
				fallback: __("No se registró ningún cambio. Revise el archivo y los campos obligatorios."),
			});
		}
	}

	async function review(decision) {
		const evidence = reviewControls.evidence.get_value();
		if (!evidence) {
			frappe.msgprint({
				title: __("Seleccione un comprobante"),
				message: __("Elija el documento que desea revisar antes de continuar."),
				indicator: "orange",
			});
			return;
		}
		try {
			const response = await frappe.call({
				method: "nexora.financial.service.review_evidence",
				type: "POST",
				args: {
					evidence,
					decision,
					idempotency_key: uuid(),
					notes: reviewControls.review_notes.get_value(),
				},
				freeze: true,
				freeze_message: __("Registrando la decisión…"),
			});
			ui.showSuccess({
				message: __("Revisión registrada: {0}", [ui.label("status", response.message.status)]),
				documentNumber: response.message.document_number,
			});
			await loadEvidence();
		} catch (error) {
			ui.showError(error, { title: __("No fue posible registrar la revisión") });
		}
	}

	async function loadEvidence() {
		try {
			const response = await frappe.call({
				method: "nexora.financial.service.list_evidence",
				type: "POST",
				args: { project: controls.project.get_value(), limit: 50 },
			});
			renderEvidence(response.message || []);
		} catch (error) {
			console.error("NEXORA evidence list failed", error);
			ui.showError(error, { title: __("No fue posible consultar los comprobantes") });
		}
	}

	function renderEvidence(rows) {
		const target = $(page.body).find(".nxr-evidence-rows").empty();
		if (!rows.length) {
			target.text(__("Aún no hay comprobantes para mostrar."));
			return;
		}
		target.append(`<div class="table-responsive"><table class="table table-bordered">
			<thead><tr><th>${__("Documento")}</th><th>${__("Estado")}</th><th>${__("Tipo")}</th><th>${__(
			"Origen"
		)}</th><th>${__("Versión")}</th><th>SHA-256</th></tr></thead>
			<tbody></tbody></table></div>`);
		const body = target.find("tbody");
		rows.forEach((row) => {
			const tr = $(`<tr role="button" tabindex="0">
				<td>${frappe.utils.escape_html(row.document_number)}</td>
				<td>${frappe.utils.escape_html(ui.label("status", row.status))}</td>
				<td>${frappe.utils.escape_html(ui.label("evidenceKind", row.evidence_kind))}</td>
				<td>${frappe.utils.escape_html(ui.label("channel", row.channel))}</td>
				<td>${row.version}</td>
				<td><code>${frappe.utils.escape_html(String(row.content_sha256 || "").slice(0, 16))}…</code></td>
			</tr>`).appendTo(body);
			const select = () => reviewControls.evidence.set_value(row.name);
			tr.on("click", select);
			tr.on("keydown", (event) => {
				if (event.key === "Enter" || event.key === " ") {
					event.preventDefault();
					select();
				}
			});
		});
	}

	function buildReviewControls(body) {
		const parent = $(body).find(".nxr-review-fields");
		const evidence = frappe.ui.form.make_control({
			parent,
			df: {
				fieldname: "evidence",
				label: __("Comprobante"),
				fieldtype: "Link",
				options: "NXR Evidence",
				reqd: 1,
			},
			render_input: true,
		});
		const reviewNotes = frappe.ui.form.make_control({
			parent,
			df: { fieldname: "review_notes", label: __("Notas de revisión"), fieldtype: "Small Text" },
			render_input: true,
		});
		$(`<button class="nxr-ds-btn nxr-ds-btn--success nxr-ds-btn--sm mr-2">${__("Validar")}</button>`)
			.appendTo(parent)
			.on("click", () => review("Validated"));
		$(`<button class="nxr-ds-btn nxr-ds-btn--danger nxr-ds-btn--sm">${__("Rechazar")}</button>`)
			.appendTo(parent)
			.on("click", () => review("Rejected"));
		return { evidence, review_notes: reviewNotes };
	}
};
