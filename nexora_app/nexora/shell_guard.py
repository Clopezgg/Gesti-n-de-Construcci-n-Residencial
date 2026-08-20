"""Envoltorio delgado de `nexora.shell_guard_core` para el hook `update_website_context` (Bloque 154).

Toda la decisión —qué ruta bloquear, para quién, a dónde redirigir— vive en
`nexora.shell_guard_core.resolve_redirect()`, una función pura sin ningún `import frappe`. Este
módulo es el único punto que sí toca Frappe: lee la sesión y el `request` reales y traduce la
decisión en una redirección real.

Registrado en `update_website_context`, no en `before_request` (intento anterior de este mismo
bloque, revertido tras un fallo real de CI). Razón, verificada contra el código real de Frappe
15.x (`frappe/app.py`, `frappe/website/serve.py`, `frappe/website/path_resolver.py`,
`frappe/website/page_renderers/{template_page,base_template_page}.py`):

- `before_request` corre dentro de `init_request()`, que Frappe llama desde el manejador
  genérico de excepciones de `frappe/app.py::application()`. Ese manejador NO reconoce
  `frappe.Redirect` — cae al `else` final y sirve una página de error con un código 301 sin
  sentido, no una redirección real. Así es como falló de verdad en CI: la URL nunca cambiaba.
- `/app` se renderiza como cualquier otra página `www` vía `TemplatePage`, dentro del
  `try/except` de `frappe.website.serve.get_response()`, que SÍ reconoce `frappe.Redirect`
  específicamente y construye una `RedirectPage` real —el mismo mecanismo que ya usa
  `frappe.www.login.get_context()` para la redirección de sesión ya iniciada, documentado en
  `www/login.py`.
- `update_website_context` corre dentro de `BaseTemplatePage.post_process_context()`, llamado
  por `TemplatePage.get_html()`, dentro de ese mismo `render()` protegido — para `/app` y para
  cualquier otra página `www` (incluida `/login`). `resolve_redirect()` ya se limita a rutas
  `/app/*`, así que en el resto de páginas esta guarda no hace nada.
- No hace falta sustituir `nexora/www/app.py`/`app.html`: `TemplatePage.set_template_path()`
  busca la plantilla en la app instalada más reciente que la tenga y solo entonces busca su
  `.py` compañero *dentro de esa misma app* — sin un `app.html` propio en `nexora`, un
  `nexora/www/app.py` nunca se habría ejecutado. `update_website_context` no tiene esa
  restricción: es un hook independiente de qué app resolvió la plantilla.
"""

from __future__ import annotations

from typing import Any

import frappe

from nexora.shell_guard_core import resolve_redirect


def enforce(context: Any = None) -> None:
	"""Hook de `update_website_context`. Ver docstring del módulo para el porqué."""
	if frappe.session.user == "Guest":
		return
	request = getattr(frappe.local, "request", None)
	if request is None:
		return
	target = resolve_redirect(request.path, frappe.get_roles(frappe.session.user))
	if not target:
		return
	frappe.redirect(target)
