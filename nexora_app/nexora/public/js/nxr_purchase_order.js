frappe.ui.form.on("NXR Purchase Order", {
	refresh(frm) {
		if (!frm.doc.name || !["Sent", "Completed"].includes(frm.doc.status)) return;
		if (!frm.doc.financial_commitment) return;
		if (!frm.doc.project || !frm.doc.supplier_entity) return;
		frm.add_custom_button(
			__("Registrar pago"),
			() => {
				const dialog = new frappe.ui.Dialog({
					title: __("Registrar pago de compra"),
					fields: [
						{
							fieldname: "amount_hnl",
							label: __("Importe HNL"),
							fieldtype: "Currency",
							reqd: 1,
							default: 0,
							options: "HNL",
						},
						{
							fieldname: "economic_category",
							label: __("Clasificación económica"),
							fieldtype: "Data",
							reqd: 1,
						},
						{ fieldname: "evidence", label: __("Evidencia"), fieldtype: "Attach" },
						{ fieldname: "description", label: __("Descripción"), fieldtype: "Small Text" },
					],
					primary_action_label: __("Ejecutar pago"),
					primary_action(values) {
						frappe
							.call({
								method: "nexora.purchases.financial_bridge.pay_purchase_order",
								type: "POST",
								args: {
									payload: {
										purchase_order: frm.doc.name,
										amount_hnl: values.amount_hnl,
										economic_category: values.economic_category,
										evidence: values.evidence,
										description: values.description,
										idempotency_key: `purchase-payment-${frm.doc.name}-${Date.now()}`,
									},
								},
								freeze: true,
								freeze_message: __("Registrando pago en el Libro Central…"),
							})
							.then((response) => {
								dialog.hide();
								frappe.show_alert({
									message: __("Pago registrado correctamente."),
									indicator: "green",
								});
								frm.reload_doc();
								if (response.message?.name)
									frappe.set_route("Form", "NXR Operation", response.message.name);
							})
							.catch((error) => {
								window.nexora?.ui?.showError?.(error, {
									title: __("No fue posible ejecutar el pago"),
									fallback: __("Revise la recepción, compromiso, fondo y permisos."),
								});
							});
					},
				});
				dialog.show();
			},
			__("Finanzas")
		);
	},
});
