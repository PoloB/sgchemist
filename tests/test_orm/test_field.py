"""Testing instrumented fields."""

from __future__ import annotations

from typing import Any
from typing import Callable
from typing import TypeVar

import pytest

from sgchemist.orm import DateTimeField
from sgchemist.orm import EntityField
from sgchemist.orm import ImageField
from sgchemist.orm import ListField
from sgchemist.orm import NumberField
from sgchemist.orm import TextField
from sgchemist.orm import error
from sgchemist.orm import field_info
from sgchemist.orm.constant import DateType
from sgchemist.orm.entity import LazyEntityClassEval
from sgchemist.orm.entity import LazyEntityCollectionClassEval
from sgchemist.orm.entity import SgBaseEntity
from sgchemist.orm.field_info import cast_column
from sgchemist.orm.fields import AbstractField
from sgchemist.orm.fields import update_entity_from_value
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
from tests.classes import Asset
from tests.classes import Project
from tests.classes import Shot
from tests.classes import Task

T = TypeVar("T")


@pytest.fixture(scope="module")
def entity_class() -> type[Shot]:
    """The test entity class."""
    return Shot


@pytest.fixture()
def lazy_class_eval(entity_class: type[Shot]) -> LazyEntityClassEval:
    """The test lazy entity."""
    return LazyEntityClassEval(entity_class.__name__, entity_class.__registry__)


@pytest.fixture()
def lazy_collection_eval(
    lazy_class_eval: LazyEntityClassEval,
) -> LazyEntityCollectionClassEval:
    """The test lazy collection."""
    return LazyEntityCollectionClassEval([lazy_class_eval])


def test_lazy_entity_class_eval(
    lazy_class_eval: LazyEntityClassEval,
    entity_class: type[SgBaseEntity],
) -> None:
    """Test the lazy entity getter."""
    assert lazy_class_eval.get() is entity_class
    assert lazy_class_eval.class_name == entity_class.__name__


def test_lazy_entity_collection_eval(
    lazy_collection_eval: LazyEntityCollectionClassEval,
    entity_class: type[SgBaseEntity],
) -> None:
    """Test the lazy entity collection getter."""
    assert lazy_collection_eval.get_by_type(entity_class.__sg_type__) is entity_class


@pytest.mark.parametrize(
    (
        "field",
        "exp_dict",
    ),
    [
        (
            Shot.name,
            {
                "entity": Shot,
                "default_value": None,
                "name": "code",
                "name_in_relationship": "name",
                "alias_field": None,
                "parent_field": None,
                "original_field": Shot.name,
                "primary": False,
                "is_relationship": False,
                "is_list": False,
            },
        ),
        (
            Shot.id,
            {
                "entity": Shot,
                "default_value": None,
                "name": "id",
                "name_in_relationship": "id",
                "alias_field": None,
                "parent_field": None,
                "original_field": Shot.id,
                "primary": True,
                "is_relationship": False,
                "is_list": False,
            },
        ),
        (
            Shot.project,
            {
                "entity": Shot,
                "default_value": None,
                "name": "project",
                "name_in_relationship": "project",
                "alias_field": None,
                "parent_field": None,
                "original_field": Shot.project,
                "primary": False,
                "is_relationship": True,
                "is_list": False,
            },
        ),
        (
            Shot.parent_shots,
            {
                "entity": Shot,
                "default_value": [],
                "name": "parent_shots",
                "name_in_relationship": "parent_shots",
                "alias_field": None,
                "parent_field": None,
                "original_field": Shot.parent_shots,
                "primary": False,
                "is_relationship": True,
                "is_list": True,
            },
        ),
        (
            Task.entity,
            {
                "entity": Task,
                "default_value": None,
                "name": "entity",
                "name_in_relationship": "entity",
                "alias_field": None,
                "parent_field": None,
                "original_field": Task.entity,
                "primary": False,
                "is_relationship": True,
                "is_list": False,
            },
        ),
        (
            Task.asset,
            {
                "entity": Task,
                "default_value": None,
                "name": "entity",
                "name_in_relationship": "entity",
                "alias_field": Task.entity,
                "parent_field": None,
                "original_field": Task.asset,
                "primary": False,
                "is_relationship": True,
                "is_list": False,
            },
        ),
        (
            Task.asset.f(Asset.project),
            {
                "entity": Task,
                "default_value": None,
                "name": "entity.Asset.project",
                "name_in_relationship": "entity.Asset.project",
                "alias_field": None,
                "parent_field": Task.asset,
                "original_field": Asset.project,
                "primary": False,
                "is_relationship": True,
                "is_list": False,
            },
        ),
    ],
)
def test_field_attributes(
    field: AbstractField[T],
    exp_dict: dict[str, Any],
) -> None:
    """Tests the fields attributes."""
    assert isinstance(repr(field), str)
    info = field.__info__
    assert info["entity"] is exp_dict["entity"]
    assert info["default_value"] == exp_dict["default_value"]
    assert info["name"] == exp_dict["name"]
    assert info["name_in_relation"] == exp_dict["name_in_relationship"]
    assert info["alias_field"] is exp_dict["alias_field"]
    assert info["parent_field"] is exp_dict["parent_field"]
    assert info["original_field"] is exp_dict["original_field"]
    assert info["primary"] is exp_dict["primary"]
    assert info["is_relationship"] is exp_dict["is_relationship"]
    assert info["is_list"] is exp_dict["is_list"]


