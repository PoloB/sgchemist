"""Defines multiple typing alias used across sgchemist."""

from __future__ import absolute_import
from __future__ import annotations

from typing import Any
from typing import Tuple
from typing import Union

from .constant import GroupingType
from .constant import Order
from .fields import AbstractField

EntityHash = Tuple[str, int]
OrderField = Tuple[AbstractField[Any], Order]
GroupingField = Tuple[AbstractField[Any], GroupingType, Union[Order, str]]
