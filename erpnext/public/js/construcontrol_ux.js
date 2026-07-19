(() => {
  "use strict";

  const CC_DOCTYPES = new Set([
    "CC Funding Source", "CC Expense Control", "CC Payable Control", "CC Labor Contract",
    "CC Construction Phase", "CC Material Ledger", "CC Inventory Movement", "CC Procurement Request",
    "CC Progress Update", "CC Weekly Closing", "CC Audit Log", "CC User Access",
    "CC Financial Institution", "CC Integration Registry", "CC Project Profile",
  ]);

  function route() {
    try { return window.frappe?.get_route?.() || []; } catch (_error) { return []; }
  }

  function isConstruControl() {
    return document.body.classList.contains("cc-construcontrol-route");
  }

  function escape(value) {
    return window.frappe?.utils?.escape_html?.(String(value ?? "")) || String(value ?? "");
  }

  function goBackFromCurrent() {
    const current = route();
    if (current[0] === "Form" && current[1]) {
      frappe.set_route("List", current[1]);
      return;
    }
    if (current[0] === "List" || current[0] === "query-report") {
      frappe.set_route("construcontrol-dashboard");
      return;
    }
    if (window.history.length > 1) window.history.back();
    else frappe.set_route("construcontrol-dashboard");
  }

  function confirmDiscard(callback) {
    const frm = window.cur_frm;
    if (!frm?.is_dirty?.()) {
      callback();
      return;
    }
    frappe.confirm("Hay cambios sin guardar. ¿Descartarlos y salir?", callback);
  }

  function ensureFormCommandBar() {
    const current = route();
    const isForm = current[0] === "Form" && CC_DOCTYPES.has(String(current[1] || ""));
    let bar = document.querySelector(".cc-form-command-bar");
    if (!isConstruControl() || !isForm) {
      bar?.remove();
      return;
    }
    if (bar) return;

    bar = document.createElement("div");
    bar.className = "cc-form-command-bar";
    bar.setAttribute("role", "toolbar");
    bar.setAttribute("aria-label", "Acciones del formulario");
    bar.innerHTML = `
      <button type="button" class="btn btn-default" data-cc-command="close">Cerrar</button>
      <button type="button" class="btn btn-default" data-cc-command="cancel">Cancelar cambios</button>
      <button type="button" class="btn btn-primary" data-cc-command="save">Guardar</button>
      <button type="button" class="btn btn-default" data-cc-command="save-new">Guardar y nuevo</button>
    `;
    bar.addEventListener("click", event => {
      const command = event.target.closest?.("[data-cc-command]")?.dataset.ccCommand;
      const frm = window.cur_frm;
      if (!command) return;
      if (command === "close") return confirmDiscard(goBackFromCurrent);
      if (command === "cancel") {
        if (!frm) return;
        return confirmDiscard(() => frm.reload_doc());
      }
      if (!frm) return;
      if (command === "save") return frm.save();
      if (command === "save-new") {
        return frm.save().then(() => frappe.new_doc(frm.doctype));
      }
    });
    document.body.appendChild(bar);
  }

  function ensureCloseActionIsCurrent() {
    document.addEventListener("click", event => {
      const button = event.target.closest?.(".cc-close-view");
      if (!button || !isConstruControl()) return;
      event.preventDefault();
      event.stopImmediatePropagation();
      confirmDiscard(goBackFromCurrent);
    }, true);
  }

  function ensureModalCloseButtons() {
    if (!isConstruControl()) return;
    document.querySelectorAll(".modal.show .modal-content").forEach(content => {
      const header = content.querySelector(".modal-header");
      if (!header || header.querySelector(".cc-modal-close")) return;
      const button = document.createElement("button");
      button.type = "button";
      button.className = "cc-modal-close";
      button.setAttribute("aria-label", "Cerrar ventana");
      button.textContent = "×";
      button.addEventListener("click", () => {
        const modal = content.closest(".modal");
        const standardClose = modal?.querySelector('[data-dismiss="modal"], .btn-modal-close, .modal-header .close');
        if (standardClose) standardClose.click();
        else $(modal).modal("hide");
      });
      header.appendChild(button);
    });
  }

  function ensureMissingPageRecovery() {
    if (!isConstruControl()) return;
    const bodyText = String(document.querySelector(".page-body")?.textContent || "");
    const missing = bodyText.includes("Lamentablemente, no se puede encontrar")
      || document.querySelector(".page-missing, .not-found, [data-page-status='404']");
    if (!missing || document.querySelector(".cc-route-recovery")) return;
    const target = document.querySelector(".layout-main-section") || document.querySelector(".page-body");
    if (!target) return;
    const card = document.createElement("section");
    card.className = "cc-route-recovery";
    card.innerHTML = `<div class="cc-route-recovery-mark">!</div><div><h3>Esta opción no está disponible</h3><p>La ruta solicitada no pertenece a la navegación activa de ConstruControl.</p><div class="cc-route-recovery-actions"><button type="button" class="btn btn-primary" data-recovery="home">Volver al inicio</button><button type="button" class="btn btn-default" data-recovery="back">Regresar</button></div></div>`;
    card.addEventListener("click", event => {
      const action = event.target.closest?.("[data-recovery]")?.dataset.recovery;
      if (action === "home") frappe.set_route("construcontrol-dashboard");
      if (action === "back") goBackFromCurrent();
    });
    target.prepend(card);
  }

  function friendlyErrorMessage(reason) {
    const raw = String(reason?.message || reason || "").trim();
    if (!raw) return "No se pudo completar la operación.";
    if (raw.includes("Traceback") || raw.includes("pymysql") || raw.includes("frappe.")) {
      return "No se pudo completar la operación. El error técnico quedó registrado para revisión.";
    }
    return raw.slice(0, 240);
  }

  function installErrorRecovery() {
    window.addEventListener("unhandledrejection", event => {
      if (!isConstruControl()) return;
      const message = friendlyErrorMessage(event.reason);
      window.setTimeout(() => {
        frappe.show_alert({message: escape(message), indicator: "red"}, 7);
      }, 0);
    });
  }

  function enhance() {
    if (!isConstruControl()) {
      document.querySelector(".cc-form-command-bar")?.remove();
      return;
    }
    ensureFormCommandBar();
    ensureModalCloseButtons();
    ensureMissingPageRecovery();
  }

  ensureCloseActionIsCurrent();
  installErrorRecovery();
  window.addEventListener("load", () => window.setTimeout(enhance, 80));
  window.addEventListener("keydown", event => {
    if (!isConstruControl() || event.key !== "Escape") return;
    const modal = document.querySelector(".modal.show");
    if (modal) {
      modal.querySelector(".cc-modal-close, [data-dismiss='modal'], .btn-modal-close")?.click();
      return;
    }
  });
  if (window.frappe?.router?.on) frappe.router.on("change", () => window.setTimeout(enhance, 80));
  if (document.body && window.MutationObserver) {
    let pending = false;
    const observer = new MutationObserver(() => {
      if (pending || !isConstruControl()) return;
      pending = true;
      window.setTimeout(() => { pending = false; enhance(); }, 40);
    });
    observer.observe(document.body, {childList: true, subtree: true});
  }
})();
