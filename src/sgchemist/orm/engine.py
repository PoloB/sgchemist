"""Definition of engines to communicate with the Shotgrid instance.

The engine is responsible for connecting to the Shotgrid instance and executing
the queries given by the Session object.

The engine ShotgunAPIEngine uses the python shotgun-api3 package.
You can reimplement a new engine using, for example, the REST api by subclassing the
SgEngine abstract class.
"""

from __future__ import annotations

import abc
from typing import Any
from typing import Type
from typing import TypeVar

import shotgun_api3

from . import field_info
from .constant import BatchRequestType
from .entity import SgBaseEntity
from .query import SgBatchQuery
from .query import SgFindQueryData
from .serializer import ShotgunAPIBatchQuerySerializer
from .serializer import ShotgunAPIObjectSerializer

T = TypeVar("T", bound=SgBaseEntity)


class SgEngine:
    """Abstract definition of an engine to communicate with Shotgun."""

    __metaclass__ = abc.ABCMeta

    @abc.abstractmethod
    def find(self, query: SgFindQueryData[Type[T]]) -> list[dict[str, Any]]:
        """Execute a find query and return the rows.

        Each row is referring to a single Shotgrid entity.
        If an entity is referencing other nested entities, these entities are also
        returned as rows.

        Args:
            query: query state to execute.
        """

    @abc.abstractmethod
    def batch(
        self, batch_queries: list[SgBatchQuery]
    ) -> list[tuple[bool, dict[str, Any]]]:
        """Execute a batch query and return the rows.

        Each row is referring to a single Shotgrid entity.
        If an entity is referencing other nested entities, these entities are also
        returned as rows.

        Args:
            batch_queries: query state to execute.
        """


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

    def find(self, query: SgFindQueryData[Type[T]]) -> list[dict[str, Any]]:
        """Execute a find query and return the rows.

        Args:
            query (SgFindQueryData): query state to execute.

        Returns:
            rows returned by the query.
        """
        model = query.model
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
        self, batch_queries: list[SgBatchQuery]
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
