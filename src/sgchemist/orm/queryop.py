"""Defines operators for building queries."""

from __future__ import annotations

import abc
from typing import TYPE_CHECKING
from typing import Any
from typing import TypeVar

from typing_extensions import Self

from .constant import LogicalOperator
from .constant import Operator

if TYPE_CHECKING:
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
        self.operator = operator
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
