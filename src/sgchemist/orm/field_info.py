"""Retrieve information from fields."""

from __future__ import annotations

from typing import TYPE_CHECKING
from typing import Any
from typing import Callable
from typing import Generic
from typing import TypeVar

from typing_extensions import NotRequired
from typing_extensions import TypedDict
from typing_extensions import overload

if TYPE_CHECKING:
    from collections.abc import Iterable

    from sgchemist.orm import SgBaseEntity
    from sgchemist.orm.annotation import FieldAnnotation
    from sgchemist.orm.entity import LazyEntityCollectionClassEval
    from sgchemist.orm.entity import SgEntityMeta
    from sgchemist.orm.fields import AbstractField
    from sgchemist.orm.typing_alias import EntityProtocol

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
    original_field: AbstractField[Any]
    primary: bool
    is_relationship: bool
    is_list: bool
    lazy_collection: NotRequired[LazyEntityCollectionClassEval]
    entity_iterator: NotRequired[Callable[[T], Iterable[EntityProtocol]]]


def get_alias(field: AbstractField[Any]) -> AbstractField[Any] | None:
    """Return the alias field of the field or None if there is no alias field."""
    return field.__info__["alias_field"]


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


def get_attribute_by_field_name(entity: SgEntityMeta) -> dict[str, str]:
    """Return entity attribute name per field name for the given entity."""
    return entity.__attr_per_field_name__


def get_attribute_by_relationship_name(entity: SgEntityMeta) -> dict[str, str]:
    """Return entity attribute name per field name for the given entity."""
    field_mapper = entity.__attr_per_field_name__
    return {
        get_name_in_relation(field): field_mapper[get_name(field)]
        for field in entity.__fields__
    }


def get_hash(
    field: AbstractField[Any],
) -> tuple[AbstractField[Any], ...]:
    """Return the hash of the attribute."""
    parent_field = field.__info__["parent_field"]
    parent_hash = get_hash(parent_field) if parent_field else ()
    return (*parent_hash, field)


def get_types(field: AbstractField[Any]) -> tuple[type[SgBaseEntity], ...]:
    """Return the Python types of the attribute.

    Returns:
        tuple[Type[Any], ...]: Python types of the attribute
    """
    return tuple(field.__info__["lazy_collection"].get_all())


def get_field_hierarchy(field: AbstractField[Any]) -> list[AbstractField[Any]]:
    """Return the fields from root to leaf.

    Examples:
        If the input field in `Asset.project.f(Project.id), the function will return
        `[Asset.project, Project.id]`.

    Args:
        field: Field to get hierarchy from.
    """
    fields = []
    current_field: AbstractField[Any] | None = field
    while current_field:
        fields.append(current_field.__info__["original_field"])
        current_field = current_field.__info__["parent_field"]
    fields.reverse()
    return fields


def iter_entities_from_field_value(
    field_info: FieldInfo[T],
    field_value: T,
) -> Iterable[EntityProtocol]:
    """Iterate the entities from the given field value."""
    yield from field_info["entity_iterator"](field_value)


T_col = TypeVar("T_col")


@overload
def cast_value_over(
    info: FieldInfo[T],
    func: Callable[[dict[str, Any]], T],
    value: dict[str, Any],
) -> T: ...


@overload
def cast_value_over(info: FieldInfo[T], func: Callable[[Any], T], value: T) -> T: ...


@overload
def cast_value_over(
    info: FieldInfo[T],
    func: Callable[[dict[str, Any]], T],
    value: list[dict[str, Any]],
) -> T: ...


def cast_value_over(
    info: FieldInfo[T],
    func: Callable[[Any], T],
    value: T | dict[str, Any] | list[dict[str, Any]],
) -> T | list[T]:
    """Cast the value according to the given field info."""
    if not info["is_relationship"]:
        assert not isinstance(value, dict)
        assert not isinstance(value, list)
        return value
    if info["is_list"]:
        assert isinstance(value, list)
        return [func(v) for v in value]
    return func(value)


def cast_column(
    info: FieldInfo[T],
    column_value: T | dict[str, Any] | list[dict[str, Any]],
    func: Callable[[type[SgBaseEntity], dict[str, Any]], T],
) -> T:
    """Cast the given row value to be used for instancing the entity.

    Used by the session to convert the column value to a value for instantiating
    the entity.
    The model_factory is a function that takes an entity class and a row as
    argument. Use this factory if the instrumented attribute is representing another
    entity that you need to be instantiated.

    Args:
        info: the field info
        column_value: the column value to cast
        func: the function to call for instantiating an entity from a row.

    Returns:
        result of the applied function
    """
    if not info["is_list"] and column_value is None:
        return None

    def _cast_column(col: dict[str, Any]) -> T:
        return func(info["lazy_collection"].get_by_type(col["type"]), col)

    return cast_value_over(info, _cast_column, column_value)
