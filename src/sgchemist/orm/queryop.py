"""Defines operators for building queries."""

from __future__ import annotations

import abc
import datetime
from typing import TYPE_CHECKING
from typing import Any
from typing import Generic
from typing import TypeVar
from typing import Union

from typing_extensions import Protocol
from typing_extensions import Self
from typing_extensions import TypedDict

from .constant import DateType
from .constant import LogicalOperator
from .typing_util import Comparable

if TYPE_CHECKING:
    from .entity import SgBaseEntity
    from .fields import AbstractField

T = TypeVar("T")
Tser = TypeVar("Tser")
Tsumup = TypeVar("Tsumup")
Tcomp = TypeVar("Tcomp", bound=Comparable)


class WithSgType(Protocol):
    """Defines an element which has a str __sg_type__ attribute."""

    __sg_type__: str


class FilterOperator(Generic[T, Tser], abc.ABC):
    """A Shotgrid operator."""

    __sg_op__: str

    @abc.abstractmethod
    def eval(self, value: T) -> bool:
        """Evaluate the filter on the given value."""

    @abc.abstractmethod
    def serialize(self) -> Tser:
        """Serialize the filter value."""


class FilterOperatorBetween(FilterOperator[Tcomp, list[Union[Tcomp, None]]]):
    """A between filter."""

    __sg_op__ = "between"

    def __init__(self, low_bound: Tcomp | None, high_bound: Tcomp | None) -> None:
        """Initialize the filter operator."""
        self.__low_bound = low_bound
        self.__high_bound = high_bound

    def eval(self, value: Tcomp | None) -> bool:
        """Evaluate the filter on the given value."""
        if value is None or self.__low_bound is None or self.__high_bound is None:
            return False

        return self.__low_bound <= value <= self.__high_bound

    def serialize(self) -> list[Tcomp | None]:
        """Serialize the filter value."""
        return [self.__low_bound, self.__high_bound]


class FilterOperatorContains(FilterOperator[str, str]):
    """A contains filter."""

    __sg_op__ = "contains"

    def __init__(self, string: str) -> None:
        """Initialize the filter operator."""
        self.__string = string

    def eval(self, value: str) -> bool:
        """Evaluate the filter on the given value."""
        return self.__string in value

    def serialize(self) -> str:
        """Serialize the filter value."""
        return self.__string


class FilterOperatorEndsWith(FilterOperator[str, str]):
    """A endswith filter."""

    __sg_op__ = "end_with"

    def __init__(self, string: str) -> None:
        """Initialize the filter operator."""
        self.__string = string

    def eval(self, value: str) -> bool:
        """Evaluate the filter on the given value."""
        return value.endswith(self.__string)

    def serialize(self) -> str:
        """Serialize the filter value."""
        return self.__string


class FilterOperatorGreaterThan(FilterOperator[Tcomp, Tcomp]):
    """A endswith filter."""

    __sg_op__ = "greater_than"

    def __init__(self, value: Tcomp) -> None:
        """Initialize the filter operator."""
        self.__value = value

    def eval(self, value: Tcomp) -> bool:
        """Evaluate the filter on the given value."""
        if value is None or self.__value is None:
            return False
        return value > self.__value

    def serialize(self) -> Tcomp:
        """Serialize the filter value."""
        return self.__value


class FilterOperatorIn(FilterOperator[T, list[T]]):
    """An in filter."""

    __sg_op__ = "in"

    def __init__(self, container: list[T]) -> None:
        """Initialize the filter operator."""
        self.__value = container

    def eval(self, value: T) -> bool:
        """Evaluate the filter on the given value."""
        return value in self.__value

    def serialize(self) -> list[T]:
        """Serialize the filter value."""
        return self.__value


class FilterOperatorInCalendarDay(FilterOperator[datetime.datetime, int]):
    """An in_calendar_day filter."""

    __sg_op__ = "in_calendar_day"

    def __init__(self, offset: int) -> None:
        """Initialize the filter operator."""
        self.__offset = offset

    def eval(self, value: datetime.datetime) -> bool:
        """Evaluate the filter on the given value."""
        today = datetime.datetime.now(value.tzinfo)
        offset_today = today + datetime.timedelta(days=self.__offset)
        if self.__offset >= 0:
            return today < value < offset_today
        return today > value > offset_today

    def serialize(self) -> int:
        """Serialize the filter value."""
        return self.__offset


