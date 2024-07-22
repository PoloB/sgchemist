"""Defines operators for building queries."""

from __future__ import annotations

import abc
import datetime
import operator
from typing import TYPE_CHECKING
from typing import Any
from typing import Generic
from typing import TypeVar

from typing_extensions import Self

from .constant import DateType
from .constant import LogicalOperator
from .entity import SgEntityMeta

if TYPE_CHECKING:
    from . import SgBaseEntity
    from .fields import AbstractField

T = TypeVar("T")


class FilterOperator(Generic[T], abc.ABC):
    """A Shotgrid operator."""

    __sg_op__: str

    def eval(self, value: T) -> bool:
        """Evaluate the filter on the given value."""


class FilterOperatorBetween(FilterOperator[T]):
    """A between filter."""

    __sg_op__ = "between"

    def __init__(self, low_bound: T, high_bound: T) -> None:
        """Initialize the filter operator."""
        self.__low_bound = low_bound
        self.__high_bound = high_bound

    def eval(self, value: T) -> bool:
        return self.__low_bound <= value <= self.__high_bound


class FilterOperatorContains(FilterOperator[str]):
    """A contains filter."""

    __sg_op__ = "contains"

    def __init__(self, string: str) -> None:
        """Initialize the filter operator."""
        self.__string = string

    def eval(self, value: str) -> bool:
        return self.__string in value


class FilterOperatorEndsWith(FilterOperator[str]):
    """A endswith filter."""

    __sg_op__ = "end_with"

    def __init__(self, string: str) -> None:
        """Initialize the filter operator."""
        self.__string = string

    def eval(self, value: str) -> bool:
        return value.endswith(self.__string)


class FilterOperatorGreaterThan(FilterOperator[T]):
    """A endswith filter."""

    __sg_op__ = "greater_than"

    def __init__(self, value: T) -> None:
        """Initialize the filter operator."""
        self.__value = value

    def eval(self, value: T) -> bool:
        return value > self.__value


class FilterOperatorIn(FilterOperator[T]):
    """An in filter."""

    __sg_op__ = "in"

    def __init__(self, container: list[T]) -> None:
        """Initialize the filter operator."""
        self.__value = container

    def eval(self, value: T) -> bool:
        return value in self.__value


class FilterOperatorInCalendarDay(FilterOperator[datetime.datetime]):
    """An in_calendar_day filter."""

    __sg_op__ = "in_calendar_day"

    def __init__(self, offset: int) -> None:
        """Initialize the filter operator."""
        self.__offset = offset

    def eval(self, value: datetime.datetime) -> bool:
        op = operator.le if self.__offset >= 0 else operator.gt
        today = datetime.datetime.now(value.tzinfo)
        offset_today = today + datetime.timedelta(days=self.__offset)
        return op(today, value) and op(value, offset_today)


class FilterOperatorInCalendarMonth(FilterOperator[datetime.datetime]):
    """An in_calendar_month filter."""

    __sg_op__ = "in_calendar_month"

    def __init__(self, offset: int) -> None:
        """Initialize the filter operator."""
        self.__offset = offset

    def eval(self, value: datetime.datetime) -> bool:
        # There are not always the same number of days between two months
        op = operator.le if self.__offset >= 0 else operator.gt
        today = datetime.datetime.now(value.tzinfo)
        year_offset, month = divmod(today.month + self.__offset, 12)
        calendar_month = today.replace(year=today.year + year_offset, month=month)
        return op(today, value) and op(value, calendar_month)


class FilterOperatorInCalendarWeek(FilterOperator[datetime.datetime]):
    """An in_calendar_week filter."""

    __sg_op__ = "in_calendar_week"

    def __init__(self, offset: int) -> None:
        """Initialize the filter operator."""
        self.__offset = offset

    def eval(self, value: datetime.datetime) -> bool:
        op = operator.le if self.right >= 0 else operator.gt
        today = datetime.datetime.now(value.tzinfo)
        offset_today = today + datetime.timedelta(weeks=self.right)
        return op(today, value) and op(value, offset_today)


class FilterOperatorInCalendarYear(FilterOperator[datetime.datetime]):
    """An in_calendar_year filter."""

    __sg_op__ = "in_calendar_year"

    def __init__(self, offset: int) -> None:
        """Initialize the filter operator."""
        self.__offset = offset

    def eval(self, value: datetime.datetime) -> bool:
        # There are not always the same number of days between two years
        op = operator.le if self.__offset >= 0 else operator.gt
        today = datetime.datetime.now(value.tzinfo)
        calendar_year = today.replace(year=today.year + self.__offset)
        return op(today, value) and op(value, calendar_year)


