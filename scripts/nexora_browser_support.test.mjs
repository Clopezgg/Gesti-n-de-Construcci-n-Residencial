// Prueba de regresión real (node:test, sin dependencias nuevas) del bug
// preexistente del arnés de navegador: `apiResponse()` creaba una promesa que,
// si nadie llegaba a esperarla porque una acción intermedia fallaba antes,
// quedaba huérfana. Cuando Playwright cierra el contexto en el `finally` del
// perfil, esa promesa rechaza y, sin nadie escuchándola, Node la trata como un
// rechazo no manejado y mata el proceso completo — el fallo real
// "Target page, context or browser has been closed" en `Frappe real ·
// escritorio · tableta · iPhone · PWA` (CI, confirmado en dos ramas distintas,
// una sin relación con NXR-UX-0015/NXR-CNV-0001).
//
// Ejecutar: node --test scripts/nexora_browser_support.test.mjs

import assert from "node:assert/strict";
import { test } from "node:test";

import { apiResponse } from "./nexora_browser_support.mjs";

// Doble de prueba mínimo de un Playwright `Page`: solo lo que `apiResponse`
// toca. `waitForResponse` se resuelve o rechaza cuando el test lo decide,
// simulando exactamente el momento en que Playwright cierra el contexto.
function fakePage(waitForResponseImpl) {
  return { waitForResponse: waitForResponseImpl };
}

test("apiResponse no deja una promesa huérfana cuando nadie llega a esperarla", async () => {
  let rejectUnderlying;
  const underlying = new Promise((_resolve, reject) => {
    rejectUnderlying = reject;
  });
  const page = fakePage(() => underlying);

  let unhandled = null;
  const onUnhandledRejection = (reason) => {
    unhandled = reason;
  };
  process.on("unhandledRejection", onUnhandledRejection);

  try {
    // Mismo patrón real que los 16 llamadores en nexora_browser_smoke.mjs:
    // se crea la promesa y NUNCA se espera (equivale a que la acción
    // intermedia real, p. ej. un clic, haya fallado antes por otra razón).
    apiResponse(page, "review_evidence", "decisión «Validar» sobre el comprobante");

    // Mismo evento que produce Playwright real al cerrar el contexto.
    rejectUnderlying(new Error("Target page, context or browser has been closed"));

    // Deja correr la cola de microtareas y el chequeo de rechazos no
    // manejados de Node (se dispara en el siguiente turno del event loop).
    await new Promise((resolve) => setImmediate(resolve));
    await new Promise((resolve) => setImmediate(resolve));

    assert.equal(
      unhandled,
      null,
      "apiResponse() dejó un rechazo no manejado: el bug del arnés no está corregido."
    );
  } finally {
    process.off("unhandledRejection", onUnhandledRejection);
  }
});

test("apiResponse sigue rechazando con el mensaje real cuando sí se espera", async () => {
  const page = fakePage(() =>
    Promise.reject(new Error("Target page, context or browser has been closed"))
  );

  await assert.rejects(
    () => apiResponse(page, "send_message", "mensaje real al asistente"),
    (error) => {
      assert.match(error.message, /nunca pidió «mensaje real al asistente»/);
      assert.match(error.message, /send_message/);
      assert.ok(error.cause instanceof Error, "debe conservar la causa original");
      return true;
    },
    "el manejador silencioso no debe alterar lo que recibe quien sí espera la promesa"
  );
});

test("apiResponse resuelve normalmente cuando la respuesta real llega a tiempo", async () => {
  const fakeResponse = { ok: true };
  const page = fakePage(() => Promise.resolve(fakeResponse));

  const result = await apiResponse(page, "seed_demo_data", "operación real");
  assert.equal(result, fakeResponse);
});
