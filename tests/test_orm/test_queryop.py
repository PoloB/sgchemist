"""Tests query operators."""

from __future__ import annotations

import datetime
from typing import Any

import pytest
from classes import Project

from sgchemist.orm import DateField
from sgchemist.orm import EntityField
from sgchemist.orm.constant import DateType
from sgchemist.orm.constant import LogicalOperator
from sgchemist.orm.entity import SgBaseEntity
from sgchemist.orm.fields import AbstractValueField
from sgchemist.orm.fields import TextField
from sgchemist.orm.queryop import FilterOperator
from sgchemist.orm.queryop import FilterOperatorBetween
from sgchemist.orm.queryop import FilterOperatorContains
from sgchemist.orm.queryop import FilterOperatorEndsWith
from sgchemist.orm.queryop import FilterOperatorGreaterThan
from sgchemist.orm.queryop import FilterOperatorIn
from sgchemist.orm.queryop import FilterOperatorInCalendarDay
from sgchemist.orm.queryop import FilterOperatorInCalendarMonth
from sgchemist.orm.queryop import FilterOperatorInCalendarWeek
from sgchemist.orm.queryop import FilterOperatorInCalendarYear
from sgchemist.orm.queryop import FilterOperatorInLast
from sgchemist.orm.queryop import FilterOperatorInNext
from sgchemist.orm.queryop import FilterOperatorIs
from sgchemist.orm.queryop import FilterOperatorIsNot
from sgchemist.orm.queryop import FilterOperatorLessThan
from sgchemist.orm.queryop import FilterOperatorNotContains
from sgchemist.orm.queryop import FilterOperatorNotIn
from sgchemist.orm.queryop import FilterOperatorNotInLast
from sgchemist.orm.queryop import FilterOperatorNotInNext
from sgchemist.orm.queryop import FilterOperatorStartsWith
from sgchemist.orm.queryop import FilterOperatorTypeIs
from sgchemist.orm.queryop import FilterOperatorTypeIsNot
from sgchemist.orm.queryop import SgFieldCondition
from sgchemist.orm.queryop import SgFilterOperation
from sgchemist.orm.queryop import SgNullCondition


@pytest.fixture
def field() -> AbstractValueField[Any]:
    """Returns the test field."""

    class SgEntity(SgBaseEntity):
        pass

    class _TestModel(SgEntity):
        __sg_type__ = "test"
        test: TextField

    return _TestModel.test


def test_field_condition(field: AbstractValueField[Any]) -> None:
    """Tests field condition."""
    cond1 = SgFieldCondition(field, FilterOperatorIs("foo"))
    cond2 = SgFieldCondition(field, FilterOperatorIs("name"))
    and_cond = cond1 & cond2
    assert isinstance(and_cond, SgFilterOperation)
    assert and_cond.operator is LogicalOperator.ALL
    assert and_cond.sg_objects == [cond1, cond2]
    or_cond = cond1 | cond2
    assert isinstance(or_cond, SgFilterOperation)
    assert or_cond.operator is LogicalOperator.ANY
    assert or_cond.sg_objects == [cond1, cond2]


def test_filter_operator(field: AbstractValueField[Any]) -> None:
    """Tests filter operator."""
    cond1 = SgFieldCondition(field, FilterOperatorIs("foo"))
    cond2 = SgFieldCondition(field, FilterOperatorIs("name"))
    and_cond = cond1 & cond2
    or_cond = cond1 | cond2
    and_log = and_cond & or_cond
    assert isinstance(and_log, SgFilterOperation)
    assert and_log.operator is LogicalOperator.ALL
    assert and_log.sg_objects == [and_cond, or_cond]
    or_log = and_cond | or_cond
    assert isinstance(or_log, SgFilterOperation)
    assert or_log.operator is LogicalOperator.ANY
    assert or_log.sg_objects == [and_cond, or_cond]
    # Test simple concatenation
    and_concat = and_cond & cond1
    assert isinstance(and_concat, SgFilterOperation)
    assert and_concat.operator is LogicalOperator.ALL
    assert and_concat.sg_objects == [cond1, cond2, cond1]
    or_concat = or_cond | cond1
    assert isinstance(or_concat, SgFilterOperation)
    assert or_concat.operator is LogicalOperator.ANY
    assert or_concat.sg_objects == [cond1, cond2, cond1]
    # Test concat between two logical operators
    and_concat_and = and_cond & and_cond
    assert isinstance(and_concat_and, SgFilterOperation)
    assert and_concat_and.operator is LogicalOperator.ALL
    assert and_concat_and.sg_objects == [cond1, cond2, cond1, cond2]
    or_concat_or = or_cond | or_cond
    assert isinstance(or_concat_or, SgFilterOperation)
    assert or_concat_or.operator is LogicalOperator.ANY
    assert or_concat_or.sg_objects == [cond1, cond2, cond1, cond2]