class FilterOperatorInLast(FilterOperator[datetime.datetime]):
    """An in_last filter."""

    __sg_op__ = "in_last"

    def __init__(self, offset: int, date_type: DateType) -> None:
        """Initialize the filter operator."""
        self.__offset = offset
        self.__date_type = date_type

    def eval(self, value: datetime.datetime) -> bool:
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


class FilterOperatorInNext(FilterOperator[datetime.datetime]):
    """An in_next filter."""

    __sg_op__ = "in_next"

    def __init__(self, offset: int, date_type: DateType) -> None:
        """Initialize the filter operator."""
        self.__offset = offset
        self.__date_type = date_type

    def eval(self, value: datetime.datetime) -> bool:
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


class FilterOperatorIS(FilterOperator[T]):
    """An in_last filter."""

    __sg_op__ = "is"

    def __init__(self, value: T) -> None:
        """Initialize the filter operator."""
        self.__value = value

    def eval(self, value: T) -> bool:
        return value == self.__value


class FilterOperatorIsNot(FilterOperator[T]):
    """An in_last filter."""

    __sg_op__ = "is_not"

    def __init__(self, value: T) -> None:
        """Initialize the filter operator."""
        self.__value = value

    def eval(self, value: T) -> bool:
        return value != self.__value


class FilterOperatorLessThan(FilterOperator[T]):
    """An in_last filter."""

    __sg_op__ = "less_than"

    def __init__(self, value: T) -> None:
        """Initialize the filter operator."""
        self.__value = value

    def eval(self, value: T) -> bool:
        return value < self.__value


class FilterOperatorNotContains(FilterOperator[str]):
    """A not_contains filter."""

    __sg_op__ = "not_contains"

    def __init__(self, string: str) -> None:
        """Initialize the filter operator."""
        self.__string = string

    def eval(self, value: str) -> bool:
        return self.__string not in value


class FilterOperatorNotIn(FilterOperator[T]):
    """A not_in filter."""

    __sg_op__ = "not_in"

    def __init__(self, container: list[T]) -> None:
        """Initialize the filter operator."""
        self.__container = container

    def eval(self, value: T) -> bool:
        return value not in self.__container


class FilterOperatorNotInLast(FilterOperator[datetime.datetime]):
    """A not_in_last filter."""

    __sg_op__ = "not_in_last"

    def __init__(self, offset: int, date_type: DateType) -> None:
        """Initialize the filter operator."""
        self.__offset = offset
        self.__date_type = date_type

    def eval(self, value: datetime.datetime) -> bool:
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


class FilterOperatorNotInNext(FilterOperator[datetime.datetime]):
    """A not_in_next filter."""

    __sg_op__ = "not_in_next"

    def __init__(self, offset: int, date_type: DateType) -> None:
        """Initialize the filter operator."""
        self.__offset = offset
        self.__date_type = date_type

    def eval(self, value: datetime.datetime) -> bool:
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


class FilterOperatorStartsWith(FilterOperator[str]):
    """A endswith filter."""

    __sg_op__ = "start_with"

    def __init__(self, string: str) -> None:
        """Initialize the filter operator."""
        self.__string = string

    def eval(self, value: str) -> bool:
        return value.startswith(self.__string)


class FilterOperatorTypeIs(FilterOperator[SgBaseEntity]):
    """A type_is filter."""

    __sg_op__ = "type_is"

    def __init__(self, entity: SgEntityMeta) -> None:
        """Initialize the filter operator."""
        self.__entity = entity

    def eval(self, value: SgBaseEntity) -> bool:
        return value.__sg_type__ == self.__entity.__sg_type__


class FilterOperatorTypeIsNot(FilterOperator[SgBaseEntity]):
    """A type_is_not filter."""

    __sg_op__ = "type_is_not"

    def __init__(self, entity: SgEntityMeta) -> None:
        """Initialize the filter operator."""
        self.__entity = entity

    def eval(self, value: SgBaseEntity) -> bool:
        return value.__sg_type__ != self.__entity.__sg_type__


class SgFilterObject(object):
    """Defines a generic query object to operate on."""

    __metaclass__ = abc.ABCMeta

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

    def matches(self, entity: SgBaseEntity) -> bool:
        """A null condition always matches the given entity."""
        return True


class SgFilterOperation(SgFilterObject):
    """Defines a filter operation between different SgFilterObjects."""

    def __init__(self, operator: LogicalOperator, sg_objects: list[SgFilterObject]):
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
        self, field: AbstractField[T], filter_operator: FilterOperator
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
