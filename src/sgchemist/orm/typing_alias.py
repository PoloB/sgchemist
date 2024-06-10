"""Defines multiple typing alias used across sgchemist."""

from __future__ import annotations

from typing import Any
from typing import Tuple
from typing import Union

from sgchemist.orm.constant import GroupingType
from sgchemist.orm.constant import Order
from sgchemist.orm.instrumentation import InstrumentedAttribute

EntityHash = Tuple[str, int]
OrderField = Tuple[InstrumentedAttribute[Any], Order]
GroupingField = Tuple[InstrumentedAttribute[Any], GroupingType, Union[Order, str]]

