"""Defines operators for building queries."""

from __future__ import annotations

import abc
import datetime
import operator
from typing import TYPE_CHECKING
from typing import Any
from typing import TypeVar

from typing_extensions import Self

from .constant import DateType
from .constant import LogicalOperator
from .constant import Operator

if TYPE_CHECKING:
    from . import SgBaseEntity
    from .fields import AbstractField

T = TypeVar("T")


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
        self,
        field: AbstractField[T],
        operator: Operator,
        right: Any,
    ) -> None:
        """Initialize the field condition.

        Args:
            field: field attribute to create the condition on
            operator: operator to use.
            right: value to compare the field against.
        """
        self.field = field
        self.op = operator
        self.right = right

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

        if self.op == Operator.BETWEEN:
            return self.right[0] <= value <= self.right[1]

        elif self.op == Operator.CONTAINS:
            return self.right in value

        elif self.op == Operator.ENDS_WITH:
            return value.endswith(self.right)

        elif self.op == Operator.GREATER_THAN:
            return value > self.right

        elif self.op == Operator.IN:
            return value in self.right

        elif self.op == Operator.IN_CALENDAR_DAY:
            op = operator.le if self.right >= 0 else operator.gt
            today = datetime.datetime.now(value.tzinfo)
            return op(today, value) and op(
                value, today + datetime.timedelta(days=self.right)
            )

        elif self.op == Operator.IN_CALENDAR_MONTH:
            # There are not always the same number of days between two months
            op = operator.le if self.right >= 0 else operator.gt
            today = datetime.datetime.now(value.tzinfo)
            year_offset, month = divmod(today.month + self.right, 12)
            calendar_month = today.replace(year=today.year + year_offset, month=month)
            return op(today, value) and op(value, calendar_month)

        elif self.op == Operator.IN_CALENDAR_WEEK:
            op = operator.le if self.right >= 0 else operator.gt
            today = datetime.datetime.now(value.tzinfo)
            return op(today, value) and op(
                value, today + datetime.timedelta(weeks=self.right)
            )

        elif self.op == Operator.IN_CALENDAR_YEAR:
            # There are not always the same number of days between two years
            op = operator.le if self.right >= 0 else operator.gt
            today = datetime.datetime.now(value.tzinfo)
            calendar_year = today.replace(year=today.year + self.right)
            return op(today, value) and op(value, calendar_year)

        elif self.op == Operator.IN_LAST:
            date_type = self.right[1]
            today = datetime.datetime.now(value.tzinfo)
            if date_type == DateType.YEAR:
                compare = today.replace(year=today.year - self.right[0])
            elif date_type == DateType.MONTH:
                year_offset, month = divmod(today.month - self.right[0], 12)
                compare = today.replace(year=today.year + year_offset, month=month)
            else:
                time_value = {f"{self.right[1].value.lower()}s": self.right[0]}
                compare = today - datetime.timedelta(**time_value)
            return today > value > compare

        elif self.op == Operator.IN_NEXT:
            date_type = self.right[1]
            today = datetime.datetime.now(value.tzinfo)
            if date_type == DateType.YEAR:
                compare = today.replace(year=today.year + self.right[0])
            elif date_type == DateType.MONTH:
                year_offset, month = divmod(today.month + self.right[0], 12)
                compare = today.replace(year=today.year + year_offset, month=month)
            else:
                time_value = {f"{self.right[1].value.lower()}s": self.right[0]}
                compare = today + datetime.timedelta(**time_value)
            return today < value < compare

        elif self.op == Operator.IS:
            return value == self.right

        elif self.op == Operator.IS_NOT:
            return value != self.right

        elif self.op == Operator.LESS_THAN:
            return value < self.right

        elif self.op == Operator.NOT_CONTAINS:
            return self.right not in value

        elif self.op == Operator.NOT_IN:
            return value not in self.right

        elif self.op == Operator.NOT_IN_LAST:
            date_type = self.right[1]
            today = datetime.datetime.now(value.tzinfo)
            if date_type == DateType.YEAR:
                compare = today.replace(year=today.year - self.right[0])
            elif date_type == DateType.MONTH:
                year_offset, month = divmod(today.month - self.right[0], 12)
                compare = today.replace(year=today.year + year_offset, month=month)
            else:
                time_value = {f"{self.right[1].value.lower()}s": self.right[0]}
                compare = today - datetime.timedelta(**time_value)
            return today < value or value < compare

        elif self.op == Operator.NOT_IN_NEXT:
            date_type = self.right[1]
            today = datetime.datetime.now(value.tzinfo)
            if date_type == DateType.YEAR:
                compare = today.replace(year=today.year + self.right[0])
            elif date_type == DateType.MONTH:
                year_offset, month = divmod(today.month + self.right[0], 12)
                compare = today.replace(year=today.year + year_offset, month=month)
            else:
                time_value = {f"{self.right[1].value.lower()}s": self.right[0]}
                compare = today + datetime.timedelta(**time_value)
            return today > value or value > compare

        elif self.op == Operator.STARTS_WITH:
            return value.startswith(self.right)

        elif self.op == Operator.TYPE_IS:
            return value.__sg_type__ == self.right

        elif self.op == Operator.TYPE_IS_NOT:
            return value.__sg_type__ != self.right
