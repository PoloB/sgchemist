"""Defines multiple typing alias used across sgchemist."""

from __future__ import absolute_import
from __future__ import annotations

from typing import Any
from typing import ForwardRef
from typing import Tuple
from typing import Type
from typing import Union

from typing_extensions import NewType
from typing_extensions import TypeAliasType

from .constant import GroupingType
from .constant import Order
from .fields import AbstractField

EntityHash = Tuple[str, int]
OrderField = Tuple[AbstractField[Any], Order]
GroupingField = Tuple[AbstractField[Any], GroupingType, Union[Order, str]]
AnnotationScanType = Union[Type[Any], str, ForwardRef, NewType, TypeAliasType]
