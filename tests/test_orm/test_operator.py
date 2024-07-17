"""Tests query operators."""

from __future__ import annotations

from typing import Any

import pytest

from sgchemist.orm.constant import LogicalOperator
from sgchemist.orm.constant import Operator
from sgchemist.orm.entity import SgBaseEntity
from sgchemist.orm.fields import AbstractValueField
from sgchemist.orm.fields import TextField
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
    cond1 = SgFieldCondition(field, Operator.IS, "foo")
    cond2 = SgFieldCondition(field, Operator.IS, "name")
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
    cond1 = SgFieldCondition(field, Operator.IS, "foo")
    cond2 = SgFieldCondition(field, Operator.IS, "name")
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
    cond1 = SgFieldCondition(field, Operator.IS, "foo")
    cond_null = null_cond & cond1
    assert cond_null is cond1
    cond_null = null_cond | cond1
    assert cond_null is cond1
