# Auditoría de `consolidation/construcontrol-canonical-20260719`

Fecha de revisión: 2026-07-20. Rama canónica comparada: `reconstruccion-definitiva-construcontrol` en `6678c04878be3e6f87d88a871f068e9555415380`.

## Identidad y alcance

- HEAD de consolidación: `7d1d91159110ea5405c79fec1661386c70f14462`.
- Árbol de consolidación: `e4c93c5ed167812260e5012e93d5c0578c27df1b`.
- Base común: `657ac685bb8131f602100137fe5f3161d504e70f`.
- Divergencia: 345 commits exclusivos de la rama canónica y 36 de consolidación.
- Diferencia de árboles desde el HEAD canónico: 20 adiciones, 90 eliminaciones y 57 modificaciones.
- SHA-256 del manifiesto ordenado de los 36 commits (`%H\t%s\n`): `5960e57058c55f0d3c2915d15e93ad8715a47c8133a3aa8b574f30991190835e`.

## Resultado por grupo de contenido

| Contenido exclusivo | Evidencia | Decisión |
|---|---|---|
| 16 archivos bajo `.github/consolidation/` | Son marcadores y doce fragmentos de un ejecutor temporal. `APPLY` declara como fuente el SHA canónico y un artifact efímero. | No portar: infraestructura transitoria y peligrosa para un repositorio con escritor único. |
| Doce fragmentos `part-*.patch` | Concatenación binaria: 84,104 bytes, 1,071 saltos de línea, SHA-256 `24660726616ead1b8db73854976ba3dc9529893eec09ad85feadc7e9a97af4ec`. `git apply --check` termina en `corrupt patch at <stdin>:1072`; el último cambio queda truncado. | No portar como lote. Revisar únicamente cambios completos y ejecutables. |
| Página `construcontrol-weekly-closing` | El árbol canónico la reemplazó por `construcontrol-closing-center`; `page_registry.py` la marca retirada y las pruebas de registro/browser exigen su ausencia. | No portar: duplicaría CL01 y rompería la regla de ocho páginas. |
| Tres bridges JavaScript de perfil, integraciones y reportes | Las rutas ya son directas en `construcontrol_mobile.js`, las páginas canónicas y el centro de reportes; los bridges añadirían listeners globales duplicados. | No portar: contenido superado. |
| Traducción de estados del centro de proyecto | Cambio completo, independiente y coherente con la UX en español. | Portado a la página canónica con la acción `Actualizar resumen` y etiquetas localizadas. |
| Cambio de migración operativa | Importa `erpnext.construcontrol.financial_rules`, módulo ausente en el árbol de consolidación y en el canónico, por lo que no es ejecutable. El fragmento mezcla además cambios funcionales con líneas compactas que Ruff rechaza. | No portar. Reimplementar contra las fuentes canónicas existentes y cubrir con pruebas dirigidas. |
| Eliminación de `phase_status.json` | Es el único fragmento adicional aplicable de forma aislada, pero elimina evidencia de fase antes de la certificación final. | No portar hasta que la política de terminado permita retirar ese marcador. |
| Versiones modificadas de 57 archivos y ausencia de 90 archivos canónicos | La consolidación parte de una topología anterior y elimina validadores, Gate C, auditoría 1:1, runtime smoke, PWA y módulos de dominio presentes en el HEAD canónico. | No usar como árbol fuente ni efectuar merge/cherry-pick. |

## Manifiesto de commits exclusivos

Los 36 commits forman una única operación de staging/ejecución, no 36 cambios funcionales independientes:

```text
cbb24c7504b2302edf69ea291e39eddb0db61c32 b4acb6c8bb23c67a13668debe1e191487b796194
e0c1337e79b7b12c25115af12969d2dd2fdc1102 0593f0a658d63394d6bd347630063392f5e2ec21
15ce218e3adea5804a86433a07fd21a7c0cb7958 ea615dcdf8e35f199c2066aa49247ef42c59abc9
8d10c55c360347d591093284d80560f023d4e715 1cb7ea186ee48d809094b966ee65871057436cfd
c484c4614cda1ee0c73496becfe3c98d35ed5c58 acd528000983f22e7ead7f59c7e1fb431897bbc5
7f0ca94cfb027a36631d5b56e9e925fb81d9adbf a5b8dbbf50f5951014d62dfb5759ad19f5860ffe
d912f0f564cda24e22644eb9fd878cfea3bfac52 6152b24e73ba35ba5bf9009dc936ecfa2caa1cf4
b1061ec4f652cd07a3d1f05df010e4deae21ae66 01ef7ea35d6e5ee4ee67278dddef128e3b74aee0
f223dca737270efcfd201f971d9d3eead68a2b37 bd84667b093cbeae902749550784e808aa8a394e
df82f11fc030a7ebc2ef2262980048dcfb5ec487 c77f755c647aa92fcbdd2209612350ace9ce054a
73ff26139ba5e4c4353ad0f1b3a9a69a4bd5640b 48f11599ea4df5900b339191189dcbd2cb4ee1cd
1896c55c1320f93a5106a0b9fe0407690c64547d b3339270c4e6b777de1d9f3bc1c3b80d07e996b6
a2be9827cee6b99b0856782664e4054595bf9733 c375437980583656a6a6012904ecb0f796ef79f2
e538a19ce9da0cc23dda826790e6db9b9750c6c2 3743aaf92ea97aa2153764265b35db01523a89b4
709d46107fe27d019e4109c364d2aa1951597041 cb1c9e22824e717f42ef5b35024163e04a25b25d
409a149885b5465166d9613892c03911fda541eb fd860b022073a4a85c5f2618cb21cd822ac824f5
1df9298466725e7b044409669c2273af0ec0612c 553be816665a92f53f8323594e09deeb272a48d6
8cf8e8e4f9869b8e63cf3c55e7fb3ace3bf212a2 7d1d91159110ea5405c79fec1661386c70f14462
```

Conclusión: no queda contenido ejecutable válido de esa rama que deba fusionarse como unidad. La única mejora aislada y segura identificada se portó manualmente; la rama puede eliminarse únicamente después de la fusión y certificación completa del SHA final.
