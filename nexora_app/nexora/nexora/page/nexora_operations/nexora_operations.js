function readOperationalLaunchContext() {
	const query = new URLSearchParams(window.location.search);
	const context = {
		movement_code: frappe.route_options?.movement_code || query.get("movement_code") || null,
		project: frappe.route_options?.project || query.get("project") || null,
		show_ledger: frappe.route_options?.show_ledger || query.get("show_ledger") || null,
	};
	frappe.route_options = null;
	return context;
}

frappe.pages["nexora-operations"].on_page_load = function (wrapper) {
	const page = frappe.ui.make_app_page({
		parent: wrapper,
		title: __("Operación diaria"),
		single_column: true,
	});
	const body = $(page.body);
	const state = {
		movements: new Map(),
		movement: null,
		syncingProject: false,
		releaseContext: null,
		projectSerial: 0,
		preview: null,
		fieldValues: {},
		// Los manejadores de campo son asíncronos y escriben en otros controles. Si dos
		// se solapan, el último en terminar pisa al anterior y puede vaciar un campo que
		// el usuario acaba de rellenar. Se encadenan para que ocurran en el orden en que
		// se pidieron, y la vista previa espera a que la cadena termine.
		pendingFieldWork: Promise.resolve(),
		accounts: new Map(),
		sources: [],
		launch: readOperationalLaunchContext(),
	};
	const controls = {};

	body.html(`
		<main class="nxr-product-shell nxr-operational-shell" data-state="loading">
			<section class="nxr-transaction nxr-card">
				<header class="nxr-operational-header">
					<div>
						<p class="nxr-eyebrow">NX10 · ${__("OPERACIÓN DIARIA")}</p>
						<h2 class="nxr-operational-title">${__("Seleccione un código de movimiento")}</h2>
						<p class="text-muted">${__(
							"Capture el documento por cabecera, línea y detalle. La auditoría conserva la fecha real de registro."
						)}</p>
					</div>
					<div class="nxr-movement-help" aria-label="${__("Códigos disponibles")}"></div>
				</header>

				<nav class="nxr-document-tabs" aria-label="${__("Secciones del documento")}">
					<button type="button" data-document-tab="general" aria-selected="true">${__("General")}</button>
					<button type="button" data-document-tab="evidence" aria-selected="false">${__("Info. documento")}</button>
				</nav>

				<section class="nxr-document-panel" data-document-panel="general">
					<div class="nxr-section-heading">
						<div><strong>${__("Cabecera del documento")}</strong><span>${__(
		"Fecha, proyecto, movimiento y referencia"
	)}</span></div>
						<span class="nxr-document-state">${__("Borrador")}</span>
					</div>
					<div class="nxr-operational-fields nxr-document-fields" data-field-section="header"></div>
				</section>

				<section class="nxr-document-panel" data-document-panel="evidence" hidden>
					<div class="nxr-section-heading">
						<div><strong>${__("Información documental")}</strong><span>${__(
		"Motivo, comprobante, solicitante y aprobador"
	)}</span></div>
					</div>
					<div class="nxr-operational-fields nxr-document-fields" data-field-section="evidence"></div>
				</section>

				<section class="nxr-line-section">
					<div class="nxr-section-heading">
						<div><strong>${__("Líneas del movimiento")}</strong><span>${__(
		"Resumen de la línea financiera activa"
	)}</span></div>
						<span class="nxr-line-count">${__("1 línea")}</span>
					</div>
					<div class="table-responsive">
						<table class="table nxr-entry-table" data-nxr-table="plain">
							<thead>
								<tr>
									<th>${__("Línea")}</th>
									<th>${__("Mov.")}</th>
									<th>${__("Concepto")}</th>
									<th>${__("Cuenta / fuente")}</th>
									<th>${__("Institución")}</th>
									<th>${__("Moneda")}</th>
									<th class="text-right">${__("Importe")}</th>
									<th>${__("Estado")}</th>
								</tr>
							</thead>
							<tbody class="nxr-entry-line"></tbody>
						</table>
					</div>
				</section>

				<nav class="nxr-detail-tabs" aria-label="${__("Detalle de la línea")}">
					<button type="button" data-detail-tab="account" aria-selected="true">${__("Cuenta")}</button>
					<button type="button" data-detail-tab="amount" aria-selected="false">${__("Importe")}</button>
					<button type="button" data-detail-tab="classification" aria-selected="false">${__("Clasificación")}</button>
					<button type="button" data-detail-tab="funds" aria-selected="false">${__("Fondos")}</button>
					<button type="button" data-detail-tab="line-evidence" aria-selected="false">${__("Evidencia")}</button>
				</nav>

				<section class="nxr-detail-panel" data-detail-panel="account">
					<div class="nxr-operational-fields" data-field-section="account"></div>
					<div class="nxr-account-hint" role="status"></div>
				</section>
				<section class="nxr-detail-panel" data-detail-panel="amount" hidden>
					<div class="nxr-operational-fields" data-field-section="amount"></div>
				</section>
				<section class="nxr-detail-panel" data-detail-panel="classification" hidden>
					<div class="nxr-operational-fields" data-field-section="classification"></div>
				</section>
				<section class="nxr-detail-panel" data-detail-panel="funds" hidden>
					<div class="nxr-allocation-panel">
						<header><strong>${__("Fuentes que pagarán")}</strong><span>${__(
		"Distribuya el importe entre fondos disponibles"
	)}</span></header>
						<div class="nxr-operational-sources"></div>
					</div>
				</section>
				<section class="nxr-detail-panel" data-detail-panel="line-evidence" hidden>
					<div class="nxr-operational-fields" data-field-section="line-evidence"></div>
				</section>

				<div class="nxr-validation-summary" role="alert" hidden></div>
				<footer class="nxr-operational-actions">
					<span class="nxr-action-status">${__("Genere una vista previa válida para contabilizar.")}</span>
					<button type="button" class="btn btn-default nxr-preview-movement">${__("Vista previa")}</button>
					<button type="button" class="btn btn-primary nxr-execute-movement" disabled>${__("Contabilizar")}</button>
				</footer>
			</section>

			<section class="nxr-operational-preview nxr-card">
				<header><strong>${__("Vista previa verificable")}</strong><span>${__(
		"Sin guardar hasta pulsar Contabilizar"
	)}</span></header>
				<div class="nxr-preview-body nxr-empty">${__("Complete los datos y genere una vista previa.")}</div>
			</section>

			<section class="nxr-operational-ledger nxr-card">
				<header><div><strong>${__("Libro Central operativo")}</strong><span>${__(
		"Fecha documental y auditoría cronológica"
	)}</span></div><button type="button" class="btn btn-xs btn-default nxr-refresh-ledger">${__(
		"Actualizar"
	)}</button></header>
				<div class="nxr-operational-ledger-body"></div>
			</section>
		</main>
	`);

	const fieldDefinitions = [
		{
			fieldname: "movement_code",
			label: __("Código de movimiento"),
			fieldtype: "Data",
			reqd: 1,
			section: "header",
		},
		{
			fieldname: "document_date",
			label: __("Fecha del documento"),
			fieldtype: "Date",
			reqd: 1,
			section: "header",
		},
		{
			fieldname: "project",
			label: __("Proyecto"),
			fieldtype: "Link",
			options: "Project",
			reqd: 1,
			section: "header",
		},
		{
			fieldname: "external_reference",
			label: __("Número de referencia"),
			fieldtype: "Data",
			section: "header",
		},
		{
			fieldname: "account_mode",
			label: __("Modo de cuenta"),
			fieldtype: "Select",
			options: [
				{ label: __("Usar cuenta existente"), value: "Existing" },
				{ label: __("Crear cuenta nueva"), value: "New" },
				{ label: __("Datos manuales, no guardar"), value: "Manual" },
			],
			reqd: 1,
			section: "account",
		},
		{
			fieldname: "financial_account",
			label: __("Cuenta frecuente existente"),
			fieldtype: "Autocomplete",
			section: "account",
		},
		{
			fieldname: "account_name",
			label: __("Nombre de la cuenta nueva"),
			fieldtype: "Data",
			section: "account",
		},
		{
			fieldname: "channel",
			label: __("Cómo se recibió"),
			fieldtype: "Select",
			options: [
				{ label: __("Remesa"), value: "Remittance" },
				{ label: __("Efectivo"), value: "Cash" },
				{ label: __("Depósito bancario"), value: "Deposit" },
				{ label: __("Transferencia"), value: "Transfer" },
				{ label: __("Otro"), value: "Other" },
			],
			section: "account",
		},
		{
			fieldname: "origin_or_sender",
			label: __("Remitente u origen"),
			fieldtype: "Data",
			section: "account",
		},
		{
			fieldname: "institution",
			label: __("Banco o remesadora"),
			fieldtype: "Link",
			options: "Bank",
			section: "account",
		},
		{
			fieldname: "account_reference",
			label: __("Cuenta destino"),
			fieldtype: "Data",
			section: "account",
		},
		{
			fieldname: "currency",
			label: __("Moneda"),
			fieldtype: "Link",
			options: "Currency",
			section: "amount",
		},
		{
			fieldname: "original_amount",
			label: __("Importe original"),
			fieldtype: "Currency",
			section: "amount",
		},
		{
			fieldname: "exchange_rate",
			label: __("Tasa a HNL"),
			fieldtype: "Float",
			section: "amount",
		},
		{
			fieldname: "amount_hnl",
			label: __("Importe HNL"),
			fieldtype: "Currency",
			section: "amount",
		},
		{
			fieldname: "economic_category",
			label: __("Categoría económica"),
			fieldtype: "Link",
			options: "NXR Economic Category",
			section: "classification",
		},
		{
			fieldname: "cost_center",
			label: __("Centro de costo"),
			fieldtype: "Link",
			options: "Cost Center",
			section: "classification",
		},
		{
			fieldname: "beneficiary",
			label: __("Contratista o proveedor"),
			fieldtype: "Link",
			options: "NXR Entity",
			section: "classification",
		},
		{
			fieldname: "payment_method",
			label: __("Medio de pago"),
			fieldtype: "Select",
			options: [
				{ label: __("Efectivo"), value: "Cash" },
				{ label: __("Depósito"), value: "Deposit" },
				{ label: __("Transferencia"), value: "Transfer" },
				{ label: __("Otro"), value: "Other" },
			],
			section: "classification",
		},
		{
			fieldname: "reference_name",
			label: __("Documento original"),
			fieldtype: "Link",
			options: "NXR Operation",
			get_query: () => ({
				filters: { project: controls.project?.get_value() || "", status: "Executed" },
			}),
			section: "line-evidence",
		},
		{
			fieldname: "description",
			label: __("Concepto o motivo"),
			fieldtype: "Small Text",
			section: "evidence",
		},
		{
			fieldname: "evidence",
			label: __("Comprobante"),
			fieldtype: "Attach",
			section: "evidence",
		},
		{
			fieldname: "requester",
			label: __("Solicitante"),
			fieldtype: "Link",
			options: "User",
			section: "line-evidence",
		},
		{
			fieldname: "approved_by",
			label: __("Aprobador"),
			fieldtype: "Link",
			options: "User",
			section: "line-evidence",
		},
	];

	for (const definition of fieldDefinitions) {
		const target = body.find(`[data-field-section="${definition.section}"]`);
		const slot = $(
			`<div class="nxr-operational-field" data-field="${definition.fieldname}"></div>`
		).appendTo(target);
		const control = frappe.ui.form.make_control({
			parent: slot,
			df: {
				...definition,
				change: () => {
					state.pendingFieldWork = state.pendingFieldWork
						.catch(() => {})
						.then(() => fieldChanged(definition.fieldname))
						.catch((error) => console.error("NEXORA operations field handler failed", error));
				},
			},
			render_input: true,
		});
		controls[definition.fieldname] = control;
	}

	controls.document_date.set_value(frappe.datetime.get_today());
	controls.account_mode.set_value("New");
	controls.channel.set_value("Remittance");
	controls.currency.set_value("HNL");
	controls.exchange_rate.set_value(1);
	controls.payment_method.set_value("Transfer");

	controls.movement_code.$input.on("keydown", (event) => {
		if (event.key === "Enter") {
			event.preventDefault();
			applyMovement();
		}
	});
	body.on("click", ".nxr-movement-chip", function () {
		controls.movement_code.set_value($(this).data("code"));
		applyMovement();
	});
	body.on("click", "[data-document-tab]", function () {
		selectTab("document", $(this).data("document-tab"));
	});
	body.on("click", "[data-detail-tab]", function () {
		selectTab("detail", $(this).data("detail-tab"));
	});
	body.on("click", ".nxr-preview-movement", () => void previewMovement());
	body.on("click", ".nxr-execute-movement", () => void executeMovement());
	body.on("click", ".nxr-refresh-ledger", () => void loadLedger());
	body.on("input", ".nxr-source-amount", () => {
		invalidatePreview("allocation-amount");
		renderEntryLine();
	});

	wrapper.nexora_apply_operational_context = async () => {
		const launch = readOperationalLaunchContext();
		if (!launch.project && !launch.movement_code && !launch.show_ledger) return;
		if (launch.project) await controls.project.set_value(launch.project);
		if (launch.movement_code) await controls.movement_code.set_value(launch.movement_code);
		applyMovement();
		if (launch.show_ledger) body.find(".nxr-operational-ledger")[0]?.scrollIntoView({ block: "start" });
	};

	// Si la carga inicial falla, la pantalla debe quedar utilizable en vez de
	// congelarse en "cargando" sin explicacion.
	initialize().catch((error) => {
		console.error("NEXORA operations failed to initialize", error);
		body.find(".nxr-operational-shell").attr("data-state", "ready");
		// Si el bundle compartido no cargó, `showError` no existe y la pantalla quedaría
		// «lista» y muda. La rama es explícita porque `showError` no devuelve valor: con
		// `||` el respaldo se ejecutaba siempre y el usuario veía dos diálogos.
		const title = __("No fue posible preparar la operación diaria");
		const message = __("Seleccione un proyecto y un código de movimiento para continuar.");
		if (typeof window.nexora.ui?.showError === "function") {
			window.nexora.ui.showError(error, { title, fallback: message });
		} else {
			frappe.msgprint({ title, message, indicator: "red" });
		}
	});

	async function initialize() {
		const response = await frappe.call({
			method: "nexora.financial.service.movement_catalog",
			type: "POST",
		});
		for (const row of response.message || []) state.movements.set(row.code, row);
		body.find(".nxr-movement-help").html(
			[...state.movements.values()]
				.map(
					(row) =>
						`<button type="button" class="nxr-movement-chip" data-code="${escape(
							row.code
						)}"><b>${escape(row.code)}</b><span>${escape(row.label)}</span></button>`
				)
				.join("")
		);
		// El proyecto viene de la ruta si se llegó desde otra pantalla; si no, se
		// hereda del contexto activo para no obligar a elegirlo de nuevo.
		const launchProject =
			state.launch.project || (await window.nexora.context?.activeProject?.()) || null;
		if (launchProject) {
			state.syncingProject = true;
			try {
				await controls.project.set_value(launchProject);
			} finally {
				state.syncingProject = false;
			}
		}
		state.releaseContext = window.nexora.context?.onContextChange?.(async (context) => {
			const desired = context?.project || "";
			if ((controls.project.get_value() || "") === desired) return;
			state.syncingProject = true;
			try {
				await controls.project.set_value(desired);
			} finally {
				state.syncingProject = false;
			}
			await loadProjectData();
		});
		$(wrapper).on("remove", () => state.releaseContext?.());
		await controls.movement_code.set_value(state.launch.movement_code || "101");
		applyMovement();
		await loadProjectData();
		body.find(".nxr-operational-shell").attr("data-state", "ready");
		if (state.launch.show_ledger)
			body.find(".nxr-operational-ledger")[0]?.scrollIntoView({ block: "start" });
	}

	async function fieldChanged(fieldname) {
		clearValidation();
		// Un evento `change` no prueba que el dato haya cambiado: Frappe lo emite también
		// cuando la pantalla reescribe un control, cuando el asistente guiado mueve el
		// campo de contenedor o cuando el foco vuelve a él. Anular la vista previa por eso
		// destruía trabajo válido —el recorrido lo mostró con `field:description` sobre un
		// gasto que el servidor ya había aprobado— y obligaba al usuario a repetirla sin
		// haber tocado nada. Solo un valor distinto la anula; ejecutar con una vista previa
		// obsoleta sigue siendo imposible porque el servidor revalida su huella.
		const previous = state.fieldValues[fieldname];
		const current = String(controls[fieldname]?.get_value() ?? "");
		state.fieldValues[fieldname] = current;
		if (previous !== current) invalidatePreview(`field:${fieldname}`);
		if (fieldname === "movement_code") applyMovement();
		if (fieldname === "project") {
			// El proyecto elegido aquí pasa a ser el contexto activo: la barra global
			// y el resto de módulos no pueden quedar contradiciendo esta pantalla.
			// Publicar el contexto no debe impedir cargar los datos del proyecto: si el
			// servidor rechaza el cambio de contexto, la pantalla igual tiene que servir.
			if (!state.syncingProject) {
				try {
					await window.nexora.context?.setActiveProject?.(controls.project.get_value() || null);
				} catch (error) {
					console.error("NEXORA operations failed to publish the active project", error);
				}
			}
			await loadProjectData();
		}
		if (fieldname === "account_mode") await applyAccountMode();
		if (fieldname === "financial_account") await applyFinancialAccount();
		if (fieldname === "channel") applyBankVisibility();
		// El comprobante deja de ser opcional según el medio de pago y el importe: hay
		// que reevaluarlo en cuanto cambia cualquiera de los dos, no solo al elegir el
		// código de movimiento.
		if (["payment_method", "amount_hnl"].includes(fieldname)) applyEvidencePolicy();
		if (fieldname === "payment_method") applyBankVisibility();
		renderEntryLine();
	}

	function selectTab(group, name) {
		body.find(`[data-${group}-tab]`).attr("aria-selected", "false");
		body.find(`[data-${group}-tab="${name}"]`).attr("aria-selected", "true");
		body.find(`[data-${group}-panel]`).attr("hidden", true);
		body.find(`[data-${group}-panel="${name}"]`).removeAttr("hidden");
	}

	function toggle(name, visible, required = false) {
		const control = controls[name];
		control.toggle(Boolean(visible));
		control.df.reqd = Boolean(required);
		control.refresh();
	}

	// La regla vive en `window.nexora.rules` (nexora.js), espejo de
	// `evaluate_evidence_policy`. Aquí solo se consulta: duplicarla sería tener la
	// misma regla de negocio en dos sitios que pueden separarse.
	function evidenceRequirement() {
		return window.nexora.rules.evidencePolicy(
			controls.payment_method.get_value(),
			controls.amount_hnl.get_value()
		);
	}

	function applyEvidencePolicy() {
		const code = String(controls.movement_code.get_value() || "").trim();
		if (code !== "102") return;
		const policy = evidenceRequirement();
		controls.evidence.df.reqd = policy.required;
		controls.evidence.df.description = policy.reason;
		controls.evidence.refresh();
	}

	function setReadOnly(name, readOnly) {
		const control = controls[name];
		control.df.read_only = Boolean(readOnly);
		control.refresh();
	}

	function applyMovement() {
		const code = String(controls.movement_code.get_value() || "").trim();
		state.movement = state.movements.get(code) || null;
		body.find(".nxr-operational-title").text(
			state.movement ? `${code} · ${state.movement.label}` : __("Código de movimiento no reconocido")
		);
		body.find(".nxr-movement-chip").attr("aria-pressed", "false");
		body.find(`.nxr-movement-chip[data-code="${code}"]`).attr("aria-pressed", "true");
		const income = code === "101";
		const expense = code === "102";
		const correction = ["303", "304", "501"].includes(code);

		toggle("account_mode", income, income);
		for (const name of [
			"financial_account",
			"account_name",
			"channel",
			"currency",
			"original_amount",
			"exchange_rate",
			"origin_or_sender",
			"institution",
			"account_reference",
		]) {
			toggle(name, income, false);
		}
		toggle("economic_category", expense, expense);
		toggle("amount_hnl", expense, expense);
		toggle("cost_center", expense, false);
		toggle("beneficiary", expense, expense);
		toggle("payment_method", expense, expense);
		toggle(
			"external_reference",
			income || expense,
			income && ["Remittance", "Deposit", "Transfer"].includes(controls.channel.get_value())
		);
		toggle("reference_name", correction, correction);
		toggle("description", expense || correction, expense || correction);
		toggle("evidence", expense || correction, code === "304");
		applyEvidencePolicy();
		toggle("requester", expense || correction, correction);
		toggle("approved_by", expense || correction, correction);
		body.find('[data-detail-tab="funds"]').toggle(expense);
		body.find('[data-detail-tab="account"]').toggle(income);
		body.find('[data-detail-tab="amount"]').toggle(income || expense);
		body.find('[data-detail-tab="classification"]').toggle(expense);
		body.find('[data-detail-tab="line-evidence"]').toggle(correction);
		selectTab("detail", income ? "account" : expense ? "classification" : "line-evidence");
		body.find(".nxr-preview-movement").prop("disabled", !state.movement);
		void applyAccountMode();
		applyBankVisibility();
		renderEntryLine();
	}

	async function applyAccountMode() {
		if (state.movement?.code !== "101") return;
		const mode = controls.account_mode.get_value() || "Manual";
		const existing = mode === "Existing";
		const creating = mode === "New";
		toggle("financial_account", existing, existing);
		toggle("account_name", creating, creating);
		for (const name of [
			"channel",
			"currency",
			"original_amount",
			"exchange_rate",
			"origin_or_sender",
			"institution",
			"account_reference",
		]) {
			toggle(
				name,
				true,
				["channel", "currency", "original_amount", "exchange_rate", "origin_or_sender"].includes(name)
			);
		}
		for (const name of ["channel", "currency", "origin_or_sender", "institution", "account_reference"]) {
			setReadOnly(name, existing);
		}
		if (!existing && controls.financial_account.get_value()) {
			await controls.financial_account.set_value("");
		}
		if (existing) {
			body.find(".nxr-account-hint").text(
				state.accounts.size
					? __("Seleccione una cuenta existente de este proyecto.")
					: __("No hay cuentas existentes. Cambie a Crear cuenta nueva.")
			);
		} else if (creating) {
			body.find(".nxr-account-hint").text(
				__("La cuenta se validará en la vista previa y se creará dentro de la misma contabilización.")
			);
		} else {
			body.find(".nxr-account-hint").text(
				__("Los datos se usarán solamente en este ingreso y no se guardarán como cuenta frecuente.")
			);
		}
		applyBankVisibility();
		renderEntryLine();
	}

	function applyBankVisibility() {
		if (state.movement?.code === "102") {
			// `_resolve_expense_account` exige banco y referencia de cuenta para todo
			// gasto pagado por depósito o transferencia. Sin mostrarlos, ese pago era
			// imposible de completar: el servidor pedía datos que la pantalla ocultaba.
			const bank = window.nexora.rules.requiresBankAccountDetails(controls.payment_method.get_value());
			toggle("institution", bank, bank);
			toggle("account_reference", bank, bank);
			setReadOnly("institution", false);
			setReadOnly("account_reference", false);
			return;
		}
		if (state.movement?.code !== "101") return;
		const existing = controls.account_mode.get_value() === "Existing";
		const channel = controls.channel.get_value();
		const bank = ["Remittance", "Deposit", "Transfer"].includes(channel);
		toggle("institution", bank, bank);
		toggle("account_reference", bank, bank);
		setReadOnly("institution", existing);
		setReadOnly("account_reference", existing);
		toggle(
			"external_reference",
			channel !== "Cash",
			["Remittance", "Deposit", "Transfer"].includes(channel)
		);
	}

	async function loadProjectData() {
		// Cambiar de proyecto rapido dispara varias cargas: sin este contador, la
		// respuesta del proyecto anterior puede pisar cuentas y saldos del actual.
		const serial = ++state.projectSerial;
		state.preview = null;
		body.find(".nxr-execute-movement").prop("disabled", true);
		await controls.financial_account.set_value("");
		const project = controls.project.get_value();
		if (serial !== state.projectSerial) return;
		if (!project) {
			state.accounts.clear();
			state.sources = [];
			controls.financial_account.set_data([]);
			renderSources([]);
			await controls.account_mode.set_value("New");
			await applyAccountMode();
			await loadLedger();
			return;
		}
		const [accountsResponse, sourcesResponse] = await Promise.all([
			frappe.call({
				method: "nexora.financial.service.list_financial_accounts",
				type: "POST",
				args: { project },
			}),
			frappe.call({
				method: "nexora.financial.service.list_source_balances",
				type: "POST",
				args: { project },
			}),
		]);
		// Solo la carga mas reciente puede escribir el estado y repintar.
		if (serial !== state.projectSerial || controls.project.get_value() !== project) return;
		state.accounts.clear();
		const accountOptions = (accountsResponse.message || []).map((row) => {
			state.accounts.set(row.name, row);
			return { label: row.label, value: row.name };
		});
		controls.financial_account.set_data(accountOptions);
		state.sources = sourcesResponse.message || [];
		renderSources(state.sources);
		// La pantalla no elige por el usuario. Poner «Existing» en cuanto el proyecto tiene
		// cuentas guardadas hacía `setReadOnly` sobre origen, canal, moneda y referencia,
		// y `refresh()` repinta el control: lo que la persona acababa de escribir
		// desaparecía y el campo quedaba bloqueado. Y el asistente sigue exigiendo el
		// origen para avanzar, así que pedía un dato que él mismo impedía teclear.
		// «Manual» es el modo neutro —no guarda nada y deja escribir—; usar una cuenta
		// existente es una elección explícita que el asistente ofrece en su segunda etapa.
		await controls.account_mode.set_value("Manual");
		await applyAccountMode();
		await loadLedger();
	}

	async function applyFinancialAccount() {
		const name = controls.financial_account.get_value();
		if (!name) return;
		if (controls.account_mode.get_value() !== "Existing") {
			await controls.financial_account.set_value("");
			return;
		}
		if (!state.accounts.has(name)) {
			showValidation([
				{
					field: "financial_account",
					message: __("Seleccione una cuenta existente de la lista o use Crear cuenta nueva."),
				},
			]);
			await controls.financial_account.set_value("");
			return;
		}
		const response = await frappe.call({
			method: "nexora.financial.service.get_financial_account",
			type: "POST",
			args: { account: name, project: controls.project.get_value() },
		});
		const row = response.message || {};
		for (const [field, value] of Object.entries({
			origin_or_sender: row.origin_or_sender,
			institution: row.institution,
			account_reference: row.account_reference,
			currency: row.currency,
			channel: row.default_channel,
		})) {
			await controls[field].set_value(value || "");
		}
		body.find(".nxr-account-hint").text(
			__("Cuenta aplicada: {0} · {1} · {2}", [
				row.account_name || name,
				row.institution || __("Sin institución"),
				row.masked_account_reference || __("Sin cuenta"),
			])
		);
		applyBankVisibility();
		renderEntryLine();
	}

	function renderSources(rows) {
		const target = body.find(".nxr-operational-sources").empty();
		const available = rows.filter((row) => Number(row.available_hnl) > 0);
		if (!available.length) {
			target.html(`<p class="nxr-empty">${__("El proyecto no tiene fondos disponibles.")}</p>`);
			return;
		}
		for (const row of available) {
			target.append(`
				<label class="nxr-operational-source">
					<span><strong>${escape(row.source)}</strong><small>${__("Disponible")}: ${money(
				row.available_hnl
			)}</small></span>
					<input class="form-control nxr-source-amount" type="number" min="0" step="0.01" value="0" data-source="${escape(
						row.source
					)}">
				</label>
			`);
		}
	}

	function allocations() {
		return body
			.find(".nxr-source-amount")
			.toArray()
			.map((input) => ({ source: input.dataset.source, amount_hnl: input.value }))
			.filter((row) => Number(row.amount_hnl) > 0);
	}

	function payload() {
		// `account_mode` solo se muestra en el ingreso: allí el usuario elige entre usar
		// una cuenta guardada, crear una nueva o no guardar nada. En el gasto el control
		// está oculto y conserva el «New» con el que arranca la pantalla, así que el
		// servidor recibía modo «New» con nombre de cuenta vacío y rechazaba la vista
		// previa de TODO gasto. El envío debe reflejar lo que la pantalla ofrece.
		const isIncome = String(controls.movement_code.get_value() || "").trim() === "101";
		const accountMode = isIncome ? controls.account_mode.get_value() || "Manual" : "Manual";
		return {
			movement_code: String(controls.movement_code.get_value() || "").trim(),
			document_date: controls.document_date.get_value(),
			project: controls.project.get_value(),
			account_mode: accountMode,
			financial_account: accountMode === "Existing" ? controls.financial_account.get_value() : "",
			save_financial_account: accountMode === "New" ? 1 : 0,
			account_name: accountMode === "New" ? controls.account_name.get_value() : "",
			channel: controls.channel.get_value(),
			currency: controls.currency.get_value(),
			original_amount: controls.original_amount.get_value(),
			exchange_rate: controls.exchange_rate.get_value(),
			origin_or_sender: controls.origin_or_sender.get_value(),
			institution: controls.institution.get_value(),
			account_reference: controls.account_reference.get_value(),
			external_reference: controls.external_reference.get_value(),
			economic_category: controls.economic_category.get_value(),
			amount_hnl: controls.amount_hnl.get_value(),
			cost_center: controls.cost_center.get_value(),
			analytic_splits:
				controls.cost_center.get_value() && Number(controls.amount_hnl.get_value()) > 0
					? [
							{
								cost_center: controls.cost_center.get_value(),
								amount_hnl: controls.amount_hnl.get_value(),
							},
					  ]
					: [],
			beneficiary_doctype: controls.beneficiary.get_value() ? "NXR Entity" : "",
			beneficiary: controls.beneficiary.get_value(),
			payment_method: controls.payment_method.get_value(),
			reference_name: controls.reference_name.get_value(),
			description: controls.description.get_value(),
			reason: controls.description.get_value(),
			evidence: controls.evidence.get_value(),
			requester: controls.requester.get_value(),
			approved_by: controls.approved_by.get_value(),
			allocations: allocations(),
		};
	}

	function validateBeforePreview() {
		const data = payload();
		const errors = [];
		const required = (field, message) => {
			if (!data[field]) errors.push({ field, message });
		};
		if (!state.movement)
			errors.push({ field: "movement_code", message: __("Seleccione un movimiento válido.") });
		required("document_date", __("Seleccione la fecha del documento."));
		required("project", __("Seleccione el proyecto."));
		if (data.movement_code === "101") {
			required("account_mode", __("Seleccione cómo desea registrar la cuenta."));
			if (data.account_mode === "Existing") {
				required("financial_account", __("Seleccione una cuenta frecuente existente."));
				if (data.financial_account && !state.accounts.has(data.financial_account)) {
					errors.push({
						field: "financial_account",
						message: __("La cuenta escrita no existe en la lista del proyecto."),
					});
				}
			}
			if (data.account_mode === "New") {
				required("account_name", __("Escriba un nombre para la cuenta nueva."));
			}
			required("channel", __("Seleccione cómo se recibió el ingreso."));
			required("currency", __("Seleccione la moneda."));
			if (Number(data.original_amount) <= 0) {
				errors.push({ field: "original_amount", message: __("El importe debe ser mayor que cero.") });
			}
			if (Number(data.exchange_rate) <= 0) {
				errors.push({ field: "exchange_rate", message: __("La tasa debe ser mayor que cero.") });
			}
			required("origin_or_sender", __("Escriba el remitente u origen."));
			if (["Remittance", "Deposit", "Transfer"].includes(data.channel)) {
				required("institution", __("Seleccione el banco o remesadora."));
				required("account_reference", __("Escriba la cuenta destino."));
				required("external_reference", __("Escriba el número de referencia."));
			}
		}
		if (data.movement_code === "102") {
			required("economic_category", __("Seleccione la categoría económica."));
			required("beneficiary", __("Seleccione el contratista o proveedor."));
			required("payment_method", __("Seleccione el medio de pago."));
			const evidence = evidenceRequirement();
			if (evidence.required && !String(data.evidence || "").trim()) {
				errors.push({ field: "evidence", message: evidence.reason });
			}
			// Marcar el campo como obligatorio no impide enviar: quien bloquea la vista
			// previa es esta función. `_resolve_expense_account` exige los dos datos.
			if (window.nexora.rules.requiresBankAccountDetails(data.payment_method)) {
				required("institution", __("El pago requiere banco o institución."));
				required("account_reference", __("El pago requiere número o referencia de cuenta."));
			}
			if (Number(data.amount_hnl) <= 0) {
				errors.push({ field: "amount_hnl", message: __("El importe debe ser mayor que cero.") });
			}
			if (!data.allocations.length) {
				errors.push({ field: null, message: __("Distribuya el gasto entre fondos disponibles.") });
			}
		}
		if (["303", "304", "501"].includes(data.movement_code)) {
			required("reference_name", __("Seleccione el documento original."));
			if (String(data.description || "").trim().length < 10) {
				errors.push({
					field: "description",
					message: __("Explique el motivo con al menos 10 caracteres."),
				});
			}
			// Los tres códigos de corrección exigen segregación en el servidor
			// (`requires_segregation` en REVERSAL_NO_CASH y DOCUMENT_SUBSTITUTION). Sin
			// comprobarlo aquí, elegirse a uno mismo como solicitante —lo natural, porque
			// es quien llena el formulario— se rechazaba recién en la vista previa.
			const segregation = window.nexora.rules.segregationError(data.requester, data.approved_by);
			if (segregation) {
				errors.push({ field: segregation.field, message: segregation.message });
			}
			// DOCUMENT_SUBSTITUTION declara `requires_evidence=True`.
			if (data.movement_code === "304") {
				required("evidence", __("Adjunte el documento que sustituye al original."));
			}
		}
		return errors;
	}

	function showValidation(errors) {
		clearValidation();
		const summary = body.find(".nxr-validation-summary");
		summary
			.html(
				`<strong>${__("Revise antes de continuar")}</strong><ul>${errors
					.map((row) => `<li>${escape(row.message)}</li>`)
					.join("")}</ul>`
			)
			.removeAttr("hidden");
		for (const row of errors) {
			if (row.field) body.find(`[data-field="${row.field}"]`).addClass("nxr-field-invalid");
		}
		const first = errors.find((row) => row.field);
		controls[first?.field]?.$input?.trigger("focus");
	}

	function clearValidation() {
		body.find(".nxr-validation-summary").attr("hidden", true).empty();
		body.find(".nxr-field-invalid").removeClass("nxr-field-invalid");
	}

	async function previewMovement() {
		// No se calcula a mitad de una escritura de la pantalla: la vista previa saldría
		// con valores viejos y la escritura pendiente la anularía justo después.
		await state.pendingFieldWork.catch(() => {});
		const errors = validateBeforePreview();
		if (errors.length) {
			showValidation(errors);
			return;
		}
		clearValidation();
		try {
			const response = await frappe.call({
				method: "nexora.financial.service.preview_operational_movement",
				type: "POST",
				args: { payload: payload() },
				freeze: true,
				freeze_message: __("Validando fecha, permisos, saldos y referencias…"),
			});
			state.preview = response.message;
			renderPreview(state.preview);
			renderEntryLine();
			body.find(".nxr-operational-shell").removeAttr("data-preview-invalidated-by");
			body.find(".nxr-execute-movement").prop("disabled", false);
			body.find(".nxr-action-status").text(__("Vista previa vigente. Ya puede contabilizar."));
		} catch (error) {
			invalidatePreview("server-refused-preview");
			body.find(".nxr-validation-summary")
				.html(
					`<strong>${__("No se pudo validar")}</strong><p>${__(
						"Revise el mensaje del servidor y corrija los datos señalados."
					)}</p>`
				)
				.removeAttr("hidden");
			throw error;
		}
	}

	function renderPreview(preview) {
		const sourceRows = (preview.sources || [])
			.map(
				(row) =>
					`<tr><td>${escape(row.source)}</td><td>${money(row.amount_hnl)}</td><td>${money(
						row.balance_before_hnl
					)}</td><td>${money(row.balance_after_hnl)}</td></tr>`
			)
			.join("");
		body.find(".nxr-preview-body").removeClass("nxr-empty").html(`
			<div class="nxr-preview-summary">
				<span><small>${__("Movimiento")}</small><strong>${escape(preview.movement_code)} · ${escape(
			preview.movement_label
		)}</strong></span>
				<span><small>${__("Fecha documento")}</small><strong>${date(preview.document_date)}</strong></span>
				<span><small>${__("Importe")}</small><strong>${money(preview.amount_hnl)}</strong></span>
				<span><small>${__("Documento")}</small><strong>${escape(
			preview.document_to_generate || __("Operación NEXORA")
		)}</strong></span>
			</div>
			${
				sourceRows
					? `<div class="table-responsive"><table class="table table-bordered"><thead><tr><th>${__(
							"Fuente"
					  )}</th><th>${__("Importe")}</th><th>${__("Saldo anterior")}</th><th>${__(
							"Saldo posterior"
					  )}</th></tr></thead><tbody>${sourceRows}</tbody></table></div>`
					: ""
			}
		`);
	}

	async function executeMovement() {
		if (!state.preview) return;
		const data = {
			...payload(),
			idempotency_key: uuid(),
			preview_hash: state.preview.preview_hash,
		};
		const response = await frappe.call({
			method: "nexora.financial.service.execute_operational_movement",
			type: "POST",
			args: { payload: data },
			freeze: true,
			freeze_message: __("Contabilizando operación y preservando auditoría…"),
		});
		frappe.show_alert({
			message: __("Documento {0} contabilizado", [response.message.document_number || ""]),
			indicator: "green",
		});
		document.dispatchEvent(
			new CustomEvent("nexora:data-changed", { detail: { area: "finance", type: data.movement_code } })
		);
		await resetAfterExecution();
		await loadProjectData();
	}

	async function resetAfterExecution() {
		invalidatePreview("after-execution");
		await controls.financial_account.set_value("");
		await controls.account_name.set_value("");
		await controls.original_amount.set_value("");
		await controls.amount_hnl.set_value("");
		await controls.external_reference.set_value("");
		await controls.description.set_value("");
		body.find(".nxr-source-amount").val(0);
		renderEntryLine();
	}

	// «La información cambió» es una afirmación que la consola no podía justificar: se
	// anulaba la vista previa sin dejar rastro de quién lo pidió. Con el motivo escrito
	// en la carcasa, un recorrido rojo distingue «el usuario editó un campo» de «la
	// pantalla se refrescó sola», que son problemas distintos.
	function invalidatePreview(reason = "unknown") {
		state.preview = null;
		body.find(".nxr-operational-shell").attr("data-preview-invalidated-by", reason);
		body.find(".nxr-execute-movement").prop("disabled", true);
		body.find(".nxr-action-status").text(__("Genere una vista previa válida para contabilizar."));
		body.find(".nxr-document-state").text(__("Borrador"));
		body.find(".nxr-preview-body")
			.addClass("nxr-empty")
			.text(__("La información cambió. Genere una nueva vista previa."));
	}

	function renderEntryLine() {
		const data = payload();
		const account =
			data.account_mode === "Existing"
				? state.accounts.get(data.financial_account)?.account_name || __("Cuenta existente")
				: data.account_mode === "New"
				? data.account_name || __("Cuenta nueva")
				: data.account_reference || __("Datos manuales");
		const concept =
			data.movement_code === "101"
				? data.origin_or_sender
				: data.beneficiary || data.description || __("Sin concepto");
		const amount =
			data.movement_code === "101"
				? Number(data.original_amount || 0) * Number(data.exchange_rate || 0)
				: Number(data.amount_hnl || state.preview?.amount_hnl || 0);
		const status = state.preview ? __("Validado") : __("Borrador");
		body.find(".nxr-document-state").text(status);
		body.find(".nxr-entry-line").html(`
			<tr data-state="${state.preview ? "validated" : "draft"}">
				<td>1</td>
				<td><b>${escape(data.movement_code || "—")}</b></td>
				<td>${escape(concept || __("Sin concepto"))}</td>
				<td>${escape(account)}</td>
				<td>${escape(data.institution || "—")}</td>
				<td>${escape(data.currency || "—")}</td>
				<td class="text-right">${money(amount)}</td>
				<td>${escape(status)}</td>
			</tr>
		`);
	}

	async function loadLedger() {
		const response = await frappe.call({
			method: "nexora.financial.service.list_operational_ledger",
			type: "POST",
			args: { project: controls.project.get_value() || null, limit: 100 },
		});
		renderLedger(response.message || []);
	}

	function renderLedger(rows) {
		const target = body.find(".nxr-operational-ledger-body");
		if (!rows.length) {
			target.html(`<p class="nxr-empty">${__("No hay operaciones para mostrar.")}</p>`);
			return;
		}
		target.html(`
			<div class="table-responsive">
				<table class="table nxr-ledger-table">
					<thead><tr>
						<th>${__("Día")}</th><th>${__("Fecha documento")}</th><th>${__("Documento")}</th>
						<th>${__("Mov.")}</th><th>${__("Movimiento")}</th><th>${__("Remitente / beneficiario")}</th>
						<th>${__("Institución")}</th><th>${__("Cuenta")}</th><th>${__("Moneda")}</th>
						<th class="text-right">${__("Importe")}</th><th>${__("Estado")}</th>
					</tr></thead>
					<tbody>${rows.map(ledgerRow).join("")}</tbody>
				</table>
			</div>
		`);
	}

	function ledgerRow(row) {
		const decorated = row.struck ? `<s>${money(row.amount_hnl)}</s>` : money(row.amount_hnl);
		return `<tr data-tone="${escape(row.tone)}" data-movement="${escape(row.movement_code)}">
			<td>${escape(row.day)}</td><td>${date(row.document_date)}</td>
			<td><a href="${frappe.utils.get_form_link("NXR Operation", row.name)}">${escape(
			row.document_number || row.name
		)}</a></td>
			<td><b>${escape(row.movement_code)}</b></td><td>${escape(row.movement_label)}</td>
			<td>${escape(row.counterparty)}</td><td>${escape(row.institution)}</td><td>${escape(row.account)}</td>
			<td>${escape(row.currency)}</td><td class="text-right"><span data-tone="${escape(
			row.tone
		)}">${decorated}</span></td><td>${escape(row.status)}</td>
		</tr>`;
	}

	function uuid() {
		return window.nexora.ui.generateId();
	}

	function money(value) {
		return window.nexora.ui.formatMoney(value);
	}

	function date(value) {
		return window.nexora.ui.formatDate(value);
	}

	function escape(value) {
		return window.nexora.ui.escapeHtml(value);
	}
};

frappe.pages["nexora-operations"].on_page_show = function (wrapper) {
	void wrapper.nexora_apply_operational_context?.();
};
