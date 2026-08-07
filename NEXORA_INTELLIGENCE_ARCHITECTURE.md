# NEXORA Intelligence Platform (NIP) — Arquitectura oficial del subsistema de IA

> **Estado: propuesta de arquitectura, sin implementación.** Este documento no crea código,
> no modifica archivos de producción y no representa trabajo terminado. Está subordinado a
> [`NEXORA_CONSTITUTION.md`](NEXORA_CONSTITUTION.md) (máxima autoridad, Capítulo 72) y a
> [`AGENTS.md`](AGENTS.md). Ante cualquier contradicción, prevalece la Constitución. Se
> apoya en los patrones ya vigentes en `nexora_app/nexora/` (capas `core.py` / `service.py`
> / `api.py`, `require_action`, `service_write`, idempotencia, `NXR Audit Event`) en lugar
> de inventar convenciones nuevas.
>
> Queda a la espera de aprobación explícita antes de iniciar cualquier bloque de
> implementación (Capítulo 5: autorización requerida para introducir dependencias
> comerciales, credenciales inexistentes o cambios que afecten reglas financieras
> fundamentales — todos aplicables aquí).

---

## 1. Visión general

NEXORA Intelligence Platform (NIP) es la capa de inteligencia artificial transversal de
NEXORA. No es un chatbot añadido a una pantalla, no es una integración puntual con un
proveedor externo y no es un módulo aislado que otros módulos deban "consultar". Es un
**servicio de plataforma**, igual en jerarquía a lo que hoy son `financial/`, `directory/`
o `contracts/` dentro de `nexora_app/nexora/`, del cual el resto de módulos —presentes y
futuros— consumen capacidades de forma consistente.

La analogía correcta no es "NEXORA + IA". Es: **NIP es a la inteligencia lo que el Libro
Central (`NXR Operation Effect`) es a los fondos** — una fuente de servicio única,
auditable y con reglas que existen en un solo lugar (Capítulo 44), de la que todos los
módulos leen sin duplicar lógica.

NIP nunca es la fuente de verdad de un dato financiero, operativo o contractual. Los
DocTypes `NXR *` y las reglas de `financial/core.py` siguen siendo la única fuente
canónica (`docs/nexora/ARQUITECTURA.md` — "Fuentes canónicas"). NIP **usa, sugiere,
redacta, explica, extrae y automatiza sobre** esa fuente; nunca la sustituye ni crea una
paralela.

## 2. Objetivos

1. Ofrecer una única puerta de entrada (`AI Gateway`) para que cualquier módulo de NEXORA
   invoque capacidades de IA, sin que cada módulo implemente su propio cliente HTTP hacia
   un proveedor.
2. Desacoplar completamente NEXORA de cualquier proveedor de IA individual. Cambiar de
   proveedor, añadir uno nuevo o repartir tráfico entre varios debe ser un cambio de
   configuración, no de código en los módulos consumidores.
3. Permitir que la IA actúe sobre el sistema **sin adquirir privilegios propios**: toda
   acción que NIP ejecuta pasa por el mismo `require_action`, el mismo `service_write` y
   la misma auditoría que ya usan `financial/service.py`, `contracts/service.py`, etc.
4. Reducir carga cognitiva, clics y escritura del usuario (Capítulo 8), aplicado a
   escenarios reales: redactar un cierre semanal, explicar una variación presupuestal,
   extraer datos de una factura fotografiada, dictar un gasto de campo por voz.
5. Hacer que el costo, la latencia y la disponibilidad de IA sean gobernables: presupuesto
   por proveedor, límites de uso, *circuit breakers*, *fallback* entre proveedores.
6. Dejar trazabilidad completa de toda interacción con IA: quién preguntó, qué modelo
   respondió, qué herramientas se ejecutaron y con qué resultado (Capítulo 50).
7. Empezar pequeño y verificable: cada bloque del roadmap (sección 25) debe dejar una
   mejora perceptible y probada (Capítulo 11), nunca una plataforma completa "de un
   golpe".

## 3. Principios de diseño

- **Ningún privilegio propio.** NIP nunca escribe directamente sobre un DocType `NXR *`.
  Toda escritura ocurre exclusivamente a través de las funciones ya existentes en
  `service.py` de cada dominio, respetando `require_action`, `service_write`,
  idempotencia y las reglas de `financial/core.py`. La IA es un actor más frente a
  `permissions.py`, nunca un atajo alrededor de él.
- **Agnosticismo de proveedor real, no cosmético.** Ningún módulo de negocio importa un
  SDK de un proveedor de IA. Todos hablan con una interfaz interna estable (`AI Core`);
  el proveedor concreto es un detalle de configuración resuelto en tiempo de ejecución por
  el `AI Provider Manager` y el `Model Router`.
- **Una sola regla, un solo lugar (Capítulo 44).** No se crea un segundo sistema de
  auditoría, un segundo sistema de permisos ni un segundo motor de idempotencia. NIP
  extiende `NXR Audit Event`, `permissions.ACTION_ROLES` y el patrón
  `NXR Idempotency Record` — no los reemplaza ni los duplica.
- **Nada de datos reales sin decisión explícita.** Enviar información financiera,
  personal o contractual real a un proveedor externo es una decisión de producto, no una
  consecuencia automática de "tener IA activada". Por defecto, todo lo enviado a un
  proveedor externo se minimiza y se redacta (sección 17); habilitar el envío de datos
  reales sin redactar a un proveedor concreto requiere autorización explícita (Capítulo 5:
  "comprometer datos reales").