class FilterOperatorInCalendarMonth(FilterOperator[datetime.datetime, int]):
    """An in_calendar_month filter."""

    __sg_op__ = "in_calendar_month"

    def __init__(self, offset: int) -> None:
        """Initialize the filter operator."""
        self.__offset = offset

    def eval(self, value: datetime.datetime) -> bool:
        """Evaluate the filter on the given value."""
        # There are not always the same number of days between two months
        today = datetime.datetime.now(value.tzinfo)
        year_offset, month = divmod(today.month + self.__offset, 12)
        calendar_month = today.replace(year=today.year + year_offset, month=month)
        if self.__offset >= 0:
            return today < value < calendar_month
        return today > value > calendar_month

    def serialize(self) -> int:
        """Serialize the filter value."""
        return self.__offset


class FilterOperatorInCalendarWeek(FilterOperator[datetime.datetime, int]):
    """An in_calendar_week filter."""

    __sg_op__ = "in_calendar_week"

    def __init__(self, offset: int) -> None:
        """Initialize the filter operator."""
        self.__offset = offset

    def eval(self, value: datetime.datetime) -> bool:
        """Evaluate the filter on the given value."""
        today = datetime.datetime.now(value.tzinfo)
        offset_today = today + datetime.timedelta(weeks=self.__offset)
        if self.__offset >= 0:
            return today < value < offset_today
        return today > value > offset_today

    def serialize(self) -> int:
        """Serialize the filter value."""
        return self.__offset


class FilterOperatorInCalendarYear(FilterOperator[datetime.datetime, int]):
    """An in_calendar_year filter."""

    __sg_op__ = "in_calendar_year"

    def __init__(self, offset: int) -> None:
        """Initialize the filter operator."""
        self.__offset = offset

    def eval(self, value: datetime.datetime) -> bool:
        """Evaluate the filter on the given value."""
        # There are not always the same number of days between two years
        today = datetime.datetime.now(value.tzinfo)
        calendar_year = today.replace(year=today.year + self.__offset)
        if self.__offset >= 0:
            return today < value < calendar_year
        return today > value > calendar_year

    def serialize(self) -> int:
        """Serialize the filter value."""
        return self.__offset


class FilterOperatorInLast(FilterOperator[datetime.datetime, list[Union[str, int]]]):
    """An in_last filter."""

    __sg_op__ = "in_last"

    def __init__(self, offset: int, date_type: DateType) -> None:
        """Initialize the filter operator."""
        self.__offset = offset
        self.__date_type = date_type

    def eval(self, value: datetime.datetime) -> bool:
        """Evaluate the filter on the given value."""
        today = datetime.datetime.now(value.tzinfo)
        if self.__date_type == DateType.YEAR:
            compare = today.replace(year=today.year - self.__offset)
        elif self.__date_type == DateType.MONTH:
            year_offset, month = divmod(today.month - self.__offset, 12)
            compare = today.replace(year=today.year + year_offset, month=month)
        else:
            time_value = {f"{self.__date_type.value.lower()}s": self.__offset}
            compare = today - datetime.timedelta(**time_value)
        return today > value > compare

    def serialize(self) -> list[str | int]:
        """Serialize the filter value."""
        return [self.__offset, self.__date_type.value]


class FilterOperatorInNext(FilterOperator[datetime.datetime, list[Union[str, int]]]):
    """An in_next filter."""

    __sg_op__ = "in_next"

    def __init__(self, offset: int, date_type: DateType) -> None:
        """Initialize the filter operator."""
        self.__offset = offset
        self.__date_type = date_type

    def eval(self, value: datetime.datetime) -> bool:
        """Evaluate the filter on the given value."""
        today = datetime.datetime.now(value.tzinfo)
        if self.__date_type == DateType.YEAR:
            compare = today.replace(year=today.year + self.__offset)
        elif self.__date_type == DateType.MONTH:
            year_offset, month = divmod(today.month + self.__offset, 12)
            compare = today.replace(year=today.year + year_offset, month=month)
        else:
            time_value = {f"{self.__date_type.value.lower()}s": self.__offset}
            compare = today + datetime.timedelta(**time_value)
        return today < value < compare

    def serialize(self) -> list[str | int]:
        """Serialize the filter value."""
        return [self.__offset, self.__date_type.value]


class FilterOperatorIs(FilterOperator[T, T]):
    """An in_last filter."""

    __sg_op__ = "is"

    def __init__(self, value: T) -> None:
        """Initialize the filter operator."""
        self.__value = value

    def eval(self, value: T) -> bool:
        """Evaluate the filter on the given value."""
        return value == self.__value

    def serialize(self) -> T:
        """Serialize the filter value."""
        return self.__value


class FilterOperatorIsNot(FilterOperator[T, T]):
    """An in_last filter."""

    __sg_op__ = "is_not"

    def __init__(self, value: T) -> None:
        """Initialize the filter operator."""
        self.__value = value

    def eval(self, value: T) -> bool:
        """Evaluate the filter on the given value."""
        return value != self.__value

    def serialize(self) -> T:
        """Serialize the filter value."""
        return self.__value


