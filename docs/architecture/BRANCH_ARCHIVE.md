# Archivo de ramas retiradas

El repositorio queda con una sola rama, `main` (c96ced6a), por decisión del responsable
del proyecto. Borrar una rama **no borra sus commits**: quedan alcanzables por su
identificador mientras GitHub no recoja basura, y este archivo conserva el extremo exacto
de cada una para poder devolverla en un solo comando.

Restaurar cualquiera:

```bash
git fetch origin <sha>
git branch <nombre> <sha>
git push -u origin <nombre>
```

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

## Qué significa la columna «commits fuera de `main`»

Cuenta los commits alcanzables desde la rama y no desde `main`. Un número alto no implica
trabajo valioso: casi todas parten de una base antigua y arrastran historia que después se
integró por otra vía. Ninguna se revisó una por una antes de retirarlas; por eso existe
este archivo.