def test_null_condition(field: AbstractValueField[Any]) -> None:
    """Tests null condition."""
    null_cond = SgNullCondition()
    self_null = null_cond & SgNullCondition()
    assert isinstance(self_null, SgNullCondition)
    self_null = null_cond | SgNullCondition()
    assert isinstance(self_null, SgNullCondition)
    cond1 = SgFieldCondition(field, FilterOperatorIs("foo"))
    cond_null = null_cond & cond1
    assert cond_null is cond1
    cond_null = null_cond | cond1
    assert cond_null is cond1


def test_field_condition_matches() -> None:
    """Test the field condition matches method."""

    class SgEntity(SgBaseEntity):
        pass

    class RefEntity(SgEntity):
        __sg_type__ = "ref"

    class TestEntity(SgEntity):
        __sg_type__ = "test"
        name: TextField
        date: DateField
        entity: EntityField[TestEntity | RefEntity]

    # BETWEEN
    cond = TestEntity.id.between(0, 10)
    assert cond.matches(TestEntity(id=0))
    assert cond.matches(TestEntity(id=10))
    assert cond.matches(TestEntity(id=5))
    assert not cond.matches(TestEntity(id=-1))
    assert not cond.matches(TestEntity(id=11))
    assert not cond.matches(TestEntity())

    # CONTAINS
    cond = TestEntity.name.contains("foo")
    assert cond.matches(TestEntity(name="foo"))
    assert cond.matches(TestEntity(name="foobar"))
    assert cond.matches(TestEntity(name="barfoo"))
    assert not cond.matches(TestEntity(name="barfo"))

    # ENDS_WITH
    cond = TestEntity.name.endswith("foo")
    assert cond.matches(TestEntity(name="foo"))
    assert cond.matches(TestEntity(name="barfoo"))
    assert not cond.matches(TestEntity(name="foobar"))
    assert not cond.matches(TestEntity(name="barfo"))

    # GREATER_THAN
    cond = TestEntity.id.gt(5)
    assert cond.matches(TestEntity(id=6))
    assert not cond.matches(TestEntity(id=5))
    assert not cond.matches(TestEntity(id=0))

    # IN
    cond = TestEntity.id.is_in([1, 4])
    assert cond.matches(TestEntity(id=1))
    assert cond.matches(TestEntity(id=4))
    assert not cond.matches(TestEntity(id=0))
    assert not cond.matches(TestEntity(id=3))

    now = datetime.datetime.now(datetime.timezone.utc)

    # IN_CALENDAR_DAY
    cond = TestEntity.date.in_calendar_day(1)
    assert cond.matches(TestEntity(date=now + datetime.timedelta(days=1)))
    assert not cond.matches(TestEntity(date=now + datetime.timedelta(days=2)))
    assert not cond.matches(TestEntity(date=now - datetime.timedelta(days=1)))
    assert not cond.matches(TestEntity(date=now))  # here now is always before the call
    cond = TestEntity.date.in_calendar_day(-1)
    assert not cond.matches(TestEntity(date=now - datetime.timedelta(days=2)))
    assert not cond.matches(TestEntity(date=now + datetime.timedelta(days=1)))
    assert cond.matches(TestEntity(date=now))

    # IN_CALENDAR_MONTH
    cond = TestEntity.date.in_calendar_month(1)
    year_offset, month = divmod(now.month + 1, 12)
    assert cond.matches(
        TestEntity(date=now.replace(year=now.year + year_offset, month=month))
    )
    year_offset, month = divmod(now.month + 2, 12)
    assert not cond.matches(
        TestEntity(date=now.replace(year=now.year + year_offset, month=month))
    )
    year_offset, month = divmod(now.month - 1, 12)
    assert not cond.matches(
        TestEntity(date=now.replace(year=now.year + year_offset, month=month))
    )
    assert not cond.matches(TestEntity(date=now))
    cond = TestEntity.date.in_calendar_month(-1)
    year_offset, month = divmod(now.month - 2, 12)
    assert not cond.matches(
        TestEntity(date=now.replace(year=now.year + year_offset, month=month))
    )
    year_offset, month = divmod(now.month + 1, 12)
    assert not cond.matches(
        TestEntity(date=now.replace(year=now.year + year_offset, month=month))
    )
    assert cond.matches(TestEntity(date=now))

    # IN_CALENDAR_WEEK
    cond = TestEntity.date.in_calendar_week(1)
    assert cond.matches(TestEntity(date=now + datetime.timedelta(weeks=1)))
    assert not cond.matches(TestEntity(date=now + datetime.timedelta(weeks=2)))
    assert not cond.matches(TestEntity(date=now - datetime.timedelta(weeks=1)))
    assert not cond.matches(TestEntity(date=now))  # here now is always before the call
    cond = TestEntity.date.in_calendar_week(-1)
    assert not cond.matches(TestEntity(date=now - datetime.timedelta(weeks=2)))
    assert not cond.matches(TestEntity(date=now + datetime.timedelta(weeks=1)))
    assert cond.matches(TestEntity(date=now))

    # IN_CALENDAR_YEAR
    cond = TestEntity.date.in_calendar_year(1)
    assert cond.matches(TestEntity(date=now.replace(year=now.year + 1)))
    assert not cond.matches(TestEntity(date=now.replace(year=now.year + 2)))
    assert not cond.matches(TestEntity(date=now.replace(year=now.year - 1)))
    assert not cond.matches(TestEntity(date=now))
    cond = TestEntity.date.in_calendar_year(-1)
    assert not cond.matches(TestEntity(date=now.replace(year=now.year - 2)))
    assert not cond.matches(TestEntity(date=now.replace(year=now.year + 1)))
    assert cond.matches(TestEntity(date=now))

    # IN_LAST
    cond = TestEntity.date.in_last(2, DateType.DAY)
    assert cond.matches(TestEntity(date=now - datetime.timedelta(days=1)))
    assert not cond.matches(TestEntity(date=now - datetime.timedelta(days=3)))
    assert not cond.matches(TestEntity(date=now + datetime.timedelta(days=1)))
    assert cond.matches(TestEntity(date=now))
    cond = TestEntity.date.in_last(2, DateType.WEEK)
    assert cond.matches(TestEntity(date=now - datetime.timedelta(weeks=1)))
    assert not cond.matches(TestEntity(date=now - datetime.timedelta(weeks=3)))
    assert not cond.matches(TestEntity(date=now + datetime.timedelta(weeks=1)))
    assert cond.matches(TestEntity(date=now))
    cond = TestEntity.date.in_last(2, DateType.MONTH)
    year_offset, month = divmod(now.month - 1, 12)
    assert cond.matches(
        TestEntity(date=now.replace(year=now.year + year_offset, month=month))
    )
    year_offset, month = divmod(now.month - 3, 12)
    assert not cond.matches(
        TestEntity(date=now.replace(year=now.year + year_offset, month=month))
    )
    year_offset, month = divmod(now.month + 1, 12)
    assert not cond.matches(
        TestEntity(date=now.replace(year=now.year + year_offset, month=month))
    )
    assert cond.matches(TestEntity(date=now))
    cond = TestEntity.date.in_last(2, DateType.YEAR)
    assert cond.matches(TestEntity(date=now.replace(year=now.year - 1)))
    assert not cond.matches(TestEntity(date=now.replace(year=now.year - 3)))
    assert not cond.matches(TestEntity(date=now.replace(year=now.year + 1)))
    assert cond.matches(TestEntity(date=now))

    # IN_NEXT
    cond = TestEntity.date.in_next(2, DateType.DAY)
    assert cond.matches(TestEntity(date=now + datetime.timedelta(days=1)))
    assert not cond.matches(TestEntity(date=now + datetime.timedelta(days=3)))
    assert not cond.matches(TestEntity(date=now - datetime.timedelta(days=1)))
    assert not cond.matches(TestEntity(date=now))
    cond = TestEntity.date.in_next(2, DateType.WEEK)
    assert cond.matches(TestEntity(date=now + datetime.timedelta(weeks=1)))
    assert not cond.matches(TestEntity(date=now + datetime.timedelta(weeks=3)))
    assert not cond.matches(TestEntity(date=now - datetime.timedelta(weeks=1)))
    assert not cond.matches(TestEntity(date=now))
    cond = TestEntity.date.in_next(2, DateType.MONTH)
    year_offset, month = divmod(now.month + 1, 12)
    assert cond.matches(
        TestEntity(date=now.replace(year=now.year + year_offset, month=month))
    )
    year_offset, month = divmod(now.month + 3, 12)
    assert not cond.matches(
        TestEntity(date=now.replace(year=now.year + year_offset, month=month))
    )
    year_offset, month = divmod(now.month - 1, 12)
    assert not cond.matches(
        TestEntity(date=now.replace(year=now.year + year_offset, month=month))
    )
    assert not cond.matches(TestEntity(date=now))
    cond = TestEntity.date.in_next(2, DateType.YEAR)
    assert cond.matches(TestEntity(date=now.replace(year=now.year + 1)))
    assert not cond.matches(TestEntity(date=now.replace(year=now.year + 3)))
    assert not cond.matches(TestEntity(date=now.replace(year=now.year - 1)))
    assert not cond.matches(TestEntity(date=now))

    # IS
    cond = TestEntity.id.eq(0)
    assert cond.matches(TestEntity(id=0))
    assert not cond.matches(TestEntity(id=1))

    # IS_NOT
    cond = TestEntity.id.neq(0)
    assert not cond.matches(TestEntity(id=0))
    assert cond.matches(TestEntity(id=1))

    # LESS_THAN
    cond = TestEntity.id.lt(5)
    assert not cond.matches(TestEntity(id=6))
    assert not cond.matches(TestEntity(id=5))
    assert cond.matches(TestEntity(id=0))

    # NOT_CONTAINS
    cond = TestEntity.name.not_contains("foo")
    assert not cond.matches(TestEntity(name="foo"))
    assert not cond.matches(TestEntity(name="foobar"))
    assert not cond.matches(TestEntity(name="barfoo"))
    assert cond.matches(TestEntity(name="barfo"))

    # NOT_IN
    cond = TestEntity.id.is_not_in([1, 4])
    assert not cond.matches(TestEntity(id=1))
    assert not cond.matches(TestEntity(id=4))
    assert cond.matches(TestEntity(id=0))
    assert cond.matches(TestEntity(id=3))

    # NOT_IN_LAST
    cond = TestEntity.date.not_in_last(2, DateType.DAY)
    assert not cond.matches(TestEntity(date=now - datetime.timedelta(days=1)))
    assert cond.matches(TestEntity(date=now - datetime.timedelta(days=3)))
    assert cond.matches(TestEntity(date=now + datetime.timedelta(days=1)))
    assert not cond.matches(TestEntity(date=now))
    cond = TestEntity.date.not_in_last(2, DateType.WEEK)
    assert not cond.matches(TestEntity(date=now - datetime.timedelta(weeks=1)))
    assert cond.matches(TestEntity(date=now - datetime.timedelta(weeks=3)))
    assert cond.matches(TestEntity(date=now + datetime.timedelta(weeks=1)))
    assert not cond.matches(TestEntity(date=now))
    cond = TestEntity.date.not_in_last(2, DateType.MONTH)
    year_offset, month = divmod(now.month - 1, 12)
    assert not cond.matches(
        TestEntity(date=now.replace(year=now.year + year_offset, month=month))
    )
    year_offset, month = divmod(now.month - 3, 12)
    assert cond.matches(
        TestEntity(date=now.replace(year=now.year + year_offset, month=month))
    )
    year_offset, month = divmod(now.month + 1, 12)
    assert cond.matches(
        TestEntity(date=now.replace(year=now.year + year_offset, month=month))
    )
    assert not cond.matches(TestEntity(date=now))
    cond = TestEntity.date.not_in_last(2, DateType.YEAR)
    assert not cond.matches(TestEntity(date=now.replace(year=now.year - 1)))
    assert cond.matches(TestEntity(date=now.replace(year=now.year - 3)))
    assert cond.matches(TestEntity(date=now.replace(year=now.year + 1)))
    assert not cond.matches(TestEntity(date=now))

    # NOT_IN_NEXT
    cond = TestEntity.date.not_in_next(2, DateType.DAY)
    assert not cond.matches(TestEntity(date=now + datetime.timedelta(days=1)))
    assert cond.matches(TestEntity(date=now + datetime.timedelta(days=3)))
    assert cond.matches(TestEntity(date=now - datetime.timedelta(days=1)))
    assert cond.matches(TestEntity(date=now))
    cond = TestEntity.date.not_in_next(2, DateType.WEEK)
    assert not cond.matches(TestEntity(date=now + datetime.timedelta(weeks=1)))
    assert cond.matches(TestEntity(date=now + datetime.timedelta(weeks=3)))
    assert cond.matches(TestEntity(date=now - datetime.timedelta(weeks=1)))
    assert cond.matches(TestEntity(date=now))
    cond = TestEntity.date.not_in_next(2, DateType.MONTH)
    year_offset, month = divmod(now.month + 1, 12)
    assert not cond.matches(
        TestEntity(date=now.replace(year=now.year + year_offset, month=month))
    )
    year_offset, month = divmod(now.month + 3, 12)
    assert cond.matches(
        TestEntity(date=now.replace(year=now.year + year_offset, month=month))
    )
    year_offset, month = divmod(now.month - 1, 12)
    assert cond.matches(
        TestEntity(date=now.replace(year=now.year + year_offset, month=month))
    )
    assert cond.matches(TestEntity(date=now))
    cond = TestEntity.date.not_in_next(2, DateType.YEAR)
    assert not cond.matches(TestEntity(date=now.replace(year=now.year + 1)))
    assert cond.matches(TestEntity(date=now.replace(year=now.year + 3)))
    assert cond.matches(TestEntity(date=now.replace(year=now.year - 1)))
    assert cond.matches(TestEntity(date=now))

    # STARTS_WITH
    cond = TestEntity.name.startswith("foo")
    assert cond.matches(TestEntity(name="foo"))
    assert not cond.matches(TestEntity(name="barfoo"))
    assert cond.matches(TestEntity(name="foobar"))
    assert not cond.matches(TestEntity(name="barfo"))

    # TYPE_IS
    cond = TestEntity.entity.type_is(RefEntity)
    assert not cond.matches(TestEntity(entity=TestEntity()))
    assert cond.matches(TestEntity(entity=RefEntity()))

    # TYPE_IS_NOT
    cond = TestEntity.entity.type_is_not(RefEntity)
    assert cond.matches(TestEntity(entity=TestEntity()))
    assert not cond.matches(TestEntity(entity=RefEntity()))


