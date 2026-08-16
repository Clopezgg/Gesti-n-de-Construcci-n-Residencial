# NEXORA Intelligence Platform — Bloque 6: Sistema Operativo Conversacional Empresarial

> Subordinado a [`NEXORA_INTELLIGENCE_ARCHITECTURE.md`](../../NEXORA_INTELLIGENCE_ARCHITECTURE.md),
> [`AGENTS.md`](../../AGENTS.md) y [`NEXORA_CONSTITUTION.md`](../../NEXORA_CONSTITUTION.md).
> Se apoya en NIP Bloques 1–5.3 (Gateway, Adapters, Credential Manager, Runtime,
> Orchestrator) tal cual existen hoy, sin modificarlos, y en las capas de servicio de
> negocio ya certificadas (`contracts`, `purchases`, `inventory`, `budget`, `directory`,
> `financial`, `progress`, `notifications`, `close`) descritas en
> [`PROJECT_RECONSTRUCTION.md`](../../PROJECT_RECONSTRUCTION.md). Numerado como "Bloque 6"
> dentro de la serie de documentos de diseño `NIP_BLOQUE_*` (el último publicado como
> archivo fue el 5.2; el propio Bloque 6 de `EXECUTION_STATE.md` — fusión del stack NIP a
> `main` — no generó un documento de diseño propio). **No confundir** con
> `BLOQUE_11_BUSCADOR_DASHBOARD.md` (numeración antigua de bloques funcionales del ERP,
> cerrada hace tiempo) ni con el "Bloque 11" de `PROJECT_RECONSTRUCTION.md` (una
> reconstrucción narrativa de otra sesión). La entrada operativa de este trabajo en
> `EXECUTION_STATE.md` se numera "Bloque 11" porque continúa la numeración secuencial de
> *esa* bitácora (Bloque 10 fue el cierre de producción anterior).

## Por qué existe este documento antes que el código

El encargo pide explícitamente "no construyas una solución rápida... no dupliques reglas
de negocio... reutiliza toda la lógica existente". Antes de escribir una sola línea se
auditó el código real (no la documentación) de NIP, `permissions.py`, `financial/db.py`
y las nueve capas de servicio de dominio. El hallazgo central, confirmado leyendo el
código, no infiriéndolo:

