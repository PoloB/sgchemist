"""Implements an engine for the official Shotgrid API 3."""

from __future__ import annotations

from typing import TYPE_CHECKING
from typing import Any
from typing import TypeVar

from sgchemist.orm import SgBaseEntity
from sgchemist.orm import field_info
from sgchemist.orm.constant import BatchRequestType
from sgchemist.orm.engine import SgEngine
from sgchemist.orm.serializer import ShotgunAPIBatchQuerySerializer
from sgchemist.orm.serializer import ShotgunAPIObjectSerializer

if TYPE_CHECKING:
    import shotgun_api3

    from sgchemist.orm.query import SgBatchQuery
    from sgchemist.orm.query import SgFindQueryData

T = TypeVar("T", bound=SgBaseEntity)


class ShotgunAPIEngine(SgEngine):
    """Engine implementation based on shotgun-api3."""

    def __init__(self, shotgun_object: shotgun_api3.Shotgun) -> None:
        """Initialize the engine.

        Args:
            shotgun_object (shotgun_api3.Shotgun): Shotgun API object.
        """
        self._sg = shotgun_object
        self._query_serializer = ShotgunAPIObjectSerializer()
        self._batch_serializer = ShotgunAPIBatchQuerySerializer()

    def find(self, query: SgFindQueryData[type[T]]) -> list[dict[str, Any]]:
        """Execute a find query and return the rows.

        Args:
            query (SgFindQueryData): query state to execute.

        Returns:
            rows returned by the query.
        """
        model = query.entity
        field_by_name = {
            field_info.get_name(field): field
            for field in query.fields + query.loading_fields
        }
        orders = [
            {"field_name": field_info.get_name(field), "direction": direction.value}
            for field, direction in query.order_fields
        ]
        condition = query.condition
        filters = self._query_serializer.serialize_filter(condition)
        records: list[dict[str, Any]] = self._sg.find(
            entity_type=model.__sg_type__,
            filters=filters,
            fields=list(field_by_name),
            order=orders,
            limit=query.limit,
            retired_only=query.retired_only,
            page=query.page,
            include_archived_projects=query.include_archived_projects,
            additional_filter_presets=query.additional_filter_presets,
        )
        # Reorganize the row contents
        for field in query.loading_fields:
            key = field_info.get_name(field)
            column_name, _, target_key = key.split(".")
            for row in records:
                row[column_name][target_key] = row.pop(key)
        return records

    def batch(
        self,
        batch_queries: list[SgBatchQuery],
    ) -> list[tuple[bool, dict[str, Any]]]:
        """Execute a batch query and return the rows.

        Args:
            batch_queries: query state to execute.

        Returns:
            rows returned by the query.
        """
        serialized_batch = self._batch_serializer.serialize(batch_queries)
        returned_data = self._sg.batch(serialized_batch)
        rows: list[tuple[bool, dict[str, Any]]] = []
        for batch_index, batch in enumerate(batch_queries):
            record = returned_data[batch_index]
            # shotgun_api3 returns a list of bool to tell if the elements has been
            # deleted
            success = True
            if batch.request_type == BatchRequestType.DELETE:
                success = record
                record = {}
            rows.append((success, record))
        return rows
