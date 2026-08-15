frappe.pages["nexora-monthly-closing"].on_page_load = async function (wrapper) {
  const page = frappe.ui.make_app_page({ parent: wrapper, title: __("Cierre mensual NEXORA"), single_column: true });
  const body = $(page.body);
  const month = page.add_field({ fieldname: "close_month", label: __("Mes"), fieldtype: "Data", reqd: 1, default: frappe.datetime.get_today().slice(0, 7) });
  const project = page.add_field({ fieldname: "project", label: __("Proyecto"), fieldtype: "Link", options: "Project" });
  const calculate = () => run("nexora.close.service.create_monthly_close", { close_month: month.get_value(), project: project.get_value() || null, idempotency_key: `monthly-close-preview-${frappe.session.user}-${Date.now()}` }, __("Generando fotografía mensual…"), true);
  const list = () => frappe.call({ method: "nexora.close.service.list_monthly_closes", type: "POST", args: { payload: { project: project.get_value() || null, page: 1, page_size: 50 } } }).then((r) => renderHistory(r.message?.rows || []));
  page.add_button(__("Calcular y guardar"), calculate);
  page.add_button(__("Actualizar historial"), list);
  body.html(`<main class="nxr-product-shell nxr-bi-shell"><section class="nxr-bi-hero"><div><p class="nxr-eyebrow">CL02 · ${__("CIERRE MENSUAL")}</p><h2>${__("Fotografía financiera mensual")}</h2><p>${__("Inmutable, trazable y corregible mediante documento enlazado.")}</p></div></section><section class="nxr-ds-card nxr-bi-table-card"><header><h3>${__("Resultado")}</h3></header><div class="nxr-monthly-result"></div></section><section class="nxr-ds-card nxr-bi-table-card"><header><h3>${__("Historial")}</h3></header><div class="nxr-monthly-history"></div></section></main>`);

  async function run(method, payload, freeze_message, show_result) {
    if (!payload.close_month || !/^\d{4}-\d{2}$/.test(payload.close_month)) {
      frappe.msgprint(__("El mes debe tener formato AAAA-MM."));
      return;
    }
    try {
      const response = await frappe.call({ method, type: "POST", args: { payload }, freeze: true, freeze_message });
      if (show_result) {
        const result = response.message || {};
        body.find(".nxr-monthly-result").html(`<pre class="small">${frappe.utils.escape_html(JSON.stringify(result, null, 2))}</pre>`);
      }
      await list();
    } catch (error) {
      window.nexora?.ui?.showError?.(error, { title: __("No fue posible procesar el cierre mensual"), fallback: __("Revise el período, proyecto y permisos.") });
    }
  }

  function renderHistory(rows) {
    if (!rows.length) {
      body.find(".nxr-monthly-history").html(`<div class="text-muted">${__("No hay cierres mensuales registrados.")}</div>`);
      return;
    }
    const html = rows.map((row) => `<tr><td>${frappe.utils.escape_html(row.document_number || row.name)}</td><td>${frappe.utils.escape_html(row.close_month || "")}</td><td>${frappe.utils.escape_html(row.status || "")}</td><td>${frappe.utils.escape_html(String(row.total_available_hnl || 0))}</td><td>${frappe.utils.escape_html(String(row.snapshot_hash || "").slice(0, 16))}</td><td>${row.correction_of ? frappe.utils.escape_html(row.correction_of) : ""}</td></tr>`).join("");
    body.find(".nxr-monthly-history").html(`<table class="table"><thead><tr><th>Número</th><th>Mes</th><th>Estado</th><th>Disponible HNL</th><th>Huella</th><th>Corrige a</th></tr></thead><tbody>${html}</tbody></table>`);
  }

  try { await list(); } catch (_) {}
};
