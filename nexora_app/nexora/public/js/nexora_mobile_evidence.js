(() => {
  "use strict";

  function isEvidenceRoute() {
    const route = window.location.hash || window.location.pathname || "";
    return /NXR%20Evidence|NXR%20Evidencia|nexora-evidence/i.test(route);
  }

  function markCameraInputs() {
    if (!isEvidenceRoute()) return;
    document.querySelectorAll('input[type="file"]').forEach((input) => {
      const wrapper = input.closest(".form-group, .frappe-control, .control-input") || input.parentElement;
      const text = (wrapper?.innerText || wrapper?.getAttribute("data-fieldname") || "").toLowerCase();
      if (text.includes("evidencia") || text.includes("evidence") || wrapper?.querySelector('[data-fieldname="file"]')) {
        input.setAttribute("accept", "image/*,video/*,.pdf,.doc,.docx,.xls,.xlsx");
        input.setAttribute("capture", "environment");
      }
    });
  }

  const observer = new MutationObserver(markCameraInputs);
  observer.observe(document.documentElement, { childList: true, subtree: true });
  $(document).on("page-change.nexoraMobileEvidence", markCameraInputs);
  markCameraInputs();
})();