- **No existe ningún código conversacional, de chat, NLU, intención o canal externo en
  todo el repositorio.** Los propios documentos de diseño de NIP (Bloques 2–5.2) lo
  declaran por escrito como fuera de su alcance ("Ninguna interfaz gráfica, ningún chat,
  ninguna memoria"). Este bloque es, en ese sentido, genuinamente nuevo.
- **Pero la capa de negocio que ese chat necesita ya existe, está probada y auditada.**
  Cada módulo de dominio expone funciones `@frappe.whitelist` con la misma forma:
  `create_*`/`transition_*`/`get_*`/`list_*`, cada una empezando con
  `require_action(...)` (RBAC) y terminando con `audit(...)` (trazabilidad), muchas con
  pares `preview_*`/`execute_*` para operaciones financieras. Esa consistencia es lo que
  hace posible construir un motor conversacional *sin* reimplementar una sola regla de
  negocio: el motor no necesita saber cómo se calcula una retención de contrato o cómo se
  bloquea una fuente de fondos — solo necesita saber **qué función invocar, con qué
  payload, bajo qué permiso**, y dejar que esa función haga exactamente lo que ya hace
  hoy para el usuario que hace clic en la pantalla.

## Decisión arquitectónica central

**Un núcleo conversacional único, sin cerebro por canal.**

```
                    ┌─────────────────────────────────────────┐
                    │   NEXORA Conversational Core (NCC)       │
                    │   nexora_app/nexora/conversation/        │
                    │                                           │
                    │  · Identidad (Channel Account → User)    │
                    │  · Memoria de conversación (DocTypes)    │
                    │  · Resolución de intención (NLU vía NIP) │
                    │  · Registro de intenciones (Registry)    │
                    │  · Relleno de campos faltantes (Slots)   │
                    │  · Vista previa + confirmación obligatoria│
                    │  · Ejecución vía función de servicio real │
                    │  · Permisos (permissions.require_action) │
                    │  · Auditoría (financial.db.audit)        │
                    └───────────────┬───────────────────────────┘
                                     │  mismo contrato de payload/permiso/auditoría
                                     │  que ya usa la UI de Desk
              ┌──────────────────────┼──────────────────────────┐
              │                      │                          │
    ┌─────────▼────────┐  ┌──────────▼─────────┐  ┌─────────────▼──────────┐
    │  Adaptador Web/   │  │  Adaptador WhatsApp │  │  Adaptadores futuros    │
    │  PWA (Desk/PWA)   │  │  Business Cloud API │  │  (voz, correo, OCR de  │
    │  ya existe: Desk  │  │  (Bloque 11.2)      │  │  documentos, app móvil) │
    │  llama servicios  │  │                     │  │  mismo contrato de     │
    │  directamente     │  │                     │  │  mensaje canónico      │
    └───────────────────┘  └─────────────────────┘  └─────────────────────────┘
```

Los canales **traducen** (formato del canal ↔ mensaje canónico); nunca deciden, nunca
ejecutan lógica de negocio y nunca conocen las funciones de servicio de NEXORA
directamente. Toda decisión — qué se entendió, si hace falta preguntar algo, si hace
falta confirmar, si el usuario puede hacerlo, qué pasó — vive en el núcleo. Esto responde
directamente al principio del encargo: "no diseñes asistentes separados por canal...
todo debe compartir exactamente el mismo cerebro".

### Por qué no un framework de chatbot externo

Se evaluó (referencia, no dependencia — mismo criterio que la decisión sobre OmniRoute en
el Bloque 5.2) apoyarse en un framework de orquestación conversacional de terceros. Se
descarta por la misma razón que OmniRoute: introduciría un segundo runtime/proceso, una
segunda superficie de permisos paralela a `permissions.py`, y una segunda ruta de
auditoría paralela a `financial.db.audit`. El "cerebro" de NEXORA ya sabe resolver
proveedores de IA con fallback (`intelligence.orchestrator`); lo único que falta es la
capa de diálogo, intención y confirmación — que es exactamente lo que este bloque añade,
en Python, en el mismo proceso Frappe, sin runtime adicional.

## Modelo de datos (Bloque 11.1)

Cuatro DocTypes nuevos, mínimos, sin duplicar ningún dato que ya viva en un DocType de
negocio — solo el estado propio de la conversación:

| DocType | Propósito |
| --- | --- |
| `NXR Channel Account` | Vincula una identidad externa (p. ej. un número de WhatsApp) con un `User` real de NEXORA. Nunca se crea sola: la crea un administrador explícitamente (`conversation_manage_channel`), nunca por auto-registro desde el canal. Sin vínculo verificado, un mensaje entrante no tiene sesión ni permisos. |
| `NXR Conversation` | Un hilo de conversación: canal, referencia externa del hilo, `Channel Account`, `User` resuelto, estado (`Active`/`Archived`), última actividad. |
| `NXR Conversation Message` | Cada turno (entrante o saliente): tipo de contenido (texto/imagen/documento/audio — mismo vocabulario que `NXR Evidence.channel`/`evidence_kind` donde aplica), contenido, intención resuelta (JSON), fecha. Solo-append, igual que `NXR Audit Event`. |
| `NXR Conversation Pending Intent` | El "borrador" de una operación mientras se completan campos o se espera confirmación: qué intención del `Registry`, qué payload llevamos, qué campos faltan, el resultado de `preview_*` si la intención lo requiere, y su estado (`Collecting`/`AwaitingConfirmation`/`Confirmed`/`Cancelled`/`Executed`/`Failed`). Nunca ejecuta nada por sí sola — solo lo hace el motor de despacho, y solo en `Confirmed`. |

Ninguno de los dos primeros duplica `User`/`Contact`; ninguno de los dos últimos duplica
`NXR Operation`, `NXR Contract`, etc. — cuando una intención se ejecuta, el documento de
negocio real se crea exactamente como si viniera de la UI, y el `Pending Intent` solo
guarda la referencia al resultado.

## Flujo de una solicitud

1. **Recepción** (canal → núcleo): el adaptador de canal recibe un mensaje externo,
   resuelve el `Channel Account` (si no hay vínculo, responde pidiendo que un
   administrador lo conecte — nunca ejecuta nada sin identidad verificada) y llama a
   `conversation.dispatch.ingest_message(...)` con un mensaje canónico
   `{channel, external_thread_id, external_sender, content_type, content, raw}`.
2. **Persistencia de contexto**: se guarda `NXR Conversation Message`, se recupera o crea
   `NXR Conversation`.
3. **Resolución de intención** (Bloque 11.3, NLU vía `intelligence.orchestrator.execute`):
   el texto (o la transcripción/OCR futura) más el historial reciente de la conversación
   se envían al orquestador de NIP pidiendo una respuesta estructurada (JSON) contra el
   catálogo de intenciones del `Registry` — nunca contra una lista cerrada de comandos:
   el catálogo describe *qué operaciones existen y qué campos necesitan*, no frases
   exactas que el usuario deba memorizar.
4. **Relleno de campos (slots)**: `conversation.core.missing_slots(spec, payload)` calcula
   qué campos obligatorios de la operación aún faltan. Si faltan, el núcleo genera una
   única pregunta dirigida (no un formulario completo) y espera la siguiente respuesta,
   que se fusiona sobre el `Pending Intent` existente — así es como se sostiene una
   conversación larga con correcciones ("no, mejor cambia el monto a...") sin perder lo
   ya capturado.
5. **Permiso**: antes de mostrar cualquier vista previa, `permissions.require_action(...)`
   con la acción declarada por esa intención en el `Registry` — la misma función, los
   mismos roles, que ya usa la UI de Desk. Si el usuario no tiene el rol, el núcleo lo
   dice y no continúa.
6. **Vista previa obligatoria para lo crítico**: si la intención toca dinero, contratos,
   inventario o fondos, el `Registry` la marca `requires_confirmation=True` y declara su
   función `preview_*` (reutilizando las ya existentes:
   `financial.operational_commands.preview_operational_movement`,
   `financial.analytics.preview_central_operation`,
   `financial.corrections.preview_operation_correction`, etc.). El núcleo llama a esa
   función real, muestra el resultado en lenguaje natural y **exige una confirmación
   explícita** del usuario antes de ejecutar. Ninguna automatización (§ "Automatizaciones")
   puede saltarse este paso.
7. **Ejecución**: solo tras confirmación, el núcleo invoca la función `execute_*`/`create_*`
   real vía `frappe.get_attr(dotted_path)(payload)` — el mismo mecanismo que
   `override_whitelisted_methods` en `hooks.py` ya usa para redirigir rutas, y el mismo
   punto de entrada que golpea `frappe.call` desde el JavaScript de Desk. Esa función
   hace su propio `require_action`, su propio `service_write`, su propia
   idempotencia (`idempotency_key` generada por el núcleo) y su propio `audit(...)` —
   nada de eso se reimplementa.
8. **Respuesta**: el resultado real (número de documento, estado) se traduce a lenguaje
   natural y se envía por el canal de origen.
9. **Auditoría de la conversación misma**: además de la auditoría que cada función de
   servicio ya genera, el núcleo audita sus propios eventos
   (`conversation_message_received`, `conversation_intent_confirmed`,
   `conversation_intent_executed`, `conversation_intent_rejected_by_permission`) con la
   misma primitiva `financial.db.audit`, para que quede trazable *que* una operación se
   originó por conversación y desde qué canal — sin crear un segundo sistema de
   auditoría.

## El Registry: metadatos, no lógica

`conversation/registry.py` no reimplementa ninguna regla de negocio. Cada entrada es
declarativa:

```python
IntentSpec(
    key="register_expense",
    permission_action="execute",              # ya existe en permissions.ACTION_ROLES
    preview_method="nexora.financial.service.preview_operational_movement",
    execute_method="nexora.financial.service.execute_operational_movement",
    requires_confirmation=True,
    slots=(
        Slot("project", required=True, description="¿En qué proyecto?"),
        Slot("amount_hnl", required=True, description="¿Por cuánto?"),
        Slot("payment_method", required=True, description="¿Cómo se pagó?"),
        ...
    ),
)
```

Añadir una intención nueva nunca implica escribir una función de negocio nueva — implica
declarar qué función real ya existente se invoca y qué campos necesita. Esto es
literalmente lo que pide el encargo ("no inventes un flujo nuevo si ya existe uno
correcto en el ERP"). La primera versión del catálogo (Bloque 11.1) cubre un subconjunto
real y representativo — no la lista cerrada final — para probar el mecanismo de extremo
a extremo antes de expandirlo módulo por módulo:

- `register_expense` / `register_income` → `financial.service.preview_operational_movement`
  / `execute_operational_movement`.
- `query_fund_balance` → `financial.sources.list_source_balances` (solo lectura, sin
  confirmación).
- `query_contract` → `contracts.service.get_contract` (solo lectura).
- `register_evidence` → `financial.evidence.register_evidence` (para el caso "adjunto la
  factura").

Expandir a compras, inventario, presupuestos, directorio, etc. es trabajo de
**catálogo**, no de arquitectura — cada nueva intención es una entrada más en
`registry.py` apuntando a una función que ya existe y ya está probada.

## Resolución de intención sin comandos (Bloque 11.3)

El núcleo no usa expresiones regulares ni un árbol de comandos: usa
`intelligence.orchestrator.execute("text", {"messages": [...]}, correlation_id)` (el
mismo Orchestrator del Bloque 5.2, con su mismo fallback multi-proveedor) pidiéndole al
modelo que devuelva **un objeto JSON estricto** con la forma
`{"intent": <clave del Registry o null>, "confidence": 0..1, "fields": {...},
"clarification_question": <string o null>}`. Se eligió *salida estructurada por
instrucción de prompt* en vez de "function calling" nativo del proveedor porque
`ProviderRequest.payload` (Bloque 1) ya soporta `messages` genérico y ningún adaptador de
los nueve proveedores certificados en el Bloque 5 implementa hoy un esquema de
herramientas — añadirlo tocaría los nueve adaptadores ya certificados sin necesidad: el
mismo resultado (una intención estructurada) se logra con el contrato de mensajes que ya
existe, sin modificar una sola línea de `intelligence/providers/`. El prompt del sistema
se construye a partir del propio `Registry` (nombres de intención + campos + descripción),
así que el catálogo de "qué puede entender NEXORA" y "qué le decimos al modelo que puede
hacer" son la misma fuente — no hay dos listas que puedan desincronizarse.

## WhatsApp Business Cloud API (Bloque 11.2)

WhatsApp es la puerta principal, no el cerebro. Diseño:

- **Conexión por Embedded Signup de Meta** (flujo oficial OAuth-like de WhatsApp
  Business Cloud API): el administrador, desde un panel de Desk nuevo
  (`nexora-conversation-channels`, mismo patrón que `nexora-ai-providers` del Bloque
  5.2), inicia sesión con su cuenta de WhatsApp Business y Meta devuelve un código que el
  backend intercambia por un token de acceso de larga duración, un `waba_id` y un
  `phone_number_id` — sin que ningún número o token se escriba jamás en código, commit,
  log o documentación.
- **Almacenamiento de credenciales**: se reutiliza exactamente el patrón ya certificado
  de `intelligence/credentials.py` + `intelligence/runtime.py` — variable de entorno
  primero (bootstrap), `Password` fieldtype cifrado en base de datos después (nuevo
  `NXR Channel Credential`, mismo mecanismo que `NXR AI Provider Credential`). Nunca se
  expone en ninguna respuesta.
- **Reemplazo de cuenta sin reprogramar**: como con los proveedores de IA, cambiar la
  cuenta de WhatsApp Business es una operación administrativa (reconectar) — cero código
  nuevo, porque el adaptador solo lee la credencial activa.
- **Webhook** (`nexora.conversation.channels.whatsapp.webhook`, `@frappe.whitelist`,
  público pero verificado): la verificación inicial de Meta (`GET` con
  `hub.challenge`) y el verify token de la app se validan contra la credencial
  almacenada; los eventos `POST` verifican la firma `X-Hub-Signature-256` (HMAC-SHA256
  con el app secret) antes de aceptar cualquier payload — un mensaje sin firma válida
  nunca llega al núcleo conversacional.
- **Salida**: `POST /{phone_number_id}/messages` de la Graph API oficial de Meta.
- **Evidencia por WhatsApp**: `financial/evidence.py` ya declara `"WhatsApp"` como canal
  permitido de `NXR Evidence` (`ALLOWED_CHANNELS`) — este bloque conecta ese valor, que
  ya existía sin consumidor real, a su primer consumidor real: una foto/factura recibida
  por WhatsApp se registra como `NXR Evidence` con `channel="WhatsApp"`,
  `sender`/`source_message_date` tomados del propio mensaje, sin ampliar el DocType.

Este sub-bloque requiere credenciales reales de Meta que solo el propietario puede
generar (cuenta de WhatsApp Business, app de Meta, verify token) — el código deja
exactamente el espacio de conexión descrito arriba, sin bloquear el resto del sistema
mientras esas credenciales no existan.

## Seguridad

- **Identidad nunca implícita**: un mensaje de un número/canal sin `NXR Channel Account`
  vinculado y verificado no tiene usuario NEXORA asociado — el núcleo responde pidiendo
  que un administrador lo conecte y no evalúa ninguna intención.
- **Permisos**: cada intención declara la acción de `permissions.ACTION_ROLES` que ya
  gobierna esa operación en la UI — no hay una segunda tabla de permisos para el chat.
- **Confirmación obligatoria** para toda intención marcada `requires_confirmation` — sin
  excepción, incluida cualquier automatización (siguiente sección).
- **Auditoría total**: cada mensaje, cada intención resuelta, cada confirmación, cada
  ejecución y cada rechazo por permisos queda en `NXR Audit Event` vía la misma
  `financial.db.audit` — un auditor revisando la bitácora ve el origen conversacional
  igual que vería cualquier otro origen.
- **Evidencia asociada**: cuando una operación se origina en una foto/documento recibido
  por un canal, ese archivo se registra como `NXR Evidence` antes de referenciarse desde
  la operación — nunca como un adjunto suelto sin trazabilidad.

## Automatizaciones (diseño; implementación en sub-bloque posterior a 11.3)

Motor basado en el *scheduler* de Frappe (`hooks.py: scheduler_events`, mecanismo nativo
ya usado en el resto del ecosistema Frappe/ERPNext — no se introduce un segundo
programador de tareas). Cada regla de automatización:

- Detecta un evento o condición (vencimiento de compromiso, evidencia pendiente de
  revisión hace más de N días, anomalía simple de gasto) usando las mismas funciones de
  lectura (`list_*`, `get_*`) que ya existen — nunca una copia del cálculo.
- Si la acción sugerida es informativa (recordatorio, resumen), se envía directamente por
  el canal del usuario.
- Si la acción sugerida sería una operación real, el motor **prepara** un
  `NXR Conversation Pending Intent` en estado `AwaitingConfirmation` (nunca `Confirmed`) y
  se lo presenta al usuario responsable por el canal — la ejecución sigue exactamente el
  mismo camino de confirmación humana del flujo conversacional normal. Ninguna
  automatización ejecuta una operación crítica sin que un humano autorizado confirme.

## Qué se implementa en cada sub-bloque interno

| Sub-bloque | Contenido | Estado |
| --- | --- | --- |
| 11.1 | Modelo de datos (4 DocTypes), `conversation/core.py` (puro: slots, confirmación, fusión de payload), `conversation/registry.py` (catálogo inicial, 5 intenciones reales), `conversation/dispatch.py` (motor de despacho channel-agnostic: ingesta, permisos, preview/confirm/execute, auditoría), acciones nuevas en `permissions.py`, pruebas puras. Sin canal conectado todavía — se ejerce con mensajes canónicos construidos directamente, como el resto de NIP se ejerció con dobles de prueba antes de tener un proveedor real conectado. | Este documento + implementación que sigue |
| 11.2 | Adaptador WhatsApp Business Cloud API: Embedded Signup, `NXR Channel Credential`, webhook firmado, envío saliente, panel de conexión en Desk. | Pendiente — requiere credenciales reales de Meta que solo el propietario puede emitir |
| 11.3 | `conversation/nlu.py`: construcción del prompt de sistema desde el `Registry`, llamada a `intelligence.orchestrator.execute`, parseo y validación estricta de la respuesta JSON contra el esquema de la intención elegida. | Pendiente |
| 11.4 | Motor de automatizaciones vía scheduler + expansión del `Registry` a compras, inventario, presupuestos, directorio. | Pendiente |

## Limitaciones de este entorno (reales, no supuestas)

Idénticas a las ya documentadas en `EXECUTION_STATE.md` para todos los bloques NIP
anteriores: este sandbox no tiene `bench`/Frappe ni MariaDB, así que los DocTypes nuevos
no se pueden migrar ni ejercer contra un sitio real aquí — se valida lo que es puro
Python (igual que `orchestrator_core.py`/`prompt_optimizer.py` en el Bloque 5.2) y se
deja el resto a la batería de aceptación real de CI (`NEXORA financial invariants`,
`NEXORA app`), que sí corre contra Frappe/MariaDB reales. WhatsApp Business Cloud API no
se puede probar en vivo sin que el propietario complete el Embedded Signup con su propia
cuenta — el Bloque 11.2 deja el mecanismo de conexión listo, no una prueba en vivo.
