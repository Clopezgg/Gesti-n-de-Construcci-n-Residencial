frappe.pages["nexora-evidence"].on_page_load = function (wrapper) {
	const page = frappe.ui.make_app_page({
		parent: wrapper,
		title: __("Evidencias NEXORA"),
		single_column: true,
	});
	const controls = {};
	const field = (definition) => {
		const control = page.add_field(definition);
		controls[definition.fieldname] = control;
		return control;
	};
	field({ fieldname: "project", label: __("Proyecto"), fieldtype: "Link", options: "Project", reqd: 1 });
	field({
		fieldname: "evidence_kind",
		label: __("Tipo de evidencia"),
		fieldtype: "Select",
		options: ["Payment Proof", "External Authorization", "Real Return", "Document Substitution", "Other"],
		reqd: 1,
	});
	field({
		fieldname: "channel",
		label: __("Canal"),
		fieldtype: "Select",
		options: ["WhatsApp", "Bank Receipt", "Cash Receipt", "Email", "Other"],
		reqd: 1,
	});
	field({ fieldname: "file_url", label: __("Archivo privado"), fieldtype: "Attach", reqd: 1 });
	field({ fieldname: "source_message_date", label: __("Fecha del mensaje o comprobante"), fieldtype: "Datetime" });
	field({ fieldname: "sender", label: __("Emisor o autorizador externo"), fieldtype: "Data" });
	field({ fieldname: "external_reference", label: __("Referencia externa"), fieldtype: "Data" });
	field({ fieldname: "notes", label: __("Notas"), fieldtype: "Small Text" });
	field({
		fieldname: "supersedes",
		label: __("Sustituye evidencia"),
		fieldtype: "Link",
		options: "NXR Evidence",
	});

	$(page.body).append(`
		<div class="nxr-finance-grid nxr-evidence-grid">
			<section class="nxr-card">
				<h3>${__("Expediente verificable")}</h3>
				<p class="text-muted">${__(
					"El servidor exige archivo privado, calcula SHA-256 y conserva cada versión. Las autorizaciones especiales requieren canal WhatsApp, autorizador, fecha y referencia."
				)}</p>
				<div class="nxr-evidence-result nxr-empty">${__("Registre una evidencia para continuar.")}</div>
			</section>
			<section class="nxr-card nxr-evidence-review">
				<h3>${__("Revisión humana")}</h3>
				<div class="nxr-review-fields"></div>
			</section>
			<section class="nxr-card nxr-evidence-list">
				<h3>${__("Evidencias recientes")}</h3>
				<div class="nxr-evidence-rows"></div>
			</section>
		</div>
	`);

	const reviewControls = buildReviewControls(page.body);
	page.add_button(__("Registrar evidencia"), registerEvidence, "primary");
	page.add_button(__("Actualizar lista"), loadEvidence);
	loadEvidence();

	function uuid() {
		return globalThis.crypto?.randomUUID?.() || `nxr-${Date.now()}-${Math.random().toString(16).slice(2)}`;
	}

	function payload() {
		return Object.fromEntries(Object.entries(controls).map(([name, control]) => [name, control.get_value()]));
	}

	async function registerEvidence() {
		const data = { ...payload(), idempotency_key: uuid() };
		const response = await frappe.call({
			method: "nexora.financial.service.register_evidence",
			type: "POST",
			args: { payload: data },
			freeze: true,
			freeze_message: __("Calculando huella y registrando evidencia…"),
		});
		const result = response.message;
		$(page.body)
			.find(".nxr-evidence-result")
			.removeClass("nxr-empty")
			.html(
				`<p><strong>${__("Documento")}:</strong> ${frappe.utils.escape_html(result.document_number)}</p>
				<p><strong>${__("Estado")}:</strong> ${frappe.utils.escape_html(result.status)}</p>
				<p><strong>${__("Versión")}:</strong> ${result.version}</p>
				<p><strong>SHA-256:</strong> <code>${frappe.utils.escape_html(result.content_sha256)}</code></p>`
			);
		reviewControls.evidence.set_value(result.evidence);
		frappe.show_alert({ message: __("Evidencia {0} registrada", [result.document_number]), indicator: "green" });
		await loadEvidence();
	}

	async function review(decision) {
		const evidence = reviewControls.evidence.get_value();
		if (!evidence) {
			frappe.throw(__("Seleccione una evidencia para revisar."));
		}
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
			freeze_message: __("Registrando decisión de revisión…"),
		});
		frappe.show_alert({
			message: __("Evidencia {0}: {1}", [response.message.document_number, response.message.status]),
			indicator: decision === "Validated" ? "green" : "red",
		});
		await loadEvidence();
	}

	async function loadEvidence() {
		const response = await frappe.call({
			method: "nexora.financial.service.list_evidence",
			type: "POST",
			args: { project: controls.project.get_value(), limit: 50 },
		});
		const rows = response.message || [];
		const target = $(page.body).find(".nxr-evidence-rows").empty();
		if (!rows.length) {
			target.text(__("Aún no hay evidencias."));
			return;
		}
		target.append(`<div class="table-responsive"><table class="table table-bordered">
			<thead><tr><th>${__("Número")}</th><th>${__("Estado")}</th><th>${__("Tipo")}</th><th>${__("Canal")}</th><th>${__("Versión")}</th><th>SHA-256</th></tr></thead>
			<tbody></tbody></table></div>`);
		const body = target.find("tbody");
		rows.forEach((row) => {
			const tr = $(`<tr role="button">
				<td>${frappe.utils.escape_html(row.document_number)}</td>
				<td>${frappe.utils.escape_html(row.status)}</td>
				<td>${frappe.utils.escape_html(row.evidence_kind)}</td>
				<td>${frappe.utils.escape_html(row.channel)}</td>
				<td>${row.version}</td>
				<td><code>${frappe.utils.escape_html(String(row.content_sha256 || "").slice(0, 16))}…</code></td>
			</tr>`).appendTo(body);
			tr.on("click", () => reviewControls.evidence.set_value(row.name));
		});
	}

	function buildReviewControls(body) {
		const parent = $(body).find(".nxr-review-fields");
		const evidence = frappe.ui.form.make_control({
			parent,
			df: { fieldname: "evidence", label: __("Evidencia"), fieldtype: "Link", options: "NXR Evidence", reqd: 1 },
			render_input: true,
		});
		const reviewNotes = frappe.ui.form.make_control({
			parent,
			df: { fieldname: "review_notes", label: __("Notas de revisión"), fieldtype: "Small Text" },
			render_input: true,
		});
		$(`<button class="btn btn-success btn-sm mr-2">${__("Validar")}</button>`)
			.appendTo(parent)
			.on("click", () => review("Validated"));
		$(`<button class="btn btn-danger btn-sm">${__("Rechazar")}</button>`)
			.appendTo(parent)
			.on("click", () => review("Rejected"));
		return { evidence, review_notes: reviewNotes };
	}
};
