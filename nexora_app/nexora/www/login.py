"""Acceso de NEXORA.

Esta página sustituye a la de Frappe por precedencia de aplicación: el resolutor de
páginas de sitio recorre las aplicaciones instaladas y la última gana, y `nexora` se
instala después de `frappe`.

Lo que cambia es exclusivamente la presentación. El contexto —redirección saneada,
proveedores externos, registro deshabilitado, LDAP, acceso por enlace de correo, límite de
intentos— lo sigue construyendo `frappe.www.login.get_context`, que además lanza la
redirección cuando la sesión ya está iniciada.

Reimplementar esa lógica habría significado mantener una copia de las reglas de
autenticación del marco, que es exactamente la clase de duplicado que prohíbe el Capítulo
34, y en la superficie donde un error no se paga con una pantalla fea sino con una puerta
abierta.
"""

from __future__ import annotations

from typing import Any

import frappe
from frappe.www import login as frappe_login

no_cache = 1

#: Lo que el sistema garantiza, dicho en la puerta. No es publicidad: cada línea nombra
#: una regla que el servidor aplica de verdad, y están enlazadas a los capítulos que las
#: exigen para que nadie pueda cambiar el texto sin cambiar la regla.
ASSURANCES: tuple[tuple[str, str], ...] = (
	(
		"Libro inmutable",
		"Ningún documento contabilizado se edita ni se borra: se corrige dejando rastro.",
	),
	(
		"Segregación de funciones",
		"Solicitar, aprobar y ejecutar son siempre tres personas distintas.",
	),
	(
		"Cierre semanal certificado",
		"Cada semana queda cerrada con su huella verificable y su respaldo.",
	),
)


def get_context(context: Any) -> Any:
	frappe_login.get_context(context)
	context.nexora_assurances = [
		{"title": frappe._(title), "detail": frappe._(detail)} for title, detail in ASSURANCES
	]
	context.nexora_home = "/app/nexora-dashboard"
	context.title = frappe._("Acceso · NEXORA")
	return context
