from __future__ import annotations

from collections.abc import Mapping

NOTIFICATION_CHANNELS = frozenset({"Inbox", "Email", "PWA", "WhatsApp"})
NOTIFICATION_PRIORITIES = frozenset({"Low", "Normal", "High", "Critical"})

# Bloque 23 (NXR-NOT-0006): distinción real entre "el registro existe" y
# "se entregó". Inbox/PWA se consideran entregados en el momento de crear el
# registro — la bandeja (dentro de la app o de la PWA instalada) ES el
# mecanismo de entrega, no hay un segundo paso de red que pueda fallar
# aparte. Email/WhatsApp exigen una llamada real a un canal externo que
# puede fallar de verdad — solo esos dos generan un intento de entrega
# separado, con su propio estado Delivered/Failed y posibilidad de reintento.
EXTERNAL_DELIVERY_CHANNELS = frozenset({"Email", "WhatsApp"})
MAX_DELIVERY_RETRIES = 3


class NotificationError(ValueError):
	pass


def validate_channel(channel: str) -> None:
	if channel not in NOTIFICATION_CHANNELS:
		raise NotificationError(f"Canal desconocido: {channel}")


def validate_priority(priority: str) -> None:
	if priority not in NOTIFICATION_PRIORITIES:
		raise NotificationError(f"Prioridad desconocida: {priority}")


def requires_external_delivery(channel: str) -> bool:
	return channel in EXTERNAL_DELIVERY_CHANNELS


def can_retry_delivery(retry_count: int) -> bool:
	return retry_count < MAX_DELIVERY_RETRIES


def render_template(template: str, context: Mapping[str, str]) -> str:
	return template.format(**context)
