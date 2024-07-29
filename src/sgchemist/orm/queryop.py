"""Defines operators for building queries."""

from __future__ import annotations

import abc
import datetime
import statistics
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
Tsumup = TypeVar("Tsumup")
Tcomp = TypeVar("Tcomp", bound=Comparable)


class WithSgType(Protocol):
    """Defines an element which has a str __sg_type__ attribute."""

    __sg_type__: str


class FilterOperator(Generic[T], abc.ABC):
    """A Shotgrid operator."""

    __sg_op__: str

    @abc.abstractmethod
    def eval(self, value: T) -> bool:
        """Evaluate the filter on the given value."""

    @abc.abstractmethod
    def serialize(self) -> Any:
        """Serialize the filter value."""


class FilterOperatorBetween(FilterOperator[Tcomp]):
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

    def serialize(self) -> Any:
        """Serialize the filter value."""
        return [self.__low_bound, self.__high_bound]


class FilterOperatorContains(FilterOperator[str]):
    """A contains filter."""

    __sg_op__ = "contains"

    def __init__(self, string: str) -> None:
        """Initialize the filter operator."""
        self.__string = string

    def eval(self, value: str) -> bool:
        """Evaluate the filter on the given value."""
        return self.__string in value

    def serialize(self) -> Any:
        """Serialize the filter value."""
        return self.__string


class FilterOperatorEndsWith(FilterOperator[str]):
    """A endswith filter."""

    __sg_op__ = "end_with"

    def __init__(self, string: str) -> None:
        """Initialize the filter operator."""
        self.__string = string

    def eval(self, value: str) -> bool:
        """Evaluate the filter on the given value."""
        return value.endswith(self.__string)

    def serialize(self) -> Any:
        """Serialize the filter value."""
        return self.__string


class FilterOperatorGreaterThan(FilterOperator[Tcomp]):
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

    def serialize(self) -> Any:
        """Serialize the filter value."""
        return self.__value


class FilterOperatorIn(FilterOperator[T]):
    """An in filter."""

    __sg_op__ = "in"

    def __init__(self, container: list[T]) -> None:
        """Initialize the filter operator."""
        self.__value = container

    def eval(self, value: T) -> bool:
        """Evaluate the filter on the given value."""
        return value in self.__value

    def serialize(self) -> Any:
        """Serialize the filter value."""
        return self.__value


class FilterOperatorInCalendarDay(FilterOperator[datetime.datetime]):
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

    def serialize(self) -> Any:
        """Serialize the filter value."""
        return self.__offset


class FilterOperatorInCalendarMonth(FilterOperator[datetime.datetime]):
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

    def serialize(self) -> Any:
        """Serialize the filter value."""
        return self.__offset


class FilterOperatorInCalendarWeek(FilterOperator[datetime.datetime]):
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

    def serialize(self) -> Any:
        """Serialize the filter value."""
        return self.__offset


class FilterOperatorInCalendarYear(FilterOperator[datetime.datetime]):
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

    def serialize(self) -> Any:
        """Serialize the filter value."""
        return self.__offset


class FilterOperatorInLast(FilterOperator[datetime.datetime]):
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

    def serialize(self) -> Any:
        """Serialize the filter value."""
        return [self.__offset, self.__date_type.value]


class FilterOperatorInNext(FilterOperator[datetime.datetime]):
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

    def serialize(self) -> Any:
        """Serialize the filter value."""
        return [self.__offset, self.__date_type.value]


class FilterOperatorIs(FilterOperator[T]):
    """An in_last filter."""

    __sg_op__ = "is"

    def __init__(self, value: T) -> None:
        """Initialize the filter operator."""
        self.__value = value

    def eval(self, value: T) -> bool:
        """Evaluate the filter on the given value."""
        return value == self.__value

    def serialize(self) -> Any:
        """Serialize the filter value."""
        return self.__value


class FilterOperatorIsNot(FilterOperator[T]):
    """An in_last filter."""

    __sg_op__ = "is_not"

    def __init__(self, value: T) -> None:
        """Initialize the filter operator."""
        self.__value = value

    def eval(self, value: T) -> bool:
        """Evaluate the filter on the given value."""
        return value != self.__value

    def serialize(self) -> Any:
        """Serialize the filter value."""
        return self.__value


class FilterOperatorLessThan(FilterOperator[Tcomp]):
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

    def serialize(self) -> Any:
        """Serialize the filter value."""
        return self.__value


class FilterOperatorNotContains(FilterOperator[str]):
    """A not_contains filter."""

    __sg_op__ = "not_contains"

    def __init__(self, string: str) -> None:
        """Initialize the filter operator."""
        self.__string = string

    def eval(self, value: str) -> bool:
        """Evaluate the filter on the given value."""
        return self.__string not in value

    def serialize(self) -> Any:
        """Serialize the filter value."""
        return self.__string


class FilterOperatorNotIn(FilterOperator[T]):
    """A not_in filter."""

    __sg_op__ = "not_in"

    def __init__(self, container: list[T]) -> None:
        """Initialize the filter operator."""
        self.__container = container

    def eval(self, value: T) -> bool:
        """Evaluate the filter on the given value."""
        return value not in self.__container

    def serialize(self) -> Any:
        """Serialize the filter value."""
        return self.__container


