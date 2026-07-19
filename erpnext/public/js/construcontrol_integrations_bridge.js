(() => {
  "use strict";

  document.addEventListener("click", event => {
    const trigger = event.target.closest?.('[data-code="INT"]');
    if (!trigger || !document.body.classList.contains("cc-construcontrol-route")) return;
    event.preventDefault();
    event.stopPropagation();
    frappe.set_route("construcontrol-integrations");
  }, true);
})();
