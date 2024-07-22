"""Constants for querying Shotgrid."""

from __future__ import annotations

from enum import Enum


class DateType(str, Enum):
    """Available date types."""

    HOUR = "HOUR"
    DAY = "DAY"
    WEEK = "WEEK"
    MONTH = "MONTH"
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


class GroupingType(str, Enum):
    """Available grouping types."""

    EXACT = "exact"
    TENS = "tens"
    HUNDREDS = "hundreds"
    THOUSANDS = "thousands"
    TENS_OF_THOUSANDS = "tensofthousands"
    HUNDRED_OF_THOUSANDS = "hundredsofthousands"
    MILLIONS = "millions"
    DAY = "day"
    MONTH = "month"
    QUARTER = "quarter"
    YEAR = "year"
    CLUSTERED_DATE = "clustered_date"
    ONE_DAY = "oneday"
    FIVE_DAYS = "fivedays"
    ENTITY_TYPE = "entitytype"
    FIRST_LETTER = "firstletter"
