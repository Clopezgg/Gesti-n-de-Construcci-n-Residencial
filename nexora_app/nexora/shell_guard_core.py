"""Lógica pura de la guarda de ruta del Desk crudo — sin Frappe, sin red (Bloque 154).

Frappe no distingue quién debería ver su escritorio genérico —listas de DocType,
formularios, ajustes— de quién solo debería ver las pantallas de NEXORA. Un rol NEXORA
sin `System Manager`/`NEXORA Administrator` que teclea `/app/user` o llega por un enlace
suelto aterriza en el Desk crudo del marco tal cual, sin ningún filtro (Bloque 150,
hallazgo auditado pero no implementado en su momento por su sensibilidad de seguridad).

Esta guarda NO sustituye al permiso real de cada DocType (`Role Permission Manager`):
quien ya tenga permiso de lectura sobre un DocType lo sigue teniendo vía API tal cual.
Es una capa de experiencia/defensa adicional que evita que un rol pensado exclusivamente
para las pantallas de NEXORA aterrice, por accidente o por un enlace suelto, en la
pantalla equivocada del marco.

Deja pasar dos familias de ruta, no solo una: `/app/nexora-*` (las pantallas propias,
páginas de Frappe) y `/app/nxr-*` (las vistas de formulario nativas de los DocType de
NEXORA — `NXR Contract`, `NXR Operation`, `NXR Fund Source`, `NXR Entity Compliance`,
`NXR Monthly Close`, `NXR Weekly Close` — a las que varias pantallas ya enlazan de verdad
vía `frappe.utils.get_form_link()`). Bloquear solo `/app/nexora-*` habría roto esos
enlaces reales para cualquier rol sin admin, la primera vez que alguien pulsara "ver
contrato" desde el panel ejecutivo.

`resolve_redirect()` vive separado de cualquier llamada a `frappe.*` a propósito, mismo
patrón que `nexora.administration.core`: para poder probarse sola con `pytest` normal,
sin necesitar un sitio Frappe real disponible. `nexora.shell_guard.enforce()` es el
envoltorio delgado que sí toca Frappe, y llama a esta función para decidir.
"""

from __future__ import annotations

from collections.abc import Iterable

#: Duplicado deliberado de `nexora.permissions.ACCESS_ROLES`/`ADMINISTRATOR_ONLY_ROLES`
#: — mismo patrón que `nexora.administration.core.ALLOWED_NEXORA_ROLES`: este módulo no
#: importa `nexora.permissions` (que sí importa Frappe) para poder probarse solo, sin
#: sitio real. Deben mantenerse sincronizados a mano si cambia el catálogo de roles.
ACCESS_ROLES = {
	"System Manager",
	"NEXORA Administrator",
	"NEXORA Finance Manager",
	"NEXORA Finance Operator",
	"NEXORA Auditor",
	"NEXORA Project Viewer",
}
ADMINISTRATOR_ONLY_ROLES = {"System Manager", "NEXORA Administrator"}

#: A dónde vuelve un rol NEXORA sin acceso de administrador que aterriza en una
#: pantalla cruda del Desk. Mismo destino que `role_home_page` en `hooks.py` para
#: cada uno de esos roles.
NEXORA_HOME = "/app/nexora-dashboard"

#: Prefijos de ruta que un rol NEXORA sin acceso de administrador sí puede alcanzar
#: dentro de `/app/`. Ver docstring del módulo.
ALLOWED_APP_PREFIXES = ("/app/nexora-", "/app/nxr-")


def resolve_redirect(path: str, roles: Iterable[str]) -> str | None:
	"""Decide si `path` debe rebotar a `NEXORA_HOME` para este conjunto de roles."""
	role_set = set(roles)
	if not role_set & ACCESS_ROLES:
		# Ni siquiera es un usuario de NEXORA — fuera del alcance de esta guarda; el
		# resto del Desk sigue rigiéndose por sus propios permisos de siempre.
		return None
	if role_set & ADMINISTRATOR_ONLY_ROLES:
		# System Manager / NEXORA Administrator: el Desk es su herramienta de verdad,
		# tal como ya documenta `nexora_shell.js` (regla 1 de convivencia con Frappe).
		return None
	normalized = (path or "").split("?", 1)[0].rstrip("/").lower()
	if not normalized.startswith("/app"):
		return None
	if normalized in ("", "/app"):
		# La raíz ya resuelve por `role_home_page` de `hooks.py`.
		return None
	if normalized.startswith(ALLOWED_APP_PREFIXES):
		return None
	return NEXORA_HOME
