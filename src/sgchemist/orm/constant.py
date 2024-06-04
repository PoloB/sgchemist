"""Constants for querying Shotgrid."""

from __future__ import annotations

from enum import Enum


class Operator(str, Enum):
    """Available operators for field filters."""

    BETWEEN = "between"
    CONTAINS = "contains"
    ENDS_WITH = "end_with"
    GREATER_THAN = "greater_than"
    IN = "in"
    IN_CALENDAR_DAY = "in_calendary_day"
    IN_CALENDAR_MONTH = "in_calendary_month"
    IN_CALENDAR_WEEK = "in_calendary_week"
    IN_CALENDAR_YEAR = "in_calendary_year"
    IN_LAST = "in_last"
    IN_NEXT = "in_next"
    IS = "is"
    IS_NOT = "is_not"
    LESS_THAN = "less_than"
    NAME_CONTAINS = "name_contains"
    NAME_ID = "name_id"
    NAME_IS = "name_is"
    NAME_NOT_CONTAINS = "name_not_contains"
    NOT_BETWEEN = "not_between"
    NOT_CONTAINS = "not_contains"
    NOT_IN = "not_in"
    NOT_IN_LAST = "not_in_last"
    NOT_IN_NEXT = "not_in_next"
    STARTS_WITH = "start_with"
    TYPE_IS = "type_is"
    TYPE_IS_NOT = "type_is_not"


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
