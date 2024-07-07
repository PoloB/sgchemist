"""Retrieve information from fields."""

from __future__ import annotations

from typing import TYPE_CHECKING
from typing import Any
from typing import Callable
from typing import Generic
from typing import Iterator
from typing import TypeVar

from typing_extensions import NotRequired
from typing_extensions import TypedDict

from sgchemist.orm import error
from sgchemist.orm.annotation import LazyEntityClassEval
from sgchemist.orm.annotation import LazyEntityCollectionClassEval

if TYPE_CHECKING:
    from sgchemist.orm import SgEntity
    from sgchemist.orm.annotation import FieldAnnotation
    from sgchemist.orm.fields import AbstractField
    from sgchemist.orm.meta import SgEntityMeta

T = TypeVar("T")


class FieldInfo(TypedDict, Generic[T]):
    """Defines information of a field."""

    annotation: NotRequired[FieldAnnotation]
    entity: NotRequired[SgEntityMeta]
    default_value: NotRequired[T]
    field: AbstractField[T]
    name: str
    name_in_relation: str
    alias_field: AbstractField[Any] | None
    parent_field: AbstractField[Any] | None
    primary: bool
    is_relationship: bool
    is_list: bool
    lazy_collection: NotRequired[LazyEntityCollectionClassEval]


def initialize_from_annotation(
    field: AbstractField[Any],
    parent_class: SgEntityMeta,
    annotation: FieldAnnotation,
    attribute_name: str,
) -> None:
    """Create a field from a descriptor."""
    if annotation.field_type is not field.__class__:
        raise error.SgInvalidAnnotationError(
            f"Cannot initialize field of type {field.__class__.__name__} "
            f"with a {annotation.field_type.__name__}"
        )
    info = field.__info__
    if info["alias_field"]:
        if len(annotation.entities) != 1:
            raise error.SgInvalidAnnotationError(
                "A alias field shall target a single entity"
            )
        # Make sure the entity type in annotation is in the target annotation
        target_entity = annotation.entities[0]
        target_annotation = info["alias_field"].__info__["annotation"]
        if target_entity not in target_annotation.entities:
            raise error.SgInvalidAnnotationError(
                "An alias field must target a multi target field containing "
                "its entity"
            )
        # An alias field use the same name as its target
        info["name"] = info["alias_field"].__info__["name"]
    info["entity"] = parent_class
    info["annotation"] = annotation
    info["name"] = info["name"] or attribute_name
    info["name_in_relation"] = info["name_in_relation"] or info["name"]

    # Make some checks
    if info["is_relationship"] and len(annotation.entities) == 0:
        raise error.SgInvalidAnnotationError("Expected at least one entity field")
    # Construct a multi target entity
    lazy_evals = [
        LazyEntityClassEval(entity, parent_class.__registry__)
        for entity in annotation.entities
    ]
    info["lazy_collection"] = LazyEntityCollectionClassEval(lazy_evals)
    if "default_value" not in info:
        info["default_value"] = field.default_value


def get_alias(field: AbstractField[Any]) -> AbstractField[Any] | None:
    """Return the alias field of the field or None if there is no alias field."""
    return field.__info__["alias_field"]


def get_annotation(field: AbstractField[Any]) -> FieldAnnotation:
    """Return the annotation of the field."""
    return field.__info__["annotation"]


def get_default_value(field: AbstractField[T]) -> T:
    """Return the default value of the field."""
    return field.__info__["default_value"]


def is_alias(field: AbstractField[Any]) -> bool:
    """Return whether the attribute is an alias.

    Returns:
        bool: whether the attribute is an alias
    """
    return field.__info__["alias_field"] is not None


def is_primary(field: AbstractField[Any]) -> bool:
    """Return whether the field is a primary field."""
    return field.__info__["primary"]


def get_name(field: AbstractField[Any]) -> str:
    """Return the name of the field."""
    return field.__info__["name"]


def get_name_in_relation(field: AbstractField[Any]) -> str:
    """Return the name of the field from another relationship."""
    return field.__info__["name_in_relation"]


def get_hash(
    field: AbstractField[Any],
) -> tuple[AbstractField[Any], ...]:
    """Return the hash of the attribute."""
    parent_field = field.__info__["parent_field"]
    parent_hash = get_hash(parent_field) if parent_field else tuple()
    field_hash = (*parent_hash, field)
    return field_hash


def get_types(field: AbstractField[Any]) -> tuple[type[SgEntity], ...]:
    """Return the Python types of the attribute.

    Returns:
        tuple[Type[Any], ...]: Python types of the attribute
    """
    return tuple(field.__info__["lazy_collection"].get_all())


def update_entity_from_value(
    field: AbstractField[Any], entity: SgEntity, field_value: Any
) -> None:
    """Update an entity from a row value.

    Used by the Session to convert the value returned by an update back to the
    entity field.

    Args:
        field: the field to update the value from
        entity: the entity to update
        field_value: the row value
    """
    if field.__info__["is_relationship"]:
        return
    entity.__state__.set_value(field, field_value)


def iter_entities_from_field_value(
    field: AbstractField[Any], field_value: Any
) -> Iterator[SgEntity]:
    """Iterate entities from a field value.

    Used by the Session to get the entities within the field values if any.

    Args:
        field: the field to iterate entities from
        field_value: the value to iter entities from

    Returns:
        the entities within the field value
    """
    info = field.__info__
    if not info["is_relationship"]:
        return
    if info["is_list"]:
        for value in field_value:
            yield value
        return
    if field_value is None:
        return
    yield field_value


def cast_column(
    field: AbstractField[Any],
    column_value: Any,
    model_factory: Callable[[type[SgEntity], dict[str, Any]], Any],
) -> Any:
    """Cast the given row value to be used for instancing the entity.

    Used by the session to convert the column value to a value for instantiating
    the entity.
    The model_factory is a function that takes an entity class and a row as
    argument. Use this factory if the instrumented attribute is representing another
    entity that you need to be instantiated.

    Args:
        field: the field to cast the value to
        column_value: the column value to cast
        model_factory: the function to call for instantiating an entity from a row.

    Returns:
        result of the applied function
    """
    info = field.__info__
    if not info["is_relationship"]:
        return column_value

    if not info["is_list"] and column_value is None:
        return None

    def _cast_column(col: dict[str, Any]) -> Any:
        return model_factory(info["lazy_collection"].get_by_type(col["type"]), col)

    def _cast_value_over(
        func: Callable[[Any], Any],
        value: Any,
    ) -> Any:
        if info["is_list"]:
            return [func(v) for v in value]
        else:
            return func(value)

    return _cast_value_over(_cast_column, column_value)
