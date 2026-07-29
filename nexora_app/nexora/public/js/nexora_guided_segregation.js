frappe.provide("nexora");

(() => {
	"use strict";

	const selector = "#page-nexora-operations .nxr-operational-shell";
	let observer;
	let scheduled = false;

	function shell() {
		return document.querySelector(selector);
	}

	function field(root, name) {
		return root?.querySelector(`[data-field="${name}"]`);
	}

	function input(root, name) {
		return field(root, name)?.querySelector("input:not([type='hidden']),select,textarea");
	}

	function value(root, name) {
		return String(input(root, name)?.value || "").trim();
	}

	function activateStageTwo(root) {
		root.querySelector('.nxr-guided-progress [data-guided-go="2"]')?.click();
	}

	function clearErrors(root) {
		for (const name of ["requester", "approved_by"]) {
			field(root, name)?.classList.remove("nxr-guided-primary-error");
		}
	}

	function validateActors(root) {
		if (value(root, "movement_code") !== "102") return true;
		clearErrors(root);
		const requester = value(root, "requester");
		const approver = value(root, "approved_by");
		const executor = String(frappe.session.user || "").trim();
		const missing = [];
		if (!requester) missing.push("requester");
		if (!approver) missing.push("approved_by");
		if (missing.length) {
			activateStageTwo(root);
			for (const name of missing) field(root, name)?.classList.add("nxr-guided-primary-error");
			input(root, missing[0])?.focus();
			frappe.show_alert({
				message: __("Seleccione solicitante y aprobador antes de revisar el gasto."),
				indicator: "orange",
			});
			return false;
		}
		if (new Set([requester, approver, executor]).size !== 3) {
			activateStageTwo(root);
			field(root, "requester")?.classList.add("nxr-guided-primary-error");
			field(root, "approved_by")?.classList.add("nxr-guided-primary-error");
			input(root, requester === executor ? "requester" : "approved_by")?.focus();
			frappe.msgprint({
				title: __("Segregación obligatoria"),
				message: __(
					"Solicitante, aprobador y usuario que registra deben ser tres personas distintas."
				),
				indicator: "orange",
			});
			return false;
		}
		return true;
	}

	function enhance() {
		const root = shell();
		if (!root || value(root, "movement_code") !== "102") return;
		const target = root.querySelector('[data-guided-fields="conditional"]');
		if (!target) return;
		for (const name of ["requester", "approved_by"]) {
			const wrapper = field(root, name);
			if (!wrapper) continue;
			if (wrapper.parentElement !== target) target.appendChild(wrapper);
			wrapper.hidden = false;
			wrapper.style.setProperty("display", "block", "important");
		}
	}

	function schedule() {
		if (scheduled) return;
		scheduled = true;
		requestAnimationFrame(() => {
			scheduled = false;
			enhance();
		});
	}

	document.addEventListener(
		"click",
		(event) => {
			const preview = event.target.closest(`${selector} .nxr-guided-preview`);
			if (!preview) return;
			const root = preview.closest(".nxr-operational-shell");
			if (validateActors(root)) return;
			event.preventDefault();
			event.stopPropagation();
			event.stopImmediatePropagation();
		},
		true
	);

	function install() {
		observer?.disconnect();
		observer = new MutationObserver(schedule);
		observer.observe(document.documentElement, { childList: true, subtree: true });
		frappe.router?.on?.("change", schedule);
		schedule();
	}

	window.nexora.guidedSegregation = Object.freeze({ validateActors, enhance: schedule });
	if (typeof frappe.ready === "function") frappe.ready(install);
	else install();
})();
