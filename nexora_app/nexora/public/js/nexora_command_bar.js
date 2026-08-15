(() => {
  "use strict";

  const state = { dialog: null, lastQuery: "" };

  function openCommandBar() {
    if (!window.frappe || !frappe.ui) return;
    if (state.dialog) {
      state.dialog.show();
      const field = state.dialog.get_field("query");
      if (field) field.set_focus();
      return;
    }

    const dialog = new frappe.ui.Dialog({
      title: "Buscar en NEXORA",
      fields: [
        {
          fieldname: "query",
          label: "Buscar",
          fieldtype: "Data",
          description: "Documentos, entidades, fondos, operaciones, compras, inventario y contratos",
        },
        {
          fieldname: "results",
          fieldtype: "HTML",
          options: '<div class="nxr-command-results" aria-live="polite"><div class="text-muted">Escriba para buscar.</div></div>',
        },
      ],
      primary_action_label: "Buscar",
      primary_action: () => executeSearch(dialog),
    });
    state.dialog = dialog;
    dialog.show();

    const query = dialog.get_field("query");
    if (query) {
      query.$input.on("keydown.nexoraCommandBar", (event) => {
        if (event.key === "Enter") {
          event.preventDefault();
          executeSearch(dialog);
        }
      });
      query.$input.on("input.nexoraCommandBar", frappe.utils.debounce(() => executeSearch(dialog), 280));
      query.set_focus();
    }
  }

  function renderResults(dialog, rows) {
    const field = dialog.get_field("results");
    if (!field || !field.$wrapper) return;
    const wrapper = field.$wrapper.find(".nxr-command-results");
    if (!rows.length) {
      wrapper.html('<div class="text-muted">No se encontraron resultados autorizados.</div>');
      return;
    }
    const html = rows.map((row) => {
      const title = frappe.utils.escape_html(String(row.title || row.name || ""));
      const label = frappe.utils.escape_html(String(row.label || row.doctype || ""));
      const status = frappe.utils.escape_html(String(row.status || ""));
      const name = frappe.utils.escape_html(String(row.name || ""));
      const project = row.project ? `<span class="text-muted">${frappe.utils.escape_html(String(row.project))}</span>` : "";
      return `<button type="button" class="btn btn-sm btn-block text-left nxr-command-result" data-doctype="${frappe.utils.escape_html(String(row.doctype || ""))}" data-name="${name}">
        <div><strong>${title}</strong></div><div><span class="badge badge-secondary">${label}</span> ${status} ${project}</div>
      </button>`;
    }).join("");
    wrapper.html(html);
    wrapper.find(".nxr-command-result").on("click", function () {
      const doctype = this.dataset.doctype;
      const name = this.dataset.name;
      dialog.hide();
      if (!doctype || !name) return;
      frappe.set_route("Form", doctype, name);
    });
  }

  function executeSearch(dialog) {
    const query = String(dialog.get_value("query") || "").trim();
    if (!query || query === state.lastQuery) return;
    state.lastQuery = query;
    frappe.call({
      method: "nexora.boot.universal_search_consolidated",
      args: { payload: { query, limit: 25 } },
      freeze: false,
    }).then((response) => {
      renderResults(dialog, response.message || []);
    }).catch(() => {
      renderResults(dialog, []);
    });
  }

  $(document).on("keydown.nexoraCommandBar", (event) => {
    if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "k") {
      event.preventDefault();
      openCommandBar();
    }
  });

  window.nexoraCommandBar = { open: openCommandBar };
})();
