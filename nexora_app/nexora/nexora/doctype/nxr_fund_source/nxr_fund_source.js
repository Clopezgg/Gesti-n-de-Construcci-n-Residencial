frappe.ui.form.on("NXR Fund Source", {
	refresh(frm) {
		const canCancel = ["System Manager", "NEXORA Administrator", "NEXORA Finance Manager"].some(
			(role) => frappe.user_roles.includes(role)
		);
		if (frm.is_new() || !canCancel || !["Active", "Exhausted"].includes(frm.doc.status)) return;

		frm.add_custom_button(
			__("Anular ingreso"),
			() => openCancellationDialog(frm),
			__("Acciones")
		);
	},
});

function uuid() {
	return (
		globalThis.crypto?.randomUUID?.() ||
		`nxr-cancel-${Date.now()}-${Math.random().toString(16).slice(2)}`
	);
}

function openCancellationDialog(frm) {
	const dialog = new frappe.ui.Dialog({
		title: __("Anular ingreso"),
		fields: [
			{
				fieldtype: "HTML",
				options: `<div class="alert alert-warning">${__(
					"La anulación no borra el registro. NEXORA creará una operación compensatoria y conservará la trazabilidad. Solo procede cuando el ingreso no tiene gastos, reservas ni ajustes relacionados."
				)}</div>`,
			},
			{
				fieldname: "reason",
				label: __("Motivo de la anulación"),
				fieldtype: "Small Text",
				reqd: 1,
				description: __("Explique claramente qué dato fue ingresado de forma incorrecta."),
			},
		],
		primary_action_label: __("Confirmar anulación"),
		primary_action: async (values) => {
			const reason = String(values.reason || "").trim();
			if (reason.length < 10) {
				frappe.msgprint(__("El motivo debe tener al menos 10 caracteres."));
				return;
			}
			const confirmed = await new Promise((resolve) => {
				frappe.confirm(
					__("¿Confirma que desea anular el ingreso {0}?", [frm.doc.source_code || frm.doc.name]),
					() => resolve(true),
					() => resolve(false)
				);
			});
			if (!confirmed) return;

			dialog.get_primary_btn().prop("disabled", true);
			try {
				const response = await frappe.call({
					method: "nexora.financial.sources.cancel_fund_source",
					type: "POST",
					args: {
						source: frm.doc.name,
						reason,
						idempotency_key: uuid(),
					},
					freeze: true,
					freeze_message: __("Anulando ingreso y recalculando saldo…"),
				});
				dialog.hide();
				await frm.reload_doc();
				frappe.show_alert({
					message: __("Ingreso anulado. Operación compensatoria: {0}", [
						response.message?.document_number || "",
					]),
					indicator: "green",
				});
			} finally {
				dialog.get_primary_btn().prop("disabled", false);
			}
		},
	});
	dialog.show();
}
