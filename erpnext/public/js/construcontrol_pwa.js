(() => {
  "use strict";

  const VERSION = "2026.07.20-b12";
  const VERSION_URL = "/assets/erpnext/construcontrol/deploy-version.json";
  const WORKER_URL = "/construcontrol-service-worker.js";
  const RELOAD_KEY = "cc-pwa-controller-reload";
  const ACTION_LOCK_MS = 1600;
  const actionLocks = new WeakMap();
  let registration = null;
  let controllerReloading = false;
  let controllerWasPresent = Boolean(navigator.serviceWorker?.controller);

  const isAppPath = () => window.location.pathname.startsWith("/app/");
  const route = () => {
    try {
      return window.frappe?.get_route?.() || [];
    } catch (_error) {
      return [];
    }
  };
  const isConstruControlRoute = () => {
    const current = route();
    return (
      document.body.classList.contains("cc-construcontrol-route") ||
      String(current[0] || "").startsWith("construcontrol-") ||
      String(current[1] || "").startsWith("CC ")
    );
  };

  function ensureManifestVersion() {
    const link =
      document.querySelector('link[rel="manifest"][data-cc]') ||
      document.querySelector('link[rel="manifest"]');
    if (link && !link.href.includes(`v=${VERSION}`)) {
      link.href = `/assets/erpnext/construcontrol/manifest.webmanifest?v=${encodeURIComponent(
        VERSION
      )}`;
    }
  }

  function setOfflineBanner(offline) {
    let banner = document.querySelector(".cc-offline-banner");
    if (!offline) {
      banner?.remove();
      return;
    }
    if (!isConstruControlRoute() || banner) return;
    banner = document.createElement("div");
    banner.className = "cc-offline-banner";
    banner.setAttribute("role", "status");
    banner.textContent =
      "Sin conexión. Los datos no se guardarán hasta recuperar internet.";
    document.body.appendChild(banner);
  }

  function configureEvidenceInputs() {
    if (!isConstruControlRoute()) return;
    document.querySelectorAll('input[type="file"]').forEach((input) => {
      if (!input.accept) input.accept = "image/*,application/pdf";
      input.setAttribute("data-cc-camera-gallery", "enabled");
      input.removeAttribute("capture");
    });
  }

  function installDuplicateActionGuard() {
    document.addEventListener(
      "click",
      (event) => {
        if (!isConstruControlRoute()) return;
        const button = event.target.closest?.(
          '.primary-action, [data-cc-command="save"], [data-cc-command="save-new"], .modal .btn-primary'
        );
        if (!button || button.disabled) return;
        const previous = actionLocks.get(button) || 0;
        const now = Date.now();
        if (now - previous < ACTION_LOCK_MS) {
          event.preventDefault();
          event.stopImmediatePropagation();
          return;
        }
        actionLocks.set(button, now);
        button.dataset.ccActionLocked = "1";
        window.setTimeout(() => {
          actionLocks.delete(button);
          delete button.dataset.ccActionLocked;
        }, ACTION_LOCK_MS);
      },
      true
    );
  }

  function installDirtyReloadGuard() {
    window.addEventListener("beforeunload", (event) => {
      if (!isConstruControlRoute() || !window.cur_frm?.is_dirty?.()) return;
      event.preventDefault();
      event.returnValue = "";
    });
  }

  function offerUpdate(worker) {
    if (!worker || !isConstruControlRoute()) return;
    const activate = () => worker.postMessage({ type: "SKIP_WAITING" });
    if (window.frappe?.confirm) {
      frappe.confirm(
        "Hay una versión nueva de ConstruControl. ¿Actualizar ahora?",
        activate
      );
    } else {
      activate();
    }
  }

  function watchRegistration(reg) {
    registration = reg;
    if (reg.waiting) offerUpdate(reg.waiting);
    reg.addEventListener("updatefound", () => {
      const installing = reg.installing;
      if (!installing) return;
      installing.addEventListener("statechange", () => {
        if (
          installing.state === "installed" &&
          navigator.serviceWorker.controller
        ) {
          offerUpdate(installing);
        }
      });
    });
  }

  async function checkDeployVersion() {
    if (!registration || !navigator.onLine || !isConstruControlRoute()) return;
    try {
      const response = await fetch(`${VERSION_URL}?t=${Date.now()}`, {
        cache: "no-store",
        credentials: "same-origin",
      });
      if (!response.ok) return;
      const payload = await response.json();
      if (payload.version && payload.version !== VERSION) {
        await registration.update();
      }
      registration.active?.postMessage({ type: "CLEAR_OLD_CACHES" });
    } catch (_error) {
      // Network failures are surfaced by the offline banner; no stale data is substituted.
    }
  }

  async function registerServiceWorker() {
    if (
      !isAppPath() ||
      !isConstruControlRoute() ||
      !("serviceWorker" in navigator) ||
      !window.isSecureContext
    ) {
      return;
    }
    try {
      const reg = await navigator.serviceWorker.register(WORKER_URL, {
        scope: "/",
        updateViaCache: "none",
      });
      watchRegistration(reg);
      await reg.update();
      await checkDeployVersion();
    } catch (error) {
      if (isConstruControlRoute()) {
        console.warn("ConstruControl PWA registration failed", error);
      }
    }
  }

  function installControllerReload() {
    if (!("serviceWorker" in navigator)) return;
    navigator.serviceWorker.addEventListener("controllerchange", () => {
      const hadController = controllerWasPresent;
      controllerWasPresent = true;

      // A fresh installation claims the current tab for the first time. Reloading here
      // interrupts Frappe while it is constructing the page and can leave it hidden.
      if (!hadController) return;
      if (controllerReloading || !isConstruControlRoute()) return;
      if (sessionStorage.getItem(RELOAD_KEY) === VERSION) return;
      controllerReloading = true;
      sessionStorage.setItem(RELOAD_KEY, VERSION);
      window.location.reload();
    });
  }

  function enhance() {
    if (!isConstruControlRoute()) {
      document.querySelector(".cc-offline-banner")?.remove();
      return;
    }
    ensureManifestVersion();
    configureEvidenceInputs();
    setOfflineBanner(!navigator.onLine);
  }

  installDuplicateActionGuard();
  installDirtyReloadGuard();
  installControllerReload();
  window.addEventListener("online", () => {
    setOfflineBanner(false);
    checkDeployVersion();
  });
  window.addEventListener("offline", () => setOfflineBanner(true));
  window.addEventListener("load", () => {
    enhance();
    registerServiceWorker();
  });
  window.addEventListener("focus", checkDeployVersion);
  window.frappe?.router?.on?.("change", () =>
    window.setTimeout(enhance, 60)
  );

  if (document.body && window.MutationObserver) {
    let scheduled = false;
    new MutationObserver(() => {
      if (scheduled || !isConstruControlRoute()) return;
      scheduled = true;
      window.setTimeout(() => {
        scheduled = false;
        configureEvidenceInputs();
      }, 80);
    }).observe(document.body, { childList: true, subtree: true });
  }
})();
