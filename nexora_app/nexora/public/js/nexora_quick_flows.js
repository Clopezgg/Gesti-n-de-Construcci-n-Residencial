frappe.provide("nexora");

(() => {
	const guidedContextKey = "nexora:guided-operation-context";
	const escapedCurrencyMarkup = /^\s*<div\b[^>]*>\s*([^<]+?)\s*<\/div>\s*$/i;
	const executionKeys = new Map();
	let executionInFlight = false;
	let observer = null;

	function routeName() {
		return String((frappe.get_route?.() || [])[0] || "").toLowerCase();
	}

	function uuid() {
		return (
			globalThis.crypto?.randomUUID?.() || `nxr-${Date.now()}-${Math.random().toString(16).slice(2)}`
		);
	}

	function normalizeDashboardCurrency(root = document) {
		root.querySelectorAll?.(
			"#page-nexora-dashboard [data-currency], #page-nexora-dashboard .nxr-pending-total"
		).forEach((node) => {
			const match = String(node.textContent || "")
				.trim()
				.match(escapedCurrencyMarkup);
			if (match) node.textContent = match[1].trim();
		});
	}

	function activeContext() {
		const current = window.nexora.context?.get?.() || {};
		return {
			project: current.project || frappe.route_options?.project || null,
			period: current.period || null,
			from_date: current.from_date || null,
			to_date: current.to_date || null,
		};
	}

	function saveGuidedContext(context) {
		try {
			window.sessionStorage?.setItem(guidedContextKey, JSON.stringify(context));
		} catch (error) {
			console.warn("NEXORA could not persist guided operation context", error);
		}
	}

	function readGuidedContext() {
		try {
			return JSON.parse(window.sessionStorage?.getItem(guidedContextKey) || "null");
		} catch (error) {
			console.warn("NEXORA guided operation context is invalid", error);
			return null;
		}
	}

	function clearGuidedContext() {
		try {
			window.sessionStorage?.removeItem(guidedContextKey);
		} catch (error) {
			console.warn("NEXORA could not clear guided operation context", error);
		}
	}

	function openOperationalFlow(movementCode) {
		const context = { ...activeContext(), movement_code: movementCode };
		saveGuidedContext(context);
		frappe.route_options = {
			movement_code: movementCode,
			guided: movementCode === "101" ? "income" : "expense",
			project: context.project,
			from_date: context.from_date,
			to_date: context.to_date,
			nexora_period: context.period,
		};
		frappe.set_route("nexora-operations");
	}

	function replaceLegacyFinanceCards(root = document) {
		if (routeName() !== "nexora-finance") return;
		const income = root.querySelector?.("#page-nexora-finance .nxr-source-create");
		if (income && income.dataset.unifiedIncome !== "ready") {
			income.dataset.unifiedIncome = "ready";
			income.innerHTML = `<h3>${__("Registrar ingreso")}</h3><p class="text-muted">${__(
				"Use el formulario único con cuenta, moneda, vista previa y confirmación financiera."
			)}</p><button type="button" class="btn btn-primary" data-nexora-unified-income="1">${__(
				"Abrir ingreso"
			)}</button>`;
		}
		const expense = root.querySelector?.('#page-nexora-finance [data-operation="CONSTRUCTION_PAYMENT"]');
		if (expense) expense.setAttribute("data-nexora-unified-expense", "1");
	}

	function guidedCopy(code) {
		return code === "101"
			? {
					title: __("Registrar ingreso"),
					description: __(
						"Complete procedencia, cuenta e importe. NEXORA validará el efecto antes de registrar."
					),
					preview: __("Revisar ingreso"),
					execute: __("Registrar ingreso"),
					guide: __("El ingreso solo se guarda después de una vista previa válida."),
			  }
			: {
					title: __("Registrar gasto o pago"),
					description: __(
						"Indique beneficiario, clasificación, medio de pago y cómo se distribuirá entre los fondos."
					),
					preview: __("Revisar gasto"),
					execute: __("Registrar gasto"),
					guide: __(
						"La vista previa mostrará saldo anterior, importe afectado y saldo resultante de cada fondo."
					),
			  };
	}

	function revealAdvancedOperations(shell) {
		shell?.removeAttribute("data-guided-operation");
		shell?.querySelector(".nxr-movement-help")?.removeAttribute("hidden");
		shell?.querySelector('[data-field="movement_code"]')?.removeAttribute("hidden");
		shell?.querySelector(".nxr-guided-operation-guide")?.remove();
		clearGuidedContext();
	}

	function enhanceGuidedOperation(root = document) {
		if (routeName() !== "nexora-operations") return;
		const context = readGuidedContext();
		const code = String(context?.movement_code || "");
		if (!["101", "102"].includes(code)) return;
		const shell = root.querySelector?.("#page-nexora-operations .nxr-operational-shell");
		const active = shell?.querySelector(`.nxr-movement-chip[data-code="${code}"][aria-pressed="true"]`);
		if (!shell || !active || shell.dataset.guidedOperation === code) return;
		shell.dataset.guidedOperation = code;
		shell.setAttribute("data-guided-operation", code);
		shell.querySelector(".nxr-movement-help")?.setAttribute("hidden", "");
		shell.querySelector('[data-field="movement_code"]')?.setAttribute("hidden", "");
		const copy = guidedCopy(code);
		const title = shell.querySelector(".nxr-operational-title");
		if (title) title.textContent = copy.title;
		const description = shell.querySelector(".nxr-operational-header .text-muted");
		if (description) description.textContent = copy.description;
		const tabs = shell.querySelector(".nxr-document-tabs");
		if (tabs && !shell.querySelector(".nxr-guided-operation-guide")) {
			const guide = document.createElement("div");
			guide.className = "nxr-account-hint nxr-guided-operation-guide";
			guide.innerHTML = `<strong>${copy.title}</strong><br>${
				context.period ? __("Período activo: {0}.", [context.period]) : ""
			} ${
				copy.guide
			} <button type="button" class="btn btn-xs btn-default" data-nexora-operation-advanced="1">${__(
				"Ver operaciones avanzadas"
			)}</button>`;
			tabs.parentElement?.insertBefore(guide, tabs);
		}
		const preview = shell.querySelector(".nxr-preview-movement");
		const execute = shell.querySelector(".nxr-execute-movement");
		if (preview) preview.textContent = copy.preview;
		if (execute) execute.textContent = copy.execute;
		if (code === "102") shell.querySelector('[data-detail-tab="classification"]')?.click();
	}

	function normalizeDateInput(value) {
		const text = String(value || "").trim();
		if (!text) return "";
		try {
			return String(frappe.datetime.user_to_str?.(text) || text).slice(0, 10);
		} catch (_error) {
			return text.slice(0, 10);
		}
	}

	function validateActivePeriod(event) {
		const preview = event.target?.closest?.("#page-nexora-operations .nxr-preview-movement");
		if (!preview) return false;
		const context = readGuidedContext();
		if (!context?.from_date || !context?.to_date) return false;
		const field = document.querySelector('#page-nexora-operations [data-field="document_date"] input');
		const documentDate = normalizeDateInput(field?.value);
		if (!documentDate || (documentDate >= context.from_date && documentDate <= context.to_date))
			return false;
		event.preventDefault();
		event.stopPropagation();
		event.stopImmediatePropagation();
		frappe.msgprint({
			title: __("Fecha fuera del período activo"),
			message: __("Seleccione una fecha entre {0} y {1}, o cambie el período activo.", [
				frappe.datetime.str_to_user(context.from_date),
				frappe.datetime.str_to_user(context.to_date),
			]),
			indicator: "orange",
		});
		field?.focus();
		return true;
	}

	function financialExecutionButton() {
		return document.querySelector("#page-nexora-operations .nxr-execute-movement");
	}

	function setExecutionBusy(busy) {
		const button = financialExecutionButton();
		if (!button) return;
		button.disabled =
			Boolean(busy) ||
			!button.closest(".nxr-operational-shell")?.querySelector(".nxr-preview-body:not(.nxr-empty)");
		if (busy) button.setAttribute("aria-busy", "true");
		else button.removeAttribute("aria-busy");
	}

	function executionFingerprint(payload = {}) {
		const previewHash = String(payload.preview_hash || "").trim();
		if (!previewHash) return "";
		return `${String(payload.movement_code || "operation")}:${previewHash}`;
	}

	function installServerExecutionGuard() {
		if (frappe.call?.__nexoraExecutionGuard) return;
		const originalCall = frappe.call;
		const guardedCall = function (options, ...args) {
			const method = typeof options === "string" ? options : options?.method;
			if (method !== "nexora.financial.service.execute_operational_movement") {
				return originalCall.call(this, options, ...args);
			}
			const payload = options?.args?.payload || {};
			const fingerprint = executionFingerprint(payload);
			if (fingerprint) {
				const stableKey = executionKeys.get(fingerprint) || payload.idempotency_key || uuid();
				executionKeys.set(fingerprint, stableKey);
				payload.idempotency_key = stableKey;
			}
			if (executionInFlight) {
				frappe.show_alert({
					message: __("La operación ya se está registrando. Espere la respuesta del servidor."),
					indicator: "orange",
				});
				return Promise.reject(new Error("NEXORA_DUPLICATE_SUBMISSION_BLOCKED"));
			}
			executionInFlight = true;
			setExecutionBusy(true);
			let request;
			try {
				request = originalCall.call(this, options, ...args);
			} catch (error) {
				executionInFlight = false;
				setExecutionBusy(false);
				throw error;
			}
			return (async () => {
				try {
					const response = await request;
					if (fingerprint) executionKeys.delete(fingerprint);
					return response;
				} finally {
					executionInFlight = false;
					setExecutionBusy(false);
				}
			})();
		};
		guardedCall.__nexoraExecutionGuard = true;
		guardedCall.__nexoraOriginalCall = originalCall;
		frappe.call = guardedCall;
	}

	function preventDoubleExecution(event) {
		const button = event.target?.closest?.("#page-nexora-operations .nxr-execute-movement");
		if (!button || button.getAttribute("aria-busy") !== "true") return false;
		event.preventDefault();
		event.stopPropagation();
		event.stopImmediatePropagation();
		frappe.show_alert({ message: __("La operación ya se está registrando."), indicator: "orange" });
		return true;
	}

	function refreshGuidedContext(context) {
		const current = readGuidedContext();
		if (!current) return;
		saveGuidedContext({
			...current,
			project: context?.project || null,
			period: context?.period || null,
			from_date: context?.from_date || null,
			to_date: context?.to_date || null,
		});
	}

	function canManageDocuments() {
		return ["System Manager", "NEXORA Administrator", "NEXORA Finance Manager"].some((role) =>
			frappe.user.has_role(role)
		);
	}

	function documentPrintUrl(frm) {
		return `/printview?doctype=${encodeURIComponent(frm.doctype)}&name=${encodeURIComponent(
			frm.docname
		)}&trigger_print=1`;
	}

	function openOperationHistory(frm) {
		frappe.route_options = { project: frm.doc.project || null, show_ledger: 1 };
		frappe.set_route("nexora-operations");
	}

	function correctionActionLabel(code) {
		return {
			303: __("Anular operación"),
			304: __("Sustituir documento"),
			501: __("Revertir operación"),
		}[code];
	}

	function correctionExplanation(code) {
		return code === "304"
			? __(
					"El documento original se conservará y se creará una sustitución auditada con el comprobante nuevo."
			  )
			: __("El documento original se conservará y se creará un movimiento compensatorio auditado.");
	}

	function correctionPreviewHtml(preview) {
		const sources = (preview.sources || [])
			.map(
				(row) =>
					`<tr><td>${frappe.utils.escape_html(row.source || "")}</td><td>${
						window.nexora.ui?.formatMoney?.(row.balance_before_hnl) || row.balance_before_hnl
					}</td><td>${window.nexora.ui?.formatMoney?.(row.amount_hnl) || row.amount_hnl}</td><td>${
						window.nexora.ui?.formatMoney?.(row.balance_after_hnl) || row.balance_after_hnl
					}</td></tr>`
			)
			.join("");
		return `<div class="alert alert-info"><strong>${frappe.utils.escape_html(
			preview.movement_label || __("Corrección auditada")
		)}</strong><br>${__("El original no será eliminado ni sobrescrito.")}</div>${
			sources
				? `<div class="table-responsive"><table class="table table-bordered"><thead><tr><th>${__(
						"Fondo"
				  )}</th><th>${__("Saldo anterior")}</th><th>${__("Importe afectado")}</th><th>${__(
						"Saldo resultante"
				  )}</th></tr></thead><tbody>${sources}</tbody></table></div>`
				: ""
		}`;
	}

	function correctionActors(values) {
		const requester = String(values.requester || "").trim();
		const approvedBy = String(values.approved_by || "").trim();
		const executor = String(frappe.session.user || "").trim();
		// Aquí el ejecutor es la sesión activa, así que el mensaje puede tutear al usuario.
		// Faltar un actor y repetirlo se corrigen distinto, y se explican por separado.
		if (!requester || !approvedBy) {
			frappe.msgprint({
				title: __("Segregación obligatoria"),
				message: __(
					"Indique solicitante y aprobador. Junto con usted, que queda registrado " +
						"como ejecutor, deben ser tres usuarios distintos."
				),
				indicator: "orange",
			});
			return null;
		}
		if (new Set([requester, approvedBy, executor]).size !== 3) {
			frappe.msgprint({
				title: __("Segregación obligatoria"),
				message: __(
					"Solicitante, aprobador y ejecutor deben ser tres usuarios distintos. " +
						"Usted queda registrado como ejecutor, así que elija un solicitante y un " +
						"aprobador distintos de usted y entre sí."
				),
				indicator: "orange",
			});
			return null;
		}
		return { requester, approved_by: approvedBy };
	}

	function openControlledCorrection(frm, code) {
		if (!canManageDocuments()) {
			frappe.msgprint({
				title: __("Acción no autorizada"),
				message: __("Se requiere Gerente financiero o Administrador."),
				indicator: "red",
			});
			return;
		}
		const state = { preview: null, busy: false, idempotencyKey: "" };
		let dialog;
		const invalidate = () => {
			if (!dialog || state.busy) return;
			state.preview = null;
			state.idempotencyKey = "";
			dialog.fields_dict.preview.$wrapper.empty();
			dialog.set_primary_action(__("Vista previa"), preview);
		};
		dialog = new frappe.ui.Dialog({
			title: correctionActionLabel(code),
			fields: [
				{
					fieldname: "notice",
					fieldtype: "HTML",
					options: `<div class="alert alert-warning">${correctionExplanation(code)}</div>`,
				},
				{
					fieldname: "document",
					label: __("Documento original"),
					fieldtype: "Data",
					default: frm.doc.document_number || frm.docname,
					read_only: 1,
				},
				{
					fieldname: "requester",
					label: __("Solicitante"),
					fieldtype: "Link",
					options: "User",
					reqd: 1,
					description: __("Debe ser diferente del aprobador y del usuario que ejecuta."),
					onchange: invalidate,
				},
				{
					fieldname: "approved_by",
					label: __("Aprobador"),
					fieldtype: "Link",
					options: "User",
					reqd: 1,
					description: __("Debe ser diferente del solicitante y del usuario que ejecuta."),
					onchange: invalidate,
				},
				{
					fieldname: "reason",
					label: __("Motivo"),
					fieldtype: "Small Text",
					reqd: 1,
					description: __("Explique la razón con al menos 10 caracteres."),
					onchange: invalidate,
				},
				{
					fieldname: "evidence",
					label: code === "304" ? __("Comprobante sustituto") : __("Comprobante opcional"),
					fieldtype: "Attach",
					reqd: code === "304" ? 1 : 0,
					onchange: invalidate,
				},
				{ fieldname: "preview", fieldtype: "HTML" },
			],
		});

		function correctionPayload(values, actors) {
			return {
				movement_code: code,
				document_date: state.preview?.document_date || frappe.datetime.get_today(),
				project: frm.doc.project,
				reference_name: frm.docname,
				description: values.reason,
				reason: values.reason,
				evidence: values.evidence || "",
				...actors,
			};
		}

		async function preview() {
			const values = dialog.get_values();
			if (!values || state.busy) return;
			if (String(values.reason || "").trim().length < 10) {
				frappe.msgprint(__("Explique el motivo con al menos 10 caracteres."));
				return;
			}
			const actors = correctionActors(values);
			if (!actors) return;
			state.busy = true;
			try {
				const response = await frappe.call({
					method: "nexora.financial.service.preview_operational_movement",
					type: "POST",
					args: { payload: correctionPayload(values, actors) },
					freeze: true,
					freeze_message: __("Validando permisos, estado y efecto financiero…"),
				});
				state.preview = response.message;
				dialog.fields_dict.preview.$wrapper.html(correctionPreviewHtml(state.preview));
				dialog.set_primary_action(correctionActionLabel(code), execute);
			} catch (error) {
				window.nexora.ui?.showError?.(error, {
					title: __("No fue posible validar la corrección"),
					fallback: __("No se modificó el documento original."),
				});
			} finally {
				state.busy = false;
			}
		}

		async function execute() {
			if (!state.preview || state.busy) return preview();
			const values = dialog.get_values();
			if (!values) return;
			const actors = correctionActors(values);
			if (!actors) return;
			state.busy = true;
			state.idempotencyKey ||= uuid();
			dialog.get_primary_btn()?.prop("disabled", true).attr("aria-busy", "true");
			try {
				const response = await frappe.call({
					method: "nexora.financial.service.execute_operational_movement",
					type: "POST",
					args: {
						payload: {
							...correctionPayload(values, actors),
							preview_hash: state.preview.preview_hash,
							idempotency_key: state.idempotencyKey,
						},
					},
					freeze: true,
					freeze_message: __("Creando el documento relacionado y preservando auditoría…"),
				});
				dialog.hide();
				window.nexora.ui?.showSuccess?.({
					message: __("Corrección registrada"),
					documentNumber: response.message?.document_number || "",
				});
				await frm.reload_doc();
			} catch (error) {
				window.nexora.ui?.showError?.(error, {
					title: __("No fue posible registrar la corrección"),
					fallback: __("La transacción se revirtió y el documento original permanece sin cambios."),
				});
			} finally {
				state.busy = false;
				dialog.get_primary_btn()?.prop("disabled", false).removeAttr("aria-busy");
			}
		}

		dialog.set_primary_action(__("Vista previa"), preview);
		dialog.show();
	}

	function installOperationDocumentActions() {
		if (!frappe.ui?.form?.on) return;
		frappe.ui.form.on("NXR Operation", {
			refresh(frm) {
				const posted = ["Executed", "Compensated Partial", "Compensated Total"].includes(
					frm.doc.status
				);
				if (!posted) return;
				frm.add_custom_button(__("Ver historial"), () => openOperationHistory(frm), __("Documento"));
				frm.add_custom_button(
					__("Descargar"),
					() => window.open(documentPrintUrl(frm), "_blank", "noopener"),
					__("Documento")
				);
				if (!canManageDocuments() || frm.doc.status !== "Executed") return;
				if (frm.doc.operation_type === "Inflow" && window.nexora_open_operation_correction) {
					frm.add_custom_button(
						__("Corregir fecha o datos"),
						() => window.nexora_open_operation_correction(frm.doc.document_number, frm),
						__("Correcciones")
					);
					frm.add_custom_button(
						__("Corregir importe"),
						() => window.nexora_open_operation_correction(frm.doc.document_number, frm),
						__("Correcciones")
					);
				}
				frm.add_custom_button(
					__("Sustituir documento"),
					() => openControlledCorrection(frm, "304"),
					__("Correcciones")
				);
				frm.add_custom_button(
					__("Anular operación"),
					() => openControlledCorrection(frm, "303"),
					__("Correcciones")
				);
				frm.add_custom_button(
					__("Revertir operación"),
					() => openControlledCorrection(frm, "501"),
					__("Correcciones")
				);
			},
		});
	}

	function mobileCardValue(cell) {
		return String(cell?.textContent || "").trim() || __("Sin dato");
	}

	function tableToMobileCards(table, name) {
		if (!table) return;
		const headers = [...table.querySelectorAll("thead th")].map((cell) => mobileCardValue(cell));
		if (!headers.length) return;
		const rows = [...table.querySelectorAll("tbody tr")];
		const signature = rows.map((row) => row.innerHTML).join("\u241e");
		if (table.dataset.mobileSignature === signature) return;
		let cards = table.parentElement?.querySelector(`.nxr-mobile-cards[data-source="${name}"]`);
		if (!cards) {
			cards = document.createElement("section");
			cards.className = "nxr-mobile-cards";
			cards.dataset.source = name;
			cards.setAttribute("aria-label", __("Vista móvil de documentos"));
			table.parentElement?.appendChild(cards);
		}
		cards.innerHTML = rows
			.map((row) => {
				const cells = [...row.children];
				const fields = cells
					.map((cell, index) => {
						const label = headers[index] || __("Dato");
						const emphasis = ["Documento", "Importe", "Monto", "Estado"].some((key) =>
							label.includes(key)
						);
						return `<div class="nxr-mobile-card-field${
							emphasis ? " is-emphasis" : ""
						}"><span>${frappe.utils.escape_html(label)}</span><div>${
							cell.innerHTML || frappe.utils.escape_html(mobileCardValue(cell))
						}</div></div>`;
					})
					.join("");
				return `<article class="nxr-mobile-operation-card" role="group">${fields}</article>`;
			})
			.join("");
		table.dataset.mobileCards = "ready";
		table.dataset.mobileSignature = signature;
	}

	function enhanceMobileOperationalLists(root = document) {
		const tables = [
			["#page-nexora-dashboard .nxr-dashboard-recent-rows", "dashboard-recent"],
			["#page-nexora-operations .nxr-operational-ledger table", "operational-ledger"],
			["#page-nexora-operations .nxr-entry-table", "operational-entry"],
			["#page-nexora-search .nxr-search-results table", "search-results"],
		];
		for (const [selector, name] of tables) {
			root.querySelectorAll?.(selector).forEach((table) => tableToMobileCards(table, name));
		}
	}

	const visibleVocabulary = new Map([
		["Contabilizar", __("Registrar definitivamente")],
		["Código de movimiento", __("Tipo de movimiento")],
		["Cabecera del documento", __("Datos generales")],
		["Líneas del movimiento", __("Detalle del movimiento")],
		["Fuente de fondos", __("Fondo")],
		["Fuentes que pagarán", __("Fondos que cubrirán este pago")],
		["Cuenta frecuente existente", __("Cuenta guardada")],
		["Posted", __("Registrado definitivamente")],
		["Executed", __("Registrado definitivamente")],
		["Draft", __("Borrador")],
		["Pending", __("Pendiente")],
		["Approved", __("Aprobado")],
		["Cancelled", __("Anulado")],
	]);

	function normalizeVisibleVocabulary(root = document) {
		root.querySelectorAll?.('[id^="page-nexora"], .nxr-product-shell').forEach((surface) => {
			const walker = document.createTreeWalker(surface, NodeFilter.SHOW_TEXT);
			let node;
			while ((node = walker.nextNode())) {
				const current = String(node.nodeValue || "").trim();
				if (visibleVocabulary.has(current)) {
					node.nodeValue = node.nodeValue.replace(current, visibleVocabulary.get(current));
				}
			}
		});
	}

	function install() {
		const enhance = () => {
			normalizeDashboardCurrency(document);
			replaceLegacyFinanceCards(document);
			enhanceGuidedOperation(document);
			enhanceMobileOperationalLists(document);
			normalizeVisibleVocabulary(document);
		};
		observer?.disconnect();
		observer = new MutationObserver(() => window.requestAnimationFrame(enhance));
		observer.observe(document.documentElement, { childList: true, subtree: true, characterData: true });
		frappe.router?.on?.("change", () => window.requestAnimationFrame(enhance));
		enhance();
	}

	window.nexora.normalizeDashboardCurrency = normalizeDashboardCurrency;
	window.nexora.openIncomeFlow = () => openOperationalFlow("101");
	window.nexora.openIncomeDialog = window.nexora.openIncomeFlow;
	window.nexora.openExpenseFlow = () => openOperationalFlow("102");
	window.nexora.openExpenseDialog = window.nexora.openExpenseFlow;

	document.addEventListener(
		"click",
		(event) => {
			if (validateActivePeriod(event) || preventDoubleExecution(event)) return;
			const advanced = event.target?.closest?.("[data-nexora-operation-advanced]");
			if (advanced) {
				event.preventDefault();
				revealAdvancedOperations(advanced.closest(".nxr-operational-shell"));
				return;
			}
			const income = event.target?.closest?.(
				'.nxr-quick-income, [data-action="income"], [data-launch-income], [data-nexora-unified-income], .nxr-source-create button'
			);
			if (income && !income.closest("#page-nexora-operations")) {
				event.preventDefault();
				event.stopPropagation();
				event.stopImmediatePropagation();
				openOperationalFlow("101");
				return;
			}
			const expense = event.target?.closest?.(
				'.nxr-quick-expense, [data-action="expense"], [data-operation="CONSTRUCTION_PAYMENT"], [data-nexora-unified-expense]'
			);
			if (expense && !expense.closest("#page-nexora-operations")) {
				event.preventDefault();
				event.stopPropagation();
				event.stopImmediatePropagation();
				openOperationalFlow("102");
			}
		},
		true
	);

	document.addEventListener("nexora:context-changed", (event) => refreshGuidedContext(event.detail || {}));
	document.addEventListener("nexora:data-changed", (event) => {
		if (["101", "102"].includes(String(event.detail?.type || ""))) clearGuidedContext();
	});

	installServerExecutionGuard();
	installOperationDocumentActions();
	if (typeof frappe.ready === "function") frappe.ready(install);
	else install();
})();
