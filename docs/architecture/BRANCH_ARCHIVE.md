# Archivo de ramas retiradas

El repositorio queda con una sola rama, `main`, por decisión del responsable del
proyecto. Borrar una rama **no borra sus commits**: quedan alcanzables por su
identificador mientras GitHub no recoja basura, y este archivo conserva el extremo exacto
de cada una para poder devolverla en un solo comando.

Restaurar cualquiera:

```bash
git fetch origin <sha>
git branch <nombre> <sha>
git push -u origin <nombre>
```

## Retiro 2026-08-07 (Bloque Final — consolidación definitiva)

A diferencia del retiro de 2026-08-05 (más abajo), esta vez **cada rama se revisó
individualmente antes de borrarla**: PR asociado (fusionado/cerrado, vía `gh pr list
--state all`), diff de contenido único (`git diff main...<rama>`), y en los casos no
triviales, comparación de contenido byte a byte contra `main` o contra la rama que la
superseó. Ninguna se borró solo por tener un PR cerrado — se verificó qué contenía.

**Ramas fusionadas en esta sesión antes de retirarse** (contenido 100% confirmado en
`main` vía el PR indicado, squash-merge):

| Rama | PR | Commit de squash en `main` |
|---|---|---|
| `feat/nip-block1-ai-gateway-provider-manager` … `feat/nip-block5.2-orchestrator-omniroute-integration` (6 ramas, Bloques NIP 1–5.3) | #86 | `f63f86e4` |
| `docs/nip-block6-close-execution-state` | #87 | `d5e4938f` |
| `docs/nip-architecture` (`NEXORA_INTELLIGENCE_ARCHITECTURE.md`, citado por el propio código de `nexora/intelligence/`) | #75 | `a51095a2` |
| `claude/nexora-surgical-audit-lsxcuh` (recorrido de las ocho operaciones del Capítulo 53) | #72 | `d0a3758c` |
| `docs/analisis-inicial` | ya era antecesor de la rama NIP antes de este bloque | — |

**Ramas retiradas del retiro de 2026-08-05 que en realidad nunca se habían borrado**
(el `git push origin --delete` de esa fecha, documentado abajo, no llegó a ejecutarse o
no se completó — las 29 ramas seguían presentes en `origin` el 2026-08-07, con el mismo
SHA exacto de punta, confirmado antes de borrarlas ahora):

- Ancestros directos de `main` (contenido ya integrado por su propio commit, sin squash):
  `fix/nexora-date-string-normalization`, `fix/nexora-predeploy-block-1b`,
  `nexora-block1-identity`.
