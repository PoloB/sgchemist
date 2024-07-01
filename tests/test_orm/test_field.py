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

from sgchemist.orm import DateTimeField
from sgchemist.orm import EntityField
from sgchemist.orm import ImageField
from sgchemist.orm import ListField
from sgchemist.orm import MultiEntityField
from sgchemist.orm import NumberField
from sgchemist.orm import TextField
from sgchemist.orm import error
from sgchemist.orm.annotation import LazyEntityClassEval
from sgchemist.orm.annotation import LazyEntityCollectionClassEval
from sgchemist.orm.constant import DateType
from sgchemist.orm.constant import Operator
from sgchemist.orm.entity import SgEntity
from sgchemist.orm.fields import AbstractField
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
    "field, exp_name, exp_class, exp_default, exp_primary, "
    "exp_name_in_rel, exp_types",
    [
        (Shot.name, "code", Shot, None, False, "name", tuple()),
        (Shot.id, "id", Shot, None, True, "id", tuple()),
        (Shot.project, "project", Shot, None, False, "project", (Project,)),
        (
            Shot.parent_shots,
            "parent_shots",
            Shot,
            [],
            False,
            "parent_shots",
            (Shot,),
        ),
        (Task.entity, "entity", Task, None, False, "entity", (Asset, Shot)),
    ],
)
def test_field_attributes(
    field: AbstractField[Any],
    exp_name: str,
    exp_class: Type[SgEntity],
    exp_default: Any,
    exp_primary: bool,
    exp_name_in_rel: str,
    exp_types: Tuple[Type[SgEntity], ...],
) -> None:
    """Tests the fields attributes."""
    assert isinstance(repr(field), str)
    assert field.__info__.field_name == exp_name
    assert field.__info__.entity is exp_class
    assert field.__info__.default_value == exp_default
    assert not field.__info__.is_alias()
    assert field.__info__.name_in_relation == exp_name_in_rel
    assert set(field.__cast__.get_types()) == set(exp_types)


@pytest.mark.parametrize(
    "field, exp_field_name",
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
    assert field.__info__.field_name == exp_field_name


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
    "field, value_to_set, exp_value",
    [
        (Shot.id, 5, 5),
        (Shot.project, Project(), None),
        (Task.entity, Asset(), None),
    ],
)
def test_update_entity_from_row_value(
    field: AbstractField[Any], value_to_set: Any, exp_value: Any
) -> None:
    """Tests the update entity from row attribute."""
    inst = field.__info__.entity()
    field.__cast__.update_entity_from_row_value(inst, value_to_set)
    assert inst.__state__.get_slot(field).value == exp_value


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
    field: AbstractField[Any], value: Any, exp_value: Any
) -> None:
    """Tests the entity iterator."""
    assert list(field.__cast__.iter_entities_from_field_value(value)) == exp_value


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
    field: AbstractField[Any],
    func: Callable[[Any], Any],
    value: Any,
    exp_value: Any,
) -> None:
    """Tests the cast value over method."""
    assert field.__cast__.cast_value_over(func, value) == exp_value


@pytest.mark.parametrize(
    "field, func, value, exp_value",
    [
        (Shot.id, lambda x, y: x, 5, 5),
        (Shot.project, lambda x, y: x, None, None),
        (Shot.project, lambda x, y: x, SgRow("Project", 1, True, {}), Project),
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
    field: AbstractField[Any],
    func: Callable[[Type[SgEntity], SgRow[Any]], Any],
    value: Any,
    exp_value: Any,
) -> None:
    """Tests the cast column method."""
    assert field.__cast__.cast_column(value, func) == exp_value


@pytest.mark.parametrize(
    "field_condition, exp_op, exp_right",
    [
        (NumberField().eq(5), Operator.IS, 5),
        (NumberField().neq(5), Operator.IS_NOT, 5),
        (NumberField().gt(5), Operator.GREATER_THAN, 5),
        (NumberField().lt(5), Operator.LESS_THAN, 5),
        (NumberField().between(5, 10), Operator.BETWEEN, [5, 10]),
        (NumberField().not_between(5, 10), Operator.NOT_BETWEEN, [5, 10]),
        (NumberField().is_in([5, 10]), Operator.IN, [5, 10]),
        (NumberField().is_not_in([5, 10]), Operator.NOT_IN, [5, 10]),
        (TextField().startswith("test"), Operator.STARTS_WITH, "test"),
        (TextField().endswith("test"), Operator.ENDS_WITH, "test"),
        (TextField().contains("test"), Operator.CONTAINS, "test"),
        (TextField().not_contains("test"), Operator.NOT_CONTAINS, "test"),
        (TextField().is_in(["test"]), Operator.IN, ["test"]),
        (TextField().is_not_in(["test"]), Operator.NOT_IN, ["test"]),
        (EntityField().type_is(Shot), Operator.TYPE_IS, "Shot"),
        (EntityField().type_is_not(Shot), Operator.TYPE_IS_NOT, "Shot"),
        (EntityField().is_in([]), Operator.IN, []),
        (EntityField().is_not_in([]), Operator.NOT_IN, []),
        (MultiEntityField().name_contains("test"), Operator.NAME_CONTAINS, "test"),
        (
            MultiEntityField().name_not_contains("test"),
            Operator.NAME_NOT_CONTAINS,
            "test",
        ),
        (MultiEntityField().name_is("test"), Operator.NAME_IS, "test"),
        (DateTimeField().in_last(2, DateType.DAY), Operator.IN_LAST, [2, DateType.DAY]),
        (
            DateTimeField().not_in_last(2, DateType.DAY),
            Operator.NOT_IN_LAST,
            [2, DateType.DAY],
        ),
        (DateTimeField().in_next(2, DateType.DAY), Operator.IN_NEXT, [2, DateType.DAY]),
        (
            DateTimeField().not_in_next(2, DateType.DAY),
            Operator.NOT_IN_NEXT,
            [2, DateType.DAY],
        ),
        (DateTimeField().in_calendar_day(2), Operator.IN_CALENDAR_DAY, 2),
        (DateTimeField().in_calendar_week(2), Operator.IN_CALENDAR_WEEK, 2),
        (DateTimeField().in_calendar_month(2), Operator.IN_CALENDAR_MONTH, 2),
        (DateTimeField().in_calendar_year(2), Operator.IN_CALENDAR_YEAR, 2),
        (ImageField().exists(), Operator.IS_NOT, None),
        (ImageField().not_exists(), Operator.IS, None),
        (ListField().is_in(["a", "b"]), Operator.IN, ["a", "b"]),
        (ListField().is_not_in(["a", "b"]), Operator.NOT_IN, ["a", "b"]),
    ],
)
def test_condition(
    field_condition: SgFieldCondition, exp_op: Operator, exp_right: Any
) -> None:
    """Tests the filter methods."""
    assert field_condition.operator is exp_op
    assert field_condition.right == exp_right
