"""Testing instrumented fields."""

from typing import Any
from typing import Callable
from typing import Tuple
from typing import Type

import pytest
from classes import Asset
from classes import Project
from classes import Shot
from classes import Task

from sgchemist.orm.constant import DateType
from sgchemist.orm.constant import Operator
from sgchemist.orm.entity import SgEntity
from sgchemist.orm.instrumentation import InstrumentedAttribute
from sgchemist.orm.instrumentation import InstrumentedField
from sgchemist.orm.instrumentation import LazyEntityClassEval
from sgchemist.orm.instrumentation import LazyEntityCollectionClassEval
from sgchemist.orm.queryop import SgFieldCondition
from sgchemist.orm.row import SgRow


@pytest.fixture(scope="module")
def entity_class() -> Type[Shot]:
    """The test entity class."""
    return Shot


@pytest.fixture
def lazy_class_eval(entity_class: Type[Shot]) -> LazyEntityClassEval:
    """The test lazy entity."""
    return LazyEntityClassEval(entity_class.__name__, entity_class.__registry__)


@pytest.fixture
def lazy_collection_eval(
    lazy_class_eval: LazyEntityClassEval,
) -> LazyEntityCollectionClassEval:
    """The test lazy collection."""
    return LazyEntityCollectionClassEval([lazy_class_eval])


def test_lazy_entity_class_eval(
    lazy_class_eval: LazyEntityClassEval, entity_class: Type[SgEntity]
) -> None:
    """Test the lazy entity getter."""
    assert lazy_class_eval.get() is entity_class
    assert lazy_class_eval.class_name == entity_class.__name__


def test_lazy_entity_collection_eval(
    lazy_collection_eval: LazyEntityCollectionClassEval, entity_class: Type[SgEntity]
) -> None:
    """Test the lazy entity collection getter."""
    assert lazy_collection_eval.get_by_type(entity_class.__sg_type__) is entity_class


@pytest.mark.parametrize(
    "field, exp_name, exp_attr_name, exp_class, exp_default, exp_primary, "
    "exp_name_in_rel, exp_types",
    [
        (Shot.name, "code", "name", Shot, None, False, "name", (str,)),
        (Shot.id, "id", "id", SgEntity, None, True, "id", (int,)),
        (Shot.project, "project", "project", Shot, None, False, "project", (Project,)),
        (
            Shot.parent_shots,
            "parent_shots",
            "parent_shots",
            Shot,
            [],
            False,
            "parent_shots",
            (Shot,),
        ),
        (Task.entity, "entity", "entity", Task, None, False, "entity", (Asset, Shot)),
    ],
)
def test_instrumented_field_attributes(
    field: InstrumentedField[Any],
    exp_name: str,
    exp_attr_name: str,
    exp_class: Type[SgEntity],
    exp_default: Any,
    exp_primary: bool,
    exp_name_in_rel: str,
    exp_types: Tuple[Type[SgEntity], ...],
) -> None:
    """Tests the instrumented field attributes."""
    assert isinstance(repr(field), str)
    assert field.get_name() == exp_name
    assert field.get_attribute_name() == exp_attr_name
    assert field.get_parent_class() is exp_class
    assert field.get_default_value() == exp_default
    assert not field.is_alias()
    assert field.get_name_in_relation() == exp_name_in_rel
    assert set(field.get_types()) == set(exp_types)


@pytest.mark.parametrize(
    "field, exp_field_name",
    [
        (Shot.project.id, "project.Project.id"),
        (Shot.assets.id, "assets.Asset.id"),
        (Task.asset.id, "entity.Asset.id"),
        (Task.asset.project.id, "entity.Asset.project.Project.id"),
        (Shot.tasks.entity, "tasks.Task.entity"),
        (Asset.shots.tasks.entity, "shots.Shot.tasks.Task.entity"),
        (Task.entity.Asset.id, "entity.Asset.id"),
    ],
)
def test_build_relative_to(field: InstrumentedAttribute[Any], exp_field_name: str) -> None:
    """Tests the relative field names."""
    assert field.get_name() == exp_field_name


t = Task
reveal_type(t)


def test_missing_attribute_on_target_selector() -> None:
    """Tests that getting a non-existing field raises an error."""
    with pytest.raises(AttributeError):
        _ = Task.entity.Asset.non_existing_field  # type: ignore


@pytest.mark.parametrize(
    "field, value_to_set, exp_value",
    [
        (Shot.id, 5, 5),
        (Shot.project, Project(), None),
        (Task.entity, Asset(), None),
    ],
)
def test_update_entity_from_row_value(
    field: InstrumentedAttribute[Any], value_to_set: Any, exp_value: Any
) -> None:
    """Tests the update entity from row attribute."""
    inst = field.get_parent_class()()
    field.update_entity_from_row_value(inst, value_to_set)
    assert inst.__state__.get_current_value(field.get_attribute_name()) == exp_value


