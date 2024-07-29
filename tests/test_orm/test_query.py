"""Tests the query objects."""

from __future__ import annotations

from typing import Any

import pytest

from sgchemist.orm import error
from sgchemist.orm.constant import BatchRequestType
from sgchemist.orm.constant import Order
from sgchemist.orm.query import SgBatchQuery
from sgchemist.orm.query import SgFindQuery
from sgchemist.orm.query import SgFindQueryData
from sgchemist.orm.query import SgSummarizeQuery
from sgchemist.orm.query import SgSummarizeQueryData
from sgchemist.orm.query import select
from sgchemist.orm.query import summarize
from sgchemist.orm.queryop import SgNullCondition

from .classes import Asset
from .classes import Project
from .classes import Shot


@pytest.fixture
def project_entity() -> type[Project]:
    """Returns the Project entity."""
    return Project


@pytest.fixture
def shot_entity() -> type[Shot]:
    """Returns the Shot entity."""
    return Shot


@pytest.fixture
def asset_entity() -> type[Asset]:
    """Returns the Asset entity."""
    return Asset


@pytest.fixture
def find_query_data(shot_entity: type[Shot]) -> SgFindQueryData[type[Shot]]:
    """Returns the find query state."""
    return SgFindQueryData(shot_entity, tuple(shot_entity.__fields__))


@pytest.fixture
def summarize_query_data(shot_entity: type[Shot]) -> SgSummarizeQueryData[type[Shot]]:
    """Returns the summarize query state."""
    return SgSummarizeQueryData(shot_entity)


@pytest.fixture
def find_query(find_query_data: SgFindQueryData[Any]) -> SgFindQuery[Any]:
    """Returns the find query."""
    return SgFindQuery(find_query_data)


@pytest.fixture
def summarize_query(
    summarize_query_data: SgSummarizeQueryData[Any],
) -> SgSummarizeQuery[Any]:
    """Returns the summarize query."""
    return SgSummarizeQuery(summarize_query_data)


@pytest.fixture
def test_shot(shot_entity: type[Shot]) -> Shot:
    """Returns the test shot."""
    return shot_entity(name="test_shot")


def test_state(shot_entity: type[Shot], find_query_data: SgFindQueryData[Any]) -> None:
    """Tests the find query state init attributes."""
    assert find_query_data.entity is shot_entity
    assert isinstance(find_query_data.condition, SgNullCondition)
    assert isinstance(find_query_data.order_fields, tuple)
    assert len(find_query_data.order_fields) == 0
    assert isinstance(find_query_data.limit, int)
    assert find_query_data.limit == 0
    assert find_query_data.retired_only is False
    assert find_query_data.page == 0
    assert find_query_data.include_archived_projects is True
    assert find_query_data.additional_filter_presets == []


def test_summarize_state(
    shot_entity: type[Shot], summarize_query_data: SgSummarizeQueryData[Any]
) -> None:
    """Tests the summarize query state init attributes."""
    assert summarize_query_data.entity is shot_entity
    assert isinstance(summarize_query_data.condition, SgNullCondition)
    assert isinstance(summarize_query_data.grouping_fields, tuple)
    assert len(summarize_query_data.grouping_fields) == 0
    assert summarize_query_data.include_archived_projects is True


def test_where(shot_entity: type[Shot], find_query: SgFindQuery[Any]) -> None:
    """Tests the where clause."""
    condition = shot_entity.name.eq("foo")
    new_query = find_query.where(condition)
    assert new_query.get_data().condition is condition
    new_query.where(shot_entity.id.eq(42))


def test_order_by(shot_entity: type[Shot], find_query: SgFindQuery[Any]) -> None:
    """Tests the order_by clause."""
    new_query = find_query.order_by(shot_entity.name, "asc")
    assert new_query.get_data().order_fields == ((shot_entity.name, Order.ASC),)
    new_query = new_query.order_by(shot_entity.id, Order.DESC)
    assert new_query.get_data().order_fields == (
        (shot_entity.name, Order.ASC),
        (shot_entity.id, Order.DESC),
    )


def test_limit(find_query: SgFindQuery[Any]) -> None:
    """Tests the limit clause."""
    new_query = find_query.limit(1)
    assert new_query.get_data().limit == 1
    new_query = new_query.limit(42)
    assert new_query.get_data().limit == 42


def test_retired_only(find_query: SgFindQuery[Any]) -> None:
    """Tests the retired_only clause."""
    new_query = find_query.retired_only()
    assert new_query.get_data().retired_only is True


def test_page(find_query: SgFindQuery[Any]) -> None:
    """Tests the page clause."""
    new_query = find_query.page(1)
    assert new_query.get_data().page == 1