class FilterOperatorNotInLast(FilterOperator[datetime.datetime]):
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

    def serialize(self) -> Any:
        """Serialize the filter value."""
        return [self.__offset, self.__date_type.value]


class FilterOperatorNotInNext(FilterOperator[datetime.datetime]):
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

    def serialize(self) -> Any:
        """Serialize the filter value."""
        return [self.__offset, self.__date_type.value]


class FilterOperatorStartsWith(FilterOperator[str]):
    """A endswith filter."""

    __sg_op__ = "start_with"

    def __init__(self, string: str) -> None:
        """Initialize the filter operator."""
        self.__string = string

    def eval(self, value: str) -> bool:
        """Evaluate the filter on the given value."""
        return value.startswith(self.__string)

    def serialize(self) -> Any:
        """Serialize the filter value."""
        return self.__string


class FilterOperatorTypeIs(FilterOperator[WithSgType]):
    """A type_is filter."""

    __sg_op__ = "type_is"

    def __init__(self, entity: WithSgType) -> None:
        """Initialize the filter operator."""
        self.__entity = entity

    def eval(self, value: WithSgType) -> bool:
        """Evaluate the filter on the given value."""
        return value.__sg_type__ == self.__entity.__sg_type__

    def serialize(self) -> Any:
        """Serialize the filter value."""
        return self.__entity.__sg_type__


class FilterOperatorTypeIsNot(FilterOperator[WithSgType]):
    """A type_is_not filter."""

    __sg_op__ = "type_is_not"

    def __init__(self, entity: WithSgType) -> None:
        """Initialize the filter operator."""
        self.__entity = entity

    def eval(self, value: WithSgType) -> bool:
        """Evaluate the filter on the given value."""
        return value.__sg_type__ != self.__entity.__sg_type__

    def serialize(self) -> Any:
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
        self, field: AbstractField[T], filter_operator: FilterOperator[Any]
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


class SummaryOperator(Generic[T, Tsumup], abc.ABC):
    """A Shotgrid operator."""

    __sg_op__: str

    @abc.abstractmethod
    def eval(self, value: list[T]) -> Tsumup:
        """Evaluate the filter on the given value."""


class RecordCountSummaryOperator(SummaryOperator[T, int]):
    """Return the number of count."""

    __sg_op__ = "record_count"

    def eval(self, value: list[T]) -> int:
        """Return the number of records in the given value."""
        return len(value)


class CountSummaryOperator(SummaryOperator[T, int]):
    """Return the number of rows."""

    __sg_op__ = "count"

    def eval(self, value: list[T]) -> int:
        """Return the number of elements."""
        return len([v for v in value if v is not None])


class SumSummaryOperator(SummaryOperator[float, float]):
    """Sum summary operator."""

    __sg_op__ = "sum"

    def eval(self, value: list[float]) -> float:
        """Return the sum of elements."""
        return sum(value)


class MaximumSummaryOperator(SummaryOperator[float, float]):
    """Maximum summary operator."""

    __sg_op__ = "maximum"

    def eval(self, value: list[float]) -> float:
        """Return the maximum value in the elements."""
        return max(value)


class MinimumSummaryOperator(SummaryOperator[float, float]):
    """Minimum summary operator."""

    __sg_op__ = "minimum"

    def eval(self, value: list[float]) -> float:
        """Return the minimum of the elements."""
        return min(value)


class AverageSummaryOperator(SummaryOperator[float, float]):
    """Sum summary operator."""

    __sg_op__ = "average"

    def eval(self, value: list[float]) -> float:
        """Return the sum of elements."""
        return statistics.mean(value)


class EarliestSummaryOperator(SummaryOperator[Tcomp, Tcomp]):
    """Earliest summary operator."""

    __sg_op__ = "earliest"

    def eval(self, value: list[Tcomp]) -> Tcomp:
        """Return the earliest value in the elements."""
        return min(value)


class LatestSummaryOperator(SummaryOperator[Tcomp, Tcomp]):
    """Earliest summary operator."""

    __sg_op__ = "latest"

    def eval(self, value: list[Tcomp]) -> Tcomp:
        """Return the earliest value in the elements."""
        return max(value)


class SummaryGroupOperator(Generic[T, Tsumup], abc.ABC):
    """A grouping operation."""

    __sg_op__: str

    @abc.abstractmethod
    def get_grouping_key(self, value: T) -> Tsumup:
        """Return the grouping key from the given value."""


class ExactGroupOperator(SummaryGroupOperator[T, T]):
    """An exact grouping operator."""

    __sg_op__ = "exact"

    def get_grouping_key(self, value: T) -> T:
        """Return the value itself."""
        return value


OptionalIntFloat = Union[int, float, None]


class TensGroupOperator(SummaryGroupOperator[OptionalIntFloat, OptionalIntFloat]):
    """Groups by tens."""

    __sg_op__ = "tens"

    def get_grouping_key(self, value: OptionalIntFloat) -> OptionalIntFloat:
        """Return the integer division by ten."""
        if value is None:
            return None
        return divmod(value, 10)[0] * 10


