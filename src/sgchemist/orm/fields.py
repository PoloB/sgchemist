"""Definition of all the fields used by Shotgrid entities.

The main function of these fields is to provide the correct type annotations.
Internally, only the classes inheriting from InstrumentedAttribute are used.
"""

from __future__ import absolute_import
from __future__ import annotations

import abc
from datetime import date
from datetime import datetime
from typing import TYPE_CHECKING
from typing import Any
from typing import Dict
from typing import Generic
from typing import List
from typing import Optional
from typing import TypeVar
from typing import overload

from typing_extensions import Self

from . import error
from .constant import DateType
from .constant import Operator
from .field_info import get_types
from .queryop import SgFieldCondition

if TYPE_CHECKING:
    from .entity import SgBaseEntity
    from .field_info import FieldInfo

T = TypeVar("T")
T2 = TypeVar("T2")


class AbstractField(Generic[T], metaclass=abc.ABCMeta):
    """Definition of an abstract field."""

    cast_type: type[T]
    default_value: T
    __sg_type__: str = ""
    __info__: FieldInfo[T]

    __slots__ = (
        "__info__",
        "default_value",
        "cast_type",
    )

    def __init__(
        self,
        name: str = "",
        default_value: T | None = None,
        name_in_relation: str = "",
        alias_field: AbstractField[Any] | None = None,
        parent_field: AbstractField[Any] | None = None,
        primary: bool = False,
        as_list: bool = False,
        is_relationship: bool = False,
    ) -> None:
        """Initialize an instrumented attribute.

        Args:
            name: the name of the field
            default_value: the default value of the field
            name_in_relation: the name of the field in relationship
            alias_field: the alias field of the field
            parent_field: the parent field of the field
            primary: whether the field is primary or not
            as_list: whether the field is list or not
            is_relationship: whether the field is a relationship
        """
        self.__info__ = {
            "field": self,
            "name": name,
            "name_in_relation": name_in_relation,
            "alias_field": alias_field,
            "parent_field": parent_field,
            "primary": primary,
            "is_relationship": is_relationship,
            "is_list": as_list,
        }
        if default_value is not None:
            self.__info__["default_value"] = default_value

    def __repr__(self) -> str:
        """Returns a string representation of the instrumented attribute.

        Returns:
            the instrumented attribute representation
        """
        return (
            f"{self.__class__.__name__}"
            f"({self.__info__['entity'].__name__}.{self.__info__['name']})"
        )

    def _relative_to(self, relative_attribute: AbstractField[Any]) -> Self:
        """Build a new instrumented field relative to the given attribute.

        Args:
            relative_attribute: the relative attribute

        Returns:
            the attribute relative to the given attribute
        """
        field_info = self.__info__
        new_field_name = ".".join(
            [
                relative_attribute.__info__["name"],
                field_info["entity"].__sg_type__,
                field_info["name"],
            ]
        )
        new_field = self.__class__()
        # Modify the field info according to the new data
        new_field_info = field_info.copy()
        new_field_info["name"] = new_field_name
        new_field_info["field"] = new_field
        new_field_info["parent_field"] = relative_attribute
        new_field_info["name_in_relation"] = new_field_name
        new_field.__info__ = new_field_info
        return new_field

    def eq(self, other: T) -> SgFieldCondition:
        """Filter entities where this field is equal to the given value.

        This is the equivalent of the "is" filter of Shotgrid.

        Args:
            other: The value to compare the field against

        Returns:
            The field condition
        """
        return SgFieldCondition(self, Operator.IS, other)

    def neq(self, other: T) -> SgFieldCondition:
        """Filter entities where this field is not equal to the given value.

        This is the equivalent of the "is_not" filter of Shotgrid.

        Args:
            other: The value to compare the field against

        Returns:
            The field condition
        """
        return SgFieldCondition(self, Operator.IS_NOT, other)


T_field = TypeVar("T_field", bound=AbstractField[Any])


class AbstractValueField(AbstractField[Optional[T]], metaclass=abc.ABCMeta):
    """Definition of an abstract value field."""

    def __init__(
        self,
        name: str = "",
        default_value: T | None = None,
        name_in_relation: str = "",
    ):
        """Initialize an instrumented field.

        Args:
            name: the name of the field
            default_value: default value of the field
            name_in_relation: the name of the attribute in the relationship
        """
        super().__init__(
            name=name,
            default_value=default_value,
            name_in_relation=name_in_relation,
            is_relationship=False,
            as_list=False,
        )


