"""Defines operators for building queries."""

from __future__ import annotations

import abc
from typing import Any
from typing import List
from typing import TYPE_CHECKING
from typing import TypeVar

from sgchemist.orm.constant import LogicalOperator
from sgchemist.orm.constant import Operator

if TYPE_CHECKING:
    from sgchemist.orm.instrumentation import InstrumentedAttribute

T = TypeVar("T")


class SgFilterObject(object):
    """Defines a generic query object to operate on."""

    __metaclass__ = abc.ABCMeta

    @abc.abstractmethod
    def __and__(self, other: SgFilterObject) -> SgFilterObject:
        """Combines this object with another with a and operation.

        Args:
            other (Self): object to combine.

        Returns:
            SgFilterObject: combined object.
        """

    @abc.abstractmethod
    def __or__(self, other: SgFilterObject) -> SgFilterObject:
        """Combines this object with another with a or operation.

        Args:
            other (Self): object to combine.

        Returns:
            SgFilterObject: combined object.
        """


class SgNullCondition(SgFilterObject):
    """Defines a null condition."""

    def __and__(self, other: SgFilterObject) -> SgFilterObject:
        """Returns the other object as null condition has no effect.

        Args:
            other (SgFilterObject): object to combine.

        Returns:
            SgFilterObject: combined object.
        """
        return other

    def __or__(self, other: SgFilterObject) -> SgFilterObject:
        """Returns the other object as null condition has no effect.

        Args:
            other (SgFilterObject): object to combine.

        Returns:
            SgFilterObject: combined object.
        """
        return other


class SgFilterOperation(SgFilterObject):
    """Defines a filter operation between different SgFilterObjects."""

    def __init__(self, operator: LogicalOperator, sg_objects: List[SgFilterObject]):
        """Initialize the filter operation.

        Args:
            operator (LogicalOperator): operator to use.
            sg_objects (list[SgFilterObject]): list of filter objects.
        """
        self.operator = operator
        self.sg_objects = sg_objects

    def _op(
        self, operator: LogicalOperator, other: SgFilterObject
    ) -> SgFilterOperation:
        """Returns a new filter operation combining this operation with another object.

        Args:
            operator (LogicalOperator): operator to use.
            other (SgFilterObject): object to combine.

        Returns:
            Self: combined object.
        """
        objects: List[SgFilterObject] = [self, other]

        # Concatenate filters if possible to decrease nesting
        if isinstance(other, SgFilterOperation):
            if other.operator == self.operator == operator:
                objects = self.sg_objects + other.sg_objects
        elif self.operator == operator:
            objects = self.sg_objects + [other]

        return self.__class__(operator, objects)

    def __and__(self, other: SgFilterObject) -> SgFilterOperation:
        """Combines this operation with another object with a and operator.

        Args:
            other (SgFilterObject): object to combine.

        Returns:
            SgFilterOperation: combined object.
        """
        return self._op(LogicalOperator.ALL, other)

    def __or__(self, other: SgFilterObject) -> SgFilterOperation:
        """Combines this operation with another object with a or operator.

        Args:
            other (SgFilterObject): object to combine.

        Returns:
            SgFilterOperation: combined object.
        """
        return self._op(LogicalOperator.ANY, other)


class SgFieldCondition(SgFilterObject):
    """Defines a field condition."""

    def __init__(
        self,
        field: InstrumentedAttribute[T],
        operator: Operator,
        right: Any,
    ) -> None:
        """Initialize the field condition.

        Args:
            field (InstrumentedAttribute[T]): field attribute to create the condition on
            operator (Operator): operator to use.
            right (Any): value to compare the field against.
        """
        self.field = field
        self.operator = operator
        self.right = right

    def __and__(self, other: SgFilterObject) -> SgFilterOperation:
        """Combines this operation with another object with a and operator.

        Returns:
            SgFilterOperation: combined object.
        """
        return SgFilterOperation(LogicalOperator.ALL, [self, other])

    def __or__(self, other: SgFilterObject) -> SgFilterOperation:
        """Combines this operation with another object with a or operator.

        Returns:
            SgFilterOperation: combined object.
        """
        return SgFilterOperation(LogicalOperator.ANY, [self, other])