class HundredsGroupOperator(SummaryGroupOperator[OptionalIntFloat, OptionalIntFloat]):
    """Groups by hundreds."""

    __sg_op__ = "hundred"

    def get_grouping_key(self, value: OptionalIntFloat) -> OptionalIntFloat:
        """Return the integer division by hundred."""
        if value is None:
            return None
        return divmod(value, 100)[0] * 100


class ThousandsGroupOperator(SummaryGroupOperator[OptionalIntFloat, OptionalIntFloat]):
    """Groups by thousands."""

    __sg_op__ = "thousands"

    def get_grouping_key(self, value: OptionalIntFloat) -> OptionalIntFloat:
        """Return the integer division by a thousand."""
        if value is None:
            return None
        return divmod(value, 1000)[0] * 1000


class TensOfThousandsGroupOperator(
    SummaryGroupOperator[OptionalIntFloat, OptionalIntFloat]
):
    """Groups by tens of thousand."""

    __sg_op__ = "tensofthousands"

    def get_grouping_key(self, value: OptionalIntFloat) -> OptionalIntFloat:
        """Return the integer division by ten thousand."""
        if value is None:
            return None
        return divmod(value, 10000)[0] * 10000


class HundredsOfThousandsGroupOperator(
    SummaryGroupOperator[OptionalIntFloat, OptionalIntFloat]
):
    """Groups by hundreds of thousands."""

    __sg_op__ = "hundredsofthousands"

    def get_grouping_key(self, value: OptionalIntFloat) -> OptionalIntFloat:
        """Return the integer division by hundred thousand."""
        if value is None:
            return None
        return divmod(value, 100000)[0] * 100000


class MillionsGroupOperator(SummaryGroupOperator[OptionalIntFloat, OptionalIntFloat]):
    """Groups by millions."""

    __sg_op__ = "millions"

    def get_grouping_key(self, value: OptionalIntFloat) -> OptionalIntFloat:
        """Return the integer division by one million."""
        if value is None:
            return None
        return divmod(value, 1000000)[0] * 1000000


Date = Union[datetime.datetime, datetime.date]


class DayGroupOperator(SummaryGroupOperator[Date, datetime.date]):
    """Groups by days."""

    __sg_op__ = "day"

    def get_grouping_key(self, value: Date) -> datetime.date:
        """Return the day of the value."""
        return datetime.date(year=value.year, month=value.month, day=value.day)


class WeekGroupOperator(SummaryGroupOperator[Date, datetime.date]):
    """Groups by months."""

    __sg_op__ = "week"

    def get_grouping_key(self, value: Date) -> datetime.date:
        """Return the week of the value."""
        week = value - datetime.timedelta(days=value.weekday())
        return datetime.date(year=week.year, month=week.month, day=week.day)


class MonthGroupOperator(SummaryGroupOperator[Date, datetime.date]):
    """Groups by months."""

    __sg_op__ = "month"

    def get_grouping_key(self, value: Date) -> datetime.date:
        """Return the month of the value."""
        return datetime.date(year=value.year, month=value.month, day=1)


class QuarterGroupOperator(SummaryGroupOperator[Date, datetime.date]):
    """Groups by quarters."""

    __sg_op__ = "quarter"

    def get_grouping_key(self, value: Date) -> datetime.date:
        """Return the quarter of the value."""
        quarter = max((value.month - 1) // 3, 1)
        return datetime.date(year=value.year, month=quarter, day=1)


class YearGroupOperator(SummaryGroupOperator[Date, datetime.date]):
    """Groups by months."""

    __sg_op__ = "year"

    def get_grouping_key(self, value: Date) -> datetime.date:
        """Return the month of the value."""
        return datetime.date(year=value.year, month=1, day=1)


class FirstLetterGroupOperator(SummaryGroupOperator[str, str]):
    """Groups by entity types."""

    __sg_op__ = "firstletter"

    def get_grouping_key(self, value: str) -> str:
        """Return the entity type of the value."""
        if not value:
            return ""
        return value[0]


class SgSummaryField(SgSerializable, Generic[T, Tsumup]):
    """A summary for a given field."""

    def __init__(
        self, field: AbstractField[T], summary_op: SummaryOperator[T, Tsumup]
    ) -> None:
        """Initialize the summary field."""
        self.field = field
        self.op = summary_op

    def sum_up(self, entities: list[SgBaseEntity]) -> Tsumup:
        """Summarize the given list of entities."""
        values = [entity.get_value(self.field) for entity in entities]
        return self.op.eval(values)


class SgGroupingField(SgSerializable, Generic[T, Tsumup]):
    """A grouping field."""

    def __init__(
        self, field: AbstractField[T], grouping_op: SummaryGroupOperator[T, Tsumup]
    ) -> None:
        """Initialize the grouping field."""
        self.field = field
        self.op = grouping_op

    def get_group_key(self, entity: SgBaseEntity) -> Tsumup:
        """Return the grouping key for the given entity."""
        value = entity.get_value(self.field)
        return self.op.get_grouping_key(value)