- **Degradación segura.** Si no hay proveedor configurado, si todos fallan, o si se agota
  el presupuesto, el ERP sigue funcionando exactamente igual que hoy sin IA. Ninguna
  función crítica de NEXORA depende de que la IA esté disponible.
- **Server-side siempre.** Ninguna clave, credencial o decisión de permiso vive en el
  frontend (Capítulos 45, 48, 49). El frontend solo conversa con `AI Gateway`, nunca
  directamente con un proveedor.
- **Determinismo donde importa.** Redacción, resumen y conversación pueden ser
  probabilísticos. Los cálculos financieros, saldos y validaciones de negocio nunca los
  produce un modelo de lenguaje: los produce `financial/core.py` como hoy. La IA puede
  *explicar* un saldo; nunca *calcula* un saldo.
- **Extensible sin romper lo existente.** Cada módulo nuevo se conecta a NIP publicando
  sus propias herramientas (`Tool Engine`, sección 12) sobre sus propias funciones de
  servicio ya existentes, sin que `nexora/intelligence/` necesite conocer los detalles
  internos de `financial`, `contracts`, `directory`, etc.
- **Sin dependencias comerciales obligatorias.** El sistema debe poder operar con un solo
  proveedor gratuito o de bajo costo configurado. No se fuerza la instalación de SDKs de
  proveedores no habilitados (imports perezosos, dependencias opcionales).

## 4. Arquitectura general

