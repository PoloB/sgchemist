"""Defines multiple typing alias used across sgchemist."""

from __future__ import absolute_import
from __future__ import annotations

from typing import Any
from typing import Optional
from typing import Protocol
from typing import Tuple
from typing import Union

from .constant import GroupingType
from .constant import Order
from .fields import AbstractField

EntityHash = Tuple[str, int]
OrderField = Tuple[AbstractField[Any], Order]
GroupingField = Tuple[AbstractField[Any], GroupingType, Union[Order, str]]


class Comparable(Protocol):
    """Protocol for annotating comparable types."""

    def __lt__(self, other: Any) -> bool:
        """Return the comparison of two elements."""

    def __le__(self, other: Any) -> bool:
        """Return the comparison of two elements."""


OptionalCompare = Optional[Comparable]
