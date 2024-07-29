"""Definition of a mock engine that can be used for testing."""

from __future__ import annotations

import collections
from typing import Any
from typing import TypeVar

from sgchemist.orm import SgBaseEntity
from sgchemist.orm import field_info
from sgchemist.orm.constant import BatchRequestType
from sgchemist.orm.engine import SgEngine
from sgchemist.orm.entity import SgEntityMeta
from sgchemist.orm.query import SgBatchQuery
from sgchemist.orm.query import SgFindQueryData
from sgchemist.orm.query import SgSummarizeQueryData
from sgchemist.orm.queryop import SgGroupingField
from sgchemist.orm.queryop import SgSummaryField
from sgchemist.orm.serializer import serialize_entity

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
                f"Base entity {entity.__name__} is not a subclass of "
                f"{SgBaseEntity.__name__}"
            )
        for sub_entity in entity.__registry__.values():
            self._entities[sub_entity.__sg_type__] = sub_entity

    def _serialize_entity(
        self,
        entity: SgBaseEntity,
        query: SgFindQueryData[Any],
        as_relationship: bool = False,
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
            raise ValueError(f"Entity {entity.__sg_type__} is not registered")

        # Filter all the entities
        filter_entities = []
        for inst in self._db.get(entity.__sg_type__, {}).values():
            if not query.condition.matches(inst):
                continue

            # Get the serialized entity
            serialized_entity = self._serialize_entity(inst, query)
            filter_entities.append(serialized_entity)
        return filter_entities

    def summarize(self, query: SgSummarizeQueryData[type[T]]) -> dict[str, Any]:
        """Execute a summary query."""
        entity = query.entity
        if entity.__sg_type__ not in self._entities:
            raise ValueError(f"Entity {entity.__sg_type__} is not registered")

        def _summarize(
            instances: list[SgBaseEntity], summaries: list[SgSummaryField[Any, Any]]
        ) -> dict[str, Any]:
            group_summaries = {}
            for summary_field in summaries:
                field_name = field_info.get_name(summary_field.field)
                field_summary = summary_field.sum_up(instances)
                group_summaries[field_name] = field_summary
            return group_summaries

        def _group(
            instances: list[SgBaseEntity],
            summaries: list[SgSummaryField[Any, Any]],
            groups: list[SgGroupingField[Any, Any]],
        ) -> list[dict[str, Any]]:
            if not groups:
                return []

            group_data = []
            group_on = groups[0]
            instances_per_group = collections.defaultdict(list)
            for inst_ in instances:
                group_key = group_on.get_group_key(inst_)
                instances_per_group[group_key].append(inst_)

            for group_key, grouped_instances in instances_per_group.items():
                sub_groups = _group(grouped_instances, summaries, groups[1:])
                group_dict = {
                    "group_name": group_key if group_key is not None else "",
                    "group_value": group_key,
                    "summaries": _summarize(grouped_instances, summaries),
                }
                if sub_groups:
                    group_dict["groups"] = sub_groups
                group_data.append(group_dict)
            return group_data

        # Aggregate the results per group
        matching_instances = []
        for inst in self._db.get(entity.__sg_type__, {}).values():
            if not query.condition.matches(inst):
                continue
            matching_instances.append(inst)

        full_data: dict[str, Any] = {
            "summaries": _summarize(matching_instances, list(query.fields)),
        }
        if query.grouping_fields:
            full_data["groups"] = _group(
                matching_instances, list(query.fields), list(query.grouping_fields)
            )
        return full_data

    def batch(
        self, batch_queries: list[SgBatchQuery]
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
