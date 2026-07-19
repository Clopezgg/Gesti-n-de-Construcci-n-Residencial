(() => {
  "use strict";

  const CHANNEL_LABELS = {
    remittance: "Remesa",
    deposit: "Depósito",
    transfer: "Transferencia",
    cash: "Efectivo",
    other: "Otro ingreso",
  };

  function calculate(frm) {
    if (!frm.fields_dict.gross_amount) return;
    const gross = frappe.utils.flt(frm.doc.gross_amount || frm.doc.original_amount || frm.doc.amount_hnl || 0);
    const fee = frappe.utils.flt(frm.doc.fee_amount || 0);
    const currency = String(frm.doc.original_currency || frm.doc.currency || "HNL").toUpperCase();
    const rate = currency === "HNL" ? 1 : frappe.utils.flt(frm.doc.treasury_exchange_rate || frm.doc.exchange_rate || 1);
    const net = Math.max(gross - fee, 0);
    const netHnl = net * Math.max(rate, 0);
    frm.set_value("net_amount", net);
    frm.set_value("net_amount_hnl", netHnl);
    frm.set_value("amount_hnl", netHnl);
    if (frm.fields_dict.original_amount) frm.set_value("original_amount", gross);
    if (frm.fields_dict.exchange_rate) frm.set_value("exchange_rate", rate);
    if (frm.fields_dict.currency) frm.set_value("currency", currency);
  }

  function fallbackBadge(data, channel) {
    const name = data?.short_name || data?.institution_name || CHANNEL_LABELS[channel] || "Ingreso";
    const initials = String(name).split(/\s+/).slice(0, 2).map(part => part[0] || "").join("").toUpperCase();
    const color = data?.brand_color || "#175c4c";
    return `<div class="cc-institution-badge" style="--cc-institution-color:${frappe.utils.escape_html(color)}"><span class="cc-institution-mark">${frappe.utils.escape_html(initials)}</span><span><strong>${frappe.utils.escape_html(name)}</strong><small>${frappe.utils.escape_html(CHANNEL_LABELS[channel] || "Ingreso")}</small></span></div>`;
  }

  function renderInstitution(frm) {
    const field = frm.fields_dict.institution_brand_html;
    if (!field) return;
    const institution = frm.doc.financial_institution;
    const channel = frm.doc.transaction_channel;
    if (!institution) {
      field.$wrapper.html(fallbackBadge(null, channel));
      return;
    }
    frappe.xcall("erpnext.construcontrol.finance.get_institution_visual", {institution})
      .then(data => {
        const visual = data || {};
        const logo = visual.logo_file || visual.logo_path;
        const badge = fallbackBadge(visual, channel);
        if (!logo) {
          field.$wrapper.html(badge);
          return;
        }
        const name = visual.short_name || visual.institution_name || institution;
        const color = visual.brand_color || "#175c4c";
        field.$wrapper.html(`<div class="cc-institution-badge" style="--cc-institution-color:${frappe.utils.escape_html(color)}"><span class="cc-institution-logo"><img alt="${frappe.utils.escape_html(name)}" src="${frappe.utils.escape_html(logo)}"></span><span><strong>${frappe.utils.escape_html(name)}</strong><small>${frappe.utils.escape_html(CHANNEL_LABELS[channel] || "Ingreso")}</small></span></div>`);
      })
      .catch(() => field.$wrapper.html(fallbackBadge(null, channel)));
  }

  function updateChannel(frm) {
    const channel = frm.doc.transaction_channel;
    if (channel === "cash" && !frm.doc.financial_institution) frm.set_value("financial_institution", "CASH");
    const needsInstitution = channel !== "cash";
    frm.toggle_reqd("financial_institution", needsInstitution);
    frm.toggle_reqd("transaction_reference", ["remittance", "deposit", "transfer"].includes(channel));
    frm.toggle_reqd("sender", channel === "remittance");
    renderInstitution(frm);
  }

  frappe.ui.form.on("CC Funding Source", {
    refresh(frm) {
      updateChannel(frm);
      calculate(frm);
      if (!frm.is_new()) {
        frm.add_custom_button("Ver estado de cuenta", () => frappe.set_route("query-report", "FI01 Estado de Cuenta"), "ConstruControl");
      }
    },
    transaction_channel: updateChannel,
    financial_institution: renderInstitution,
    gross_amount: calculate,
    fee_amount: calculate,
    original_currency: calculate,
    treasury_exchange_rate: calculate,
  });
})();
