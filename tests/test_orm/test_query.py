"""Tests the query objects."""

from typing import Type

import pytest

from classes import Shot
from sgchemist.orm.constant import BatchRequestType
from sgchemist.orm.constant import GroupingType
from sgchemist.orm.constant import Order
from sgchemist.orm.query import SgBatchQuery
from sgchemist.orm.query import SgFindQuery
from sgchemist.orm.query import SgFindQueryData
from sgchemist.orm.query import SgSummarizeQuery
from sgchemist.orm.query import SgSummarizeQueryData
from sgchemist.orm.query import select
from sgchemist.orm.query import summarize
from sgchemist.orm.queryop import SgNullCondition


@pytest.fixture
def shot_entity() -> Type[Shot]:
    """Returns the TestShot entity."""
    return Shot


@pytest.fixture
def find_query_state(shot_entity) -> SgFindQueryData:
    """Returns the find query state."""
    return SgFindQueryData(shot_entity)


@pytest.fixture
def summarize_query_state(shot_entity) -> SgSummarizeQueryData:
    """Returns the summarize query state."""
    return SgSummarizeQueryData(shot_entity)


@pytest.fixture
def find_query(find_query_state) -> SgFindQuery:
    """Returns the find query."""
    return SgFindQuery(find_query_state)


@pytest.fixture
def summarize_query(summarize_query_state) -> SgSummarizeQuery:
    """Returns the summarize query."""
    return SgSummarizeQuery(summarize_query_state)


@pytest.fixture
def test_shot(shot_entity):
    """Returns the test shot."""
    return shot_entity(name="test_shot")


def test_state(shot_entity, find_query_state):
    """Tests the find query state init attributes."""
    assert find_query_state.model is shot_entity
    assert isinstance(find_query_state.condition, SgNullCondition)
    assert isinstance(find_query_state.order_fields, tuple)
    assert len(find_query_state.order_fields) == 0
    assert isinstance(find_query_state.limit, int)
    assert find_query_state.limit == 0
    assert find_query_state.retired_only is False
    assert find_query_state.page == 0
    assert find_query_state.include_archived_projects is True
    assert find_query_state.additional_filter_presets == []


def test_summarize_state(shot_entity, summarize_query_state):
    """Tests the summarize query state init attributes."""
    assert summarize_query_state.model is shot_entity
    assert summarize_query_state.condition is None
    assert isinstance(summarize_query_state.grouping, tuple)
    assert len(summarize_query_state.grouping) == 0
    assert summarize_query_state.include_archived_projects is True


def test_state_copy(find_query, find_query_state):
    """Tests the copy is not the original state."""
    # A copy is made in the getter
    assert find_query.get_data() is not find_query_state


def test_where(shot_entity, find_query):
    """Tests the where clause."""
    condition = shot_entity.name.eq("foo")
    new_query = find_query.where(condition)
    assert new_query.get_data().condition is condition
    new_query.where(shot_entity.id.eq(42))


def test_order_by(shot_entity, find_query):
    """Tests the order_by clause."""
    new_query = find_query.order_by(shot_entity.name, "asc")
    assert new_query.get_data().order_fields == ((shot_entity.name, Order.ASC),)
    new_query = new_query.order_by(shot_entity.id, Order.DESC)
    assert new_query.get_data().order_fields == (
        (shot_entity.name, Order.ASC),
        (shot_entity.id, Order.DESC),
    )


def test_limit(find_query):
    """Tests the limit clause."""
    new_query = find_query.limit(1)
    assert new_query.get_data().limit == 1
    new_query = new_query.limit(42)
    assert new_query.get_data().limit == 42


def test_retired_only(find_query):
    """Tests the retired_only clause."""
    new_query = find_query.retired_only()
    assert new_query.get_data().retired_only is True


def test_page(find_query):
    """Tests the page clause."""
    new_query = find_query.page(1)
    assert new_query.get_data().page == 1


def test_reject_archived_projects(find_query):
    """Tests the reject_archived_projects clause."""
    new_query = find_query.reject_archived_projects()
    assert new_query.get_data().include_archived_projects is False


def test_filter_preset(find_query):
    """Tests the filter_preset clause."""
    new_query = find_query.filter_preset("preset", foo=42)
    assert new_query.get_data().additional_filter_presets == [
        {"preset_name": "preset", "foo": 42}
    ]


def test_summarize_state_copy(summarize_query, summarize_query_state):
    """Tests the summarize query state copy."""
    # A copy is made in the getter
    assert summarize_query.get_data() is not summarize_query_state


def test_summarize_where(shot_entity, summarize_query):
    """Tests the summarize where clause."""
    condition = shot_entity.name.eq("foo")
    new_query = summarize_query.where(condition)
    assert new_query.get_data().condition is condition
    new_query.where(shot_entity.id.eq(42))


def test_summarize_group_by(shot_entity, summarize_query):
    """Tests the summarize group by clause."""
    new_query = summarize_query.group_by(shot_entity.name, GroupingType.HUNDREDS)
    assert new_query.get_data().grouping == (
        (shot_entity.name, GroupingType.HUNDREDS, Order.ASC),
    )
    new_query = new_query.group_by(shot_entity.id, GroupingType.EXACT, Order.DESC)
    assert new_query.get_data().grouping == (
        (shot_entity.name, GroupingType.HUNDREDS, Order.ASC),
        (shot_entity.id, GroupingType.EXACT, Order.DESC),
    )


def test_summarize_reject_archived_projects(summarize_query):
    """Tests the summarize reject_archived_projects clause."""
    new_query = summarize_query.reject_archived_projects()
    assert new_query.get_data().include_archived_projects is False


def test_batch_query(test_shot):
    """Tests the batch query."""
    batch_query = SgBatchQuery(BatchRequestType.CREATE, test_shot)
    assert isinstance(batch_query.request_type, BatchRequestType)
    assert batch_query.entity is test_shot


def test_select(shot_entity):
    """Tests the select method."""
    query = select(shot_entity)
    assert isinstance(query, SgFindQuery)
    assert isinstance(query.get_data().condition, SgNullCondition)


def test_summarize(shot_entity):
    """Tests the summarize method."""
    query = summarize(shot_entity)
    assert isinstance(query, SgSummarizeQuery)