class NumericField(AbstractValueField[T], metaclass=abc.ABCMeta):
    """Definition of an abstract numerical field."""

    cast_type: type[T]

    def gt(self, other: T) -> SgFieldCondition:
        """Filter entities where this field is greater than the given value.

        This is the equivalent of the "greater_than" filter of Shotgrid.

        Args:
            other: The value to compare the field against

        Returns:
            The field condition
        """
        return SgFieldCondition(self, Operator.GREATER_THAN, other)

    def lt(self, other: T) -> SgFieldCondition:
        """Filter entities where this field is less than the given value.

        This is the equivalent of the "less_than" filter of Shotgrid.

        Args:
            other: The value to compare the field against

        Returns:
            The field condition
        """
        return SgFieldCondition(self, Operator.LESS_THAN, other)

    def between(self, low: T, high: T) -> SgFieldCondition:
        """Filter entities where this field is between the low and high values.

        This is the equivalent of the "between" filter of Shotgrid.

        Args:
            low: low value of the range
            high: high value of the range

        Returns:
            The field condition.
        """
        return SgFieldCondition(self, Operator.BETWEEN, [low, high])

    def not_between(self, low: T, high: T) -> SgFieldCondition:
        """Filter entities where this field is not between the low and high values.

        This is the equivalent of the "not_between" filter of Shotgrid.

        Args:
            low: low value of the range
            high: high value of the range

        Returns:
            The field condition.
        """
        return SgFieldCondition(self, Operator.NOT_BETWEEN, [low, high])

    def is_in(self, others: list[T]) -> SgFieldCondition:
        """Filter entities where this field is within the given list of values.

        This is the equivalent of the "in" filter of Shotgrid.

        Args:
            others: values to test

        Returns:
            The field condition.
        """
        return SgFieldCondition(self, Operator.IN, others)

    def is_not_in(self, others: list[T]) -> SgFieldCondition:
        """Filter entities where this field is not within the given list of values.

        This is the equivalent of the "not_in" filter of Shotgrid.

        Args:
            others: values to test

        Returns:
            The field condition.
        """
        return SgFieldCondition(self, Operator.NOT_IN, others)


class NumberField(NumericField[Optional[int]]):
    """An integer field."""

    __sg_type__: str = "number"
    cast_type: type[int] = int
    default_value = None

    if TYPE_CHECKING:

        @overload
        def __get__(self, instance: None, owner: Any) -> NumberField: ...

        @overload
        def __get__(self, instance: Any, owner: Any) -> int | None: ...

        def __get__(self, instance: Any | None, owner: Any) -> int | None | NumberField:
            """Return the value of the field."""


class FloatField(NumericField[Optional[float]]):
    """A float field."""

    cast_type: type[float] = float
    __sg_type__: str = "float"
    default_value = None

    if TYPE_CHECKING:

        @overload
        def __get__(self, instance: None, owner: Any) -> FloatField: ...

        @overload
        def __get__(self, instance: Any, owner: Any) -> float | None: ...

        def __get__(
            self, instance: Any | None, owner: Any
        ) -> float | None | FloatField:
            """Return the value of the field."""


