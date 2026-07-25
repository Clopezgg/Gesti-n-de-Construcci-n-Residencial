from __future__ import annotations

from collections.abc import Mapping

NOTIFICATION_CHANNELS = frozenset({"Inbox", "Email", "PWA"})
NOTIFICATION_PRIORITIES = frozenset({"Low", "Normal", "High", "Critical"})


class NotificationError(ValueError):
	pass


def validate_channel(channel: str) -> None:
	if channel not in NOTIFICATION_CHANNELS:
		raise NotificationError(f"Canal desconocido: {channel}")


def validate_priority(priority: str) -> None:
	if priority not in NOTIFICATION_PRIORITIES:
		raise NotificationError(f"Prioridad desconocida: {priority}")


def render_template(template: str, context: Mapping[str, str]) -> str:
	return template.format(**context)
