(() => {
	"use strict";

	const PAYMENT_LABELS = {
		draft: "Borrador",
		pending_approval: "Pendiente de aprobación",
		approved: "Aprobado",
		partially_paid: "Pago parcial",
		paid: "Pagado",
		overdue: "Vencido",
		cancelled: "Anulado",
		reimbursed: "Reembolsado",
	};

	function amount(frm, fieldname) {
		return frappe.utils.flt(frm.doc[fieldname] || 0);
	}

	function calculate(frm) {
		if (!frm.fields_dict.subtotal_hnl) return;
		const subtotal = amount(frm, "subtotal_hnl") || amount(frm, "amount_hnl");
		const total = Math.max(
			subtotal + amount(frm, "tax_hnl") - amount(frm, "withholding_hnl") - amount(frm, "discount_hnl"),
			0
		);
		const paid = Math.min(amount(frm, "paid_amount_hnl"), total);
		frm.set_value("calculated_total_hnl", total);
		frm.set_value("amount_hnl", total);
		frm.set_value("balance_due_hnl", Math.max(total - paid, 0));
	}

	function updateRequirements(frm) {
		const paymentStatus = frm.doc.payment_status || "draft";
		const approval = frm.doc.professional_approval_status || "draft";
		frm.toggle_reqd("rejection_reason", approval === "rejected");
		frm.toggle_reqd("payment_reference", paymentStatus === "paid");
		frm.toggle_reqd("payment_date", paymentStatus === "paid");
		frm.set_df_property(
			"approved_amount_hnl",
			"description",
			approval === "approved" ? "Monto congelado al aprobar" : "Se completa al aprobar"
		);
	}

	function addActions(frm) {
		if (frm.is_new()) return;
		if (["draft", "pending"].includes(frm.doc.professional_approval_status || "draft")) {
			frm.add_custom_button(
				"Enviar a aprobación",
				() => {
					frm.set_value("professional_approval_status", "pending");
					frm.set_value("payment_status", "pending_approval");
					frm.save();
				},
				"Flujo de gasto"
			);
		}
		if (frappe.user.has_role("System Manager") || frappe.user.has_role("ConstruControl Manager")) {
			if (frm.doc.professional_approval_status === "pending") {
				frm.add_custom_button(
					"Aprobar",
					() => {
						frm.set_value("professional_approval_status", "approved");
						frm.set_value("payment_status", "approved");
						frm.save();
					},
					"Flujo de gasto"
				);
				frm.add_custom_button(
					"Rechazar",
					() => {
						frappe.prompt(
							[{ fieldname: "reason", fieldtype: "Small Text", label: "Motivo", reqd: 1 }],
							(values) => {
								frm.set_value("rejection_reason", values.reason);
								frm.set_value("professional_approval_status", "rejected");
								frm.save();
							},
							"Rechazar gasto",
							"Confirmar"
						);
					},
					"Flujo de gasto"
				);
			}
		}
		frm.add_custom_button(
			"Ver cuentas por pagar",
			() => frappe.set_route("List", "CC Payable Control"),
			"ConstruControl"
		);
	}

	function addSummary(frm) {
		const field = frm.fields_dict.payment_control_section;
		if (!field?.$wrapper || frm.is_new()) return;
		const status = PAYMENT_LABELS[frm.doc.payment_status] || frm.doc.payment_status || "Borrador";
		const total = format_currency(frm.doc.calculated_total_hnl || frm.doc.amount_hnl || 0, "HNL");
		const paid = format_currency(frm.doc.paid_amount_hnl || 0, "HNL");
		const balance = format_currency(frm.doc.balance_due_hnl || 0, "HNL");
		field.$wrapper.find(".cc-expense-summary").remove();
		field.$wrapper.append(
			`<div class="cc-expense-summary"><div><span>Estado</span><strong>${frappe.utils.escape_html(
				status
			)}</strong></div><div><span>Total</span><strong>${total}</strong></div><div><span>Pagado</span><strong>${paid}</strong></div><div><span>Saldo</span><strong>${balance}</strong></div></div>`
		);
	}

	frappe.ui.form.on("CC Expense Control", {
		refresh(frm) {
			calculate(frm);
			updateRequirements(frm);
			addActions(frm);
			addSummary(frm);
		},
		subtotal_hnl: calculate,
		tax_hnl: calculate,
		withholding_hnl: calculate,
		discount_hnl: calculate,
		paid_amount_hnl: calculate,
		payment_status(frm) {
			updateRequirements(frm);
			calculate(frm);
		},
		professional_approval_status: updateRequirements,
	});
})();