class TextField(AbstractValueField[Optional[str]]):
    """A text field."""

    cast_type: type[str] = str
    __sg_type__: str = "text"
    default_value = None

    def contains(self, text: str) -> SgFieldCondition:
        """Filter entities where this text field contains the given string.

        This is the equivalent of the "contains" filter of Shotgrid.

        Args:
            text: text to check

        Returns:
            The field condition.
        """
        return SgFieldCondition(self, Operator.CONTAINS, text)

    def not_contains(self, text: str) -> SgFieldCondition:
        """Filter entities where this text field does not contain the given string.

        This is the equivalent of the "not_contains" filter of Shotgrid.

        Args:
            text: text to check

        Returns:
            The field condition.
        """
        return SgFieldCondition(self, Operator.NOT_CONTAINS, text)

    def is_in(self, others: list[T]) -> SgFieldCondition:
        """Filter entities where this field is within the given list of values.

        This is the equivalent of the "in" filter of Shotgrid.

        Args:
            others: values to test

        Returns:
            The field condition.
        """
        return SgFieldCondition(self, Operator.IN, others)

    def is_not_in(self, others: list[T]) -> SgFieldCondition:
        """Filter entities where this field is not within the given list of values.

        This is the equivalent of the "not_in" filter of Shotgrid.

        Args:
            others: values to test

        Returns:
            The field condition.
        """
        return SgFieldCondition(self, Operator.NOT_IN, others)

    def startswith(self, text: str) -> SgFieldCondition:
        """Filter entities where this text field starts with the given text.

        This is the equivalent of the "start_with" filter of Shotgrid.

        Args:
            text: text to check

        Returns:
            The field condition.
        """
        return SgFieldCondition(self, Operator.STARTS_WITH, text)

    def endswith(self, text: str) -> SgFieldCondition:
        """Filter entities where this text field ends with the given text.

        This is the equivalent of the "end_with" filter of Shotgrid.

        Args:
            text: text to check

        Returns:
            The field condition.
        """
        return SgFieldCondition(self, Operator.ENDS_WITH, text)

    if TYPE_CHECKING:

        @overload
        def __get__(self, instance: None, owner: Any) -> TextField: ...

        @overload
        def __get__(self, instance: Any, owner: Any) -> str | None: ...

        def __get__(self, instance: Any | None, owner: Any) -> str | None | TextField:
            """Return the value of the field."""


class AbstractEntityField(AbstractField[T], metaclass=abc.ABCMeta):
    """Definition a field targeting an entity."""

    __sg_type__: str
    cast_type: type[T]

    def f(self, field: T_field) -> T_field:
        """Return the given field in relation to the given field."""
        info = field.__info__
        if info["entity"] not in get_types(self):
            raise error.SgFieldConstructionError(
                f"Cannot cast {self} as {field.__info__['entity'].__name__}. "
                f"Expected types are {get_types(field)}"
            )
        return field._relative_to(self)

    def type_is(self, entity_cls: type[SgBaseEntity]) -> SgFieldCondition:
        """Filter entities where this entity is of the given type.

        This is the equivalent of the "type_is" filter of Shotgrid.

        Args:
            entity_cls: entity to test

        Returns:
            The field condition.
        """
        return SgFieldCondition(self, Operator.TYPE_IS, entity_cls.__sg_type__)

    def type_is_not(self, entity_cls: type[SgBaseEntity]) -> SgFieldCondition:
        """Filter entities where this entity is not of the given type.

        This is the equivalent of the "type_is_not" filter of Shotgrid.

        Args:
            entity_cls: entity to test

        Returns:
            The field condition.
        """
        return SgFieldCondition(self, Operator.TYPE_IS_NOT, entity_cls.__sg_type__)

    def name_contains(self, text: str) -> SgFieldCondition:
        """Filter entities where this entity name contains the given text.

        This is the equivalent of the "name_contains" filter of Shotgrid.

        Args:
            text: text to test

        Returns:
            The field condition.
        """
        return SgFieldCondition(self, Operator.NAME_CONTAINS, text)

    def name_not_contains(self, text: str) -> SgFieldCondition:
        """Filter entities where this entity name does not contain the given text.

        This is the equivalent of the "name_contains" filter of Shotgrid.

        Args:
            text: text to test

        Returns:
            The field condition.
        """
        return SgFieldCondition(self, Operator.NAME_NOT_CONTAINS, text)

    def name_is(self, text: str) -> SgFieldCondition:
        """Filter entities where this entity name is the given text.

        This is the equivalent of the "name_is" filter of Shotgrid.

        Args:
            text: text to test

        Returns:
            The field condition.
        """
        return SgFieldCondition(self, Operator.NAME_IS, text)

    def is_in(self, others: list[T]) -> SgFieldCondition:
        """Filter entities where this field is within the given list of values.

        This is the equivalent of the "in" filter of Shotgrid.

        Args:
            others: values to test

        Returns:
            The field condition.
        """
        return SgFieldCondition(self, Operator.IN, others)

    def is_not_in(self, others: list[T]) -> SgFieldCondition:
        """Filter entities where this field is not within the given list of values.

        This is the equivalent of the "not_in" filter of Shotgrid.

        Args:
            others: values to test

        Returns:
            The field condition.
        """
        return SgFieldCondition(self, Operator.NOT_IN, others)


