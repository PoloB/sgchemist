"""Serializers to convert query object to shotgun-api3 query components."""

from __future__ import annotations

from typing import Any

from typing_extensions import TypedDict

from . import field_info
from .constant import BatchRequestType
from .entity import SgBaseEntity
from .fields import AbstractField
from .query import SgBatchQuery
from .queryop import SgFieldCondition
from .queryop import SgFilterObject
from .queryop import SgFilterOperation
from .queryop import SgNullCondition


class SerializedEntity(TypedDict):
    """Defines a serialized entity dict."""

    id: int
    type: str


class SerializedOperator(TypedDict):
    """Defines a serialized operator dict."""

    filter_operator: str
    filters: list[Any]


def serialize_entity(model: SgBaseEntity) -> SerializedEntity:
    """Serialize the given sgchemist entity to shotgun-api3 entity.

    Args:
        model: sgchemist entity to serialize

    Returns:
        serialized entity
    """
    assert model.id is not None
    return {"id": model.id, "type": model.__sg_type__}


def serialize_condition(
    condition: SgFieldCondition,
) -> tuple[str, str, Any]:
    """Serialize the given sgchemist condition to shotgun-api3 filter condition.

    Args:
        condition: sgchemist condition to serialize

    Returns:
        serialized condition
    """
    right = condition.right
    if isinstance(condition.right, SgBaseEntity):
        right = serialize_entity(condition.right)
    return (
        field_info.get_name(condition.field),
        condition.operator.value,
        right,
    )


class ShotgunAPIObjectSerializer:
    """Defines a serializer converting sgchemist objects to shotgun-api3 components."""

    def serialize_filter(
        self, sg_object: SgFilterObject | SgBaseEntity
    ) -> list[SerializedEntity | SerializedOperator | list[Any]]:
        """Returns filters for shotgun-api3 from the given sgchemist object.

        Args:
            sg_object: sgchemist object to serialize

        Returns:
            list of serialized objects
        """
        if isinstance(sg_object, SgNullCondition):
            return []
        return [self.serialize_object(sg_object)]

    def serialize_object(
        self, sg_object: SgFilterObject | SgBaseEntity
    ) -> SerializedEntity | SerializedOperator | list[Any]:
        """Serialize the given sgchemist object to shotgun-api3 object.

        Args:
            sg_object: sgchemist object to serialize

        Returns:
            serialized object
        """
        if isinstance(sg_object, SgFieldCondition):
            return list(serialize_condition(sg_object))
        elif isinstance(sg_object, SgBaseEntity):
            return serialize_entity(sg_object)
        elif isinstance(sg_object, SgFilterOperation):
            return self.serialize_operation(sg_object)
        raise AssertionError(
            f"Cannot serialize object of type {type(sg_object)}"
        )  # pragma: no cover

    def serialize_operation(
        self, filter_operator: SgFilterOperation
    ) -> SerializedOperator:
        """Serialize the given sgchemist operation to shotgun-api3 logical operator.

        Args:
            filter_operator: sgchemist operator to serialize

        Returns:
            serialized operator
        """
        return {
            "filter_operator": filter_operator.operator.value,
            "filters": [
                self.serialize_object(obj) for obj in filter_operator.sg_objects
            ],
        }


class SerializedBatchQueryCreate(TypedDict):
    """Defines the content of a batch query create."""

    request_type: str
    entity_type: str


class SerializedBatchQueryUpdate(TypedDict):
    """Defines the content of a batch query update."""

    request_type: str
    entity_type: str
    entity_id: int
    data: dict[str, Any]


class ShotgunAPIBatchQuerySerializer:
    """Defines a serializer converting sgchemist batch query to shotgun-api3 queries."""

    @staticmethod
    def serialize_entity(
        entity: SgBaseEntity, fields: list[AbstractField[Any]]
    ) -> dict[str, Any]:
        """Serialize the given sgchemist entity to shotgun-api3 batch query.

        Args:
            entity: sgchemist entity to serialize
            fields: fields to include in the serialization

        Returns:
            serialized entity
        """
        model_data = {}
        for field in fields:
            value = entity.__state__.get_value(field)
            if isinstance(value, SgBaseEntity):
                value = {
                    "type": value.__sg_type__,
                    "id": value.id,
                }
            model_data[field_info.get_name(field)] = value
        model_data.pop("id", None)
        return model_data

    def serialize(self, batch_queries: list[SgBatchQuery]) -> list[dict[str, Any]]:
        """Serialize the given sgchemist batch queries to shotgun-api3 batch queries.

        Args:
            batch_queries: sgchemist batch queries

        Returns:
            serialized batch queries
        """
        serialized_batch_queries = []
        for query in batch_queries:
            request_type = query.request_type
            entity = query.entity
            batch_data: dict[str, Any] = {
                "request_type": request_type.value,
                "entity_type": entity.__sg_type__,
            }
            if request_type == BatchRequestType.CREATE:
                model_data = self.serialize_entity(entity, entity.__fields__)
                batch_data["data"] = model_data
            elif request_type == BatchRequestType.UPDATE:
                model_data = self.serialize_entity(
                    entity, entity.__state__.modified_fields
                )
                batch_data["entity_id"] = entity.id
                batch_data["data"] = model_data
            elif request_type == BatchRequestType.DELETE:
                batch_data["entity_id"] = entity.id
            else:
                raise AssertionError(
                    f"Request type {request_type} is not supported"
                )  # pragma: no cover
            serialized_batch_queries.append(batch_data)
        return serialized_batch_queries