def test_reject_archived_projects(find_query: SgFindQuery[Any]) -> None:
    """Tests the reject_archived_projects clause."""
    new_query = find_query.reject_archived_projects()
    assert new_query.get_data().include_archived_projects is False


def test_filter_preset(find_query: SgFindQuery[Any]) -> None:
    """Tests the filter_preset clause."""
    new_query = find_query.filter_preset("preset", foo=42)
    assert new_query.get_data().additional_filter_presets == [
        {"preset_name": "preset", "foo": 42}
    ]


def test_summarize_data_attributes(
    summarize_query_data: SgSummarizeQueryData[Any],
) -> None:
    """Test summarize attributes."""
    assert summarize_query_data.entity is Shot
    assert summarize_query_data.fields is tuple()
    assert isinstance(summarize_query_data.condition, SgNullCondition)
    assert summarize_query_data.grouping_fields == tuple()
    assert summarize_query_data.include_archived_projects


def test_summarize_state_copy(
    summarize_query: SgSummarizeQuery[Any],
    summarize_query_data: SgSummarizeQueryData[Any],
) -> None:
    """Tests the summarize query state copy."""
    # A copy is made in the getter
    assert summarize_query.get_data() is summarize_query_data


def test_summarize_where(
    shot_entity: type[Shot], summarize_query: SgSummarizeQuery[Any]
) -> None:
    """Tests the summarize where clause."""
    condition = shot_entity.name.eq("foo")
    new_query = summarize_query.where(condition)
    assert new_query.get_data().condition is condition
    new_query.where(shot_entity.id.eq(42))


def test_summarize_reject_archived_projects(
    summarize_query: SgSummarizeQuery[Any],
) -> None:
    """Tests the summarize reject_archived_projects clause."""
    new_query = summarize_query.reject_archived_projects()
    assert new_query.get_data().include_archived_projects is False


def test_batch_query(test_shot: Shot) -> None:
    """Tests the batch query."""
    batch_query = SgBatchQuery(BatchRequestType.CREATE, test_shot)
    assert isinstance(batch_query.request_type, BatchRequestType)
    assert batch_query.entity is test_shot


def test_select(shot_entity: type[Shot]) -> None:
    """Tests the select method."""
    query = select(shot_entity)
    assert isinstance(query, SgFindQuery)
    assert isinstance(query.get_data().condition, SgNullCondition)


def test_summarize(shot_entity: type[Shot]) -> None:
    """Tests the summarize method."""
    query = summarize(shot_entity)
    assert isinstance(query, SgSummarizeQuery)


def test_summarize_group_by(shot_entity: type[Shot]) -> None:
    """Tests the summarize group by."""
    query = summarize(shot_entity).group_by(shot_entity.id.group_exact())
    assert isinstance(query, SgSummarizeQuery)


def test_select_any_field(
    shot_entity: type[Shot], project_entity: type[Project]
) -> None:
    """Tests select of any fields."""
    query = select(shot_entity, shot_entity.id, shot_entity.name)
    assert isinstance(query, SgFindQuery)
    assert query.get_data().fields == (shot_entity.id, shot_entity.name)
    # Query a field which is not the base entity must raise an error
    with pytest.raises(error.SgQueryError):
        select(shot_entity, shot_entity.id, project_entity.name)
    # It shall also raise an error when field is outside the scope of the entity
    with pytest.raises(error.SgQueryError):
        select(shot_entity, shot_entity.id, shot_entity.project.f(Project.name))


def test_select_loading(shot_entity: type[Shot], project_entity: type[Project]) -> None:
    """Test the select loading feature."""
    shot_fields = (shot_entity.id, shot_entity.project)
    shot_project_name_field = shot_entity.project.f(Project.name)
    query = select(shot_entity, *shot_fields).load(shot_project_name_field)
    assert isinstance(query, SgFindQuery)
    assert query.get_data().fields == shot_fields
    assert query.get_data().loading_fields == (shot_project_name_field,)
    with pytest.raises(error.SgQueryError):
        select(shot_entity).load(project_entity.name)


def test_select_loading_all(shot_entity: type[Shot], asset_entity: type[Asset]) -> None:
    """Test the select loading all feature."""
    shot_fields = (shot_entity.id, shot_entity.project)
    query = select(shot_entity, *shot_fields).load_all(shot_entity.project)
    assert isinstance(query, SgFindQuery)
    assert query.get_data().fields == shot_fields
    with pytest.raises(error.SgQueryError):
        select(shot_entity).load_all(asset_entity.project)
    # Test with no arguments
    query = select(shot_entity, *shot_fields).load_all()
    assert isinstance(query, SgFindQuery)
    assert query.get_data().fields == shot_fields
    # Test with all fields
    select(shot_entity).load_all()