class EntityField(AbstractEntityField[Optional[T]]):
    """Definition a field targeting a single entity."""

    __sg_type__: str = "entity"
    cast_type: type[T]
    default_value = None

    def __init__(self, name: str = ""):
        """Initialise the field."""
        super().__init__(
            name=name, default_value=None, is_relationship=True, as_list=False
        )

    if TYPE_CHECKING:

        @overload
        def __get__(self, instance: None, owner: Any) -> EntityField[T]: ...

        @overload
        def __get__(self, instance: Any, owner: Any) -> T | None: ...

        def __get__(
            self, instance: Any | None, owner: Any
        ) -> T | None | EntityField[T]:
            """Return the value of the field."""


class MultiEntityField(AbstractEntityField[List[T]]):
    """Definition a field targeting multiple entities."""

    __sg_type__: str = "multi_entity"

    def __init__(self, name: str = ""):
        """Initialize the field."""
        super().__init__(
            name=name, default_value=[], as_list=True, is_relationship=True
        )

    if TYPE_CHECKING:

        @overload
        def __get__(self, instance: None, owner: Any) -> MultiEntityField[T]: ...

        @overload
        def __get__(self, instance: Any, owner: Any) -> T: ...

        def __get__(self, instance: Any | None, owner: Any) -> T | MultiEntityField[T]:
            """Return the value of the field."""


class BooleanField(AbstractValueField[Optional[bool]]):
    """Definition a boolean field."""

    __sg_type__: str = "checkbox"
    default_value: bool | None = None

    if TYPE_CHECKING:

        @overload
        def __get__(self, instance: None, owner: Any) -> BooleanField: ...

        @overload
        def __get__(self, instance: Any, owner: Any) -> bool | None: ...

        def __get__(
            self, instance: Any | None, owner: Any
        ) -> bool | None | BooleanField:
            """Return the value of the field."""


class AbstractDateField(NumericField[T]):
    """Definition an abstract date field."""

    def in_last(self, count: int, date_element: DateType) -> SgFieldCondition:
        """Filter entities where this date is within the last given quantities.

        This is the equivalent of the "in_last" filter of Shotgrid.

        Args:
            count: number of days/weeks/months/years
            date_element: duration type to consider

        Returns:
            The field condition.
        """
        return SgFieldCondition(self, Operator.IN_LAST, [count, date_element])

    def not_in_last(self, count: int, date_element: DateType) -> SgFieldCondition:
        """Filter entities where this date is not within the last given quantities.

        This is the equivalent of the "not_in_last" filter of Shotgrid.

        Args:
            count: number of days/weeks/months/years
            date_element: duration type to consider

        Returns:
            The field condition.
        """
        return SgFieldCondition(self, Operator.NOT_IN_LAST, [count, date_element])

    def in_next(self, count: int, date_element: DateType) -> SgFieldCondition:
        """Filter entities where this date is within the next given quantities.

        This is the equivalent of the "in_next" filter of Shotgrid.

        Args:
            count: number of days/weeks/months/years
            date_element: duration type to consider

        Returns:
            The field condition.
        """
        return SgFieldCondition(self, Operator.IN_NEXT, [count, date_element])

    def not_in_next(self, count: int, date_element: DateType) -> SgFieldCondition:
        """Filter entities where this date is not within the next given quantities.

        This is the equivalent of the "not_in_next" filter of Shotgrid.

        Args:
            count: number of days/weeks/months/years
            date_element: duration type to consider

        Returns:
            The field condition.
        """
        return SgFieldCondition(self, Operator.NOT_IN_NEXT, [count, date_element])

    def in_calendar_day(self, offset: int) -> SgFieldCondition:
        """Filter entities where this date is equal to the offset current day.

        This is the equivalent of the "in_calendar_day" filter of Shotgrid.

        Args:
            offset: offset (e.g. 0=today, 1=tomorrow, -1=yesterday)

        Returns:
            The field condition.
        """
        return SgFieldCondition(self, Operator.IN_CALENDAR_DAY, offset)

    def in_calendar_week(self, offset: int) -> SgFieldCondition:
        """Filter entities where this date is equal to the offset current week.

        This is the equivalent of the "in_calendar_week" filter of Shotgrid.

        Args:
            offset: offset (e.g. 0=this week, 1=next week, -1=last week)

        Returns:
            The field condition.
        """
        return SgFieldCondition(self, Operator.IN_CALENDAR_WEEK, offset)

    def in_calendar_month(self, offset: int) -> SgFieldCondition:
        """Filter entities where this date is equal to the offset current month.

        This is the equivalent of the "in_calendar_month" filter of Shotgrid.

        Args:
            offset: offset (e.g. 0=this month, 1=next month, -1= last month)

        Returns:
            The field condition.
        """
        return SgFieldCondition(self, Operator.IN_CALENDAR_MONTH, offset)

    def in_calendar_year(self, offset: int) -> SgFieldCondition:
        """Filter entities where this date is equal to the offset current year.

        This is the equivalent of the "in_calendar_year" filter of Shotgrid.

        Args:
            offset: offset (e.g. 0=this year, 1=next year, -1= last year)

        Returns:
            The field condition.
        """
        return SgFieldCondition(self, Operator.IN_CALENDAR_YEAR, offset)


