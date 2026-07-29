frappe.provide("nexora");

(() => {
	"use strict";

	const model = window.nexora.guidedOperationsModel;
	if (!model) return;

	const states = new WeakMap();
	let observer;
	let scheduled = false;

	const q = (root, selector) => root?.querySelector(selector) || null;
	const qa = (root, selector) => [...(root?.querySelectorAll(selector) || [])];
	const shell = () =>
		String((frappe.get_route?.() || [])[0] || "").toLowerCase() === "nexora-operations"
			? q(document, "#page-nexora-operations .nxr-operational-shell")
			: null;
	const field = (root, name) => q(root, `[data-field="${name}"]`);
	const input = (root, name) => q(field(root, name), "input:not([type='hidden']),select,textarea");
	const read = (root, name) => String(input(root, name)?.value || "").trim();

	function write(root, name, value, notify = false) {
		const node = input(root, name);
		if (!node) return;
		const next = value == null ? "" : String(value);
		if (node.value === next) return;
		node.value = next;
		if (notify) {
			node.dispatchEvent(new Event("input", { bubbles: true }));
			node.dispatchEvent(new Event("change", { bubbles: true }));
		}
	}

	function readonly(root, name, enabled) {
		const node = input(root, name);
		if (!node) return;
		const active = Boolean(enabled);
		if (node.readOnly !== active) node.readOnly = active;
		if (node.hasAttribute("aria-readonly") !== active) node.toggleAttribute("aria-readonly", active);
		if (node.tagName === "SELECT" && node.disabled !== active) node.disabled = active;
	}

	function showField(root, name, visible) {
		const node = field(root, name);
		if (!node) return;
		const hidden = !visible;
		const display = visible ? "block" : "none";
		if (node.hidden !== hidden) node.hidden = hidden;
		if (
			node.style.getPropertyValue("display") !== display ||
			node.style.getPropertyPriority("display") !== "important"
		)
			node.style.setProperty("display", display, "important");
	}

	function movement(root) {
		return read(root, "movement_code") || "101";
	}

	function context(root) {
		const movementCode = movement(root);
		return {
			movementCode,
			project: read(root, "project"),
			currency: read(root, "currency") || "HNL",
			channel: read(root, model.channelField(movementCode)),
			counterparty: read(root, model.counterpartyField(movementCode)),
		};
	}

	function markup() {
		return `<section class="nxr-guided-wizard" aria-label="${__("Registro guiado de operación")}">
			<ol class="nxr-guided-progress" aria-label="${__("Etapas")}">
				<li><button type="button" data-guided-go="1" aria-current="step"><span>1</span>${__(
					"Datos principales"
				)}</button></li>
				<li><button type="button" data-guided-go="2"><span>2</span>${__("Datos necesarios")}</button></li>
				<li><button type="button" data-guided-go="3"><span>3</span>${__("Revisión")}</button></li>
				<li><button type="button" data-guided-go="4"><span>4</span>${__("Registro definitivo")}</button></li>
			</ol>
			<section class="nxr-guided-stage" data-guided-stage="1"><header tabindex="-1"><p>${__("ETAPA 1")}</p><h3>${__(
			"Datos principales"
		)}</h3><span>${__(
			"Complete la información esencial."
		)}</span></header><div class="nxr-guided-fields" data-guided-fields="primary"></div><div class="nxr-guided-stage-actions"><button type="button" class="btn btn-primary" data-guided-next="2">${__(
			"Continuar"
		)}</button></div></section>
			<section class="nxr-guided-stage" data-guided-stage="2" hidden><header tabindex="-1"><p>${__(
				"ETAPA 2"
			)}</p><h3>${__("Datos necesarios")}</h3><span>${__(
			"Solo se muestra lo que aplica a esta operación."
		)}</span></header><div class="nxr-guided-account" aria-live="polite"></div><div class="nxr-guided-fields" data-guided-fields="conditional"></div><div class="nxr-guided-funds"></div><div class="nxr-guided-stage-actions"><button type="button" class="btn btn-default" data-guided-back="1">${__(
			"Atrás"
		)}</button><button type="button" class="btn btn-primary nxr-guided-preview">${__(
			"Revisar operación"
		)}</button></div></section>
			<section class="nxr-guided-stage" data-guided-stage="3" hidden><header tabindex="-1"><p>${__(
				"ETAPA 3"
			)}</p><h3>${__("Revisión")}</h3><span>${__(
			"Compruebe el efecto financiero antes de registrar."
		)}</span></header><div class="nxr-guided-review nxr-empty">${__(
			"Genere una revisión válida."
		)}</div><div class="nxr-guided-stage-actions"><button type="button" class="btn btn-default" data-guided-back="2">${__(
			"Corregir datos"
		)}</button><button type="button" class="btn btn-primary" data-guided-next="4" disabled>${__(
			"Continuar al registro"
		)}</button></div></section>
			<section class="nxr-guided-stage" data-guided-stage="4" hidden><header tabindex="-1"><p>${__(
				"ETAPA 4"
			)}</p><h3>${__("Registro definitivo")}</h3><span>${__(
			"NEXORA esperará la confirmación del servidor."
		)}</span></header><div class="alert alert-warning">${__(
			"El documento ejecutado conservará auditoría y se corregirá mediante movimientos relacionados."
		)}</div><div class="nxr-guided-final-status" role="status"></div><div class="nxr-guided-stage-actions"><button type="button" class="btn btn-default" data-guided-back="3">${__(
			"Volver"
		)}</button><button type="button" class="btn btn-primary nxr-guided-execute" disabled>${__(
			"Registrar definitivamente"
		)}</button></div></section>
			<details class="nxr-guided-advanced"><summary>${__("Opciones avanzadas")}</summary><p class="text-muted">${__(
			"Clasificación detallada, responsables y datos documentales complementarios."
		)}</p><div class="nxr-guided-fields" data-guided-fields="advanced"></div><div class="nxr-guided-line-detail"></div></details>
		</section>`;
	}

	function stateFor(root) {
		let state = states.get(root);
		if (state) return state;
		state = {
			stage: 1,
			accounts: [],
			choice: "other",
			save: false,
			selected: "",
			draft: {},
			origins: new Map(),
			request: 0,
			timer: null,
			contextKey: "",
			previewRequested: false,
			movement: "",
		};
		states.set(root, state);
		q(root, ".nxr-transaction")?.insertAdjacentHTML("afterbegin", markup());
		state.wizard = q(root, ".nxr-guided-wizard");
		bind(root, state);
		return state;
	}

	function remember(state, node) {
		if (!node || state.origins.has(node)) return;
		state.origins.set(node, { parent: node.parentNode, next: node.nextSibling });
	}

	function move(state, node, target) {
		if (!node || !target || node.parentNode === target) return;
		remember(state, node);
		target.appendChild(node);
	}

	function activate(state, number, focus = true) {
		state.stage = Math.min(Math.max(Number(number) || 1, 1), 4);
		qa(state.wizard, "[data-guided-stage]").forEach((node) => {
			const hidden = Number(node.dataset.guidedStage) !== state.stage;
			if (node.hidden !== hidden) node.hidden = hidden;
		});
		qa(state.wizard, "[data-guided-go]").forEach((node) => {
			const current = Number(node.dataset.guidedGo) === state.stage;
			if (node.hasAttribute("aria-current") !== current) node.toggleAttribute("aria-current", current);
		});
		if (focus) q(state.wizard, `[data-guided-stage="${state.stage}"] > header`)?.focus();
	}

	function validatePrimary(root, state) {
		const required =
			movement(root) === "101"
				? ["document_date", "project", "origin_or_sender", "channel", "original_amount", "currency"]
				: ["document_date", "project", "beneficiary", "description", "amount_hnl", "currency"];
		const missing = required.filter((name) => !read(root, name));
		qa(state.wizard, ".nxr-guided-primary-error").forEach((node) =>
			node.classList.remove("nxr-guided-primary-error")
		);
		missing.forEach((name) => field(root, name)?.classList.add("nxr-guided-primary-error"));
		if (!missing.length) return true;
		input(root, missing[0])?.focus();
		frappe.show_alert({ message: __("Complete los datos principales señalados."), indicator: "orange" });
		return false;
	}

	function revealFirstError(root, state) {
		const invalid = q(root, ".nxr-field-invalid, .has-error");
		if (!invalid) return;
		const wrapper = invalid.closest("[data-field]") || invalid;
		const name = wrapper.dataset?.field;
		const stage = model.fieldStage(movement(root), name);
		if (stage === "advanced") q(state.wizard, ".nxr-guided-advanced").open = true;
		else activate(state, Number(stage) || 2, false);
		(input(root, name) || q(invalid, "input,select,textarea"))?.focus();
	}

	function bind(root, state) {
		state.wizard.addEventListener("click", (event) => {
			const go = event.target.closest("[data-guided-go],[data-guided-next],[data-guided-back]");
			if (go) {
				const target = Number(go.dataset.guidedGo || go.dataset.guidedNext || go.dataset.guidedBack);
				if (target === 2 && go.hasAttribute("data-guided-next") && !validatePrimary(root, state))
					return;
				if (target === 4 && go.disabled) return;
				activate(state, target);
				return;
			}
			if (event.target.closest(".nxr-guided-preview")) {
				state.previewRequested = true;
				q(root, ".nxr-preview-movement")?.click();
				setTimeout(() => revealFirstError(root, state), 0);
			}
			if (event.target.closest(".nxr-guided-execute")) {
				const original = q(root, ".nxr-execute-movement");
				if (original && !original.disabled && original.getAttribute("aria-busy") !== "true")
					original.click();
			}
		});
		state.wizard.addEventListener("change", (event) => {
			const choice = event.target.closest("[name='nxr-guided-account-choice']");
			if (choice) switchChoice(root, state, choice.value);
			const save = event.target.closest("[name='nxr-guided-save-account']");
			if (save) {
				state.save = save.value === "yes";
				applyMode(root, state);
				conditional(root, state);
			}
			const selected = event.target.closest("[data-guided-saved-account]");
			if (selected) void selectAccount(root, state, selected.value);
		});
		root.addEventListener("input", (event) => {
			const name = event.target.closest("[data-field]")?.dataset.field;
			if (
				[
					"project",
					"currency",
					"channel",
					"payment_method",
					"origin_or_sender",
					"beneficiary",
				].includes(name)
			)
				refreshAccounts(root, state);
			if (
				["currency", "channel", "payment_method", "original_amount", "exchange_rate"].includes(name)
			) {
				conditional(root, state);
				convertExpense(root);
			}
		});
	}

	function moveFields(root, state, code) {
		const targets = {
			primary: q(state.wizard, "[data-guided-fields='primary']"),
			conditional: q(state.wizard, "[data-guided-fields='conditional']"),
			advanced: q(state.wizard, "[data-guided-fields='advanced']"),
		};
		(model.PRIMARY_FIELDS[code] || []).forEach((name) => move(state, field(root, name), targets.primary));
		(model.CONDITIONAL_FIELDS[code] || []).forEach((name) =>
			move(state, field(root, name), targets.conditional)
		);
		model.ADVANCED_FIELDS.forEach((name) => move(state, field(root, name), targets.advanced));
		const technicalMode = field(root, "account_mode");
		const savedControl = field(root, "financial_account");
		if (technicalMode) technicalMode.hidden = true;
		if (savedControl) savedControl.hidden = true;
		move(state, q(root, ".nxr-line-section"), q(state.wizard, ".nxr-guided-line-detail"));
		qa(
			root,
			".nxr-document-tabs,.nxr-document-panel,.nxr-detail-tabs,.nxr-detail-panel,.nxr-operational-actions,.nxr-operational-preview"
		).forEach((node) => node.classList.add("nxr-guided-legacy-hidden"));
	}

	function accountMarkup(state) {
		const has = state.accounts.length > 0;
		if (!has) state.choice = "other";
		const options = state.accounts
			.map(
				(row) =>
					`<option value="${frappe.utils.escape_html(row.name)}"${
						row.name === state.selected ? " selected" : ""
					}>${frappe.utils.escape_html(row.label || row.account_name || row.name)}</option>`
			)
			.join("");
		return `<section class="nxr-human-account-selector"><header><strong>${__(
			"Cuenta para esta operación"
		)}</strong><span>${
			has
				? __("Seleccione una cuenta compatible o use otros datos bancarios.")
				: __("No hay cuentas compatibles. Complete los datos bancarios.")
		}</span></header>
			${
				has
					? `<div class="nxr-human-choice" role="radiogroup"><label><input type="radio" name="nxr-guided-account-choice" value="saved"${
							state.choice === "saved" ? " checked" : ""
					  }> <span>${__(
							"Seleccionar una cuenta guardada"
					  )}</span></label><label><input type="radio" name="nxr-guided-account-choice" value="other"${
							state.choice !== "saved" ? " checked" : ""
					  }> <span>${__(
							"Usar otros datos bancarios"
					  )}</span></label></div><label class="nxr-guided-saved-row"${
							state.choice === "saved" ? "" : " hidden"
					  }><span>${__(
							"Cuenta guardada"
					  )}</span><select class="form-control" data-guided-saved-account><option value="">${__(
							"Seleccione una cuenta"
					  )}</option>${options}</select></label>`
					: ""
			}
			<div class="nxr-save-account-question"${state.choice === "saved" ? " hidden" : ""}><strong>${__(
			"¿Desea guardar esta cuenta para utilizarla nuevamente?"
		)}</strong><div class="nxr-human-choice" role="radiogroup"><label><input type="radio" name="nxr-guided-save-account" value="yes"${
			state.save ? " checked" : ""
		}> <span>${__(
			"Sí, guardar para el futuro"
		)}</span></label><label><input type="radio" name="nxr-guided-save-account" value="no"${
			state.save ? "" : " checked"
		}> <span>${__(
			"No, usar solo esta vez"
		)}</span></label></div></div><p class="nxr-guided-account-status" role="status"></p></section>`;
	}

	function renderAccounts(state) {
		const target = q(state.wizard, ".nxr-guided-account");
		if (!target) return;
		const signature = JSON.stringify({
			accounts: state.accounts.map((row) => [row.name, row.label, row.account_name]),
			choice: state.choice,
			save: state.save,
			selected: state.selected,
		});
		if (target.dataset.accountSignature === signature) return;
		target.innerHTML = accountMarkup(state);
		target.dataset.accountSignature = signature;
	}

	function applyMode(root, state) {
		const mode = model.deriveInternalMode({
			choice: state.choice,
			saveForFuture: state.save,
			hasAccounts: state.accounts.length > 0,
		});
		write(root, "account_mode", mode);
		if (mode !== "Existing") write(root, "financial_account", "");
		const locked = mode === "Existing";
		["institution", "account_reference", "currency", model.channelField(movement(root))].forEach((name) =>
			readonly(root, name, locked)
		);
	}

	function switchChoice(root, state, choice) {
		if (state.choice !== "saved")
			state.draft = {
				institution: read(root, "institution"),
				account_reference: read(root, "account_reference"),
				account_name: read(root, "account_name"),
			};
		state.choice = choice === "saved" && state.accounts.length ? "saved" : "other";
		if (state.choice === "other") {
			state.selected = "";
			write(root, "financial_account", "");
			Object.entries(state.draft).forEach(([name, value]) => write(root, name, value));
		}
		applyMode(root, state);
		renderAccounts(state);
		conditional(root, state);
	}

	async function selectAccount(root, state, name) {
		state.selected = name || "";
		if (!name) return;
		const ctx = context(root);
		try {
			const response = await frappe.call({
				method: "nexora.financial.service.get_financial_account",
				type: "POST",
				args: {
					account: name,
					project: ctx.project,
					direction: model.movementDirection(ctx.movementCode),
					currency: ctx.currency || null,
					channel: ctx.channel || null,
					counterparty: ctx.counterparty || null,
				},
			});
			const row = response.message || {};
			write(root, "account_mode", "Existing");
			write(root, "financial_account", name);
			write(root, model.counterpartyField(ctx.movementCode), row.origin_or_sender || "");
			write(root, "institution", row.institution || "");
			write(root, "account_reference", row.account_reference || "");
			write(root, "currency", row.currency || "HNL");
			write(root, model.channelField(ctx.movementCode), row.default_channel || "Other", true);
			applyMode(root, state);
			q(state.wizard, ".nxr-guided-account-status").textContent = __(
				"Cuenta compatible aplicada: {0}",
				[row.masked_account_reference || row.account_name || name]
			);
			conditional(root, state);
		} catch (error) {
			state.choice = "other";
			state.selected = "";
			write(root, "financial_account", "");
			applyMode(root, state);
			renderAccounts(state);
			window.nexora.ui?.showError?.(error, {
				title: __("No puede utilizarse esa cuenta"),
				fallback: __("Use una cuenta compatible o complete otros datos bancarios."),
			});
		}
	}

	function refreshAccounts(root, state, force = false) {
		const ctx = context(root);
		const key = JSON.stringify(ctx);
		if (!force && key === state.contextKey) return;
		clearTimeout(state.timer);
		state.timer = setTimeout(() => void loadAccounts(root, state, ctx, key, force), 180);
	}

	async function loadAccounts(root, state, ctx, key, force) {
		if (!force && key === state.contextKey) return;
		state.contextKey = key;
		if (!ctx.project) {
			state.accounts = [];
			renderAccounts(state);
			applyMode(root, state);
			return;
		}
		const request = ++state.request;
		try {
			const response = await frappe.call({
				method: "nexora.financial.service.list_financial_accounts",
				type: "POST",
				args: {
					project: ctx.project,
					direction: model.movementDirection(ctx.movementCode),
					currency: ctx.currency || null,
					channel: ctx.channel || null,
					counterparty: ctx.counterparty || null,
				},
			});
			if (request !== state.request) return;
			state.accounts = model.compatibleAccounts(response.message || [], ctx);
			if (!state.accounts.some((row) => row.name === state.selected)) {
				state.selected = "";
				state.choice = "other";
			}
			renderAccounts(state);
			applyMode(root, state);
			conditional(root, state);
		} catch (_error) {
			state.accounts = [];
			state.choice = "other";
			renderAccounts(state);
			applyMode(root, state);
			q(state.wizard, ".nxr-guided-account-status").textContent = __(
				"No fue posible consultar cuentas autorizadas."
			);
		}
	}

	function conditional(root, state) {
		const code = movement(root);
		const visible = model.conditionalVisibility({
			movementCode: code,
			channel: read(root, model.channelField(code)),
			currency: read(root, "currency") || "HNL",
			accountMode: read(root, "account_mode") || "Manual",
		});
		Object.entries({
			institution: visible.showInstitution,
			account_reference: visible.showAccountReference,
			external_reference: visible.showExternalReference,
			exchange_rate: visible.showExchangeRate,
			original_amount: visible.showOriginalAmount,
			account_name: state.choice !== "saved" && visible.showAccountName,
			evidence: visible.showEvidence,
			economic_category: visible.showClassification,
			cost_center: visible.showClassification,
			payment_method: code === "102",
		}).forEach(([name, value]) => showField(root, name, Boolean(value)));
		const allocation = q(root, ".nxr-allocation-panel");
		if (code === "102" && allocation) {
			move(state, allocation, q(state.wizard, ".nxr-guided-funds"));
			allocation.hidden = false;
		} else if (allocation) allocation.hidden = true;
		if (!visible.showInstitution && state.choice !== "saved") write(root, "institution", "");
		if (!visible.showAccountReference && state.choice !== "saved") write(root, "account_reference", "");
		applyMode(root, state);
	}

	function convertExpense(root) {
		if (movement(root) !== "102" || read(root, "currency").toUpperCase() === "HNL") return;
		const original = Number(read(root, "original_amount") || 0);
		const rate = Number(read(root, "exchange_rate") || 0);
		if (original > 0 && rate > 0) write(root, "amount_hnl", (original * rate).toFixed(2), true);
	}

	function sync(root, state) {
		const preview = q(root, ".nxr-preview-body");
		const originalExecute = q(root, ".nxr-execute-movement");
		const valid = Boolean(
			preview &&
				originalExecute &&
				!originalExecute.disabled &&
				!preview.classList.contains("nxr-empty")
		);
		const review = q(state.wizard, ".nxr-guided-review");
		if (review && preview) {
			review.classList.toggle("nxr-empty", !valid);
			const reviewHtml = valid
				? preview.innerHTML
				: frappe.utils.escape_html(preview.textContent || __("Genere una revisión válida."));
			if (review.innerHTML !== reviewHtml) review.innerHTML = reviewHtml;
		}
		const next = q(state.wizard, '[data-guided-next="4"]');
		if (next.disabled === valid) next.disabled = !valid;
		const execute = q(state.wizard, ".nxr-guided-execute");
		if (execute.disabled === valid) execute.disabled = !valid;
		const busy = originalExecute?.getAttribute("aria-busy") || "false";
		if (execute.getAttribute("aria-busy") !== busy) execute.setAttribute("aria-busy", busy);
		const status = q(root, ".nxr-action-status")?.textContent || "";
		const finalStatus = q(state.wizard, ".nxr-guided-final-status");
		if (finalStatus.textContent !== status) finalStatus.textContent = status;
		if (valid && state.previewRequested) {
			state.previewRequested = false;
			activate(state, 3);
		}
		if (!valid && state.stage > 2) activate(state, 2, false);
	}

	function enhance() {
		const root = shell();
		if (!root || root.dataset.state === "loading") return;
		const code = movement(root);
		if (!["101", "102"].includes(code)) return;
		const state = stateFor(root);
		root.classList.add("nxr-guided-active");
		moveFields(root, state, code);
		if (state.movement !== code) {
			state.movement = code;
			state.choice = "other";
			state.selected = "";
			state.contextKey = "";
			activate(state, 1, false);
		}
		applyMode(root, state);
		conditional(root, state);
		renderAccounts(state);
		refreshAccounts(root, state);
		sync(root, state);
	}

	function schedule() {
		if (scheduled) return;
		scheduled = true;
		requestAnimationFrame(() => {
			scheduled = false;
			enhance();
		});
	}

	function install() {
		observer?.disconnect();
		observer = new MutationObserver(schedule);
		observer.observe(document.documentElement, {
			childList: true,
			subtree: true,
			characterData: true,
			attributes: true,
			attributeFilter: ["disabled", "aria-busy", "class"],
		});
		frappe.router?.on?.("change", schedule);
		document.addEventListener("nexora:data-changed", () => {
			const root = shell();
			const state = root && states.get(root);
			if (state) {
				state.previewRequested = false;
				activate(state, 1, false);
				refreshAccounts(root, state, true);
			}
			schedule();
		});
		schedule();
	}

	window.nexora.guidedOperations = Object.freeze({ enhance: schedule, movementContext: context });
	if (typeof frappe.ready === "function") frappe.ready(install);
	else install();
})();
