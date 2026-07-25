from __future__ import annotations

from nexora.directory import service as _service


def bootstrap() -> None:
	"""Load the canonical directory API contract before request dispatch."""


assign_entity_role = _service.assign_entity_role
consolidate_entities = _service.consolidate_entities
create_entity = _service.create_entity
create_entity_compliance = _service.create_entity_compliance
detect_entity_duplicates = _service.detect_entity_duplicates
get_entity = _service.get_entity
list_entities = _service.list_entities
resolve_canonical_entity = _service.resolve_canonical_entity
search_entities = _service.search_entities
transition_entity = _service.transition_entity
transition_entity_compliance = _service.transition_entity_compliance
transition_entity_role = _service.transition_entity_role
update_entity = _service.update_entity

__all__ = [
	"assign_entity_role",
	"bootstrap",
	"consolidate_entities",
	"create_entity",
	"create_entity_compliance",
	"detect_entity_duplicates",
	"get_entity",
	"list_entities",
	"resolve_canonical_entity",
	"search_entities",
	"transition_entity",
	"transition_entity_compliance",
	"transition_entity_role",
	"update_entity",
]
