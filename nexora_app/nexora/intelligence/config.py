from __future__ import annotations

"""Configuración inicial del subsistema de inteligencia (Bloque 1).

Estos valores son los únicos que Provider Manager y Router asumen por
defecto cuando el llamante no especifica algo distinto. Ninguno apunta a un
proveedor real: el Bloque 1 no conecta ninguna credencial ni ejecuta ninguna
llamada externa. Cambiar un límite aquí es un cambio de configuración, no de
código en los módulos consumidores (NEXORA_INTELLIGENCE_ARCHITECTURE.md,
sección 3 — "Principios de diseño").
"""

DEFAULT_PROVIDER_STATUS = "Inactive"
DEFAULT_PROVIDER_PRIORITY = 100

MIN_PROVIDER_PRIORITY = 0
MAX_PROVIDER_PRIORITY = 1000

# Límite defensivo de proveedores configurables en este bloque. Provider
# Manager no necesita más para demostrar que el enrutamiento funciona con
# varios proveedores activos, y un límite explícito evita crecimiento sin
# control mientras no exista una pantalla de administración.
MAX_PROVIDERS_REGISTERED = 20

# Bloque 3 — valores por defecto de la configuración operativa de un
# proveedor cuando el registro no especifica algo distinto. Ninguno de estos
# valores conecta un proveedor real; son límites conservadores razonables
# para cuando el despacho real exista en un bloque futuro.
DEFAULT_TIMEOUT_SECONDS = 30
DEFAULT_TEMPERATURE = 0.2
DEFAULT_MAX_TOKENS = 1024
DEFAULT_COST_HINT = "Medium"
DEFAULT_VALIDATION_STATE = "Not Configured"