@pytest.mark.parametrize(
    ("field", "exp_field_name"),
    [
        (Shot.project.f(Project.id), "project.Project.id"),
        (Shot.assets.f(Asset.id), "assets.Asset.id"),
        (Task.asset.f(Asset.id), "entity.Asset.id"),
        (Task.asset.f(Asset.project).f(Project.id), "entity.Asset.project.Project.id"),
        (Shot.tasks.f(Task.entity), "tasks.Task.entity"),
        (Asset.shots.f(Shot.tasks).f(Task.entity), "shots.Shot.tasks.Task.entity"),
        (Task.entity.f(Asset.id), "entity.Asset.id"),
    ],
)
def test_build_relative_to(field: AbstractField[Any], exp_field_name: str) -> None:
    """Tests the relative field names."""
    assert field.__info__["name"] == exp_field_name


def test_missing_attribute_on_target_selector() -> None:
    """Tests that getting a non-existing field raises an error."""
    with pytest.raises(AttributeError):
        _ = Task.entity.f(Asset.non_existing_field)  # type: ignore[attr-defined]


def test_field_casting_error() -> None:
    """Tests casting error."""
    with pytest.raises(error.SgFieldConstructionError):
        Shot.project.f(Asset.name)

    with pytest.raises(error.SgFieldConstructionError):
        Task.entity.f(Project.name)

    with pytest.raises(error.SgFieldConstructionError):
        Task.shot.f(Asset.name)


@pytest.mark.parametrize(
    ("field", "value_to_set", "exp_value"),
    [
        (Shot.id, 5, 5),
        (Shot.project, Project(), None),
        (Task.entity, Asset(), None),
    ],
)
def test_update_entity_from_row_value(
    field: AbstractField[T],
    value_to_set: T,
    exp_value: T,
) -> None:
    """Tests the update entity from row attribute."""
    inst = field.__info__["entity"]()
    update_entity_from_value(field, inst, value_to_set)
    assert inst.__state__.get_value(field) == exp_value


@pytest.mark.parametrize(
    ("field", "value", "exp_value"),
    [
        (Shot.id, None, []),
        (Shot.id, 5, []),
        (Shot.project, 5, [5]),
        (Shot.project, None, []),
        (Shot.parent_shots, [5], [5]),
        (Task.entity, None, []),
        (Task.entity, 5, [5]),
    ],
)
def test_entities_iter_entities_from_field_values(
    field: AbstractField[T],
    value: T,
    exp_value: T,
) -> None:
    """Tests the entity iterator."""
    assert (
        list(field_info.iter_entities_from_field_value(field.__info__, value))
        == exp_value
    )