@pytest.mark.parametrize(
    "field, value, exp_value",
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
    field: InstrumentedAttribute[Any], value: Any, exp_value: Any
) -> None:
    """Tests the entity iterator."""
    assert list(field.iter_entities_from_field_value(value)) == exp_value


@pytest.mark.parametrize(
    "field, func, value, exp_value",
    [
        (Shot.id, lambda x: x + 1, 5, 5),
        (Shot.project, lambda x: x + 1, 5, 6),
        (Shot.parent_shots, lambda x: x + 1, [0, 1], [1, 2]),
        (Task.entity, lambda x: x + 1, 5, 6),
    ],
)
def test_cast_value_over(
    field: InstrumentedAttribute[Any], func: Callable[[Any], Any], value: Any, exp_value: Any
) -> None:
    """Tests the cast value over method."""
    assert field.cast_value_over(func, value) == exp_value


@pytest.mark.parametrize(
    "field, func, value, exp_value",
    [
        (Shot.id, lambda x, y: x, 5, 5),
        (Shot.project, lambda x, y: x, None, None),
        (Shot.project, lambda x, y: (x, y), 5, (Project, 5)),
        (
            Shot.parent_shots,
            lambda x, y: (x, y.entity_id),
            [SgRow("Shot", 5, True, {}), SgRow("Shot", 3, True, {})],
            [(Shot, 5), (Shot, 3)],
        ),
        (Task.entity, lambda x, y: x, None, None),
        (Task.entity, lambda x, y: x, SgRow("Asset", 1, True, {}), Asset),
        (Task.entity, lambda x, y: x, SgRow("Shot", 1, True, {}), Shot),
    ],
)
def test_cast_column(
    field: InstrumentedAttribute[Any],
    func: Callable[[Type[SgEntity], SgRow[Any]], Any],
    value: Any,
    exp_value: Any,
) -> None:
    """Tests the cast column method."""
    assert field.cast_column(value, func) == exp_value


@pytest.mark.parametrize(
    "field_condition, exp_op, exp_right",
    [
        (Shot.id.eq(5), Operator.IS, 5),
        (Shot.id.neq(5), Operator.IS_NOT, 5),
        (Shot.id.gt(5), Operator.GREATER_THAN, 5),
        (Shot.id.lt(5), Operator.LESS_THAN, 5),
        (Shot.id.between(5, 10), Operator.BETWEEN, [5, 10]),
        (Shot.id.not_between(5, 10), Operator.NOT_BETWEEN, [5, 10]),
        (Shot.name.startswith("test"), Operator.STARTS_WITH, "test"),
        (Shot.name.endswith("test"), Operator.ENDS_WITH, "test"),
        (Shot.name.contains("test"), Operator.CONTAINS, "test"),
        (Shot.name.not_contains("test"), Operator.NOT_CONTAINS, "test"),
        (Shot.name.is_in(["test"]), Operator.IN, ["test"]),
        (Shot.name.is_not_in(["test"]), Operator.NOT_IN, ["test"]),
        (Task.entity.type_is(Shot), Operator.TYPE_IS, "Shot"),
        (Task.entity.type_is_not(Shot), Operator.TYPE_IS_NOT, "Shot"),
        (Shot.assets.name_contains("test"), Operator.NAME_CONTAINS, "test"),
        (Shot.assets.name_not_contains("test"), Operator.NAME_NOT_CONTAINS, "test"),
        (Shot.assets.name_is("test"), Operator.NAME_IS, "test"),
        (Task.created_at.in_last(2, DateType.DAY), Operator.IN_LAST, [2, DateType.DAY]),
        (
            Task.created_at.not_in_last(2, DateType.DAY),
            Operator.NOT_IN_LAST,
            [2, DateType.DAY],
        ),
        (Task.created_at.in_next(2, DateType.DAY), Operator.IN_NEXT, [2, DateType.DAY]),
        (
            Task.created_at.not_in_next(2, DateType.DAY),
            Operator.NOT_IN_NEXT,
            [2, DateType.DAY],
        ),
        (Task.created_at.in_calendar_day(2), Operator.IN_CALENDAR_DAY, 2),
        (Task.created_at.in_calendar_week(2), Operator.IN_CALENDAR_WEEK, 2),
        (Task.created_at.in_calendar_month(2), Operator.IN_CALENDAR_MONTH, 2),
        (Task.created_at.in_calendar_year(2), Operator.IN_CALENDAR_YEAR, 2),
        (Task.image.exists(), Operator.IS_NOT, None),
        (Task.image.not_exists(), Operator.IS, None),
    ],
)
def test_condition(
    field_condition: SgFieldCondition, exp_op: Operator, exp_right: Any
) -> None:
    """Tests the filter methods."""
    assert field_condition.operator is exp_op
    assert field_condition.right == exp_right