class DateField(AbstractDateField[Optional[date]]):
    """Definition of a date field."""

    cast_type: type[date] = date
    __sg_type__: str = "date"
    default_value: date | None = None

    if TYPE_CHECKING:

        @overload
        def __get__(self, instance: None, owner: Any) -> DateField: ...

        @overload
        def __get__(self, instance: Any, owner: Any) -> date | None: ...

        def __get__(self, instance: Any | None, owner: Any) -> date | None | DateField:
            """Return the value of the field."""


class DateTimeField(AbstractDateField[Optional[datetime]]):
    """Definition of a date time field."""

    cast_type: type[datetime] = datetime
    __sg_type__: str = "date_time"
    default_value = None

    if TYPE_CHECKING:

        @overload
        def __get__(self, instance: None, owner: Any) -> DateTimeField: ...

        @overload
        def __get__(self, instance: Any, owner: Any) -> datetime | None: ...

        def __get__(
            self, instance: Any | None, owner: Any
        ) -> datetime | None | DateTimeField:
            """Return the value of the field."""


class DurationField(NumberField):
    """Definition of a duration field."""

    __sg_type__: str = "duration"

    if TYPE_CHECKING:

        @overload
        def __get__(self, instance: None, owner: Any) -> DurationField: ...

        @overload
        def __get__(self, instance: Any, owner: Any) -> int | None: ...

        def __get__(
            self, instance: Any | None, owner: Any
        ) -> int | None | DurationField:
            """Return the value of the field."""


class ImageField(AbstractValueField[Optional[str]]):
    """Definition of an image field."""

    cast_type: type[str] = str
    __sg_type__: str = "image"
    default_value = None

    def exists(self) -> SgFieldCondition:
        """Filter entities where this image exists.

        This is the equivalent of the "is" filter of Shotgrid.

        Returns:
            The field condition.
        """
        return SgFieldCondition(self, Operator.IS_NOT, None)

    def not_exists(self) -> SgFieldCondition:
        """Filter entities where this image does not exist.

        This is the equivalent of the "is_not" filter of Shotgrid.

        Returns:
            The field condition.
        """
        return SgFieldCondition(self, Operator.IS, None)

    if TYPE_CHECKING:

        @overload
        def __get__(self, instance: None, owner: Any) -> ImageField: ...

        @overload
        def __get__(self, instance: Any, owner: Any) -> str | None: ...

        def __get__(self, instance: Any | None, owner: Any) -> str | None | ImageField:
            """Return the value of the field."""


