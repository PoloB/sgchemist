"""Definition of a mock engine that can be used for testing."""

from __future__ import annotations

import collections
from typing import Any
from typing import TypeVar

from sgchemist.orm import SgBaseEntity
from sgchemist.orm.constant import BatchRequestType
from sgchemist.orm.engine import SgEngine
from sgchemist.orm.entity import SgEntityMeta
from sgchemist.orm.query import SgBatchQuery
from sgchemist.orm.query import SgFindQueryData
from sgchemist.orm.query import SgSummarizeQueryData

T = TypeVar("T", bound=SgBaseEntity)


class MockEngine(SgEngine):
    """A mock engine that can be used for testing."""

    def __init__(self) -> None:
        """Initialize the mock engine."""
        self._entities: dict[str, SgEntityMeta] = {}
        self._db: dict[str, dict[int, SgBaseEntity]] = collections.defaultdict(dict)

    def register_base(self, entity: SgEntityMeta) -> None:
        """Register an entity."""
        if not entity.__is_base__:
            raise ValueError(
                f"Base entity {entity.__name__} is not a subclass of {SgBaseEntity.__name__}"
            )
        for sub_entity in entity.__registry__.values():
            self._entities[sub_entity.__sg_type__] = sub_entity

    def find(self, query: SgFindQueryData[type[T]]) -> list[dict[str, Any]]:
        """Execute a find query."""
        # Make sure the entity is registered
        entity = query.entity
        if entity.__sg_type__ not in self._entities:
            raise ValueError(f"Entity {entity.__sg_type__} is not registered")

        # Filter all the entities
        filter_entities = []
        for inst in self._db.get(entity.__sg_type__, {}).values():
            if query.condition.matches(inst):
                filter_entities.append(inst.as_dict())
        return filter_entities

    def summarize(self, query: SgSummarizeQueryData[type[T]]) -> dict[str, Any]:
        """Execute a summary query."""

    def batch(
        self, batch_queries: list[SgBatchQuery]
    ) -> list[tuple[bool, dict[str, Any]]]:
        """Execute a batch query."""
        results = []
        for batch_query in batch_queries:
            request_type = batch_query.request_type
            entity = batch_query.entity
            if request_type == BatchRequestType.CREATE:
                self._db[entity.__sg_type__][entity.id] = entity
                results.append((True, entity.as_dict()))
            elif request_type == BatchRequestType.UPDATE:
                results.append((True, entity.as_dict()))
            elif request_type == BatchRequestType.DELETE:
                self._db[entity.__sg_type__].pop(entity.id)
                results.append((True, entity.as_dict()))
        return results