@pytest.mark.parametrize(
    ("field", "func", "value", "exp_value"),
    [
        (Shot.id, lambda x, _: x, 5, 5),
        (Shot.project, lambda x, _: x, None, None),
        (Shot.project, lambda x, _: x, {"type": "Project", "id": 1}, Project),
        (
            Shot.parent_shots,
            lambda x, y: (x, y["id"]),
            [{"type": "Shot", "id": 5}, {"type": "Shot", "id": 3}],
            [(Shot, 5), (Shot, 3)],
        ),
        (Task.entity, lambda x, _: x, None, None),
        (Task.entity, lambda x, _: x, {"type": "Asset", "id": 1}, Asset),
        (Task.entity, lambda x, _: x, {"type": "Shot", "id": 1}, Shot),
    ],
)
def test_cast_column(
    field: AbstractField[T],
    func: Callable[[type[SgBaseEntity], dict[str, T]], T],
    value: T,
    exp_value: T,
) -> None:
    """Tests the cast column method."""
    assert cast_column(field.__info__, value, func) == exp_value


@pytest.mark.parametrize(
    ("field_condition", "exp_op"),
    [
        (NumberField().eq(5), FilterOperatorIs),
        (NumberField().neq(5), FilterOperatorIsNot),
        (NumberField().gt(5), FilterOperatorGreaterThan),
        (NumberField().lt(5), FilterOperatorLessThan),
        (NumberField().between(5, 10), FilterOperatorBetween),
        (NumberField().is_in([5, 10]), FilterOperatorIn),
        (NumberField().is_not_in([5, 10]), FilterOperatorNotIn),
        (TextField().startswith("test"), FilterOperatorStartsWith),
        (TextField().endswith("test"), FilterOperatorEndsWith),
        (TextField().contains("test"), FilterOperatorContains),
        (TextField().not_contains("test"), FilterOperatorNotContains),
        (TextField().is_in(["test"]), FilterOperatorIn),
        (TextField().is_not_in(["test"]), FilterOperatorNotIn),
        (EntityField().type_is(Shot), FilterOperatorTypeIs),
        (EntityField().type_is_not(Shot), FilterOperatorTypeIsNot),
        (EntityField().is_in([]), FilterOperatorIn),
        (EntityField().is_not_in([]), FilterOperatorNotIn),
        (DateTimeField().in_last(2, DateType.DAY), FilterOperatorInLast),
        (DateTimeField().not_in_last(2, DateType.DAY), FilterOperatorNotInLast),
        (DateTimeField().in_next(2, DateType.DAY), FilterOperatorInNext),
        (DateTimeField().not_in_next(2, DateType.DAY), FilterOperatorNotInNext),
        (DateTimeField().in_calendar_day(2), FilterOperatorInCalendarDay),
        (DateTimeField().in_calendar_week(2), FilterOperatorInCalendarWeek),
        (DateTimeField().in_calendar_month(2), FilterOperatorInCalendarMonth),
        (DateTimeField().in_calendar_year(2), FilterOperatorInCalendarYear),
        (ImageField().exists(), FilterOperatorIsNot),
        (ImageField().not_exists(), FilterOperatorIs),
        (ListField().is_in(["a", "b"]), FilterOperatorIn),
        (ListField().is_not_in(["a", "b"]), FilterOperatorNotIn),
    ],
)
def test_condition(
    field_condition: SgFieldCondition,
    exp_op: type[FilterOperator[Any, Any]],
) -> None:
    """Tests the filter methods."""
    assert isinstance(field_condition.op, exp_op)


@pytest.mark.parametrize(
    ("field", "expected"),
    [
        (Project.id, [Project.id]),
        (Asset.id, [Asset.id]),
        (Asset.project.f(Project.id), [Asset.project, Project.id]),
        (Task.asset.f(Asset.id), [Task.asset, Asset.id]),
        (
            Task.asset.f(Asset.project).f(Project.name),
            [Task.asset, Asset.project, Project.name],
        ),
    ],
)
def test_get_field_hierarchy(
    field: AbstractField[Any],
    expected: list[AbstractField[Any]],
) -> None:
    """Test the field hierarchy."""
    assert field_info.get_field_hierarchy(field) == expected