class ListField(AbstractValueField[Optional[List[str]]]):
    """Definition of a list field."""

    cast_type: type[list[str]] = list
    __sg_type__: str = "list"
    default_value = None

    def is_in(self, others: list[str]) -> SgFieldCondition:
        """Filter entities where this field is within the given list of values.

        This is the equivalent of the "in" filter of Shotgrid.

        Args:
            others: values to test

        Returns:
            The field condition.
        """
        return SgFieldCondition(self, Operator.IN, others)

    def is_not_in(self, others: list[str]) -> SgFieldCondition:
        """Filter entities where this field is not within the given list of values.

        This is the equivalent of the "not_in" filter of Shotgrid.

        Args:
            others: values to test

        Returns:
            The field condition.
        """
        return SgFieldCondition(self, Operator.NOT_IN, others)

    if TYPE_CHECKING:

        @overload
        def __get__(self, instance: None, owner: Any) -> ListField: ...

        @overload
        def __get__(self, instance: Any, owner: Any) -> list[str] | None: ...

        def __get__(
            self, instance: Any | None, owner: Any
        ) -> list[str] | None | ListField:
            """Return the value of the field."""


class PercentField(FloatField):
    """Definition of a percent field."""

    __sg_type__: str = "percent"

    if TYPE_CHECKING:

        @overload
        def __get__(self, instance: None, owner: Any) -> PercentField: ...

        @overload
        def __get__(self, instance: Any, owner: Any) -> float | None: ...

        def __get__(
            self, instance: Any | None, owner: Any
        ) -> float | None | PercentField:
            """Return the value of the field."""


class SerializableField(AbstractValueField[Optional[Dict[str, Any]]]):
    """Definition of a serializable field."""

    cast_type: type[dict[str, Any]] = dict
    __sg_type__: str = "serializable"
    default_value = None

    if TYPE_CHECKING:

        @overload
        def __get__(self, instance: None, owner: Any) -> SerializableField: ...

        @overload
        def __get__(self, instance: Any, owner: Any) -> dict[str, Any] | None: ...

        def __get__(
            self, instance: Any | None, owner: Any
        ) -> dict[str, Any] | None | SerializableField:
            """Return the value of the field."""


class StatusField(AbstractValueField[str]):
    """Definition of a status field."""

    __sg_type__: str = "status_list"
    default_value = "wtg"

    if TYPE_CHECKING:

        @overload
        def __get__(self, instance: None, owner: Any) -> StatusField: ...

        @overload
        def __get__(self, instance: Any, owner: Any) -> str: ...

        def __get__(self, instance: Any | None, owner: Any) -> str | StatusField:
            """Return the value of the field."""


class UrlField(AbstractValueField[Optional[str]]):
    """Definition of an url field."""

    cast_type: type[str] = str
    __sg_type__: str = "url"
    default_value = None

    if TYPE_CHECKING:

        @overload
        def __get__(self, instance: None, owner: Any) -> UrlField: ...

        @overload
        def __get__(self, instance: Any, owner: Any) -> str | None: ...

        def __get__(self, instance: Any | None, owner: Any) -> str | None | UrlField:
            """Return the value of the field."""


# Expose all the available fields (intended for model generation)
field_by_sg_type: dict[str, type[AbstractField[Any]]] = {
    field_cls.__sg_type__: field_cls
    for name, field_cls in locals().items()
    if isinstance(field_cls, type)
    and issubclass(field_cls, AbstractField)
    and field_cls.__sg_type__ is not None
}


def alias(target_relationship: AbstractEntityField[Any]) -> EntityField[Any]:
    """Defines a field as an alias relationship.

    Use this field specifier to target a specific entity type of the given multi target
    relationship:

    ```python
    from sgchemist.orm import alias_relationship
    from sgchemist.orm import EntityField
    from sgchemist.orm import SgEntity

    class Asset(SgEntity):
        __sg_type__ = "Asset"

    class Shot(SgEntity):
        __sg_type__ = "Shot"

    class Task(SgEntity):
        __sg_type__ = "Task"

        entity: EntityField[Optional[Asset | Shot]]
        asset: EntityField[Asset | None] = alias_relationship(entity)
        shot: EntityField[Shot | None] = alias_relationship(entity)

    # Create a filter using target selector
    filter = Task.entity.Shot.id.eq(123)
    # Create a filter using the alias
    filter = Task.shot.id.eq(123)
    ```
    """
    field: EntityField[Any] = EntityField()
    field.__info__["alias_field"] = target_relationship
    return field


def update_entity_from_value(
    field: AbstractField[Any], entity: SgBaseEntity, field_value: Any
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