NIP se implementa como **un nuevo módulo de dominio dentro de la app Frappe existente
`nexora_app/nexora/`** — no como una segunda app, no como un microservicio externo, no
como un repositorio paralelo (Capítulo 55; AGENTS.md: "no crear otra aplicación... fuente
de saldos paralela"). Su ubicación propuesta es `nexora_app/nexora/intelligence/`,
siguiendo exactamente la misma partición en capas que ya usan `financial/`, `directory/`,
`contracts/` y `close/`:

```
nexora/intelligence/
├── core.py            reglas puras: validación de payload, políticas de redacción,
│                       selección de ruta — sin I/O, 100% testeable sin red
├── providers/          adaptadores por proveedor (uno por SDK), detrás de la
│                       interfaz interna común; carga perezosa
├── gateway.py          orquestación de una llamada de IA de extremo a extremo
├── router.py           Model Router: decide proveedor/modelo por tarea
├── prompts.py           Prompt Manager: resolución y versionado de plantillas
├── conversation.py      Conversation Engine
├── memory.py            Memory Engine
├── tools.py              Tool Engine: registro y ejecución de herramientas
├── automation.py         Automation Engine
├── vision.py             OCR/Vision
├── voice.py              Voice (STT/TTS)
├── agents.py              Agentes: composición de router + tools + memory
├── audit.py                puente hacia NXR Audit Event (no un ledger nuevo)
├── service.py               endpoints @frappe.whitelist, igual que otros dominios
└── api.py                    bootstrap para before_request, igual que contracts/api.py
```

Vista de capas (de arriba hacia abajo, cada capa solo conoce la inmediatamente inferior):

```
┌───────────────────────────────────────────────────────────────────────┐
│  Módulos NEXORA (financial, contracts, directory, inventory, close…)   │
│  — consumen NIP mediante llamadas a nexora.intelligence.service.*      │
└───────────────────────────────────────────────────────────────────────┘
                                   │
┌───────────────────────────────────────────────────────────────────────┐
│  AI Gateway            — punto único de entrada, permisos, idempotencia │
│  Conversation Engine   — sesiones e hilos                               │
│  Agentes               — orquestación de tareas compuestas              │
└───────────────────────────────────────────────────────────────────────┘
                                   │
┌───────────────────────────────────────────────────────────────────────┐
│  AI Core: Model Router · Prompt Manager · Memory Engine · Tool Engine   │
└───────────────────────────────────────────────────────────────────────┘
                                   │
┌───────────────────────────────────────────────────────────────────────┐
│  AI Provider Manager · API Key Manager                                 │
└───────────────────────────────────────────────────────────────────────┘
                                   │
┌───────────────────────────────────────────────────────────────────────┐
│  Adaptadores de proveedor (OpenAI, Anthropic, Google, local, …)        │
└───────────────────────────────────────────────────────────────────────┘
                                   │
                     Proveedores de IA externos / locales
```

Toda flecha hacia abajo es reemplazable sin tocar las capas de arriba. Toda flecha hacia
arriba (auditoría, permisos) es obligatoria y no se puede omitir en ninguna capa.

## 5. AI Core

`AI Core` es el conjunto de componentes internos que convierten "quiero que un modelo
haga X" en una llamada concreta, segura y auditada. Agrupa: `Model Router`, `Prompt
Manager`, `Memory Engine` y `Tool Engine` (secciones 8–12). No expone red directamente;
todo el tráfico externo pasa por `AI Provider Manager`. `AI Core` es puro en el sentido de
que sus decisiones (qué proveedor, qué prompt, qué herramientas están disponibles) son
reglas de negocio de NEXORA, testeables sin red — igual que `financial/core.py` no hace
I/O y `financial/service.py` sí.

## 6. AI Gateway

Punto único de entrada para **toda** interacción con IA en NEXORA, sin excepción. Ningún
módulo llama a un proveedor ni a `AI Provider Manager` directamente; todos pasan por
`nexora.intelligence.service` (mismo patrón que `nexora.financial.service`,
`nexora.contracts.service`, etc.).

Responsabilidades del Gateway, en orden, por cada llamada:

1. `parse_payload` del pedido (idéntico a `financial/db.py`).
2. `require_action(<acción de IA correspondiente>)` contra `permissions.ACTION_ROLES`
   (sección 15) — el usuario que invoca la IA debe tener el permiso, exactamente como si
   ejecutara la acción él mismo.
3. Idempotencia: `idempotency_key` + huella de payload contra `NXR Idempotency Record`,
   igual que cualquier operación financiera (`financial/db.start_idempotency`) — evita
   reintentos duplicados de una llamada costosa a un proveedor.
4. `correlation_id` propagado a toda la cadena (Model Router → Provider → Tool Engine →
   Audit Event), para poder reconstruir un flujo completo en auditoría.
5. Resolución de ruta vía `Model Router` (sección 9).
6. Ejecución con límites: timeout, reintentos acotados, *circuit breaker* por proveedor.
7. Si el modelo solicita ejecutar una herramienta, el Gateway delega en `Tool Engine`
   (sección 12) — nunca ejecuta la herramienta el propio adaptador de proveedor.
8. Registro en `NXR Audit Event` (o su extensión, sección 18) con actor, acción, huella
   de la solicitud, proveedor/modelo usado, tokens y costo, y resultado.
9. Respuesta al módulo llamante — nunca al proveedor externo directamente al usuario.

El Gateway es el único componente de NIP que un módulo de negocio necesita conocer.

## 7. AI Provider Manager

Registro y ciclo de vida de los proveedores de IA disponibles para NEXORA. Cada proveedor
configurado es un registro `NXR AI Provider` (sección 18), con el mismo espíritu que hoy
tiene `NXR Integration`: nombre, tipo, estado (`Active`/`Inactive`/`Error`/`Disabled`),
capacidades declaradas (texto, visión, voz, embeddings), límites de uso y estado de la
última prueba de conexión.

A diferencia de `NXR Integration` —cuyo campo `credentials` es texto plano en la base de
datos—, el Provider Manager exige que toda credencial de proveedor de IA use el
fieldtype nativo `Password` de Frappe (cifrado en reposo con la clave de cifrado del
sitio, la misma `FRAPPE_ENCRYPTION_KEY` que ya protege otros secretos) o, para el
proveedor por defecto de la plataforma, una variable de entorno exclusivamente de
servidor (mismo patrón que `SUPABASE_SERVER_KEY`: nunca `VITE_`, nunca expuesta al
cliente). Esta es una divergencia deliberada respecto al patrón actual de
`NXR Integration`, no una inconsistencia — ver sección 15.

El Provider Manager es responsable de:

- Instanciar el adaptador correcto (`providers/*.py`) solo cuando el proveedor está
  activo — sin cargar SDKs de proveedores no habilitados.
- Normalizar la interfaz de cada proveedor a un contrato interno único (texto, visión,
  voz, embeddings) para que `Model Router` y `Tool Engine` nunca conozcan diferencias
  entre proveedores.
- Exponer el estado operativo de cada proveedor (salud, cuota restante, error reciente)
  al `Model Router` para decisiones de enrutamiento y *fallback*.
- Redactar credenciales en cualquier log o evento de auditoría, reutilizando el patrón ya
  existente en `nexora.integrations.core.redact_credentials`.

## 8. API Key Manager

Subcomponente del Provider Manager dedicado exclusivamente a credenciales, separado
porque las claves tienen un ciclo de vida propio (rotación, expiración, múltiples claves
por proveedor, límites de cuota por clave) distinto del ciclo de vida del proveedor en sí.

Responsabilidades:

- Resolución en capas: variable de entorno de servidor (plataforma) → clave específica de
  proyecto/tenant en `NXR AI Provider` (si NEXORA evoluciona a multi-tenant) → rechazo
  explícito si no hay clave disponible, nunca una llamada silenciosa sin autenticar.
- Rotación sin caída: permite registrar una clave nueva y desactivar la anterior sin
  interrumpir llamadas en curso.
- Cuotas y presupuesto: cada clave declara un límite de gasto o de solicitudes; al
  alcanzarlo, la clave se marca en `Error`/`Disabled` y el Model Router deja de
  enrutar hacia ella (nunca revienta el proveedor por sobreconsumo silencioso).
- Nunca se expone una clave completa fuera del backend: ni en logs, ni en
  `NXR Audit Event`, ni en el frontend. Solo se expone un identificador corto y el
  estado.
- Prohibido, por diseño: guardar una clave de IA en un `Data`/`Small Text` legible, en
  `site_config.json` versionado, en un `.env` trackeado o en cualquier respuesta JSON
  hacia el cliente.

## 9. Model Router

Decide, para cada solicitud del Gateway, qué combinación proveedor+modelo atenderla, sin
que el módulo llamante especifique un proveedor concreto — solo especifica una **tarea**
(`chat`, `resumen`, `extracción_estructurada`, `visión`, `transcripción`, `embeddings`).

Criterios de enrutamiento, configurables sin cambio de código (`NXR AI Model Route`,
sección 18):

1. Capacidad requerida por la tarea (no todo proveedor soporta visión o voz).
2. Disponibilidad y salud reportada por el Provider Manager.
3. Costo relativo y presupuesto restante del período.
4. Latencia esperada frente a la exigencia de la tarea (una automatización nocturna
   tolera más latencia que un chat interactivo).
5. Política explícita del módulo llamante (por ejemplo: un módulo financiero puede exigir
   "solo proveedores con retención de datos = ninguna").

Si el proveedor primario falla, el Router reintenta contra el siguiente proveedor de la
cadena de *fallback* configurada, reutilizando el mismo `idempotency_key` para que el
Gateway no facture ni ejecute dos veces la misma intención.

## 10. Prompt Manager

Fuente única de plantillas de instrucción, versionadas y auditable — evita que cada
módulo escriba su propio prompt suelto en código, lo que violaría "toda regla existe en
un único lugar" (Capítulo 44) en cuanto dos módulos necesiten el mismo tipo de tarea.

Cada plantilla (`NXR AI Prompt Template`, sección 18) declara:

- Módulo propietario (financial, contracts, directory, …) y tarea que resuelve.
- Versión y estado (`Draft`/`Active`/`Retired`) — cambiar el comportamiento de un prompt
  en producción es un cambio versionado, no una edición silenciosa.
- Esquema de variables de entrada (qué contexto puede inyectarse) y qué campos de ese
  contexto están permitidos frente a los que deben redactarse antes de salir al
  proveedor (enlaza con la política de minimización de datos, sección 15).
- Rol mínimo requerido para invocar esa plantilla, resuelto contra
  `permissions.ACTION_ROLES` — un prompt que puede sugerir una reclasificación contable
  requiere como mínimo el mismo rol que hoy exige `reclassify`.

El Prompt Manager nunca interpola datos financieros reales sin pasar por la política de
redacción del Gateway; solo resuelve la plantilla y sus variables permitidas.

## 11. Conversation Engine

Gestiona sesiones de conversación multi-turno, con contexto acotado por módulo, proyecto
y usuario. Modelo de datos: `NXR AI Conversation` (sesión) y
`NXR AI Conversation Message` (turno), siguiendo el mismo patrón de idempotencia y
correlación que el resto de DocTypes `NXR *`.

Reglas:

- Una conversación pertenece siempre a un usuario y, cuando aplica, a un proyecto — nunca
  es visible entre usuarios sin el mismo control de acceso que ya protege los datos
  subyacentes (`permissions.ACCESS_ROLES`).
- El historial de una conversación es contexto de la propia conversación, no memoria de
  largo plazo automática (eso es responsabilidad del `Memory Engine`, sección siguiente,
  y es opt-in).
- Cerrar/archivar una conversación no borra su rastro de auditoría — Capítulo 50: "nunca
  se elimina trazabilidad".

## 12. Memory Engine

El componente de mayor riesgo arquitectónico del sistema, porque una memoria mal diseñada
se convierte fácilmente en **una segunda fuente de verdad**, justo lo que la Constitución
prohíbe explícitamente (AGENTS.md: "no crear... fuente de saldos paralela";
`docs/nexora/ARQUITECTURA.md`: fuentes canónicas ya definidas). Principio rector: **la
memoria solo indexa y cita a la fuente canónica; nunca la reemplaza ni cachea un valor
financiero como si fuera verdad vigente**.

Dos niveles:

- **Memoria de corto plazo (conversacional):** ventana de contexto de la conversación
  activa, gestionada por `Conversation Engine`. Vive y muere con la conversación.
- **Memoria de largo plazo (recuperación):** índice de conocimiento no financiero
  (documentación de producto, políticas, decisiones históricas, resúmenes ya aprobados)
  para dar contexto a la IA sin reenviar documentos completos en cada llamada. Backend de
  recuperación agnóstico y plegable a lo disponible: se define una interfaz interna de
  "almacén de recuperación" con una implementación mínima basada en búsqueda de texto
  sobre MariaDB (sin dependencia de un motor vectorial comercial) y la posibilidad de
  conectar un backend vectorial dedicado más adelante como decisión explícita, no como
  requisito de la fase inicial.

Prohibido en cualquier nivel de memoria:

- Guardar un saldo, un estado de operación o cualquier dato de `financial/*` como valor
  cacheado que se sirva sin recalcularlo contra la fuente canónica en el momento de
  responder.
- Persistir datos financieros reales sin cifrado ni control de acceso equivalente al que
  ya protege el DocType de origen.
- Compartir memoria entre usuarios que no comparten permisos sobre los datos de origen.

## 13. Tool Engine

El mecanismo que permite que un modelo de IA **actúe** sobre NEXORA, y el punto donde se
aplica con más fuerza el principio de "ningún privilegio propio" (sección 3).

Una herramienta (`tool`) nunca es código nuevo que escriba directamente en un DocType.
Una herramienta es un **envoltorio delgado y explícito alrededor de una función que ya
existe** en el `service.py` de un dominio — la misma función que hoy invoca la interfaz
humana. Ejemplo conceptual (sin implementar): una herramienta "registrar gasto" no
contiene lógica de negocio propia; delega íntegramente en la función de
`financial/service.py` que ya valida permisos, estado, idempotencia y reglas del Libro
Central.

Consecuencias directas de este diseño:

- El Tool Engine ejecuta cada herramienta **en nombre del usuario que inició la
  conversación**, nunca con un usuario de sistema con privilegios ampliados. Si el
  usuario no tiene el rol requerido por `require_action` para esa acción, la herramienta
  falla exactamente igual que si el usuario la invocara desde la pantalla.
- Cada módulo publica su propio catálogo de herramientas (allow-list explícita), no hay
  un mecanismo genérico de "ejecutar cualquier función" ni acceso a shell, sistema de
  archivos o base de datos fuera de las funciones publicadas.
- Toda ejecución de herramienta genera, a través de la función de servicio subyacente,
  el mismo `NXR Audit Event` que generaría la acción manual — el Tool Engine no duplica
  auditoría, la hereda.
- Las herramientas se dividen en dos categorías con gobernanza distinta: **de lectura**
  (`preview`, `read_*` — pueden ejecutarse dentro de la propia conversación sin paso
  adicional) y **de escritura** (`create_*`, `approve`, `execute` — requieren
  confirmación humana explícita antes de ejecutarse, ver `Agentes`, sección 16).

## 14. Automation Engine

Permite disparar tareas de IA por evento o por calendario (por ejemplo: revisar
diariamente operaciones sin evidencia adjunta y notificar; redactar un borrador de cierre
semanal la noche antes de que el gerente lo revise). Modelo de datos:
`NXR AI Automation` (definición: disparador, módulo, herramientas permitidas, plantilla) y
`NXR AI Automation Run` (cada ejecución, con su resultado y su correlación de auditoría).

Regla no negociable: **una automatización puede generar una propuesta, un borrador o una
notificación de forma autónoma; nunca puede ejecutar una herramienta de escritura sin
aprobación humana**, salvo que la propia herramienta ya sea de solo lectura. Esto respeta
el mismo principio que ya rige `save_closing`, `approve` y `reconcile_source` en
`permissions.ACTION_ROLES`: son acciones de rol gerencial, y una automatización no es un
gerente.

## 15. OCR/Vision

Extracción de datos estructurados desde imágenes y documentos (facturas, recibos,
avances fotográficos de obra) que hoy ya se suben como evidencia
(`financial/evidence.py`, `NXR Evidence`, `NXR Contract Evidence`, y el almacenamiento
Supabase-como-origen-histórico documentado en `erpnext/construcontrol/storage/supabase.py`
para el flujo heredado).

Flujo: la evidencia se sube exactamente por el mecanismo ya existente (sin cambios en
cómo se almacenan archivos); OCR/Vision procesa el archivo ya almacenado y produce una
**propuesta estructurada adjunta a esa evidencia** (montos, fecha, proveedor sugeridos),
nunca un registro financiero directo. La confirmación humana, a través del flujo
existente de creación de gasto/operación, es la que efectivamente crea el registro —
OCR/Vision reduce escritura (Capítulo 8), no reemplaza la validación de servidor
(Capítulo 45).

## 16. Voice

Transcripción de voz a texto (para captura rápida de operaciones en campo, alineado con
la filosofía de operaciones guiadas ya presente en `nexora_guided_operations.js`) y,
opcionalmente, texto a voz para accesibilidad. Igual que OCR/Vision, Voice solo produce
**texto candidato** que entra al flujo normal de captura guiada — nunca ejecuta una
operación financiera directamente desde una transcripción sin el paso de confirmación
humana ya existente en los flujos guiados.

## 17. Agentes

Un "agente" en NIP es una composición con propósito acotado de `Model Router` + `Prompt
Manager` + `Memory Engine` (opcional) + un **subconjunto explícito y mínimo** de
herramientas del `Tool Engine` — nunca acceso al catálogo completo de herramientas del
sistema. Ejemplos de alcance (no de implementación): un agente de conciliación que solo
tiene herramientas de lectura sobre `financial` y una de "marcar para revisión humana"; un
agente de cierre semanal asistido que solo puede leer datos de cierre y redactar (nunca
"guardar cierre", acción reservada a `save_closing`/`MANAGER_ROLES`).

Principios de diseño de agentes:

- Mínimo privilegio por diseño: el conjunto de herramientas de un agente se declara de
  forma explícita en su definición, no se infiere ni se amplía en tiempo de ejecución.
  - Ningún agente tiene una herramienta de "ejecutar código arbitrario" ni de acceso
  directo a la base de datos.
- Un agente nunca actúa con más permiso del que tiene el usuario o el proceso que lo
  invocó — hereda el principio de la sección 13.
- Toda ejecución de un agente queda correlacionada de principio a fin bajo un único
  `correlation_id`, visible en auditoría como una sola cadena de eventos.

## 18. Seguridad

- **Sin secretos en el cliente.** Ninguna clave de proveedor, prompt interno ni política
  de redacción se envía jamás al frontend. El navegador solo habla con `AI Gateway` vía
  los mismos endpoints `@frappe.whitelist` que usa el resto de NEXORA.
- **Minimización de datos hacia proveedores externos.** Por defecto, toda solicitud que
  sale de NEXORA hacia un proveedor pasa por una política de redacción (extensión del
  patrón ya existente en `nexora.integrations.core.redact_credentials`) que enmascara
  identificadores sensibles, montos exactos cuando la tarea no los requiere, y datos
  personales fuera del mínimo necesario para la tarea. Enviar datos reales sin redactar a
  un proveedor concreto es una configuración explícita por proveedor, documentada y
  autorizada (Capítulo 5), no el comportamiento por defecto.
- **Aislamiento frente a instrucciones no confiables (prompt injection).** Todo contenido
  que no provenga del propio sistema — texto de un usuario, resultado de OCR, contenido
  de un documento recuperado por el Memory Engine, salida de una herramienta — se trata
  siempre como **dato**, nunca como instrucción con la misma autoridad que el prompt del
  sistema. El Tool Engine no interpreta texto libre como una autorización de ejecución:
  toda ejecución de herramienta de escritura pasa por la validación estructurada de
  `require_action`, no por que el modelo "lo haya dicho".
- **Sin controles de seguridad solo visuales.** Igual que el resto de NEXORA (Capítulo
  48), ocultar un botón de chat o de automatización en el frontend no es una medida de
  seguridad: el backend valida rol y acción en cada llamada, sin excepción.
- **Límites de consumo por defecto.** Toda clave y todo proveedor tienen un límite de
  gasto/solicitudes; agotarlo detiene las llamadas hacia ese proveedor sin afectar al
  resto del ERP (principio de degradación segura, sección 3).
- **Cadena de suministro de proveedores.** Ningún SDK de proveedor se instala como
  dependencia obligatoria del paquete `nexora`; se declara opcional y se importa de forma
  perezosa solo si el proveedor correspondiente está activo, evitando ampliar la
  superficie de dependencias para instalaciones que no usan ese proveedor.

## 19. Auditoría

NIP no crea un sistema de auditoría paralelo. Extiende `NXR Audit Event` con nuevos
valores de `event_type` (por ejemplo: `ai.gateway.call`, `ai.tool.invoked`,
`ai.automation.run`) y reutiliza sus campos existentes (`actor`, `reference_doctype`,
`reference_name`, `payload_hash`, `before_json`/`after_json`, `correlation_id`).

Reglas específicas:

- El `actor` de un evento de IA es siempre el usuario humano que originó la solicitud (o,
  para una automatización programada, el usuario de sistema que la Constitución ya
  reconozca para ese propósito) — nunca "la IA" como actor abstracto sin persona
  responsable detrás.
- Toda ejecución de herramienta de escritura queda auditada dos veces por diseño y sin
  redundancia real: una vez como evento del Gateway (qué se pidió a la IA) y una vez como
  el evento normal que ya genera la función de servicio subyacente (qué se ejecutó) — la
  correlación (`correlation_id`) es lo que une ambos, no una duplicación de la regla.
- Se registran modelo, proveedor, tokens/costo y latencia por llamada, para permitir
  control de presupuesto y detección de anomalías de uso — sin registrar el contenido
  completo de datos sensibles enviados o recibidos; se registra huella (`payload_hash`) y
  un extracto no sensible, igual que ya hace `NXR Audit Event` con `before_json`/
  `after_json` para otras operaciones.
- Ningún evento de auditoría de IA es editable ni eliminable, igual que hoy `NXR Audit
  Event` no admite `write` para ningún rol (Capítulo 50: "nunca se elimina
  trazabilidad").

## 20. Permisos

NIP no introduce un sistema de permisos nuevo: añade acciones nuevas a
`permissions.ACTION_ROLES`, resueltas por los mismos roles que ya existen
(`NEXORA Administrator`, `NEXORA Finance Manager`, `NEXORA Finance Operator`,
`NEXORA Auditor`, `NEXORA Project Viewer`, `System Manager`). Propuesta de mapeo,
coherente con los niveles ya establecidos (`OPERATOR_ROLES`, `MANAGER_ROLES`,
`ACCESS_ROLES`):

| Acción propuesta | Rol mínimo requerido | Precedente equivalente |
|---|---|---|
| `ai_chat` | `ACCESS_ROLES` (cualquier rol NEXORA) | `preview` |
| `ai_use_tool_read` | `ACCESS_ROLES`, acotado por los permisos de lectura ya existentes sobre el dato consultado | `read_balances`, `read_entities` |
| `ai_use_tool_write` | El mismo rol que hoy exige la acción subyacente (p. ej. una herramienta que ejecuta `execute` exige `OPERATOR_ROLES`) | `execute`, `create_source` |
| `ai_manage_provider` | `MANAGER_ROLES` | `approve`, `save_closing` |
| `ai_manage_prompts` | `MANAGER_ROLES` | `reclassify` |
| `ai_manage_automation` | `MANAGER_ROLES` | `save_closing` |
| `ai_view_audit` | `REPORT_EXPORT_ROLES` (incluye `NEXORA Auditor`) | `export_reports` |

Ninguna herramienta de escritura obtiene un rol menor al que ya exige la acción
equivalente ejecutada por un humano — el Tool Engine consulta el mismo
`ACTION_ROLES`, nunca una copia relajada de él.

## 21. Integración con todos los módulos del ERP

Cada módulo de negocio (`financial`, `contracts`, `directory`, `inventory`, `close`,
`budget`, `dashboard`, `integrations`, y los que se añadan a futuro) se relaciona con NIP
exactamente en dos direcciones, sin acoplamiento adicional:

1. **Como consumidor:** llama a `nexora.intelligence.service.*` (el Gateway) para pedir
   una capacidad de IA (chat contextual, redacción, extracción, automatización),
   idéntico en forma a como hoy `contracts/api.py` llama a `contracts/service.py`.
2. **Como proveedor de herramientas:** publica, si le corresponde, un catálogo acotado de
   funciones ya existentes en su propio `service.py` como herramientas invocables por el
   Tool Engine — el módulo decide qué expone y con qué rol, `nexora/intelligence/` nunca
   conoce las reglas internas de `financial` o `contracts`, solo el contrato de la
   herramienta publicada.

`nexora/intelligence/` no importa lógica de negocio de otros dominios ni al revés —
respeta la misma independencia de capas que ya existe entre `financial/`, `directory/` y
`contracts/` hoy.

## 22. Modelo de datos

Nuevos DocTypes propuestos, todos bajo el módulo `NEXORA` y siguiendo la convención
`NXR *` ya vigente (autoname por hash donde corresponda, `track_changes`, permisos por
rol explícitos, campos de idempotencia/correlación donde aplique):

| DocType | Propósito | Notas de diseño |
|---|---|---|
| `NXR AI Provider` | Proveedor de IA configurado | Credencial en `Password` cifrado, nunca `Small Text`; estado, capacidades declaradas |
| `NXR AI Model Route` | Regla de enrutamiento por tarea | Config del Model Router, editable sin despliegue de código |
| `NXR AI Prompt Template` | Plantilla versionada | Estado `Draft`/`Active`/`Retired`; rol mínimo requerido |
| `NXR AI Conversation` | Sesión de conversación | Ligada a usuario y, si aplica, proyecto |
| `NXR AI Conversation Message` | Turno de conversación | Hijo de `NXR AI Conversation` |
| `NXR AI Tool` | Herramienta publicada por un módulo | Referencia a la función de servicio subyacente, rol mínimo, categoría lectura/escritura |
| `NXR AI Tool Invocation` | Registro de una ejecución de herramienta | Enlaza a la herramienta, a la conversación/automatización y al `NXR Audit Event` generado |
| `NXR AI Automation` | Definición de una automatización | Disparador, herramientas permitidas (solo lectura o con aprobación) |
| `NXR AI Automation Run` | Ejecución concreta de una automatización | Resultado, correlación |
| `NXR AI Usage` | Consumo agregado (tokens/costo) por proveedor/usuario/período | Base del control de presupuesto (sección 8) |

No se propone un DocType nuevo de auditoría: se extiende `NXR Audit Event` (sección 19),
en cumplimiento directo de "toda regla existe en un único lugar" (Capítulo 44).

## 23. Flujos principales

**Flujo A — Chat asistido dentro de un módulo.**
Usuario con sesión activa → módulo invoca `AI Gateway` con la tarea y contexto permitido
→ Gateway valida `require_action('ai_chat')` y idempotencia → `Model Router` selecciona
proveedor/modelo → `Prompt Manager` resuelve la plantilla → `Provider Manager` ejecuta la
llamada con la clave resuelta por `API Key Manager` → si la respuesta solicita una
herramienta, `Tool Engine` la ejecuta con los permisos del usuario → respuesta al módulo
→ `NXR Audit Event` registrado con `correlation_id` común a toda la cadena.

**Flujo B — Ingesta de evidencia con OCR.**
Usuario sube evidencia por el mecanismo ya existente → `OCR/Vision` procesa el archivo ya
almacenado → genera una propuesta estructurada adjunta a la evidencia → usuario revisa y
confirma → el flujo de creación de gasto/operación ya existente (`financial/service.py`)
crea el registro real, con las mismas validaciones de siempre.

**Flujo C — Automatización con aprobación humana.**
`Automation Engine` dispara por calendario o evento → `Agente` con herramientas de solo
lectura reúne información y redacta una propuesta → se notifica al rol gerencial
correspondiente vía `NXR Notification` (mecanismo ya existente) → el gerente aprueba desde
la pantalla normal de la acción (`approve`/`save_closing`) → la acción se ejecuta por el
camino habitual, no por el Automation Engine directamente.

**Flujo D — Fallback entre proveedores.**
`Model Router` envía la solicitud al proveedor primario → el proveedor falla o agota
cuota → `Provider Manager` marca el proveedor como degradado → `Model Router` reintenta
con el siguiente proveedor de la cadena de *fallback*, reutilizando el mismo
`idempotency_key` → si todos los proveedores fallan, el Gateway responde con un error
explícito y NEXORA continúa funcionando sin la capacidad de IA solicitada (degradación
segura, sección 3).

## 24. Riesgos

1. **Fuga de datos reales hacia proveedores externos.** Mitigado por la política de
   minimización/redacción por defecto (sección 18); requiere decisión explícita del
   propietario antes de habilitar envío de datos reales sin redactar a un proveedor
   concreto.
2. **Alucinación en contexto financiero.** Mitigado por el principio de determinismo
   (sección 3): ningún cálculo financiero lo produce un modelo; el modelo solo redacta o
   explica sobre datos ya calculados por `financial/core.py`.
3. **Memory Engine convertido en fuente de verdad paralela.** Riesgo arquitectónico más
   alto del diseño; mitigado explícitamente en la sección 12, pero requiere disciplina de
   implementación en cada bloque que lo toque.
4. **Prompt injection vía contenido no confiable** (OCR, documentos recuperados, texto
   libre de usuario). Mitigado por tratar todo contenido externo como dato, nunca como
   instrucción con autoridad de ejecución (sección 18).
5. **Costo no controlado.** Mitigado por límites de gasto por clave/proveedor (`API Key
   Manager`) y por `NXR AI Usage`, pero exige que el propietario defina presupuestos
   reales antes de habilitar tráfico de producción.
6. **Dependencia de disponibilidad de terceros.** Mitigado por el `Model Router` con
   *fallback* y por la degradación segura; no elimina el riesgo si un único proveedor
   está configurado.
7. **Latencia percibida en flujos interactivos.** Un chat o una extracción OCR más lentos
   que el resto de NEXORA pueden romper la percepción de "rendimiento" (Capítulo 38);
   requiere feedback visual de progreso, no solo backend correcto.
8. **Gobernanza erosionada si una herramienta de escritura se permite sin aprobación
   humana "por conveniencia".** Es el riesgo de que un bloque futuro relaje el principio
   de la sección 13 bajo presión de "que la IA sea más útil". Este documento fija ese
   límite como no negociable; cualquier excepción requiere modificar esta arquitectura de
   forma explícita, no una decisión de implementación silenciosa.
9. **Multiplicidad de SDKs de proveedor como superficie de mantenimiento.** Mitigado por
   dependencias opcionales e imports perezosos (sección 3), pero cada proveedor nuevo
   sigue siendo código a mantener.

## 25. Dependencias

- **Ninguna dependencia comercial obligatoria por defecto.** El sistema debe poder
  operar con un único proveedor de bajo costo o gratuito configurado; añadir SDKs de
  proveedores adicionales es una dependencia opcional instalada solo si ese proveedor se
  activa.
- **Reutiliza infraestructura ya existente:** `FRAPPE_ENCRYPTION_KEY` (cifrado de
  credenciales), el patrón de variables de entorno exclusivas de servidor ya usado por
  `SUPABASE_SERVER_KEY`, el mecanismo de notificaciones (`NXR Notification`), el
  almacenamiento de evidencia ya vigente para OCR/Vision.
- **No depende de un motor vectorial comercial** para su fase inicial (`Memory Engine`,
  sección 12); una implementación mínima sobre MariaDB es suficiente para arrancar. Un
  backend vectorial dedicado es una decisión futura explícita, no un requisito de
  arranque.
- **Decisión pendiente del propietario, no técnica:** qué proveedor(es) de IA se
  autorizan realmente para producción, y bajo qué condiciones de retención/privacidad de
  datos — este documento no elige un proveedor, define cómo NEXORA queda protegido sin
  importar cuál se elija.

## 26. Roadmap dividido por bloques implementables

Cada bloque, siguiendo el Capítulo 11, debe dejar una mejora perceptible, probada y
verificable en `main` antes de iniciar el siguiente. Ningún bloque implementa por
adelantado capacidades de un bloque posterior.

| Bloque | Contenido | Resultado verificable |
|---|---|---|
| **0** | Este documento de arquitectura | Aprobado por el propietario antes de tocar código |
| **1** | `AI Provider Manager` + `API Key Manager` + `AI Gateway` mínimo, un solo proveedor, sin UI visible | Una llamada de IA de prueba, auditada, con credencial cifrada — sin ningún módulo de negocio conectado aún |
| **2** | `Model Router` (aunque con un solo proveedor activo) + `Prompt Manager` + extensión de `NXR Audit Event` | Cambiar de modelo/proveedor es un cambio de configuración, verificado con una segunda credencial de prueba |
| **3** | `Conversation Engine` + primer punto de consumo real en un único módulo piloto (a elegir por prioridad de producto, Capítulo 64) | Un usuario con el rol adecuado puede sostener una conversación contextual en una pantalla real |
| **4** | `Tool Engine`, solo herramientas de **lectura** | La IA puede responder preguntas citando datos reales sin poder modificarlos |
| **5** | `Tool Engine`, herramientas de **escritura** con confirmación humana obligatoria, en el módulo piloto | La IA propone una acción; el usuario la confirma; se ejecuta por el camino de servicio ya existente y queda auditada |
| **6** | `OCR/Vision` sobre evidencia ya subida en el módulo piloto | Una evidencia fotografiada produce una propuesta de datos revisable, no un registro automático |
| **7** | `Memory Engine`, nivel de recuperación no financiero | La IA usa contexto histórico de producto sin cachear ningún saldo |
| **8** | `Automation Engine` + primer `Agente` con alcance mínimo, solo lectura y propuesta | Una automatización nocturna genera una notificación revisable, cero escrituras autónomas |
| **9** | `Voice` (STT) integrado a un flujo guiado existente | Un operador dicta un dato de campo que entra al flujo de captura ya existente |
| **10** | Expansión de `Tool Engine`/`Agentes` a los módulos restantes + control de costo maduro (`NXR AI Usage`, presupuestos por rol/módulo) | Cobertura de IA transversal real, con gasto gobernado y visible para `NEXORA Auditor` |

---

Documento en espera de aprobación. No se ha creado, modificado ni eliminado ningún otro
archivo del repositorio para producir esta propuesta.