@pytest.mark.parametrize(
    "operator, expected_value",
    [
        (FilterOperatorBetween(0, 2), [0, 2]),
        (FilterOperatorContains("foo"), "foo"),
        (FilterOperatorEndsWith("foo"), "foo"),
        (FilterOperatorGreaterThan(7), 7),
        (FilterOperatorIn(["foo", "bar"]), ["foo", "bar"]),
        (FilterOperatorInCalendarDay(4), 4),
        (FilterOperatorInCalendarMonth(4), 4),
        (FilterOperatorInCalendarWeek(4), 4),
        (FilterOperatorInCalendarYear(4), 4),
        (FilterOperatorInLast(4, DateType.MONTH), [4, DateType.MONTH.value]),
        (FilterOperatorInNext(4, DateType.MONTH), [4, DateType.MONTH.value]),
        (FilterOperatorIs("foo"), "foo"),
        (FilterOperatorIsNot("foo"), "foo"),
        (FilterOperatorLessThan(5), 5),
        (FilterOperatorNotContains("foo"), "foo"),
        (FilterOperatorNotIn([0, 2]), [0, 2]),
        (FilterOperatorNotInLast(5, DateType.YEAR), [5, DateType.YEAR.value]),
        (FilterOperatorNotInNext(5, DateType.YEAR), [5, DateType.YEAR.value]),
        (FilterOperatorStartsWith("foo"), "foo"),
        (FilterOperatorTypeIs(Project), Project.__sg_type__),
        (FilterOperatorTypeIsNot(Project), Project.__sg_type__),
    ],
)
def test_operator_serialize(operator: FilterOperator[Any], expected_value: Any) -> None:
    """Test serialization of filter operators."""
    assert operator.serialize() == expected_value


def test_filter_operator_matches() -> None:
    """Test the filter operator matches method."""

    class SgEntity(SgBaseEntity):
        pass

    class TestEntity(SgEntity):
        __sg_type__ = "test"

        name: TextField

    cond = TestEntity.id.eq(1) & TestEntity.name.eq("foo")
    assert cond.matches(TestEntity(id=1, name="foo"))
    assert not cond.matches(TestEntity(id=1, name="bar"))
    assert not cond.matches(TestEntity(id=0, name="foo"))
    assert not cond.matches(TestEntity(id=0, name="bar"))

    cond = TestEntity.id.eq(1) | TestEntity.name.eq("foo")
    assert cond.matches(TestEntity(id=1, name="foo"))
    assert cond.matches(TestEntity(id=1, name="bar"))
    assert cond.matches(TestEntity(id=0, name="foo"))
    assert not cond.matches(TestEntity(id=0, name="bar"))


def test_null_condition_matches() -> None:
    """Test the null condition matches method."""

    class SgEntity(SgBaseEntity):
        pass

    class TestEntity(SgEntity):
        __sg_type__ = "test"

    assert SgNullCondition().matches(TestEntity())
