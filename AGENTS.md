# NEXORA — reglas obligatorias para agentes

> **Este documento está subordinado a [`NEXORA_CONSTITUTION.md`](NEXORA_CONSTITUTION.md)**,
> máxima autoridad técnica y funcional del proyecto. La Constitución define *qué* y *por
> qué*; este documento define *cómo* se opera en este repositorio. Ante cualquier
> contradicción prevalece la Constitución (Capítulo 72). Ninguna regla se duplica aquí: si
> la Constitución ya la fija, este documento la referencia.

## Enmienda del propietario — 2026-08-16

**Regla anterior:** "No se inicia otra auditoría general ni se reconstruye el producto
desde cero" y "No se crean fases, bloques ceremoniales ni fuentes de estado paralelas"
(más abajo en este documento) se interpretaban como bloqueo total a cualquier
reconstrucción de componentes existentes, incluso defectuosos.

**Decisión actual del propietario:** orden explícita y repetida (2026-08-16) de que
NEXORA debe quedar como un único producto consolidado — sin ConstruControl como
identidad visible, sin Frappe/ERPNext expuesto al usuario ordinario, con administración
funcional propia, con datos empresariales en cero en instalación limpia y con una
experiencia operativa fuertemente familiar a un ERP empresarial (referencia: SAP, sin
copiar sus activos). El propietario confirmó expresamente seguir operando dentro de este
repositorio (sin fases ceremoniales paralelas ni auditorías generales redundantes), pero
autorizó de forma explícita reconstruir, eliminar o consolidar cualquier componente que
no cumpla ese objetivo — la categoría de decisión que el Capítulo 5 de la Constitución
exige autorizar cuando implica "eliminar información irreversible" o "comprometer datos
reales" queda autorizada para este alcance.

**Conflicto:** las dos frases citadas arriba, leídas literalmente, impedirían ejecutar esa
orden.

**Resolución:** ambas reglas se acotan (no se eliminan) a lo que siguen previniendo de
forma legítima: no repetir una auditoría general completa como sustituto de trabajo real,
y no mantener dos sistemas de fases/estado corriendo en paralelo (`PLAN_MAESTRO.md` sigue
siendo la única fuente de fases). No impiden reconstruir, eliminar o consolidar
componentes concretos que no cumplan el objetivo del propietario, siempre que se
verifiquen dependencias antes de eliminar, se pruebe lo que el entorno permita probar y
quede documentado en `EXECUTION_STATE.md` con el mismo rigor de evidencia de siempre
(Capítulos 60/61 de la Constitución no se tocan: nada se declara `IMPLEMENTADO Y
VALIDADO` sin esa evidencia completa).

**Documentos actualizados por esta enmienda:** este archivo (las dos frases marcadas
abajo con referencia a esta sección), `PLAN_MAESTRO.md` (alcance de Fase 3 ampliado) y
`EXECUTION_STATE.md` (Bloque 47 registra esta decisión con su justificación completa).

## Identidad y fuente de verdad

El producto visible se llama **NEXORA — Gestión Integral de Fondos, Proyectos y Operaciones**.

- Repositorio único: `Clopezgg/Gesti-n-de-Construcci-n-Residencial`
- Rama final y fuente de verdad: `main`
- Motor interno: Frappe/ERPNext
- Producto visible para el usuario ordinario: NEXORA
- ConstruControl: referencia funcional y visual que debe integrarse en NEXORA, no un producto paralelo

El código publicado en `main` prevalece frente a documentos, auditorías o certificaciones históricas. Una afirmación documental no demuestra una función si no existe un recorrido funcional reproducible.

## Inicio obligatorio

Antes de modificar una función:

1. verificar el repositorio, la rama predeterminada y el HEAD remoto de `main`;
2. sincronizar el árbol local sin descartar cambios ajenos;
3. buscar globalmente código, historial, pruebas, páginas, DocTypes, servicios, hooks, fixtures, assets y workflows relacionados;
4. comparar el recorrido visible con la implementación de ConstruControl que pueda reutilizarse;
5. clasificar lo encontrado como conservar, corregir, integrar, simplificar, sustituir o retirar.

