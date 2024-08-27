"""Definition of all the fields used by Shotgrid entities.

The main function of these fields is to provide the correct type annotations.
Internally, only the classes inheriting from InstrumentedAttribute are used.
"""

from __future__ import annotations

import abc
from datetime import date
from datetime import datetime
from typing import TYPE_CHECKING
from typing import Any
from typing import Dict
from typing import Generic
from typing import Iterable
from typing import List
from typing import Optional
from typing import TypeVar
from typing import Union
from typing import overload

from typing_extensions import Self

from . import error
from .field_info import get_types
from .queryop import FilterOperatorBetween
from .queryop import FilterOperatorContains
from .queryop import FilterOperatorEndsWith
from .queryop import FilterOperatorGreaterThan
from .queryop import FilterOperatorIn
from .queryop import FilterOperatorInCalendarDay
from .queryop import FilterOperatorInCalendarMonth
from .queryop import FilterOperatorInCalendarWeek
from .queryop import FilterOperatorInCalendarYear
from .queryop import FilterOperatorInLast
from .queryop import FilterOperatorInNext
from .queryop import FilterOperatorIs
from .queryop import FilterOperatorIsNot
from .queryop import FilterOperatorLessThan
from .queryop import FilterOperatorNotContains
from .queryop import FilterOperatorNotIn
from .queryop import FilterOperatorNotInLast
from .queryop import FilterOperatorNotInNext
from .queryop import FilterOperatorStartsWith
from .queryop import FilterOperatorTypeIs
from .queryop import FilterOperatorTypeIsNot
from .queryop import SgFieldCondition
from .typing_alias import EntityProtocol
from .typing_util import OptionalCompare

if TYPE_CHECKING:
    from .constant import DateType
    from .entity import SgBaseEntity
    from .entity import SgEntityMeta
    from .field_info import FieldInfo

T_e = TypeVar("T_e", bound=EntityProtocol)

