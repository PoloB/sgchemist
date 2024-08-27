"""Tests the serializer for the shotgun-api3."""

from __future__ import annotations

from typing import TYPE_CHECKING
from typing import Any

import pytest

from sgchemist.orm.constant import BatchRequestType
from sgchemist.orm.query import SgBatchQuery
from sgchemist.orm.queryop import SgNullCondition
from sgchemist.orm.serializer import ShotgunAPIBatchQuerySerializer
from sgchemist.orm.serializer import ShotgunAPIObjectSerializer
from sgchemist.orm.serializer import serialize_condition
from sgchemist.orm.serializer import serialize_entity
from tests.classes import Project
from tests.classes import Shot

if TYPE_CHECKING:
    from sgchemist.orm.fields import AbstractValueField
    from sgchemist.orm.fields import EntityField
    from sgchemist.orm.fields import TextField


@pytest.fixture
def project_entity() -> type[Project]:
    """Returns the project entity."""
    return Project


@pytest.fixture
def shot_entity() -> type[Shot]:
    """Returns the shot entity."""
    return Shot


@pytest.fixture
def find_serialize() -> ShotgunAPIObjectSerializer:
    """Returns the shotgun api serializer object."""
    return ShotgunAPIObjectSerializer()


@pytest.fixture
def batch_serialize() -> ShotgunAPIBatchQuerySerializer:
    """Returns the shotgun api batch serializer object."""
    return ShotgunAPIBatchQuerySerializer()


@pytest.fixture
def simple_field(shot_entity: type[Shot]) -> AbstractValueField[Any]:
    """Returns a simple test field."""
    return shot_entity.name


@pytest.fixture
def relation_field(shot_entity: type[Shot]) -> EntityField[Any]:
    """Returns a relation field."""
    return shot_entity.project


@pytest.fixture
def project_inst(project_entity: type[Project]) -> Project:
    """Returns a project instance."""
    return project_entity(id=101)


def test_serialize_entity(
    find_serialize: ShotgunAPIObjectSerializer,
    shot_entity: type[Shot],
) -> None:
    """Tests the serialization of an entity instance."""
    inst = shot_entity(name="foo", id=42)
    expected_serialize = {"id": 42, "type": "Shot"}
    assert serialize_entity(inst) == expected_serialize
    assert find_serialize.serialize_filter(inst) == [expected_serialize]


def test_serialize_operator(
    find_serialize: ShotgunAPIObjectSerializer,
    simple_field: TextField,
    relation_field: EntityField[Project],
    project_inst: Project,
) -> None:
    """Tests the serialization of an operator instance."""
    cond1 = simple_field.eq("foo")
    cond2 = relation_field.eq(project_inst)
    expected_serialize = {
        "filter_operator": "all",
        "filters": [
            ["code", "is", "foo"],
            ["project", "is", {"id": 101, "type": "Project"}],
        ],
    }
    assert find_serialize.serialize_operation(cond1 & cond2) == expected_serialize
    assert find_serialize.serialize_filter(cond1 & cond2) == [expected_serialize]


def test_serialize_simple_condition(
    find_serialize: ShotgunAPIObjectSerializer,
    simple_field: TextField,
) -> None:
    """Tests the serialization of a simple condition."""
    condition = simple_field.eq("foo")
    expected_serialize = ("code", "is", "foo")
    assert serialize_condition(condition) == expected_serialize
    assert find_serialize.serialize_filter(condition) == [list(expected_serialize)]


def test_serialize_entity_condition(
    find_serialize: ShotgunAPIObjectSerializer,
    relation_field: EntityField[Project],
    project_inst: Project,
) -> None:
    """Tests the serialization of a condition over an entity."""
    model_cond = relation_field.eq(project_inst)
    expected_serialize = ("project", "is", {"type": "Project", "id": 101})
    assert serialize_condition(model_cond) == expected_serialize
    assert find_serialize.serialize_filter(model_cond) == [list(expected_serialize)]


def test_serialize_null_condition(find_serialize: ShotgunAPIObjectSerializer) -> None:
    """Tests the serialization of a null condition."""
    assert find_serialize.serialize_filter(SgNullCondition()) == []


@pytest.mark.parametrize(
    ("batch_queries", "expected_serialization"),
    [
        (
            [
                SgBatchQuery(
                    BatchRequestType.CREATE,
                    Shot(name="foo", project=Project(id=2)),
                ),
            ],
            [
                {
                    "request_type": "create",
                    "entity_type": "Shot",
                    "data": {
                        "code": "foo",
                        "description": None,
                        "parent_shots": [],
                        "project": {"id": 2, "type": "Project"},
                        "tasks": [],
                        "assets": [],
                    },
                },
            ],
        ),
        (
            [
                SgBatchQuery(
                    BatchRequestType.UPDATE,
                    Shot(id=1, name="bar", project=Project(id=3)),
                ),
            ],
            [
                {
                    "request_type": "update",
                    "entity_type": "Shot",
                    "entity_id": 1,
                    "data": {
                        "code": "bar",
                        "project": {"id": 3, "type": "Project"},
                    },
                },
            ],
        ),
        (
            [
                SgBatchQuery(
                    BatchRequestType.DELETE,
                    Shot(id=1, name="foo", project=Project(id=3)),
                ),
            ],
            [
                {
                    "request_type": "delete",
                    "entity_type": "Shot",
                    "entity_id": 1,
                },
            ],
        ),
    ],
    ids=["Create", "Update", "Delete"],
)
def test_batch_serializer(
    batch_serialize: ShotgunAPIBatchQuerySerializer,
    batch_queries: list[SgBatchQuery],
    expected_serialization: list[dict[str, Any]],
) -> None:
    """Tests different batch serialization cases."""
    assert batch_serialize.serialize(batch_queries) == expected_serialization
