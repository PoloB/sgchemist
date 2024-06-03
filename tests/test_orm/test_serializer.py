"""Tests the serializer for the shotgun-api3."""

from typing import Type

import pytest

import sgchemist.orm.constant
from classes import Project
from classes import Shot
from sgchemist.orm import query
from sgchemist.orm.instrumentation import InstrumentedField
from sgchemist.orm.instrumentation import InstrumentedRelationship
from sgchemist.orm.queryop import SgNullCondition
from sgchemist.orm.serializer import ShotgunAPIBatchQuerySerializer
from sgchemist.orm.serializer import ShotgunAPIObjectSerializer
from sgchemist.orm.serializer import serialize_condition
from sgchemist.orm.serializer import serialize_entity


@pytest.fixture
def project_entity() -> Type[Project]:
    """Returns the project entity."""
    return Project


@pytest.fixture
def shot_entity() -> Type[Shot]:
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
def simple_field(shot_entity) -> InstrumentedField:
    """Returns a simple test field."""
    return shot_entity.name


@pytest.fixture
def relation_field(shot_entity) -> InstrumentedRelationship:
    """Returns a relation field."""
    return shot_entity.project


@pytest.fixture
def project_inst(project_entity) -> Project:
    """Returns a project instance."""
    return project_entity(id=101)


def test_serialize_entity(find_serialize, shot_entity):
    """Tests the serialization of an entity instance."""
    inst = shot_entity(name="foo", id=42)
    expected_serialize = {"id": 42, "type": "Shot"}
    assert serialize_entity(inst) == expected_serialize
    assert find_serialize.serialize_filter(inst) == [expected_serialize]


def test_serialize_operator(find_serialize, simple_field, relation_field, project_inst):
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


def test_serialize_simple_condition(find_serialize, simple_field):
    """Tests the serialization of a simple condition."""
    condition = simple_field.eq("foo")
    expected_serialize = ["code", "is", "foo"]
    assert serialize_condition(condition) == expected_serialize
    assert find_serialize.serialize_filter(condition) == [expected_serialize]


def test_serialize_entity_condition(find_serialize, relation_field, project_inst):
    """Tests the serialization of a condition over an entity."""
    model_cond = relation_field.eq(project_inst)
    expected_serialize = ["project", "is", {"type": "Project", "id": 101}]
    assert serialize_condition(model_cond) == expected_serialize
    assert find_serialize.serialize_filter(model_cond) == [expected_serialize]


def test_serialize_null_condition(find_serialize):
    """Tests the serialization of a null condition."""
    assert find_serialize.serialize_filter(SgNullCondition()) == []


@pytest.mark.parametrize(
    "batch_queries, expected_serialization",
    [
        (
            [
                query.SgBatchQuery(
                    sgchemist.orm.constant.BatchRequestType.CREATE,
                    Shot(name="foo", project=Project(id=2)),
                )
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
                }
            ],
        ),
        (
            [
                query.SgBatchQuery(
                    sgchemist.orm.constant.BatchRequestType.UPDATE,
                    Shot(id=1, name="bar", project=Project(id=3)),
                )
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
                }
            ],
        ),
        (
            [
                query.SgBatchQuery(
                    sgchemist.orm.constant.BatchRequestType.DELETE,
                    Shot(id=1, name="foo", project=Project(id=3)),
                )
            ],
            [
                {
                    "request_type": "delete",
                    "entity_type": "Shot",
                    "entity_id": 1,
                }
            ],
        ),
    ],
    ids=["Create", "Update", "Delete"],
)
def test_batch_serializer(batch_serialize, batch_queries, expected_serialization):
    """Tests different batch serialization cases."""
    assert batch_serialize.serialize(batch_queries) == expected_serialization
