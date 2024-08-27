"""Definition of a mock engine that can be used for testing."""

from __future__ import annotations

import collections
from typing import TYPE_CHECKING
from typing import Any
from typing import TypeVar

from sgchemist.orm import SgBaseEntity
from sgchemist.orm import field_info
from sgchemist.orm.constant import BatchRequestType
from sgchemist.orm.engine import SgEngine
from sgchemist.orm.serializer import serialize_entity

if TYPE_CHECKING:
    from sgchemist.orm.entity import SgEntityMeta
    from sgchemist.orm.query import SgBatchQuery
    from sgchemist.orm.query import SgFindQueryData

T = TypeVar("T", bound=SgBaseEntity)


class SgEntityNotRegisteredError(Exception):
    """Raised when an entity is not registered in the engine."""

    def __init__(self, entity: SgEntityMeta) -> None:
        """Initialize the exception."""
        super().__init__(f"Entity {entity} not registered in the engine.")


class SgEntityRegistrationError(Exception):
    """Raised when an entity cannot be registered in the engine."""

    def __init__(self, entity: SgEntityMeta) -> None:
        """Initialize the exception."""
        super().__init__(
            f"Base entity {entity.__name__} is not a subclass of "
            f"{SgBaseEntity.__name__}",
        )


class MockEngine(SgEngine):
    """A mock engine that can be used for testing."""

    def __init__(self) -> None:
        """Initialize the mock engine."""
        self._entities: dict[str, SgEntityMeta] = {}
        self._db: dict[str, dict[int, SgBaseEntity]] = collections.defaultdict(dict)

    def register_base(self, entity: SgEntityMeta) -> None:
        """Register an entity."""
        if not entity.__is_base__:
            raise SgEntityRegistrationError(entity)

        for sub_entity in entity.__registry__.values():
            self._entities[sub_entity.__sg_type__] = sub_entity

    def _serialize_entity(
        self,
        entity: SgBaseEntity,
        query: SgFindQueryData[Any],
        as_relationship: bool = False,  # noqa: FBT001, FBT002
    ) -> dict[str, Any]:
        data: dict[str, Any] = {"type": entity.__sg_type__}

        for field in query.fields:
            field_name = (
                field_info.get_name_in_relation(field)
                if as_relationship
                else field_info.get_name(field)
            )
            value = entity.get_value(field)
            value = field_info.cast_value_over(field.__info__, serialize_entity, value)
            data[field_name] = value

        for field in query.loading_fields:
            key = field_info.get_name(field)
            column_name, _, target_key = key.split(".")
            data[column_name][target_key] = entity.get_value(field)

        return data

    def find(self, query: SgFindQueryData[type[T]]) -> list[dict[str, Any]]:
        """Execute a find query."""
        # Make sure the entity is registered
        entity = query.entity
        if entity.__sg_type__ not in self._entities:
            raise SgEntityNotRegisteredError(entity)

        # Filter all the entities
        filter_entities = []
        for inst in self._db.get(entity.__sg_type__, {}).values():
            if not query.condition.matches(inst):
                continue

            # Get the serialized entity
            serialized_entity = self._serialize_entity(inst, query)
            filter_entities.append(serialized_entity)
        return filter_entities

    def batch(
        self,
        batch_queries: list[SgBatchQuery],
    ) -> list[tuple[bool, dict[str, Any]]]:
        """Execute a batch query."""
        results = []
        for batch_query in batch_queries:
            request_type = batch_query.request_type
            entity = batch_query.entity
            if request_type == BatchRequestType.CREATE:
                entity_db = self._db[entity.__sg_type__]
                entity_id = len(entity_db) + 1
                entity_db[entity_id] = entity
                entity_dict = entity.as_dict()
                entity_dict["id"] = entity_id
                results.append((True, entity_dict))
            elif request_type == BatchRequestType.UPDATE:
                results.append((True, entity.as_dict()))
            elif request_type == BatchRequestType.DELETE:
                assert entity.id is not None
                self._db[entity.__sg_type__].pop(entity.id)
                results.append((True, entity.as_dict()))
        return results