No se inicia otra auditoría general completa como sustituto de trabajo real, ni se
reconstruye el producto entero simultáneamente sin evidencia por bloque. Reconstruir,
eliminar o consolidar componentes concretos que no cumplan el objetivo del propietario sí
está autorizado — ver "Enmienda del propietario — 2026-08-16" arriba.

## Únicas fases de recuperación

### Fase 1 — Recuperación del producto principal

NEXORA debe ser el inicio, la navegación y la experiencia principal. Se integran dashboard, proyectos, fondos, operaciones, contratos, proveedores, evidencias, cuentas y reportes con español claro, diseño responsive y PWA segura.

### Fase 2 — Simplificación operativa

Los ingresos, remesas, depósitos, gastos, pagos y correcciones deben pedir solo datos conocidos por el usuario. El backend conserva trazabilidad, idempotencia, locks, secuencias, permisos, integridad, conciliación y rollback.

### Fase 3 — Integración y publicación definitiva

Se validan recorridos reales, permisos, saldos, errores, persistencia, escritorio, iPhone, PWA, instalación, migraciones, seguridad y CI completo.

No se crean sistemas de fases ni fuentes de estado paralelas a `PLAN_MAESTRO.md`/
`EXECUTION_STATE.md`: cualquier alcance nuevo (ver enmienda arriba) se incorpora a la
Fase 3 existente, no a una numeración de fases distinta.

## Principio funcional

«Terminado» lo define el **Capítulo 60 de la Constitución**, y su lista no se reproduce
aquí: dos copias de una misma regla se separan. Consúltela allí; si un punto falla, el
bloque continúa abierto.

Condiciones propias de este repositorio, adicionales a esa lista:

- se encuentra desde la navegación normal de NEXORA;
- usa lenguaje comprensible en español;
- funciona con datos reales;
- actualiza saldos, estados y relaciones;
- está incorporada y verificable en `main`.

Compilar, tener un DocType, una ruta o documentación no basta (Capítulo 61).

## Prohibiciones de arquitectura

- No crear otra aplicación, dashboard, navegación, ledger o fuente de saldos paralela.
- No duplicar servicios, DocTypes ni modelos financieros.
- No eliminar una implementación funcional sin demostrar su sustitución y preservar datos, permisos y relaciones.
- No exponer al usuario ordinario campos técnicos, IDs o configuraciones de Frappe que el sistema pueda derivar.
- No conservar el nombre ConstruControl como identidad del producto final.

## Git y publicación

Cada lote debe ser pequeño, coherente y recuperable:

1. revisar `git status` y `git diff`;
2. ejecutar pruebas dirigidas, validadores y formato;
3. crear un commit semántico;
4. publicar inmediatamente en `origin/main`;
5. confirmar que el SHA remoto de `main` contiene el cambio.

No acumular trabajo crítico sin commit y push. No afirmar que un cambio está realizado si solo existe localmente.

Si GitHub rechaza la escritura directa por protección real:

1. conservar el error exacto;
2. usar una sola rama transitoria para ese lote;
3. abrir un único PR hacia `main`;
4. validar y fusionar;
5. confirmar el SHA de `main`;
6. eliminar la rama transitoria cuando sea seguro.

Están prohibidos `git push --force`, `git reset --hard`, `git clean -fd`, rebases destructivos, borrados masivos, lectura o publicación de secretos y cambios de producción, AWS, Coolify o DNS sin autorización específica.

## Calidad

Corregir la causa raíz. No usar `continue-on-error`, exclusiones artificiales, pruebas vacías, mocks autorreferenciales ni silencios masivos.

Según el alcance, ejecutar:

- pruebas unitarias, de integración y negativas;
- validadores del repositorio y de NEXORA;
- sintaxis JavaScript y compilación Python;
- formatter, linter y análisis de seguridad;
- instalación/migración y rollback;
- pruebas visuales, responsive y PWA;
- GitHub Actions del mismo SHA.

La documentación posterior al cambio debe ser breve: problema, archivos, decisión, pruebas, SHA en `main` y limitaciones reales.

## Criterio final

NEXORA solo está terminada cuando sea inequívocamente el producto principal, ConstruControl esté absorbido, Frappe opere como motor interno, los flujos diarios sean sencillos, los saldos sean correctos, escritorio/iPhone/PWA estén validados, CI esté verde y no exista trabajo válido fuera de `main`.
