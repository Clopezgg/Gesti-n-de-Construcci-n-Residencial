frappe.pages["nexora-finance"].on_page_load = function (wrapper) {
  const page = frappe.ui.make_app_page({
    parent: wrapper,
    title: __("Núcleo de Fondos"),
    single_column: true,
  });

  const state = { preview: null, sources: [] };
  const project = page.add_field({
    label: __("Proyecto"), fieldname: "project", fieldtype: "Link", options: "Project", reqd: 1,
    change: () => loadSources(),
  });
  const operationType = page.add_field({
    label: __("Tipo de operación"), fieldname: "operation_type", fieldtype: "Select",
    options: ["Outflow", "Commitment Reserve", "Commitment Execution", "Commitment Release", "Real Return", "Reclassification"],
    default: "Outflow", reqd: 1, change: invalidatePreview,
  });
  const amount = page.add_field({label: __("Importe HNL"), fieldname: "amount_hnl", fieldtype: "Currency", reqd: 1, change: invalidatePreview});
  const costCenter = page.add_field({label: __("Centro de costo"), fieldname: "cost_center", fieldtype: "Link", options: "Cost Center", change: invalidatePreview});
  const requester = page.add_field({label: __("Solicitante"), fieldname: "requester", fieldtype: "Link", options: "User", reqd: 1, change: invalidatePreview});
  const approvedBy = page.add_field({label: __("Aprobador"), fieldname: "approved_by", fieldtype: "Link", options: "User", reqd: 1, change: invalidatePreview});
  const commitment = page.add_field({label: __("Compromiso"), fieldname: "commitment", fieldtype: "Link", options: "NXR Commitment", change: invalidatePreview});
  const evidence = page.add_field({label: __("Evidencia"), fieldname: "evidence", fieldtype: "Attach", change: invalidatePreview});

  $(page.body).append(`
    <div class="nxr-finance-grid">
      <section class="nxr-card"><h3>${__("Asignaciones por fuente")}</h3><div class="nxr-source-list"></div></section>
      <section class="nxr-card"><h3>${__("Vista previa antes de ejecutar")}</h3><div class="nxr-preview nxr-empty">${__("Genere una vista previa para continuar.")}</div></section>
      <section class="nxr-card nxr-source-create"><h3>${__("Alta rápida de fuente")}</h3><div class="nxr-source-fields"></div></section>
    </div>
  `);

  buildSourceFields(page.body);
  page.add_button(__("Vista previa"), previewOperation, "primary");
  const executeButton = page.add_button(__("Ejecutar operación"), executeOperation);
  executeButton.prop("disabled", true);

  function uuid() {
    return globalThis.crypto?.randomUUID?.() || `nxr-${Date.now()}-${Math.random().toString(16).slice(2)}`;
  }

  function invalidatePreview() {
    state.preview = null;
    executeButton.prop("disabled", true);
    $(page.body).find(".nxr-preview").addClass("nxr-empty").text(__("La información cambió; genere otra vista previa."));
  }

  function allocations() {
    if (operationType.get_value() === "Reclassification") return [];
    return $(page.body).find(".nxr-source-amount").toArray()
      .map((input) => ({source: input.dataset.source, amount_hnl: input.value}))
      .filter((row) => Number(row.amount_hnl) > 0);
  }

  function operationPayload() {
    return {
      operation_type: operationType.get_value(), project: project.get_value(),
      amount_hnl: operationType.get_value() === "Reclassification" ? 0 : amount.get_value(),
      cost_center: costCenter.get_value(), requester: requester.get_value(), approved_by: approvedBy.get_value(),
      commitment: commitment.get_value(), description: __("Compromiso registrado desde Núcleo de Fondos"),
      evidence: evidence.get_value(), allocations: allocations(), affects_cost: 0, affects_budget: 0,
    };
  }

  async function loadSources() {
    invalidatePreview();
    const value = project.get_value();
    if (!value) return renderSources([]);
    const response = await frappe.call({
      method: "nexora.financial.service.list_source_balances", type: "POST", args: {project: value},
      freeze: true, freeze_message: __("Consultando saldos canónicos…"),
    });
    state.sources = response.message || [];
    renderSources(state.sources);
  }

  function renderSources(rows) {
    const target = $(page.body).find(".nxr-source-list").empty();
    if (!rows.length) {
      target.append(`<p class="text-muted">${__("No hay fuentes activas para este proyecto.")}</p>`);
      return;
    }
    rows.forEach((row) => target.append(`
      <label class="nxr-source-row">
        <span><strong>${frappe.utils.escape_html(row.source)}</strong><br>
        ${__("Saldo")}: L${row.balance_hnl} · ${__("Reservado")}: L${row.reserved_hnl} · ${__("Disponible")}: L${row.available_hnl}</span>
        <input class="form-control nxr-source-amount" type="number" min="0" step="0.01" value="0" data-source="${frappe.utils.escape_html(row.source)}">
      </label>`));
    target.find("input").on("input", invalidatePreview);
  }

  async function previewOperation() {
    const response = await frappe.call({
      method: "nexora.financial.service.preview_financial_operation", type: "POST",
      args: {payload: operationPayload()}, freeze: true, freeze_message: __("Recalculando saldos en servidor…"),
    });
    state.preview = response.message;
    renderPreview(state.preview);
    executeButton.prop("disabled", false);
  }

  function renderPreview(preview) {
    const rows = (preview.sources || []).map((row) => `
      <tr><td>${frappe.utils.escape_html(row.source)}</td><td>L${row.amount_hnl}</td><td>L${row.balance_before_hnl}</td><td>L${row.balance_after_hnl}</td><td>L${row.reserved_before_hnl}</td><td>L${row.reserved_after_hnl}</td></tr>`).join("");
    $(page.body).find(".nxr-preview").removeClass("nxr-empty").html(`
      <table class="table table-bordered"><thead><tr><th>${__("Fuente")}</th><th>${__("Importe")}</th><th>${__("Saldo antes")}</th><th>${__("Saldo después")}</th><th>${__("Reservado antes")}</th><th>${__("Reservado después")}</th></tr></thead><tbody>${rows}</tbody></table>
      <p><strong>${__("Costo")}:</strong> L${preview.cost_effect_hnl} · <strong>${__("Presupuesto")}:</strong> L${preview.budget_effect_hnl}</p>
      <p><strong>${__("Documento")}:</strong> ${frappe.utils.escape_html(preview.document_to_generate)}</p>`);
  }

  async function executeOperation() {
    if (!state.preview) return;
    const payload = {...operationPayload(), idempotency_key: uuid(), preview_hash: state.preview.preview_hash};
    const method = {
      "Commitment Reserve": "nexora.financial.service.create_commitment",
      "Commitment Execution": "nexora.financial.service.execute_commitment",
      "Commitment Release": "nexora.financial.service.release_commitment",
    }[payload.operation_type] || "nexora.financial.service.execute_financial_operation";
    const response = await frappe.call({method, type: "POST", args: {payload}, freeze: true, freeze_message: __("Ejecutando operación atómica…")});
    const number = response.message.document_number || response.message.commitment_number;
    frappe.show_alert({message: __("Documento {0} ejecutado", [number]), indicator: "green"});
    await loadSources();
  }

  function buildSourceFields(body) {
    const parent = $(body).find(".nxr-source-fields");
    const fields = {};
    const definitions = [
      ["channel", __("Canal"), "Select", ["Remittance", "Cash", "Deposit", "Transfer", "Other"]],
      ["currency", __("Moneda"), "Link", "Currency"], ["original_amount", __("Importe original"), "Currency"],
      ["exchange_rate", __("Tasa a HNL"), "Float"], ["origin_or_sender", __("Procedencia o remitente"), "Data"],
      ["institution", __("Institución"), "Data"], ["account_reference", __("Cuenta"), "Data"],
      ["external_reference", __("Referencia"), "Data"],
    ];
    definitions.forEach(([fieldname, label, fieldtype, options]) => {
      fields[fieldname] = frappe.ui.form.make_control({parent, df: {fieldname, label, fieldtype, options, change: toggleBankFields}, render_input: true});
    });
    fields.currency.set_value("HNL"); fields.exchange_rate.set_value(1);
    const add = $(`<button class="btn btn-primary btn-sm">${__("Registrar fuente")}</button>`).appendTo(parent);
    add.on("click", async () => {
      const sourcePayload = Object.fromEntries(Object.entries(fields).map(([name, control]) => [name, control.get_value()]));
      Object.assign(sourcePayload, {project: project.get_value(), custodian: frappe.session.user, idempotency_key: uuid()});
      const response = await frappe.call({
        method: "nexora.financial.service.create_fund_source", type: "POST", args: {payload: sourcePayload},
        freeze: true, freeze_message: __("Registrando fuente y efecto de ingreso…"),
      });
      frappe.show_alert({message: __("Fuente {0} registrada", [response.message.source_number]), indicator: "green"});
      await loadSources();
    });
    toggleBankFields();

    function toggleBankFields() {
      const bank = ["Deposit", "Transfer"].includes(fields.channel?.get_value());
      ["institution", "account_reference", "external_reference"].forEach((name) => fields[name]?.toggle(bank));
    }
  }
};
