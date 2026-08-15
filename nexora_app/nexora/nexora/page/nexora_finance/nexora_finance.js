function readNexoraFinanceLaunchContext() {
	const launchQuery = new URLSearchParams(window.location.search);
	const context = {
		action: frappe.route_options?.nexora_action || launchQuery.get("nexora_action") || null,
		project: frappe.route_options?.project || launchQuery.get("project") || null,
	};
	frappe.route_options = null;
	return context;
}

frappe.pages["nexora-finance"].on_page_load = function (wrapper) {
	const page = frappe.ui.make_app_page({
		parent: wrapper,
		title: __("Fondos y operaciones"),
		single_column: true,
	});

	const state = {
		preview: null,
		sources: [],
		profiles: new Map(),
		categories: new Map(),
		profile: null,
		catalogsLoaded: false,
		pendingLaunchContext: readNexoraFinanceLaunchContext(),
	};
	const controls = {};
	const addField = (definition) => {
		const control = page.add_field({ ...definition, change: definition.change || invalidatePreview });
		controls[definition.fieldname] = control;
		return control;
	};

	const project = addField({
		label: __("Proyecto"),
		fieldname: "project",
		fieldtype: "Link",
		options: "Project",
		reqd: 1,
		change: () => projectChanged(),
	});
	const operationCode = addField({
		fieldname: "operation_code",
		label: __("Tipo de movimiento"),
		fieldtype: "Link",
		options: "NXR Operation Type",
		reqd: 1,
		change: applySelectedProfile,
	});
	const kernelService = addField({
		fieldname: "kernel_service",
		label: __("Información interna"),
		fieldtype: "Data",
		read_only: 1,
	});
	const economicCategory = addField({
		fieldname: "economic_category",
		label: __("Categoría"),
		fieldtype: "Link",
		options: "NXR Economic Category",
		reqd: 1,
		get_query: () => ({
			filters: [["NXR Economic Category", "name", "in", state.profile?.allowed || []]],
		}),
		change: applyCategoryVisibility,
	});
	const amount = addField({
		label: __("Importe HNL"),
		fieldname: "amount_hnl",
		fieldtype: "Currency",
	});
	const dueDate = addField({
		label: __("Vencimiento"),
		fieldname: "due_date",
		fieldtype: "Date",
	});
	const costCenter = addField({
		label: __("Centro de costo"),
		fieldname: "cost_center",
		fieldtype: "Link",
		options: "Cost Center",
	});
	const secondCostCenter = addField({
		fieldname: "second_cost_center",
		label: __("Segundo centro de costo"),
		fieldtype: "Link",
		options: "Cost Center",
	});
	const secondCostAmount = addField({
		fieldname: "second_cost_amount",
		label: __("Importe segundo centro"),
		fieldtype: "Currency",
	});
	const targetProject = addField({
		fieldname: "target_project",
		label: __("Proyecto destino"),
		fieldtype: "Link",
		options: "Project",
	});
	const destinationSource = addField({
		fieldname: "destination_source",
		label: __("Fondo de destino"),
		fieldtype: "Link",
		options: "NXR Fund Source",
	});
	const beneficiaryDoctype = addField({
		fieldname: "beneficiary_doctype",
		label: __("Tipo de beneficiario o responsable"),
		fieldtype: "Link",
		options: "DocType",
	});
	const beneficiary = addField({
		fieldname: "beneficiary",
		label: __("Beneficiario o responsable"),
		fieldtype: "Dynamic Link",
		options: "beneficiary_doctype",
	});
	const referenceName = addField({
		fieldname: "reference_name",
		label: __("Operación original"),
		fieldtype: "Link",
		options: "NXR Operation",
		change: referenceChanged,
	});
	const returnOriginalSource = addField({
		fieldname: "return_original_source",
		label: __("Fondo relacionado"),
		fieldtype: "Link",
		options: "NXR Fund Source",
	});
	const paymentMethod = addField({
		fieldname: "payment_method",
		label: __("Medio de pago"),
		fieldtype: "Select",
		options: ["Cash", "Deposit", "Transfer", "Other"],
	});
	const externalReference = addField({
		fieldname: "external_reference",
		label: __("Referencia externa"),
		fieldtype: "Data",
	});
	const requester = addField({
		label: __("Solicitante"),
		fieldname: "requester",
		fieldtype: "Link",
		options: "User",
		reqd: 1,
	});
	const approvedBy = addField({
		label: __("Aprobador"),
		fieldname: "approved_by",
		fieldtype: "Link",
		options: "User",
		reqd: 1,
	});
	const commitment = addField({
		label: __("Compromiso"),
		fieldname: "commitment",
		fieldtype: "Link",
		options: "NXR Commitment",
	});
	const evidence = addField({
		label: __("Comprobante"),
		fieldname: "evidence",
		fieldtype: "Attach",
	});

	$(page.body).append(`
    <section class="nxr-finance-guide nxr-card">
      <div>
        <p class="nxr-eyebrow">${__("OPERACIONES FRECUENTES")}</p>
        <h3>${__("¿Qué desea registrar?")}</h3>
        <p class="text-muted">${__(
			"Seleccione una acción. NEXORA mostrará únicamente los datos necesarios y explicará cualquier requisito pendiente."
		)}</p>
      </div>
      <div class="nxr-operation-shortcuts">
        <button type="button" class="nxr-ds-btn nxr-ds-btn--primary" data-operation="CONSTRUCTION_PAYMENT">${__(
			"Registrar gasto"
		)}</button>
        <button type="button" class="nxr-ds-btn nxr-ds-btn--secondary" data-launch-income="1">${__(
			"Registrar fondos"
		)}</button>
        <button type="button" class="nxr-ds-btn nxr-ds-btn--secondary" data-operation="INTERNAL_TRANSFER">${__(
			"Transferir fondos"
		)}</button>
        <button type="button" class="nxr-ds-btn nxr-ds-btn--secondary" data-operation="ADVANCE_DISBURSEMENT">${__(
			"Registrar anticipo"
		)}</button>
        <button type="button" class="nxr-ds-btn nxr-ds-btn--secondary" data-operation="REAL_RETURN">${__(
			"Registrar devolución"
		)}</button>
      </div>
      <details class="nxr-advanced-operations">
        <summary>${__("Operaciones avanzadas")}</summary>
        <p>${__(
			"Use esta sección para reclasificaciones, ajustes, liquidaciones y liberaciones de compromisos."
		)}</p>
      </details>
      <div class="nxr-prerequisite-message" role="status"></div>
    </section>
    <div class="nxr-finance-grid">
      <section class="nxr-card nxr-source-allocation"><h3>${__(
			"Asignaciones por fuente"
		)}</h3><div class="nxr-source-list"></div></section>
      <section class="nxr-card"><h3>${__(
			"Vista previa antes de ejecutar"
		)}</h3><div class="nxr-preview nxr-empty">${__(
		"Genere una vista previa para continuar."
	)}</div></section>
      <section class="nxr-card nxr-source-create"><h3>${__(
			"Alta rápida de fuente"
		)}</h3><div class="nxr-source-fields"></div></section>
      <section class="nxr-card nxr-remittance-create"><h3>${__(
			"Registrar remesa"
		)}</h3><p class="text-muted">${__(
		"Un registro de fondos, repartido en varios fondos nuevos con un solo documento."
	)}</p><div class="nxr-remittance-fields"></div><div class="nxr-remittance-destinations"></div></section>
      <section class="nxr-card nxr-ledger"><h3>${__(
			"Libro Central reciente"
		)}</h3><div class="nxr-ledger-list"></div></section>
    </div>
  `);

	buildSourceFields(page.body);
	buildRemittanceFields(page.body);
	kernelService.toggle(false);
	$(page.body).on("click", "[data-operation]", async function () {
		await operationCode.set_value($(this).data("operation"));
		updatePrerequisiteMessage();
	});
	$(page.body).on("click", "[data-launch-income]", () => {
		const section = $(page.body).find(".nxr-source-create").addClass("nxr-card-highlight")[0];
		section?.scrollIntoView({ behavior: "smooth", block: "start" });
	});
	page.add_button(__("Vista previa"), previewOperation, "primary");
	const executeButton = page.add_button(__("Ejecutar operación"), executeOperation);
	executeButton.prop("disabled", true);

	wrapper.nexora_apply_launch_context = async () => {
		const context = readNexoraFinanceLaunchContext();
		if (!context.action && !context.project) return;
		if (!state.catalogsLoaded) {
			state.pendingLaunchContext = context;
			return;
		}
		await applyLaunchContext(context);
	};

	wrapper.nexora_refresh_finance = async () => {
		if (project.get_value()) await loadSources();
	};

	let syncingProject = false;
	let releaseContext = null;
	$(wrapper).on("remove", () => releaseContext?.());

	loadCatalogs().catch((error) => console.error("NEXORA finance failed to load catalogs", error));

	function projectChanged() {
		if (syncingProject) return;
		// El proyecto elegido aquí pasa a ser el contexto activo: la barra global y el
		// resto de módulos no pueden quedar contradiciendo esta pantalla.
		Promise.resolve(window.nexora.context?.setActiveProject?.(project.get_value() || null)).catch(
			(error) => console.error("NEXORA finance failed to publish the active project", error)
		);
		loadSources();
	}

	function uuid() {
		return window.nexora.ui.generateId();
	}

	function toggle(control, visible, required = false) {
		control.toggle(Boolean(visible));
		control.df.reqd = Boolean(required);
		control.refresh();
	}

	function money(value) {
		return (
			window.nexora.ui?.formatMoney?.(value) ||
			new Intl.NumberFormat("es-HN", {
				style: "currency",
				currency: "HNL",
				minimumFractionDigits: 2,
			}).format(Number(value || 0))
		);
	}

	function roundMoney(value) {
		return Math.round((Number(value) + Number.EPSILON) * 100) / 100;
	}

	function roundRate(value) {
		return Math.round(Number(value) * 1e9) / 1e9;
	}

	function invalidatePreview() {
		state.preview = null;
		executeButton.prop("disabled", true);
		$(page.body)
			.find(".nxr-preview")
			.addClass("nxr-empty")
			.text(__("La información cambió; genere otra vista previa."));
	}

	async function loadCatalogs() {
		const response = await frappe.call({
			method: "nexora.financial.service.list_analytic_catalogs",
			type: "POST",
		});
		(response.message?.operation_types || []).forEach((row) => {
			state.profiles.set(row.code, {
				...row,
				allowed: String(row.allowed_categories || "")
					.split("\n")
					.filter(Boolean),
			});
		});
		(response.message?.economic_categories || []).forEach((row) => {
			state.categories.set(row.code, row);
		});
		applySelectedProfile();
		state.catalogsLoaded = true;
		const context = state.pendingLaunchContext;
		state.pendingLaunchContext = null;
		await applyLaunchContext(context || {});
		releaseContext = window.nexora.context?.onContextChange?.(async (context) => {
			const desired = context?.project || "";
			if ((project.get_value() || "") === desired) return;
			syncingProject = true;
			try {
				await project.set_value(desired);
			} finally {
				syncingProject = false;
			}
			await loadSources();
		});
	}

	// El proyecto llega por la ruta si se navegó desde otra pantalla; si no, se hereda
	// del contexto activo en lugar de pedirlo otra vez.
	async function applyLaunchContext(launchContext) {
		$(page.body).find(".nxr-source-create").removeClass("nxr-card-highlight");
		const launchProject =
			launchContext.project ||
			(!launchContext.action ? await window.nexora.context?.activeProject?.() : null) ||
			null;
		if (launchProject) {
			syncingProject = true;
			try {
				await project.set_value(launchProject);
			} finally {
				syncingProject = false;
			}
			await loadSources();
		}
		if (launchContext.action === "expense") {
			await operationCode.set_value("CONSTRUCTION_PAYMENT");
			frappe.show_alert({
				message: __("Complete los datos del gasto."),
				indicator: "blue",
			});
			return;
		}
		if (launchContext.action === "income") {
			const section = $(page.body).find(".nxr-source-create").addClass("nxr-card-highlight")[0];
			section?.scrollIntoView({ behavior: "smooth", block: "start" });
			frappe.show_alert({
				message: __("Complete los datos del registro de fondos."),
				indicator: "blue",
			});
		}
	}

	function applySelectedProfile() {
		state.profile = state.profiles.get(operationCode.get_value()) || null;
		kernelService.set_value(state.profile?.kernel_type || "");
		if (state.profile && !state.profile.allowed.includes(economicCategory.get_value())) {
			economicCategory.set_value("");
		}
		const profile = state.profile || {};
		const noFunds = ["Reclassification", "Analytic Adjustment"].includes(profile.kernel_type);
		const documentary = profile.code === "DOCUMENT_SUBSTITUTION";
		toggle(amount, !documentary, !["RECLASSIFICATION", "REVERSAL_NO_CASH"].includes(profile.code));
		toggle(dueDate, profile.requires_due_date, profile.requires_due_date);
		toggle(targetProject, profile.requires_target_project, profile.requires_target_project);
		toggle(destinationSource, profile.requires_destination, profile.requires_destination);
		toggle(beneficiaryDoctype, profile.requires_beneficiary, profile.requires_beneficiary);
		toggle(beneficiary, profile.requires_beneficiary, profile.requires_beneficiary);
		toggle(referenceName, profile.requires_reference, profile.requires_reference);
		toggle(returnOriginalSource, profile.code === "REAL_RETURN");
		toggle(paymentMethod, profile.requires_payment_reference, profile.requires_payment_reference);
		toggle(externalReference, profile.requires_payment_reference, profile.requires_payment_reference);
		toggle(evidence, profile.requires_evidence, profile.requires_evidence);
		toggle(
			commitment,
			["Commitment Execution", "Commitment Release"].includes(profile.kernel_type),
			["Commitment Execution", "Commitment Release"].includes(profile.kernel_type)
		);
		$(page.body)
			.find(".nxr-source-allocation")
			.toggle(!noFunds && !documentary);
		// El modo de fuente única/múltiple depende del kernel_type recién elegido, no
		// solo de si hay fuentes: re-renderizar aquí es lo que hace que un gasto
		// (Outflow) pase a radios y una transferencia interna vuelva a la grilla.
		renderSources(state.sources);
		applyCategoryVisibility();
		updatePrerequisiteMessage();
		invalidatePreview();
	}

	function applyCategoryVisibility() {
		const category = state.categories.get(economicCategory.get_value());
		const profile = state.profile || {};
		const derivedCorrection = ["RECLASSIFICATION", "REVERSAL_NO_CASH"].includes(profile.code);
		const needsCostCenter = Boolean(category?.requires_cost_center) || derivedCorrection;
		toggle(costCenter, needsCostCenter, Boolean(category?.requires_cost_center));
		toggle(secondCostCenter, needsCostCenter);
		toggle(secondCostAmount, needsCostCenter);
		invalidatePreview();
	}

	function updatePrerequisiteMessage() {
		const missing = [];
		if (!project.get_value()) missing.push(__("seleccione un proyecto"));
		if (!operationCode.get_value()) missing.push(__("seleccione el tipo de movimiento"));
		if (state.profile?.requires_beneficiary && !beneficiary.get_value()) {
			missing.push(__("seleccione un beneficiario o proveedor"));
		}
		if (state.profile?.requires_reference && !referenceName.get_value()) {
			missing.push(__("seleccione la operación original"));
		}
		if (state.profile?.requires_evidence && !evidence.get_value()) {
			missing.push(__("adjunte el comprobante"));
		}
		const needsFunds = !["Reclassification", "Analytic Adjustment"].includes(state.profile?.kernel_type);
		if (
			needsFunds &&
			project.get_value() &&
			!state.sources.some((row) => Number(row.available_hnl) > 0)
		) {
			missing.push(__("registre primero un fondo con saldo disponible"));
		}
		const target = $(page.body).find(".nxr-prerequisite-message");
		if (!missing.length) {
			target.removeClass("is-warning").addClass("is-ready").text(__("Todo listo para continuar."));
			executeButton.attr("title", __("Genere una vista previa para habilitar la ejecución."));
			return;
		}
		target
			.removeClass("is-ready")
			.addClass("is-warning")
			.text(__("Antes de continuar: {0}.", [missing.join(", ")]));
		executeButton.attr("title", missing.join(", "));
	}

	async function referenceChanged() {
		invalidatePreview();
		if (state.profile?.code !== "ADVANCE_SETTLEMENT" || !referenceName.get_value()) return;
		const response = await frappe.call({
			method: "nexora.financial.service.get_advance_status",
			type: "POST",
			args: { operation: referenceName.get_value() },
		});
		const status = response.message;
		frappe.show_alert({
			message: __("Anticipo: entregado L{0}, liquidado L{1}, pendiente L{2}", [
				status.total_disbursed_hnl,
				status.total_settled_hnl,
				status.outstanding_hnl,
			]),
			indicator: "blue",
		});
	}

	function allocations() {
		if (["Reclassification", "Analytic Adjustment"].includes(state.profile?.kernel_type)) return [];
		// Un gasto (Outflow) paga desde una sola fuente (Bloque 38): el servidor ya
		// lo exige en financial/core.py, aquí solo se refleja en la forma de recoger
		// la selección — un radio elegido, no una grilla de importes por fuente.
		if (state.profile?.kernel_type === "Outflow") {
			const selected = $(page.body).find(".nxr-source-radio:checked").val();
			return selected ? [{ source: selected, amount_hnl: amount.get_value() }] : [];
		}
		const rows = $(page.body)
			.find(".nxr-source-amount")
			.toArray()
			.map((input) => ({ source: input.dataset.source, amount_hnl: input.value }))
			.filter((row) => Number(row.amount_hnl) > 0);
		if (state.profile?.code === "REAL_RETURN" && returnOriginalSource.get_value()) {
			rows.forEach((row) => {
				row.related_source = returnOriginalSource.get_value();
			});
		}
		return rows;
	}

	function operationPayload() {
		const secondAmount = Number(secondCostAmount.get_value() || 0);
		const totalAmount = Number(amount.get_value() || 0);
		const splits = [];
		if (costCenter.get_value() && totalAmount > 0) {
			splits.push({
				cost_center: costCenter.get_value(),
				amount_hnl: totalAmount - secondAmount,
			});
		}
		if (secondCostCenter.get_value() && secondAmount > 0) {
			splits.push({
				cost_center: secondCostCenter.get_value(),
				amount_hnl: secondAmount,
			});
		}
		return {
			operation_code: operationCode.get_value(),
			economic_category: economicCategory.get_value(),
			project: project.get_value(),
			target_project: targetProject.get_value(),
			destination_source: destinationSource.get_value(),
			amount_hnl: state.profile?.code === "DOCUMENT_SUBSTITUTION" ? 0 : amount.get_value(),
			cost_center: costCenter.get_value(),
			analytic_splits: splits,
			beneficiary_doctype: beneficiaryDoctype.get_value(),
			beneficiary: beneficiary.get_value(),
			reference_doctype: state.profile?.requires_reference ? "NXR Operation" : "",
			reference_name: referenceName.get_value(),
			payment_method: paymentMethod.get_value(),
			external_reference: externalReference.get_value(),
			operation_date: frappe.datetime.get_today(),
			due_date: dueDate.get_value(),
			requester: requester.get_value(),
			approved_by: approvedBy.get_value(),
			commitment: commitment.get_value(),
			description: __("Operación registrada desde el Libro Central NEXORA"),
			evidence: evidence.get_value(),
			allocations: allocations(),
		};
	}

	async function loadSources() {
		invalidatePreview();
		const value = project.get_value();
		if (!value) {
			renderSources([]);
			updatePrerequisiteMessage();
			return;
		}
		const response = await frappe.call({
			method: "nexora.financial.service.list_source_balances",
			type: "POST",
			args: { project: value },
			freeze: true,
			freeze_message: __("Consultando saldos canónicos…"),
		});
		state.sources = response.message || [];
		renderSources(state.sources);
		updatePrerequisiteMessage();
		await loadLedger();
	}

	function renderSources(rows) {
		const target = $(page.body).find(".nxr-source-list").empty();
		if (!rows.length) {
			target.append(`
        <div class="nxr-guided-empty">
          <strong>${__("Este proyecto todavía no tiene fondos disponibles.")}</strong>
          <p>${__("Registre un fondo antes de intentar pagar, reservar o transferir dinero.")}</p>
          <button type="button" class="nxr-ds-btn nxr-ds-btn--primary nxr-ds-btn--sm" data-launch-income="1">${__(
				"Registrar primer fondo"
			)}</button>
        </div>`);
			return;
		}
		const singleSource = state.profile?.kernel_type === "Outflow";
		rows.forEach((row) =>
			target.append(`
      <label class="nxr-source-row">
        <span><strong>${frappe.utils.escape_html(row.source)}</strong><br>
        ${__("Saldo")}: ${money(row.balance_hnl)} · ${__("Reservado")}: ${money(row.reserved_hnl)} · ${__(
				"Disponible"
			)}: ${money(row.available_hnl)}</span>
        ${
			singleSource
				? `<input class="nxr-source-radio" type="radio" name="nxr-outflow-source" value="${frappe.utils.escape_html(
						row.source
				  )}">`
				: `<input class="form-control nxr-source-amount" type="number" min="0" step="0.01" value="0" data-source="${frappe.utils.escape_html(
						row.source
				  )}">`
		}
      </label>`)
		);
		target.find("input").on(singleSource ? "change" : "input", invalidatePreview);
	}

	async function previewOperation() {
		const response = await frappe.call({
			method: "nexora.financial.service.preview_central_operation",
			type: "POST",
			args: { payload: operationPayload() },
			freeze: true,
			freeze_message: __("Recalculando saldos y referencias en servidor…"),
		});
		state.preview = response.message;
		renderPreview(state.preview);
		executeButton.prop("disabled", false);
	}

	function renderPreview(preview) {
		const sourceRows = (preview.sources || [])
			.map(
				(row) => `
      <tr><td>${frappe.utils.escape_html(row.source)}</td><td>${money(row.amount_hnl)}</td><td>${money(
					row.balance_before_hnl
				)}</td><td>${money(row.balance_after_hnl)}</td><td>${money(
					row.reserved_before_hnl
				)}</td><td>${money(row.reserved_after_hnl)}</td></tr>`
			)
			.join("");
		const analyticRows = (preview.analytic_effects || [])
			.map(
				(row) =>
					`<tr><td>${frappe.utils.escape_html(
						window.nexora.ui.label("dimension", row.dimension)
					)}</td><td>${frappe.utils.escape_html(
						row.economic_category || preview.economic_category
					)}</td><td>${frappe.utils.escape_html(row.cost_center || "—")}</td><td>${money(
						row.amount_hnl
					)}</td></tr>`
			)
			.join("");
		$(page.body).find(".nxr-preview").removeClass("nxr-empty").html(`
      <table class="table table-bordered"><thead><tr><th>${__("Fuente")}</th><th>${__(
			"Importe"
		)}</th><th>${__("Saldo antes")}</th><th>${__("Saldo después")}</th><th>${__(
			"Reservado antes"
		)}</th><th>${__("Reservado después")}</th></tr></thead><tbody>${sourceRows}</tbody></table>
      <table class="table table-bordered"><thead><tr><th>${__("Dimensión")}</th><th>${__(
			"Clasificación"
		)}</th><th>${__("Centro")}</th><th>${__(
			"Efecto"
		)}</th></tr></thead><tbody>${analyticRows}</tbody></table>
      <p><strong>${__("Costo")}:</strong> ${money(preview.cost_effect_hnl)} · <strong>${__(
			"Presupuesto"
		)}:</strong> ${money(preview.budget_effect_hnl)} · <strong>${__("Ahorro")}:</strong> ${money(
			preview.savings_effect_hnl
		)} · <strong>${__("Inversión")}:</strong> ${money(preview.investment_effect_hnl)}</p>
      <p><strong>${__("Saldo referenciado")}:</strong> ${money(
			preview.reference_balance_before_hnl
		)} → ${money(preview.reference_balance_after_hnl)}</p>
      <p><strong>${__("Documento")}:</strong> ${frappe.utils.escape_html(preview.document_to_generate)}</p>`);
	}

	function serviceForProfile() {
		return (
			{
				"Commitment Reserve": "nexora.financial.service.create_commitment",
				"Commitment Execution": "nexora.financial.service.execute_commitment",
				"Commitment Release": "nexora.financial.service.release_commitment",
			}[state.profile?.kernel_type] || "nexora.financial.service.execute_central_operation"
		);
	}

	async function executeOperation() {
		if (!state.preview) return;
		const payload = {
			...operationPayload(),
			idempotency_key: uuid(),
			preview_hash: state.preview.preview_hash,
		};
		const response = await frappe.call({
			method: serviceForProfile(),
			type: "POST",
			args: { payload },
			freeze: true,
			freeze_message: __("Ejecutando operación atómica…"),
		});
		const number = response.message.document_number || response.message.commitment_number;
		frappe.show_alert({
			message: __("Movimiento {0} guardado correctamente", [number]),
			indicator: "green",
		});
		document.dispatchEvent(new CustomEvent("nexora:data-changed", { detail: { area: "finance" } }));
		await loadSources();
	}

	async function loadLedger() {
		const response = await frappe.call({
			method: "nexora.financial.service.list_central_operations",
			type: "POST",
			args: { project: project.get_value(), limit: 20 },
		});
		const rows = response.message || [];
		const target = $(page.body).find(".nxr-ledger-list").empty();
		if (!rows.length) return target.text(__("Aún no hay operaciones."));
		rows.forEach((row) =>
			target.append(
				`<div class="nxr-source-row"><strong>${frappe.utils.escape_html(
					row.document_number
				)}</strong> · ${frappe.utils.escape_html(row.operation_name || row.operation_code)} · ${money(
					row.amount_hnl
				)}</div>`
			)
		);
	}

	function buildSourceFields(body) {
		const parent = $(body).find(".nxr-source-fields");
		const fields = {};
		const definitions = [
			["channel", __("Canal"), "Select", ["Remittance", "Cash", "Deposit", "Transfer", "Other"]],
			["currency", __("Moneda"), "Link", "Currency"],
			["original_amount", __("Importe original"), "Currency"],
			["exchange_rate", __("Tasa a HNL"), "Float"],
			["origin_or_sender", __("Procedencia o remitente"), "Data"],
			["institution", __("Institución"), "Data"],
			["account_reference", __("Cuenta"), "Data"],
			["external_reference", __("Referencia"), "Data"],
		];
		definitions.forEach(([fieldname, label, fieldtype, options]) => {
			fields[fieldname] = frappe.ui.form.make_control({
				parent,
				df: { fieldname, label, fieldtype, options, change: toggleBankFields },
				render_input: true,
			});
		});
		fields.currency.set_value("HNL");
		fields.exchange_rate.set_value(1);
		const add = $(
			`<button class="nxr-ds-btn nxr-ds-btn--primary nxr-ds-btn--sm">${__("Registrar fuente")}</button>`
		).appendTo(parent);
		add.on("click", async () => {
			const sourcePayload = Object.fromEntries(
				Object.entries(fields).map(([name, control]) => [name, control.get_value()])
			);
			Object.assign(sourcePayload, {
				project: project.get_value(),
				custodian: frappe.session.user,
				idempotency_key: uuid(),
			});
			const response = await frappe.call({
				method: "nexora.financial.service.create_fund_source",
				type: "POST",
				args: { payload: sourcePayload },
				freeze: true,
				freeze_message: __("Registrando fuente y efecto de fondo…"),
			});
			frappe.show_alert({
				message: __("Fuente {0} registrada", [response.message.source_number]),
				indicator: "green",
			});
			document.dispatchEvent(
				new CustomEvent("nexora:data-changed", { detail: { area: "finance", type: "income" } })
			);
			await loadSources();
		});
		toggleBankFields();

		function toggleBankFields() {
			const bank = ["Deposit", "Transfer"].includes(fields.channel?.get_value());
			["institution", "account_reference", "external_reference"].forEach((name) =>
				fields[name]?.toggle(bank)
			);
		}
	}

	// Bloque 39: registrar remesa. Mismo patrón directo que "Alta rápida de
	// fuente" (buildSourceFields, sin paso de vista previa) — la diferencia es
	// que aquí el importe total lo suman los destinos, no un campo propio, y
	// create_remittance() abre un NXR Fund Source real por destino.
	function buildRemittanceFields(body) {
		const parent = $(body).find(".nxr-remittance-fields");
		const fields = {};
		const definitions = [
			["channel", __("Canal"), "Select", ["Remittance", "Cash", "Deposit", "Transfer", "Other"]],
			["currency", __("Moneda"), "Link", "Currency"],
			["exchange_rate", __("Tasa a HNL"), "Float"],
			["origin_or_sender", __("Procedencia o remitente"), "Data"],
			["institution", __("Institución"), "Data"],
			["account_reference", __("Cuenta"), "Data"],
			["external_reference", __("Referencia"), "Data"],
		];
		definitions.forEach(([fieldname, label, fieldtype, options]) => {
			fields[fieldname] = frappe.ui.form.make_control({
				parent,
				df: { fieldname, label, fieldtype, options, change: toggleRemittanceBankFields },
				render_input: true,
			});
		});
		fields.currency.set_value("HNL");
		fields.exchange_rate.set_value(1);

		const destinationsBody = $(body).find(".nxr-remittance-destinations");
		destinationsBody.html(`
      <div class="nxr-remittance-destination-rows"></div>
      <button type="button" class="nxr-ds-btn nxr-ds-btn--secondary nxr-ds-btn--sm nxr-remittance-add-destination">${__(
			"Agregar destino"
		)}</button>
      <div class="nxr-remittance-total"></div>
      <button type="button" class="nxr-ds-btn nxr-ds-btn--primary nxr-ds-btn--sm nxr-remittance-submit">${__(
			"Registrar remesa"
		)}</button>
    `);
		const rows = destinationsBody.find(".nxr-remittance-destination-rows");

		function destinationRows() {
			return rows
				.find(".nxr-remittance-destination-row")
				.toArray()
				.map((row) => ({
					label: $(row).find(".nxr-remittance-destination-label").val(),
					amount_hnl: $(row).find(".nxr-remittance-destination-amount").val(),
				}))
				.filter((row) => row.label && Number(row.amount_hnl) > 0);
		}

		function updateTotal() {
			const total = destinationRows().reduce((sum, row) => sum + Number(row.amount_hnl), 0);
			destinationsBody
				.find(".nxr-remittance-total")
				.text(`${__("Total de destinos")}: ${money(total)}`);
		}

		function addDestinationRow() {
			const row = $(`
        <label class="nxr-remittance-destination-row">
          <input type="text" class="form-control nxr-remittance-destination-label" placeholder="${__(
				"Destino, p. ej. Fondo construcción"
			)}">
          <input type="number" min="0" step="0.01" value="0" class="form-control nxr-remittance-destination-amount">
          <button type="button" class="nxr-ds-btn nxr-ds-btn--ghost nxr-ds-btn--sm nxr-remittance-remove-destination">${__(
				"Quitar"
			)}</button>
        </label>
      `).appendTo(rows);
			row.find("input").on("input", updateTotal);
			row.find(".nxr-remittance-remove-destination").on("click", () => {
				row.remove();
				updateTotal();
			});
			updateTotal();
		}

		destinationsBody.find(".nxr-remittance-add-destination").on("click", addDestinationRow);
		addDestinationRow();
		addDestinationRow();

		destinationsBody.find(".nxr-remittance-submit").on("click", async () => {
			const destinations = destinationRows();
			if (!destinations.length) {
				frappe.show_alert({ message: __("Agregue al menos un destino."), indicator: "orange" });
				return;
			}
			// Los destinos se capturan en HNL (lo que de verdad recibe cada fondo), pero
			// el servidor exige original_amount en la moneda original y calcula
			// total_amount_hnl = money(original_amount * exchange_rate) —money() cuantiza
			// a 2 decimales (NXRRemittance.validate, financial/model_utils.py). Ese
			// redondeo intermedio, no ruido de punto flotante, puede alejar
			// total_amount_hnl de la suma de destinos por más de un centavo en cuanto la
			// tasa no es 1 (comprobado: L100.00 a tasa 24.567891234 vuelve L99.99 tras
			// cuantizar original_amount antes de multiplicar). El servidor exige que
			// ambos coincidan exactamente (`allocated != self.total_amount_hnl`), así
			// que se recalcula aquí lo que el servidor va a obtener y se ajusta el
			// último destino por la diferencia — la misma técnica de "el último renglón
			// absorbe el redondeo" que ya se usa al repartir un total entre partes.
			const exchangeRate = roundRate(Number(fields.exchange_rate.get_value()));
			if (!Number.isFinite(exchangeRate) || exchangeRate <= 0) {
				frappe.show_alert({ message: __("La tasa debe ser mayor que cero."), indicator: "orange" });
				return;
			}
			// El servidor cuantiza cada fila (money(row.amount_hnl)) antes de sumarlas
			// (NXRRemittance.validate). Si un destino llega con más de 2 decimales —un
			// valor pegado, no tecleado— la suma que ve el servidor no es la que vio
			// este cálculo. Se cuantiza aquí primero para que ambas sumas coincidan.
			const normalizedDestinations = destinations.map((row) => ({
				...row,
				amount_hnl: roundMoney(Number(row.amount_hnl)).toFixed(2),
			}));
			const totalHnl = roundMoney(
				normalizedDestinations.reduce((sum, row) => sum + Number(row.amount_hnl), 0)
			);
			const originalAmount = roundMoney(totalHnl / exchangeRate);
			const expectedTotalHnl = roundMoney(originalAmount * exchangeRate);
			if (expectedTotalHnl !== totalHnl) {
				const lastDestination = normalizedDestinations[normalizedDestinations.length - 1];
				const adjusted = roundMoney(
					Number(lastDestination.amount_hnl) + (expectedTotalHnl - totalHnl)
				);
				if (adjusted <= 0) {
					frappe.show_alert({
						message: __(
							"El ajuste de redondeo deja el último destino en cero o negativo. Aumente su importe o reordene los destinos."
						),
						indicator: "orange",
					});
					return;
				}
				lastDestination.amount_hnl = adjusted.toFixed(2);
			}
			const remittancePayload = {
				channel: fields.channel.get_value(),
				currency: fields.currency.get_value(),
				original_amount: originalAmount,
				exchange_rate: exchangeRate,
				origin_or_sender: fields.origin_or_sender.get_value(),
				institution: fields.institution.get_value(),
				account_reference: fields.account_reference.get_value(),
				external_reference: fields.external_reference.get_value(),
				project: project.get_value(),
				custodian: frappe.session.user,
				destinations: normalizedDestinations,
				idempotency_key: uuid(),
			};
			const response = await frappe.call({
				method: "nexora.financial.service.create_remittance",
				type: "POST",
				args: { payload: remittancePayload },
				freeze: true,
				freeze_message: __("Registrando remesa y fuentes…"),
			});
			frappe.show_alert({
				message: __("Remesa {0} registrada con {1} destino(s)", [
					response.message.remittance_number,
					response.message.destinations.length,
				]),
				indicator: "green",
			});
			document.dispatchEvent(
				new CustomEvent("nexora:data-changed", { detail: { area: "finance", type: "income" } })
			);
			rows.empty();
			addDestinationRow();
			addDestinationRow();
			await loadSources();
		});
		toggleRemittanceBankFields();

		function toggleRemittanceBankFields() {
			const bank = ["Deposit", "Transfer"].includes(fields.channel?.get_value());
			["institution", "account_reference", "external_reference"].forEach((name) =>
				fields[name]?.toggle(bank)
			);
		}
	}
};

frappe.pages["nexora-finance"].on_page_show = function (wrapper) {
	void wrapper.nexora_apply_launch_context?.();
};

document.addEventListener("nexora:data-changed", () => {
	const wrapper = document.querySelector('[data-page-route="nexora-finance"]');
	void wrapper?.nexora_refresh_finance?.();
});