- Fusionadas por squash en su momento (`gh pr list --state all` confirma `MERGED`):
  `chore/nexora-consolidacion-total` (#35), `copilot/fix-failing-github-actions-job`
  (#40), `fix/guided-expense-account-mode-sync` (#45), `fix/multiple-frontend-bugs`
  (#47), `refactor/nexora-shared-format-helpers` (#65).
- Cerradas sin fusionar, contenido verificado como ya superseded/incorporado por otra
  vía antes de borrar (evidencia puntual, no solo el estado del PR):
  - `fix/remediation-1b4c5852-76f698`: su única función nueva
    (`_ensure_demo_entity` en `financial/seeds.py`) ya existe en `main` — confirmado con
    `grep` de la función en ambos árboles.
  - `fix/remediation-5f50ae47-f5336f`: diff contra `refactor/nexora-shared-format-helpers`
    (ya fusionada, #65) y contra `main` en `nexora_report_actions.js` — **vacío en ambos
    casos**, confirmando que su sugerencia se incorporó antes del merge de esa rama.
  - `fix/remediation-a7b66b3a-311b69`: sus cambios a `PROJECT_RECONSTRUCTION.md`/
    `ROADMAP.md` quedaron superados por una versión mucho más completa ya presente en
    `claude/nexora-surgical-audit-lsxcuh` (Bloque 32, ya fusionado vía #72).
  - `nexora/bloque-2-auditoria` y sus remediaciones (`fix/remediation-96a0e1b5-471bf3`,
    `fix/remediation-a5eb7470-0fdc7f`): los `__init__.py` de DocType que tocaban
    (`nxr_stock_transaction`, `nxr_supplier_quotation`, `nxr_warehouse`, etc.) ya existen
    en `main` — confirmado archivo por archivo.
  - `fix/remediation-8540136b-851362`, `fix/remediation-87b55af6-17e808`,
    `fix/remediation-87b55af6-c00e30`, `fix/remediation-96a0e1b5-471bf3`,
    `fix/remediation-a5eb7470-0fdc7f`, `fix/remediation-fc491a70-9f48b6`: solo tocaban
    `docs/architecture/file_inventory.json` (manifiesto autogenerado, ya regenerado
    muchas veces desde entonces) o archivos ya presentes en `main`.
  - `git-checkout--b-prueba-chatgpt-review`, `revert-35-chore/nexora-consolidacion-total`
    y `fix/remediation-1b4c5852-76f698` introducían `.github/workflows/cr.yml` (un
    revisor alternativo basado en ChatGPT vía `OPENAI_API_KEY`) — deliberadamente no
    adoptado: `main` usa CodeRabbit como revisor automático, confirmado en el CI de
    cada PR fusionado en esta sesión.
  - `Clopezgg-patch-2` y `coderabbitai/chat/629d637`: contienen únicamente
    `.github/agents/my-agent.agent.md`, un borrador de persona de agente que nunca llegó
    a fusionarse a `main` (PR #54 cerrado explícitamente). No se resucitó por decisión
    propia — si se quiere en `main`, es una decisión aparte del propietario, no de este
    bloque de limpieza. Restaurable con el comando de arriba usando el SHA
    `b45e9334621671dc629385729e5f4f07c9a8e8a0`.
  - El resto (`Clopezgg-patch-1`, `codex/confirmar-conexion-al-repositorio`,
    `copilot/fix-predeploy-certification-receipt[-again]`,
    `fix/remediation-5a58c127-9cebe3`, `fix/remediation-5df79678-5733c7`,
    `fix/remediation-7b5eed8e-448d4f`, `fix/remediation-8b129dae-529f93`,
    `fix/remediation-d1139fe6-51a043`, `fix/remediation-de789703-34cc0f`,
    `jules-9380881044004388841-dd6a48c4`): intentos alternativos/duplicados de
    estabilizar `scripts/nexora_browser_smoke.mjs` o de expandir el mismo trabajo NIP ya
    fusionado por una vía distinta y posterior — superados, no perdidos.

**Tags de respaldo eliminados en el mismo bloque** (los 14 `archive/*`, todos de
2026-07-26): eran puntos de restauración previos a operaciones de riesgo ya concluidas
con éxito (rollback, limpieza de historial) — 7 ya eran antecesores directos de `main`;
los otros 7 se verificaron contenido por contenido (`scripts/verify_nexora_deployment.py`,
`scripts/validate_nexora_operational_acceptance.py`) ya presentes en `main`. Se conservan
`construcontrol-v1.0.0`, `v1.0.0` y `nexora-final-validated-20260726` por ser hitos reales.

## Retiro 2026-08-05 (registro histórico original — nunca completado)

Fecha de retirada: 2026-08-05.
Ramas retiradas: 29. Commits fuera de `main`: 3243.

| Rama | Extremo | Commits fuera de `main` | Último commit |
|---|---|---|---|
| `Clopezgg-patch-1` | `1d9e9f007bbb3b43209f325e90e32ba023fbdded` | 36 | fix(ci): add auditable immutable-title exceptions for legacy sentry commits |
| `Clopezgg-patch-2` | `b45e9334621671dc629385729e5f4f07c9a8e8a0` | 2 | 📝 CodeRabbit Chat: Actualizar instrucciones del agente my-agent (#57) |
| `chore/nexora-consolidacion-total` | `9d651153bc9e1b75f867140fff586ed7680f9651` | 12 | test(nexora): report why the guided review never validates |
| `claude/nexora-surgical-audit-lsxcuh` | `c0d4ea5e53c065e48c1dd883d11faab8480493d3` | 1 | docs(certificacion): registrar el recorrido verde con su evidencia |
| `coderabbitai/chat/629d637` | `51a8732a97b1213af27d05853306516bee711f32` | 2 | 📝 CodeRabbit Chat: Actualizar instrucciones del agente my-agent |
| `codex/confirmar-conexion-al-repositorio` | `15f81b4b2ea166c6ce30e225d20dca3addb04ca6` | 50 | Implement account selection in nexora smoke test |
| `copilot/fix-failing-github-actions-job` | `a4915ff17865bb41dd44501ce47371ff1321e191` | 45 | fix(nexora-smoke): avoid guided review stage-visibility race |
| `copilot/fix-predeploy-certification-receipt` | `ee5b93b92a45048d017959f4f2db05c615b58627` | 45 | Apply remaining changes |
| `copilot/fix-predeploy-certification-receipt-again` | `8979e83b620e9259d2d70549f8b921ab801588e8` | 45 | Apply remaining changes |
| `fix/guided-expense-account-mode-sync` | `58c5f16d11eddf12a5d81f7ff8d8b37ad245afbf` | 46 | fix(nexora): sync guided wizard account_mode with Frappe control state |
| `fix/multiple-frontend-bugs` | `428a16124b8cce08469167340cdbc80443e26b3c` | 47 | fix(nexora): read document_date from Frappe control, fix falsy display values, remove duplicate correction button |
| `fix/nexora-date-string-normalization` | `d0702d6402f56c91af73b4365d9788f6f4e90269` | 1308 | docs(nexora): record textual date correction evidence |
| `fix/nexora-predeploy-block-1b` | `7195766b148b32903bb5b0ebb3bc7de21a0eb1ef` | 1386 | fix(ux): validate segregation in guided expenses |
| `fix/remediation-1b4c5852-76f698` | `177fd9c8a4b7d8bb587f7e4bb60671887e31a9f3` | 17 | fix: Escape guided operation period |
| `fix/remediation-5a58c127-9cebe3` | `52e5df52731a4f8d14fe34328619a28e5b15d205` | 47 | fix: Fix malformed template interpolations |
| `fix/remediation-5df79678-5733c7` | `0b82566730e3dc06e50362dac6b07f80cd51bf27` | 47 | fix: Force New account mode before filling account name |
| `fix/remediation-5f50ae47-f5336f` | `9c15751a47ce00fa4ade51d82ba8e8e71a573ed7` | 3 | fix: Guard Nexora UI helper calls |
| `fix/remediation-87b55af6-17e808` | `622fd51d645f18bb00e8f65696fcc42c8062d870` | 2 | fix: Regenerate file inventory manifest |
| `fix/remediation-87b55af6-c00e30` | `5edd8f36826a45416cfc28e209eb08017ea06cf3` | 2 | fix: Regenerate file inventory manifest |
| `fix/remediation-96a0e1b5-471bf3` | `d63a7e9216dc4bce6a4d52e978cc50eb5e468b21` | 2 | fix: Regenerate file inventory manifest |
| `fix/remediation-a5eb7470-0fdc7f` | `5c5e576a80be4586e73b2127cd4fe57dd5b993cf` | 4 | fix: Add post-change documentation block |
| `fix/remediation-a7b66b3a-311b69` | `acd10473ef23ee09b0e2f39319717debee0fb96a` | 2 | fix: Unify review usability gating |
| `fix/remediation-d1139fe6-51a043` | `22df42f12d453b13a4d7f240607d2ca1272a4109` | 48 | fix: Fix malformed closest selectors |
| `git-checkout--b-prueba-chatgpt-review` | `b3df91bd198d13606aa8c08b76601ced0c8bfa07` | 14 | cr.yml |
| `jules-9380881044004388841-dd6a48c4` | `feaa338447578e170ebcb5fe884d0e396840a38f` | 10 | style(test): format scripts with pre-commit mirrors-prettier config |
| `nexora-block1-identity` | `18f7219a3ae4d566c502090b2543c84e11d89768` | 0 | docs(nexora): rename current tree validation workflow |
| `nexora/bloque-2-auditoria` | `cdd40bd840f3b83263504419e927749ef026546e` | 3 | Merge pull request #50 from Clopezgg/fix/remediation-96a0e1b5-471bf3 |
| `refactor/nexora-shared-format-helpers` | `e98021b05c26fb7789e7d02b80b1a71729975c68` | 2 | style(nexora): match prettier line-width formatting in nexora_report_actions.js |
| `revert-35-chore/nexora-consolidacion-total` | `d39751352bee2ce4f8bb73985d3a59fe70269591` | 15 | Revert "chore(nexora): consolidación total del repositorio y corrección de la fecha guiada" |

### Qué significa la columna «commits fuera de `main`»

Cuenta los commits alcanzables desde la rama y no desde `main`. Un número alto no implica
trabajo valioso: casi todas parten de una base antigua y arrastran historia que después se
integró por otra vía. **Ninguna se revisó una por una antes de "retirarlas" en 2026-08-05**
— por eso existía este archivo, y por eso el retiro de 2026-08-07 sí revisó cada una
individualmente antes de borrar de verdad.
