"""Serializers to convert query object to shotgun-api3 query components."""

from __future__ import annotations

from typing import Any
from typing import Dict
from typing import List
from typing import Union

from typing_extensions import TypedDict

from .constant import BatchRequestType
from .entity import SgEntity
from .instrumentation import InstrumentedAttribute
from .query import SgBatchQuery
from .queryop import SgFieldCondition
from .queryop import SgFilterObject
from .queryop import SgFilterOperation
from .queryop import SgNullCondition

SerializedEntity = TypedDict("SerializedEntity", {"id": int, "type": str})
SerializedOperator = TypedDict(
    "SerializedOperator", {"filter_operator": str, "filters": List[Any]}
)
SerializedCondition = List[Any]
SerializedObject = Union[SerializedEntity, SerializedOperator, SerializedCondition]


def serialize_entity(model: SgEntity) -> SerializedEntity:
    """Serialize the given sgchemist entity to shotgun-api3 entity.

    Args:
        model (SgEntity): sgchemist entity to serialize

    Returns:
        SerializedEntity: serialized entity
    """
    assert model.id is not None
    return {"id": model.id, "type": model.__sg_type__}


def serialize_condition(condition: SgFieldCondition) -> SerializedCondition:
    """Serialize the given sgchemist condition to shotgun-api3 filter condition.

    Args:
        condition: sgchemist condition to serialize

    Returns:
        SerializedCondition: serialized condition
    """
    right = condition.right
    if isinstance(condition.right, SgEntity):
        right = serialize_entity(condition.right)
    return [
        condition.field.get_name(),
        condition.operator.value,
        right,
    ]


class ShotgunAPIObjectSerializer:
    """Defines a serializer converting sgchemist objects to shotgun-api3 components."""

    def serialize_filter(
        self, sg_object: Union[SgFilterObject, SgEntity]
    ) -> List[SerializedObject]:
        """Returns filters for shotgun-api3 from the given sgchemist object.

        Args:
            sg_object (SgFilterObject or SgEntity): sgchemist object to serialize

        Returns:
            list[SerializedObject]: list of serialized objects
        """
        if isinstance(sg_object, SgNullCondition):
            return []
        return [self.serialize_object(sg_object)]

    def serialize_object(
        self, sg_object: Union[SgFilterObject, SgEntity]
    ) -> SerializedObject:
        """Serialize the given sgchemist object to shotgun-api3 object.

        Args:
            sg_object (SgFilterObject or SgEntity): sgchemist object to serialize

        Returns:
            SerializedObject: serialized object
        """
        if isinstance(sg_object, SgFieldCondition):
            return serialize_condition(sg_object)
        elif isinstance(sg_object, SgEntity):
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
            SerializedOperator: serialized operator
        """
        return {
            "filter_operator": filter_operator.operator.value,
            "filters": [
                self.serialize_object(obj) for obj in filter_operator.sg_objects
            ],
        }


SerializedBatchQueryCreate = TypedDict(
    "SerializedBatchQueryCreate", {"request_type": str, "entity_type": str}
)
SerializedBatchQueryUpdate = TypedDict(
    "SerializedBatchQueryUpdate",
    {"request_type": str, "entity_type": str, "entity_id": int, "data": Dict[str, Any]},
)


class ShotgunAPIBatchQuerySerializer:
    """Defines a serializer converting sgchemist batch query to shotgun-api3 queries."""

    @staticmethod
    def serialize_entity(
        entity: SgEntity, fields: List[InstrumentedAttribute[Any]]
    ) -> Dict[str, Any]:
        """Serialize the given sgchemist entity to shotgun-api3 batch query.

        Args:
            entity (SgEntity): sgchemist entity to serialize
            fields (list[InstrumentedAttribute[Any]]): fields to include in the
                serialization

        Returns:
            dict[str, Any]: serialized entity
        """
        model_data = {}
        for field in fields:
            value = entity.__state__.get_slot(field.get_attribute_name()).value
            if isinstance(value, SgEntity):
                value = {
                    "type": value.__sg_type__,
                    "id": value.id,
                }
            model_data[field.get_name()] = value
        model_data.pop("id", None)
        return model_data

    def serialize(self, batch_queries: List[SgBatchQuery]) -> List[Dict[str, Any]]:
        """Serialize the given sgchemist batch queries to shotgun-api3 batch queries.

        Args:
            batch_queries (list[SgBatchQuery]): sgchemist batch queries

        Returns:
            list[dict[str, Any]]: serialized batch queries
        """
        serialized_batch_queries = []
        for query in batch_queries:
            request_type = query.request_type
            entity = query.entity
            batch_data: Dict[str, Any] = {
                "request_type": request_type.value,
                "entity_type": entity.__sg_type__,
            }
            if request_type == BatchRequestType.CREATE:
                model_data = self.serialize_entity(
                    entity, list(entity.__fields__.values())
                )
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