class FilterOperatorLessThan(FilterOperator[Tcomp, Tcomp]):
    """An in_last filter."""

    __sg_op__ = "less_than"

    def __init__(self, value: Tcomp) -> None:
        """Initialize the filter operator."""
        self.__value = value

    def eval(self, value: Tcomp) -> bool:
        """Evaluate the filter on the given value."""
        if value is None or self.__value is None:
            return False
        return value < self.__value

    def serialize(self) -> Tcomp:
        """Serialize the filter value."""
        return self.__value


class FilterOperatorNotContains(FilterOperator[str, str]):
    """A not_contains filter."""

    __sg_op__ = "not_contains"

    def __init__(self, string: str) -> None:
        """Initialize the filter operator."""
        self.__string = string

    def eval(self, value: str) -> bool:
        """Evaluate the filter on the given value."""
        return self.__string not in value

    def serialize(self) -> str:
        """Serialize the filter value."""
        return self.__string


class FilterOperatorNotIn(FilterOperator[T, list[T]]):
    """A not_in filter."""

    __sg_op__ = "not_in"

    def __init__(self, container: list[T]) -> None:
        """Initialize the filter operator."""
        self.__container = container

    def eval(self, value: T) -> bool:
        """Evaluate the filter on the given value."""
        return value not in self.__container

    def serialize(self) -> list[T]:
        """Serialize the filter value."""
        return self.__container


class FilterOperatorNotInLast(FilterOperator[datetime.datetime, list[Union[str, int]]]):
    """A not_in_last filter."""

    __sg_op__ = "not_in_last"

    def __init__(self, offset: int, date_type: DateType) -> None:
        """Initialize the filter operator."""
        self.__offset = offset
        self.__date_type = date_type

    def eval(self, value: datetime.datetime) -> bool:
        """Evaluate the filter on the given value."""
        today = datetime.datetime.now(value.tzinfo)
        if self.__date_type == DateType.YEAR:
            compare = today.replace(year=today.year - self.__offset)
        elif self.__date_type == DateType.MONTH:
            year_offset, month = divmod(today.month - self.__offset, 12)
            compare = today.replace(year=today.year + year_offset, month=month)
        else:
            time_value = {f"{self.__date_type.value.lower()}s": self.__offset}
            compare = today - datetime.timedelta(**time_value)
        return today < value or value < compare

    def serialize(self) -> list[str | int]:
        """Serialize the filter value."""
        return [self.__offset, self.__date_type.value]


class FilterOperatorNotInNext(FilterOperator[datetime.datetime, list[Union[str, int]]]):
    """A not_in_next filter."""

    __sg_op__ = "not_in_next"

    def __init__(self, offset: int, date_type: DateType) -> None:
        """Initialize the filter operator."""
        self.__offset = offset
        self.__date_type = date_type

    def eval(self, value: datetime.datetime) -> bool:
        """Evaluate the filter on the given value."""
        today = datetime.datetime.now(value.tzinfo)
        if self.__date_type == DateType.YEAR:
            compare = today.replace(year=today.year + self.__offset)
        elif self.__date_type == DateType.MONTH:
            year_offset, month = divmod(today.month + self.__offset, 12)
            compare = today.replace(year=today.year + year_offset, month=month)
        else:
            time_value = {f"{self.__date_type.value.lower()}s": self.__offset}
            compare = today + datetime.timedelta(**time_value)
        return today > value or value > compare

    def serialize(self) -> list[int | str]:
        """Serialize the filter value."""
        return [self.__offset, self.__date_type.value]


class FilterOperatorStartsWith(FilterOperator[str, str]):
    """A endswith filter."""

    __sg_op__ = "start_with"

    def __init__(self, string: str) -> None:
        """Initialize the filter operator."""
        self.__string = string

    def eval(self, value: str) -> bool:
        """Evaluate the filter on the given value."""
        return value.startswith(self.__string)

    def serialize(self) -> str:
        """Serialize the filter value."""
        return self.__string


class FilterOperatorTypeIs(FilterOperator[WithSgType, str]):
    """A type_is filter."""

    __sg_op__ = "type_is"

    def __init__(self, entity: WithSgType) -> None:
        """Initialize the filter operator."""
        self.__entity = entity

    def eval(self, value: WithSgType) -> bool:
        """Evaluate the filter on the given value."""
        return value.__sg_type__ == self.__entity.__sg_type__

    def serialize(self) -> str:
        """Serialize the filter value."""
        return self.__entity.__sg_type__


