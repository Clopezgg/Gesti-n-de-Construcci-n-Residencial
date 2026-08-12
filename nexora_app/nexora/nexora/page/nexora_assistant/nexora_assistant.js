// NEXORA · Asistente conversacional (Bloque 18, NXR-CNV-0001)
//
// Interfaz mínima real sobre el motor de `nexora.conversation.dispatch` — esta
// pantalla no interpreta nada por su cuenta: envía texto, pinta la respuesta
// y, cuando el motor devuelve `state === "AwaitingConfirmation"`, ofrece
// confirmar/cancelar contra la misma intención pendiente que el motor ya
// construyó. Ningún cálculo financiero ni permiso se decide aquí — todo
// viene de la respuesta real del servidor.
frappe.pages["nexora-assistant"].on_page_load = function (wrapper) {
	const page = frappe.ui.make_app_page({ parent: wrapper, title: __("Asistente"), single_column: true });
	const body = $(page.body);
	let sending = false;
	let resolving = false;

	body.html(`
		<main class="nxr-product-shell nxr-assistant-shell">
			<section class="nxr-ds-card nxr-assistant-card">
				<p class="nxr-assistant-hint">${__(
					'Prueba: "¿cuánto dinero tengo en Casa 04?", "¿qué pagos tengo pendientes?", "quiero pagar 2500 al electricista".'
				)}</p>
				<div class="nxr-assistant-messages" data-assistant-messages aria-live="polite"></div>
				<div class="nxr-assistant-pending" data-assistant-pending hidden></div>
				<form class="nxr-assistant-form" data-assistant-form>
					<input type="text" class="nxr-assistant-input" data-assistant-input
						placeholder="${__("Escribe tu mensaje…")}" autocomplete="off" />
					<button type="submit" class="nxr-ds-btn nxr-ds-btn--primary" data-assistant-send>${__("Enviar")}</button>
				</form>
			</section>
		</main>
	`);

	const messages = body.find("[data-assistant-messages]");
	const pendingBox = body.find("[data-assistant-pending]");
	const form = body.find("[data-assistant-form]");
	const input = body.find("[data-assistant-input]");

	function escape(value) {
		return window.nexora.ui.escapeHtml(value);
	}

	function addBubble(direction, text) {
		if (!text) return;
		const cls =
			direction === "Inbound"
				? "nxr-assistant-bubble nxr-assistant-bubble--user"
				: "nxr-assistant-bubble nxr-assistant-bubble--assistant";
		messages.append(`<p class="${cls}">${escape(text)}</p>`);
		messages.scrollTop(messages[0].scrollHeight);
	}

	function renderPending(data) {
		if (!data || !data.name) {
			pendingBox.attr("hidden", true).removeAttr("data-pending-intent").empty();
			return;
		}
		pendingBox.removeAttr("hidden").attr("data-pending-intent", data.name).html(`
				<button type="button" class="nxr-ds-btn nxr-ds-btn--primary" data-assistant-confirm>${__(
					"Confirmar"
				)}</button>
				<button type="button" class="nxr-ds-btn nxr-ds-btn--secondary" data-assistant-cancel>${__(
					"Cancelar"
				)}</button>
			`);
	}

	async function send(text) {
		if (sending) return;
		sending = true;
		addBubble("Inbound", text);
		try {
			const response = await frappe.call({
				method: "nexora.conversation.dispatch.send_message",
				type: "POST",
				args: { payload: { text } },
				freeze: false,
			});
			const result = response.message || {};
			addBubble("Outbound", result.message || "");
			renderPending(result.state === "AwaitingConfirmation" ? result.data : null);
		} catch (error) {
			window.nexora.ui.showError(error, {
				title: __("El asistente no pudo responder"),
				fallback: __("Intenta de nuevo en un momento."),
			});
		} finally {
			sending = false;
		}
	}

	async function resolvePending(method) {
		if (resolving) return;
		const name = pendingBox.attr("data-pending-intent");
		if (!name) return;
		resolving = true;
		pendingBox.find("[data-assistant-confirm], [data-assistant-cancel]").prop("disabled", true);
		try {
			const response = await frappe.call({
				method: `nexora.conversation.dispatch.${method}`,
				type: "POST",
				args: { payload: { pending_intent: name } },
				freeze: false,
			});
			const result = response.message || {};
			addBubble("Outbound", result.message || "");
			renderPending(null);
		} catch (error) {
			window.nexora.ui.showError(error, {
				title: __("No se pudo completar la acción"),
				fallback: __("Intenta de nuevo en un momento."),
			});
			pendingBox.find("[data-assistant-confirm], [data-assistant-cancel]").prop("disabled", false);
		} finally {
			resolving = false;
		}
	}

	form.on("submit", (event) => {
		event.preventDefault();
		const text = String(input.val() || "").trim();
		if (!text) return;
		input.val("");
		void send(text);
	});

	body.on("click", "[data-assistant-confirm]", () => void resolvePending("confirm_pending_intent"));
	body.on("click", "[data-assistant-cancel]", () => void resolvePending("cancel_pending_intent"));
};
