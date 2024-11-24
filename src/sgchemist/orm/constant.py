"""Constants for querying Shotgrid."""

from __future__ import annotations

from enum import Enum


class DateType(str, Enum):
    """Available date types."""

    HOUR = "HOUR"
    DAY = "DAY"
    WEEK = "WEEK"
    YEAR = "YEAR"


class LogicalOperator(str, Enum):
    """Available logical operators."""

    ANY = "any"
    ALL = "all"


class Order(str, Enum):
    """Available orders."""

    ASC = "asc"
    DESC = "desc"


class BatchRequestType(str, Enum):
    """Available batch request types."""

    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