class FilterOperatorTypeIsNot(FilterOperator[WithSgType, str]):
    """A type_is_not filter."""

    __sg_op__ = "type_is_not"

    def __init__(self, entity: WithSgType) -> None:
        """Initialize the filter operator."""
        self.__entity = entity

    def eval(self, value: WithSgType) -> bool:
        """Evaluate the filter on the given value."""
        return value.__sg_type__ != self.__entity.__sg_type__

    def serialize(self) -> str:
        """Serialize the filter value."""
        return self.__entity.__sg_type__


class SerializedOperator(TypedDict):
    """Defines a serialized operator dict."""

    filter_operator: str
    filters: list[Any]


class SgSerializable:
    """A serializable object for building queries."""


class SgFilterObject(SgSerializable):
    """Defines a generic query object to operate on."""

    @abc.abstractmethod
    def __and__(self, other: SgFilterObject) -> SgFilterObject:
        """Combines this object with another with a and operation.

        Args:
            other: object to combine.

        Returns:
            combined object.
        """

    @abc.abstractmethod
    def __or__(self, other: SgFilterObject) -> SgFilterObject:
        """Combines this object with another with a or operation.

        Args:
            other: object to combine.

        Returns:
            combined object.
        """

    @abc.abstractmethod
    def matches(self, entity: SgBaseEntity) -> bool:
        """Return True if this filter matches the given entity."""


class SgNullCondition(SgFilterObject):
    """Defines a null condition."""

    def __and__(self, other: SgFilterObject) -> SgFilterObject:
        """Returns the other object as null condition has no effect.

        Args:
            other: object to combine.

        Returns:
            combined object.
        """
        return other

    def __or__(self, other: SgFilterObject) -> SgFilterObject:
        """Returns the other object as null condition has no effect.

        Args:
            other: object to combine.

        Returns:
            combined object.
        """
        return other

    def matches(self, _: SgBaseEntity) -> bool:
        """A null condition always matches the given entity."""
        return True


class SgFilterOperation(SgFilterObject):
    """Defines a filter operation between different SgFilterObjects."""

    def __init__(
        self,
        operator: LogicalOperator,
        sg_objects: list[SgFilterObject],
    ) -> None:
        """Initialize the filter operation.

        Args:
            operator: operator to use.
            sg_objects: list of filter objects.
        """
        self.operator = operator
        self.sg_objects = sg_objects

    def _op(self, operator: LogicalOperator, other: SgFilterObject) -> Self:
        """Returns a new filter operation combining this operation with another object.

        Args:
            operator: operator to use.
            other: object to combine.

        Returns:
            combined object.
        """
        objects: list[SgFilterObject] = [self, other]

        # Concatenate filters if possible to decrease nesting
        if isinstance(other, SgFilterOperation):
            if other.operator == self.operator == operator:
                objects = self.sg_objects + other.sg_objects
        elif self.operator == operator:
            objects = [*self.sg_objects, other]

        return self.__class__(operator, objects)

    def __and__(self, other: SgFilterObject) -> Self:
        """Combines this operation with another object with a and operator.

        Args:
            other: object to combine.

        Returns:
            combined object.
        """
        return self._op(LogicalOperator.ALL, other)

    def __or__(self, other: SgFilterObject) -> Self:
        """Combines this operation with another object with a or operator.

        Args:
            other: object to combine.

        Returns:
            combined object.
        """
        return self._op(LogicalOperator.ANY, other)

    def matches(self, entity: SgBaseEntity) -> bool:
        """Return True if the entity matches the given filter."""
        test_func = {
            LogicalOperator.ALL: all,
            LogicalOperator.ANY: any,
        }[self.operator]
        return test_func(sg_object.matches(entity) for sg_object in self.sg_objects)


class SgFieldCondition(SgFilterObject):
    """Defines a field condition."""

    def __init__(
        self,
        field: AbstractField[T],
        filter_operator: FilterOperator[Any, Any],
    ) -> None:
        """Initialize the field condition.

        Args:
            field: field attribute to create the condition on
            filter_operator: operator to use.
        """
        self.field = field
        self.op = filter_operator

    def __and__(self, other: SgFilterObject) -> SgFilterOperation:
        """Combines this operation with another object with a and operator.

        Returns:
            combined object.
        """
        return SgFilterOperation(LogicalOperator.ALL, [self, other])

    def __or__(self, other: SgFilterObject) -> SgFilterOperation:
        """Combines this operation with another object with a or operator.

        Returns:
            combined object.
        """
        return SgFilterOperation(LogicalOperator.ANY, [self, other])

    def matches(self, entity: SgBaseEntity) -> bool:
        """Return True if the given entity matches the filter."""
        value: Any = entity.get_value(self.field)
        return self.op.eval(value)
