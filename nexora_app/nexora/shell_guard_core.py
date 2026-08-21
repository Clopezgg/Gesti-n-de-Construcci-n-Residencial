"""Lógica pura de la guarda de ruta del Desk crudo — sin Frappe, sin red (Bloque 154,
corregida en CORRECCIÓN ESTRUCTURAL DEL DESK FRAPPE).

Frappe no distingue quién debería ver su escritorio genérico —listas de DocType,
formularios, ajustes, Workspaces, el onboarding "Let's begin your journey with
ERPNext"— de quién solo debería ver las pantallas de NEXORA. Cualquier usuario de
NEXORA que teclea `/app/user`, `/app/home`, `/app/workspace`, o llega por un enlace
suelto, debe aterrizar en NEXORA, no en el Desk crudo del marco.

**Hallazgo real corregido en este bloque:** hasta ahora, `System Manager`/`NEXORA
Administrator` estaban completamente exentos de esta guarda —"el Desk es su
herramienta de verdad"—, y `role_home_page` (`hooks.py`) nunca tuvo una entrada para
`System Manager`. El usuario real "Administrator" (superusuario incorporado de
Frappe) siempre tiene el rol `System Manager`; sin ninguna de las dos correcciones,
ese usuario caía sin ningún filtro en el Workspace "Home" genérico de ERPNext. Esa
excepción se elimina aquí: ya no existe ningún rol de NEXORA exento de esta guarda.
Crear una cuenta de usuario nueva sigue siendo posible, pero como tarea de servidor
(`bench`), no de navegador — NEXORA todavía no tiene una función propia de alta de
usuarios (ver `nexora.administration.service`, que solo lista/edita cuentas ya
existentes).

Esta guarda NO sustituye al permiso real de cada DocType (`Role Permission Manager`):
quien ya tenga permiso de lectura sobre un DocType lo sigue teniendo vía API tal cual.
Es una capa de experiencia/defensa adicional que evita que cualquier usuario de NEXORA
aterrice, por accidente o por un enlace suelto, en la pantalla equivocada del marco.

Deja pasar dos familias de ruta, no solo una: `/app/nexora-*` (las pantallas propias,
páginas de Frappe) y `/app/nxr-*` (las vistas de formulario nativas de los DocType de
NEXORA — `NXR Contract`, `NXR Operation`, `NXR Fund Source`, `NXR Entity Compliance`,
`NXR Monthly Close`, `NXR Weekly Close` — a las que varias pantallas ya enlazan de verdad
vía `frappe.utils.get_form_link()`). Bloquear solo `/app/nexora-*` habría roto esos
enlaces reales para cualquier rol, la primera vez que alguien pulsara "ver contrato"
desde el panel ejecutivo.

`resolve_redirect()` vive separado de cualquier llamada a `frappe.*` a propósito, mismo
patrón que `nexora.administration.core`: para poder probarse sola con `pytest` normal,
sin necesitar un sitio Frappe real disponible. `nexora.shell_guard.enforce()` es el
envoltorio delgado que sí toca Frappe, y llama a esta función para decidir.
"""

from __future__ import annotations

from collections.abc import Iterable

#: Duplicado deliberado de `nexora.permissions.ACCESS_ROLES` — mismo patrón que
#: `nexora.administration.core.ALLOWED_NEXORA_ROLES`: este módulo no importa
#: `nexora.permissions` (que sí importa Frappe) para poder probarse solo, sin sitio
#: real. Debe mantenerse sincronizado a mano si cambia el catálogo de roles.
ACCESS_ROLES = {
	"System Manager",
	"NEXORA Administrator",
	"NEXORA Finance Manager",
	"NEXORA Finance Operator",
	"NEXORA Auditor",
	"NEXORA Project Viewer",
}

#: A dónde vuelve cualquier rol de NEXORA que aterriza en una pantalla cruda del
#: Desk — sin excepción de rol. Mismo destino que `role_home_page` en `hooks.py`
#: para cada uno de esos roles, `System Manager` incluido.
NEXORA_HOME = "/app/nexora-dashboard"

#: Prefijos de ruta que cualquier rol de NEXORA sí puede alcanzar dentro de `/app/`.
#: Ver docstring del módulo.
ALLOWED_APP_PREFIXES = ("/app/nexora-", "/app/nxr-")


def resolve_redirect(path: str, roles: Iterable[str]) -> str | None:
	"""Decide si `path` debe rebotar a `NEXORA_HOME` para este conjunto de roles."""
	role_set = set(roles)
	if not role_set & ACCESS_ROLES:
		# Ni siquiera es un usuario de NEXORA — fuera del alcance de esta guarda; el
		# resto del Desk sigue rigiéndose por sus propios permisos de siempre.
		return None
	normalized = (path or "").split("?", 1)[0].rstrip("/").lower()
	if not normalized.startswith("/app"):
		return None
	if normalized in ("", "/app"):
		# La raíz ya resuelve por `role_home_page` de `hooks.py` (ahora con entrada
		# real para `System Manager` también — ver docstring del módulo).
		return None
	if normalized.startswith(ALLOWED_APP_PREFIXES):
		return None
	return NEXORA_HOME