T = TypeVar("T")
Tcomp = TypeVar("Tcomp", bound=OptionalCompare)
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

    def __init__(  # noqa: PLR0913
        self,
        name: str = "",
        default_value: T | None = None,
        name_in_relation: str = "",
        alias_field: AbstractField[Any] | None = None,
        parent_field: AbstractField[Any] | None = None,
        primary: bool = False,  # noqa: FBT001, FBT002
        as_list: bool = False,  # noqa: FBT001, FBT002
        is_relationship: bool = False,  # noqa: FBT001, FBT002
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
            "original_field": self,
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

    def eq(self, other: T) -> SgFieldCondition:
        """Filter entities where this field is equal to the given value.

        This is the equivalent of the "is" filter of Shotgrid.

        Args:
            other: The value to compare the field against

        Returns:
            The field condition
        """
        return SgFieldCondition(self, FilterOperatorIs(other))

    def neq(self, other: T) -> SgFieldCondition:
        """Filter entities where this field is not equal to the given value.

        This is the equivalent of the "is_not" filter of Shotgrid.

        Args:
            other: The value to compare the field against

        Returns:
            The field condition
        """
        return SgFieldCondition(self, FilterOperatorIsNot(other))

    if TYPE_CHECKING:

        @overload
        def __get__(self, instance: None, owner: SgEntityMeta) -> Self: ...

        @overload
        def __get__(self, instance: SgBaseEntity, owner: SgEntityMeta) -> T: ...

        def __get__(
            self,
            instance: SgBaseEntity | None,
            owner: SgEntityMeta,
        ) -> Self | T:
            """Return field from class and value from instance."""


T_field = TypeVar("T_field", bound=AbstractField[Any])


def iter_no_entity(_: T) -> Iterable[SgBaseEntity]:
    """Return an empty iterator."""
    return iter([])


class AbstractValueField(AbstractField[T], metaclass=abc.ABCMeta):
    """Definition of an abstract value field."""

    def __init__(
        self,
        name: str = "",
        default_value: T | None = None,
        name_in_relation: str = "",
    ) -> None:
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
        self.__info__["entity_iterator"] = iter_no_entity


OptionalIntFloat = Union[int, float, None]
Tnum = TypeVar("Tnum", bound=OptionalIntFloat)


class NumericField(AbstractValueField[Tnum], metaclass=abc.ABCMeta):
    """Definition of an abstract numerical field."""

    cast_type: type[Tnum]

    def gt(self, other: Tnum) -> SgFieldCondition:
        """Filter entities where this field is greater than the given value.

        This is the equivalent of the "greater_than" filter of Shotgrid.

        Args:
            other: The value to compare the field against

        Returns:
            The field condition
        """
        return SgFieldCondition(self, FilterOperatorGreaterThan(other))

    def lt(self, other: Tnum) -> SgFieldCondition:
        """Filter entities where this field is less than the given value.

        This is the equivalent of the "less_than" filter of Shotgrid.

        Args:
            other: The value to compare the field against

        Returns:
            The field condition
        """
        return SgFieldCondition(self, FilterOperatorLessThan(other))

    def between(self, low: Tnum, high: Tnum) -> SgFieldCondition:
        """Filter entities where this field is between the low and high values.

        This is the equivalent of the "between" filter of Shotgrid.

        Args:
            low: low value of the range
            high: high value of the range

        Returns:
            The field condition.
        """
        return SgFieldCondition(self, FilterOperatorBetween(low, high))

    def is_in(self, others: list[Tnum]) -> SgFieldCondition:
        """Filter entities where this field is within the given list of values.

        This is the equivalent of the "in" filter of Shotgrid.

        Args:
            others: values to test

        Returns:
            The field condition.
        """
        return SgFieldCondition(self, FilterOperatorIn(others))

    def is_not_in(self, others: list[Tnum]) -> SgFieldCondition:
        """Filter entities where this field is not within the given list of values.

        This is the equivalent of the "not_in" filter of Shotgrid.

        Args:
            others: values to test

        Returns:
            The field condition.
        """
        return SgFieldCondition(self, FilterOperatorNotIn(others))


class NumberField(NumericField[Optional[int]]):
    """An integer field."""

    __sg_type__: str = "number"
    cast_type: type[int] = int
    default_value = None

    if TYPE_CHECKING:

        @overload
        def __get__(self, instance: None, owner: SgEntityMeta) -> Self: ...

        @overload
        def __get__(
            self,
            instance: SgBaseEntity,
            owner: SgEntityMeta,
        ) -> int | None: ...

        def __get__(
            self,
            instance: SgBaseEntity | None,
            owner: SgEntityMeta,
        ) -> int | None | Self:
            """Return the value of the field."""


class FloatField(NumericField[float]):
    """A float field."""

    cast_type: type[float] = float
    __sg_type__: str = "float"
    default_value = 0.0

    if TYPE_CHECKING:

        @overload
        def __get__(self, instance: None, owner: SgEntityMeta) -> Self: ...

        @overload
        def __get__(self, instance: SgBaseEntity, owner: SgEntityMeta) -> float: ...

        def __get__(
            self,
            instance: SgBaseEntity | None,
            owner: SgEntityMeta,
        ) -> float | Self:
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
        return SgFieldCondition(self, FilterOperatorContains(text))

    def not_contains(self, text: str) -> SgFieldCondition:
        """Filter entities where this text field does not contain the given string.

        This is the equivalent of the "not_contains" filter of Shotgrid.

        Args:
            text: text to check

        Returns:
            The field condition.
        """
        return SgFieldCondition(self, FilterOperatorNotContains(text))

    def is_in(self, others: list[T]) -> SgFieldCondition:
        """Filter entities where this field is within the given list of values.

        This is the equivalent of the "in" filter of Shotgrid.

        Args:
            others: values to test

        Returns:
            The field condition.
        """
        return SgFieldCondition(self, FilterOperatorIn(others))

    def is_not_in(self, others: list[T]) -> SgFieldCondition:
        """Filter entities where this field is not within the given list of values.

        This is the equivalent of the "not_in" filter of Shotgrid.

        Args:
            others: values to test

        Returns:
            The field condition.
        """
        return SgFieldCondition(self, FilterOperatorNotIn(others))

    def startswith(self, text: str) -> SgFieldCondition:
        """Filter entities where this text field starts with the given text.

        This is the equivalent of the "start_with" filter of Shotgrid.

        Args:
            text: text to check

        Returns:
            The field condition.
        """
        return SgFieldCondition(self, FilterOperatorStartsWith(text))

    def endswith(self, text: str) -> SgFieldCondition:
        """Filter entities where this text field ends with the given text.

        This is the equivalent of the "end_with" filter of Shotgrid.

        Args:
            text: text to check

        Returns:
            The field condition.
        """
        return SgFieldCondition(self, FilterOperatorEndsWith(text))

    if TYPE_CHECKING:

        @overload
        def __get__(self, instance: None, owner: SgEntityMeta) -> Self: ...

        @overload
        def __get__(
            self,
            instance: SgBaseEntity,
            owner: SgEntityMeta,
        ) -> str | None: ...

        def __get__(
            self,
            instance: SgBaseEntity | None,
            owner: SgEntityMeta,
        ) -> str | None | Self:
            """Return the value of the field."""


Tfield = TypeVar("Tfield", bound=AbstractField[Any])


def _build_field_relative_to(
    field: Tfield,
    relative_field: AbstractField[Any],
) -> Tfield:
    """Build a new instrumented field relative to the given attribute.

    Returns:
        the attribute relative to the given attribute
    """
    field_info = field.__info__
    new_field_name = ".".join(
        [
            relative_field.__info__["name"],
            field_info["entity"].__sg_type__,
            field_info["name"],
        ],
    )
    new_field = field.__class__()
    # Modify the field info according to the new data
    new_field_info = field_info.copy()
    new_field_info["name"] = new_field_name
    new_field_info["field"] = new_field
    new_field_info["parent_field"] = relative_field
    new_field_info["entity"] = relative_field.__info__["entity"]
    new_field_info["name_in_relation"] = new_field_name
    new_field_info["original_field"] = field
    new_field.__info__ = new_field_info
    return new_field


class AbstractEntityField(AbstractField[T], metaclass=abc.ABCMeta):
    """Definition a field targeting an entity."""

    __sg_type__: str
    cast_type: type[T]

    def f(self, field: T_field) -> T_field:
        """Return the given field in relation to the given field."""
        info = field.__info__
        if info["entity"] not in get_types(self):
            error_message = (
                f"Cannot cast {self} as {field.__info__['entity'].__name__}. "
                f"Expected types are {get_types(field)}"
            )
            raise error.SgFieldConstructionError(error_message)
        return _build_field_relative_to(field, self)

    def type_is(self, entity_cls: type[SgBaseEntity]) -> SgFieldCondition:
        """Filter entities where this entity is of the given type.

        This is the equivalent of the "type_is" filter of Shotgrid.

        Args:
            entity_cls: entity to test

        Returns:
            The field condition.
        """
        return SgFieldCondition(self, FilterOperatorTypeIs(entity_cls))

    def type_is_not(self, entity_cls: type[SgBaseEntity]) -> SgFieldCondition:
        """Filter entities where this entity is not of the given type.

        This is the equivalent of the "type_is_not" filter of Shotgrid.

        Args:
            entity_cls: entity to test

        Returns:
            The field condition.
        """
        return SgFieldCondition(self, FilterOperatorTypeIsNot(entity_cls))

    def is_in(self, others: list[T]) -> SgFieldCondition:
        """Filter entities where this field is within the given list of values.

        This is the equivalent of the "in" filter of Shotgrid.

        Args:
            others: values to test

        Returns:
            The field condition.
        """
        return SgFieldCondition(self, FilterOperatorIn(others))

    def is_not_in(self, others: list[T]) -> SgFieldCondition:
        """Filter entities where this field is not within the given list of values.

        This is the equivalent of the "not_in" filter of Shotgrid.

        Args:
            others: values to test

        Returns:
            The field condition.
        """
        return SgFieldCondition(self, FilterOperatorNotIn(others))


def iter_single_entity(field_value: T_e | None) -> Iterable[EntityProtocol]:
    """Return an iterator with only the given value."""
    if field_value is None:
        return

    yield field_value


class EntityField(AbstractEntityField[Optional[T_e]]):
    """Definition a field targeting a single entity."""

    __sg_type__: str = "entity"
    cast_type: type[T_e]
    default_value = None

    def __init__(self, name: str = "") -> None:
        """Initialise the field."""
        super().__init__(
            name=name,
            default_value=None,
            is_relationship=True,
            as_list=False,
        )
        self.__info__["entity_iterator"] = iter_single_entity

    if TYPE_CHECKING:

        @overload
        def __get__(self, instance: None, owner: SgEntityMeta) -> Self: ...

        @overload
        def __get__(
            self,
            instance: SgBaseEntity,
            owner: SgEntityMeta,
        ) -> T_e | None: ...

        def __get__(
            self,
            instance: SgBaseEntity | None,
            owner: SgEntityMeta,
        ) -> T_e | None | Self:
            """Return the value of the field."""


def iter_multiple_entities(field_value: list[T_e]) -> Iterable[EntityProtocol]:
    """Return an iterator with the given entities."""
    return iter(field_value)


class MultiEntityField(AbstractEntityField[List[T_e]]):
    """Definition a field targeting multiple entities."""

    __sg_type__: str = "multi_entity"

    def __init__(self, name: str = "") -> None:
        """Initialize the field."""
        super().__init__(
            name=name,
            default_value=[],
            as_list=True,
            is_relationship=True,
        )
        self.__info__["entity_iterator"] = iter_multiple_entities

    if TYPE_CHECKING:

        @overload
        def __get__(self, instance: None, owner: SgEntityMeta) -> Self: ...

        @overload
        def __get__(self, instance: SgBaseEntity, owner: SgEntityMeta) -> list[T_e]: ...

        def __get__(
            self,
            instance: SgBaseEntity | None,
            owner: SgEntityMeta,
        ) -> list[T_e] | Self:
            """Return the value of the field."""


class BooleanField(AbstractValueField[Optional[bool]]):
    """Definition a boolean field."""

    __sg_type__: str = "checkbox"
    default_value: bool | None = None

    if TYPE_CHECKING:

        @overload
        def __get__(self, instance: None, owner: SgEntityMeta) -> Self: ...

        @overload
        def __get__(
            self,
            instance: SgBaseEntity,
            owner: SgEntityMeta,
        ) -> bool | None: ...

        def __get__(
            self,
            instance: SgBaseEntity | None,
            owner: SgEntityMeta,
        ) -> bool | None | Self:
            """Return the value of the field."""


class AbstractDateField(AbstractValueField[Tcomp]):
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
        return SgFieldCondition(self, FilterOperatorInLast(count, date_element))

    def not_in_last(self, count: int, date_element: DateType) -> SgFieldCondition:
        """Filter entities where this date is not within the last given quantities.

        This is the equivalent of the "not_in_last" filter of Shotgrid.

        Args:
            count: number of days/weeks/months/years
            date_element: duration type to consider

        Returns:
            The field condition.
        """
        return SgFieldCondition(self, FilterOperatorNotInLast(count, date_element))

    def in_next(self, count: int, date_element: DateType) -> SgFieldCondition:
        """Filter entities where this date is within the next given quantities.

        This is the equivalent of the "in_next" filter of Shotgrid.

        Args:
            count: number of days/weeks/months/years
            date_element: duration type to consider

        Returns:
            The field condition.
        """
        return SgFieldCondition(self, FilterOperatorInNext(count, date_element))

    def not_in_next(self, count: int, date_element: DateType) -> SgFieldCondition:
        """Filter entities where this date is not within the next given quantities.

        This is the equivalent of the "not_in_next" filter of Shotgrid.

        Args:
            count: number of days/weeks/months/years
            date_element: duration type to consider

        Returns:
            The field condition.
        """
        return SgFieldCondition(self, FilterOperatorNotInNext(count, date_element))

    def in_calendar_day(self, offset: int) -> SgFieldCondition:
        """Filter entities where this date is equal to the offset current day.

        This is the equivalent of the "in_calendar_day" filter of Shotgrid.

        Args:
            offset: offset (e.g. 0=today, 1=tomorrow, -1=yesterday)

        Returns:
            The field condition.
        """
        return SgFieldCondition(self, FilterOperatorInCalendarDay(offset))

    def in_calendar_week(self, offset: int) -> SgFieldCondition:
        """Filter entities where this date is equal to the offset current week.

        This is the equivalent of the "in_calendar_week" filter of Shotgrid.

        Args:
            offset: offset (e.g. 0=this week, 1=next week, -1=last week)

        Returns:
            The field condition.
        """
        return SgFieldCondition(self, FilterOperatorInCalendarWeek(offset))

    def in_calendar_month(self, offset: int) -> SgFieldCondition:
        """Filter entities where this date is equal to the offset current month.

        This is the equivalent of the "in_calendar_month" filter of Shotgrid.

        Args:
            offset: offset (e.g. 0=this month, 1=next month, -1= last month)

        Returns:
            The field condition.
        """
        return SgFieldCondition(self, FilterOperatorInCalendarMonth(offset))

    def in_calendar_year(self, offset: int) -> SgFieldCondition:
        """Filter entities where this date is equal to the offset current year.

        This is the equivalent of the "in_calendar_year" filter of Shotgrid.

        Args:
            offset: offset (e.g. 0=this year, 1=next year, -1= last year)

        Returns:
            The field condition.
        """
        return SgFieldCondition(self, FilterOperatorInCalendarYear(offset))


class DateField(AbstractDateField[Optional[date]]):
    """Definition of a date field."""

    cast_type: type[date] = date
    __sg_type__: str = "date"
    default_value: date | None = None

    if TYPE_CHECKING:

        @overload
        def __get__(self, instance: None, owner: SgEntityMeta) -> Self: ...

        @overload
        def __get__(
            self,
            instance: SgBaseEntity,
            owner: SgEntityMeta,
        ) -> date | None: ...

        def __get__(
            self,
            instance: SgBaseEntity | None,
            owner: SgEntityMeta,
        ) -> date | None | Self:
            """Return the value of the field."""


class DateTimeField(AbstractDateField[Optional[datetime]]):
    """Definition of a date time field."""

    cast_type: type[datetime] = datetime
    __sg_type__: str = "date_time"
    default_value = None

    if TYPE_CHECKING:

        @overload
        def __get__(self, instance: None, owner: SgEntityMeta) -> Self: ...

        @overload
        def __get__(
            self,
            instance: SgBaseEntity,
            owner: SgEntityMeta,
        ) -> datetime | None: ...

        def __get__(
            self,
            instance: SgBaseEntity | None,
            owner: SgEntityMeta,
        ) -> datetime | None | Self:
            """Return the value of the field."""


class DurationField(NumberField):
    """Definition of a duration field."""

    __sg_type__: str = "duration"

    if TYPE_CHECKING:

        @overload
        def __get__(self, instance: None, owner: SgEntityMeta) -> Self: ...

        @overload
        def __get__(
            self,
            instance: SgBaseEntity,
            owner: SgEntityMeta,
        ) -> int | None: ...

        def __get__(
            self,
            instance: SgBaseEntity | None,
            owner: SgEntityMeta,
        ) -> int | None | Self:
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
        return SgFieldCondition(self, FilterOperatorIsNot(None))

    def not_exists(self) -> SgFieldCondition:
        """Filter entities where this image does not exist.

        This is the equivalent of the "is_not" filter of Shotgrid.

        Returns:
            The field condition.
        """
        return SgFieldCondition(self, FilterOperatorIs(None))

    if TYPE_CHECKING:

        @overload
        def __get__(self, instance: None, owner: SgEntityMeta) -> Self: ...

        @overload
        def __get__(
            self,
            instance: SgBaseEntity,
            owner: SgEntityMeta,
        ) -> str | None: ...

        def __get__(
            self,
            instance: SgBaseEntity | None,
            owner: SgEntityMeta,
        ) -> str | None | Self:
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
        return SgFieldCondition(self, FilterOperatorIn(others))

    def is_not_in(self, others: list[str]) -> SgFieldCondition:
        """Filter entities where this field is not within the given list of values.

        This is the equivalent of the "not_in" filter of Shotgrid.

        Args:
            others: values to test

        Returns:
            The field condition.
        """
        return SgFieldCondition(self, FilterOperatorNotIn(others))

    if TYPE_CHECKING:

        @overload
        def __get__(self, instance: None, owner: SgEntityMeta) -> Self: ...

        @overload
        def __get__(
            self,
            instance: SgBaseEntity,
            owner: SgEntityMeta,
        ) -> list[str] | None: ...

        def __get__(
            self,
            instance: SgBaseEntity | None,
            owner: SgEntityMeta,
        ) -> list[str] | None | Self:
            """Return the value of the field."""


class PercentField(FloatField):
    """Definition of a percent field."""

    __sg_type__: str = "percent"

    if TYPE_CHECKING:

        @overload
        def __get__(self, instance: None, owner: SgEntityMeta) -> Self: ...

        @overload
        def __get__(self, instance: SgBaseEntity, owner: SgEntityMeta) -> float: ...

        def __get__(
            self,
            instance: SgBaseEntity | None,
            owner: SgEntityMeta,
        ) -> float | Self:
            """Return the value of the field."""


class SerializableField(AbstractValueField[Optional[Dict[str, Any]]]):
    """Definition of a serializable field."""

    cast_type: type[dict[str, Any]] = dict
    __sg_type__: str = "serializable"
    default_value = None

    if TYPE_CHECKING:

        @overload
        def __get__(self, instance: None, owner: SgEntityMeta) -> Self: ...

        @overload
        def __get__(
            self,
            instance: SgBaseEntity,
            owner: SgEntityMeta,
        ) -> dict[str, Any] | None: ...

        def __get__(
            self,
            instance: SgBaseEntity | None,
            owner: SgEntityMeta,
        ) -> dict[str, Any] | None | Self:
            """Return the value of the field."""


class StatusField(AbstractValueField[str]):
    """Definition of a status field."""

    __sg_type__: str = "status_list"
    default_value = "wtg"

    if TYPE_CHECKING:

        @overload
        def __get__(self, instance: None, owner: SgEntityMeta) -> Self: ...

        @overload
        def __get__(self, instance: SgBaseEntity, owner: SgEntityMeta) -> str: ...

        def __get__(
            self,
            instance: SgBaseEntity | None,
            owner: SgEntityMeta,
        ) -> str | Self:
            """Return the value of the field."""


class UrlField(AbstractValueField[Optional[str]]):
    """Definition of an url field."""

    cast_type: type[str] = str
    __sg_type__: str = "url"
    default_value = None

    if TYPE_CHECKING:

        @overload
        def __get__(self, instance: None, owner: SgEntityMeta) -> Self: ...

        @overload
        def __get__(
            self,
            instance: SgBaseEntity,
            owner: SgEntityMeta,
        ) -> str | None: ...

        def __get__(
            self,
            instance: SgBaseEntity | None,
            owner: SgEntityMeta,
        ) -> str | None | Self:
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
    field: AbstractField[T],
    entity: SgBaseEntity,
    field_value: T,
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
