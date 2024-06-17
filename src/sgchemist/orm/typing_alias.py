"""Defines multiple typing alias used across sgchemist."""

from __future__ import annotations

from typing import Any
from typing import Tuple
from typing import Union

from .constant import GroupingType
from .constant import Order
from .instrumentation import InstrumentedAttribute

EntityHash = Tuple[str, int]
OrderField = Tuple[InstrumentedAttribute[Any], Order]
GroupingField = Tuple[InstrumentedAttribute[Any], GroupingType, Union[Order, str]]
