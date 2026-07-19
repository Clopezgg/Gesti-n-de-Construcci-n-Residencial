(() => {
  "use strict";

  document.addEventListener("click", event => {
    const button = event.target.closest?.(".cc-profile-button");
    if (!button || !document.body.classList.contains("cc-construcontrol-route")) return;
    event.preventDefault();
    event.stopPropagation();
    frappe.set_route("construcontrol-profile");
  }, true);
})();
