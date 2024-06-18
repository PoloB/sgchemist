"""Definition of engines to communicate with the Shotgrid instance.

The engine is responsible for connecting to the Shotgrid instance and executing
the queries given by the Session object.

The engine ShotgunAPIEngine uses the python shotgun-api3 package.
You can reimplement a new engine using, for example, the REST api by subclassing the
SgEngine abstract class.
"""

from __future__ import annotations

import abc
from typing import List
from typing import Type
from typing import TypeVar

import shotgun_api3
from typing_extensions import TypedDict

from .constant import BatchRequestType
from .entity import SgEntity
from .query import SgBatchQuery
from .query import SgFindQueryData
from .row import SgRow
from .serializer import ShotgunAPIBatchQuerySerializer
from .serializer import ShotgunAPIObjectSerializer

T = TypeVar("T", bound=SgEntity)
SgRecord = TypedDict("SgRecord", {"type": str, "id": int}, total=False)


class SgEngine:
    """Abstract definition of an engine to communicate with Shotgun."""

    __metaclass__ = abc.ABCMeta

    @abc.abstractmethod
    def find(self, query: SgFindQueryData[Type[T]]) -> List[SgRow[T]]:
        """Execute a find query and return the rows.

        Each row is referring to a single Shotgrid entity.
        If an entity is referencing other nested entities, these entities are also
        returned as rows.

        Args:
            query (SgFindQueryData): query state to execute.

        Returns:
            list[SgRow]: rows returned by the query.
        """

    @abc.abstractmethod
    def batch(self, batch_queries: List[SgBatchQuery]) -> List[SgRow[SgEntity]]:
        """Execute a batch query and return the rows.

        Each row is referring to a single Shotgrid entity.
        If an entity is referencing other nested entities, these entities are also
        returned as rows.

        Args:
            batch_queries (SgFindQueryData): query state to execute.

        Returns:
            list[SgRow]: rows returned by the query.
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

    def find(self, query: SgFindQueryData[Type[T]]) -> List[SgRow[T]]:
        """Execute a find query and return the rows.

        Args:
            query (SgFindQueryData): query state to execute.

        Returns:
            list[SgRow]: rows returned by the query.
        """
        model = query.model
        field_by_name = {field.get_name(): field for field in query.fields}
        orders = [
            {"field_name": field.get_name(), "direction": direction.value}
            for field, direction in query.order_fields
        ]
        condition = query.condition
        filters = self._query_serializer.serialize_filter(condition)
        records: List[SgRecord] = self._sg.find(
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
        rows = []

        def _cast_record(rec: SgRecord) -> SgRow[T]:
            entity_name = rec["type"]
            sanitized_record = {}
            for column_name, column_value in rec.items():
                if column_name == "type":
                    continue
                field = field_by_name[column_name]
                column_value = (
                    field.cast_value_over(_cast_record, column_value)
                    if column_value is not None
                    else column_value
                )
                sanitized_record[column_name] = column_value
            return SgRow(entity_name, rec["id"], True, sanitized_record)

        for record in records:
            rows.append(_cast_record(record))
        return rows

    def batch(self, batch_queries: List[SgBatchQuery]) -> List[SgRow[SgEntity]]:
        """Execute a batch query and return the rows.

        Args:
            batch_queries (SgFindQueryData): query state to execute.

        Returns:
            list[SgRow]: rows returned by the query.
        """
        serialized_batch = self._batch_serializer.serialize(batch_queries)
        returned_data = self._sg.batch(serialized_batch)
        rows: List[SgRow[SgEntity]] = []
        for batch_index, batch in enumerate(batch_queries):
            record = returned_data[batch_index]
            entity = batch.entity
            # shotgun_api3 returns a list of bool to tell if the elements has been
            # deleted
            entity_name = entity.__sg_type__
            success = True
            if batch.request_type == BatchRequestType.DELETE:
                entity_id = entity.id
                success = record
                content = {}
            elif batch.request_type == BatchRequestType.CREATE:
                record.pop("type")
                entity_id = record["id"]
                content = record
            else:
                record.pop("type")
                content = record
                entity_id = record["id"]
            assert entity_id is not None
            rows.append(SgRow(entity_name, entity_id, success, content))
        return rows
