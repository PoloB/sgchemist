"""Tests for the shotgun-api3 engine."""

from __future__ import annotations

import pytest

from sgchemist.engine.mock import MockEngine
from sgchemist.orm.constant import BatchRequestType
from sgchemist.orm.engine import SgEngine
from sgchemist.orm.entity import SgBaseEntity
from sgchemist.orm.query import SgBatchQuery
from sgchemist.orm.query import select
from sgchemist.orm.session import Session
from tests.classes import Project
from tests.classes import SgEntity
from tests.classes import Shot
from tests.classes import Task


def test_mock_engine_registry() -> None:
    """Test the mock engine registry."""
    mock_engine = MockEngine()

    with pytest.raises(ValueError):
        mock_engine.register_base(Project)

    mock_engine.register_base(SgEntity)


def test_mock_find_unregistered_entity() -> None:
    """Test querying an unregistered entity."""

    class TestBase(SgBaseEntity):
        pass

    mock_engine = MockEngine()
    mock_engine.register_base(TestBase)
    query = select(Project)

    with pytest.raises(ValueError):
        mock_engine.find(query.get_data())


@pytest.fixture()
def engine() -> MockEngine:
    """Returns a test engine instance."""
    engine = MockEngine()
    engine.register_base(SgEntity)
    return engine


@pytest.fixture()
def test_project() -> Project:
    """Return a TestProject instance."""
    return Project()


@pytest.fixture()
def test_shot() -> Shot:
    """Return a TestShot instance."""
    return Shot(name="shot1")


@pytest.fixture()
def test_task() -> Task:
    """Return a TestTask instance."""
    return Task(name="task1")


@pytest.fixture()
def filled_engine(
    engine: SgEngine,
    test_project: Project,
    test_shot: Shot,
    test_task: Task,
) -> SgEngine:
    """Return a ShotgunAPIEngine instance filled with some data."""
    session = Session(engine)
    session.add(test_project)
    session.commit()
    test_shot.project = test_project
    session.add(test_shot)
    session.commit()
    test_task.entity = test_shot
    session.add(test_task)
    session.commit()
    return engine


@pytest.mark.parametrize("test_model", [Shot, Project, Task])
def test_engine_find(filled_engine: SgEngine, test_model: type[SgBaseEntity]) -> None:
    """Test find queries on a filled engine."""
    find_query_state = select(test_model).get_data()
    rows = filled_engine.find(find_query_state)
    assert len(rows) == 1
    row = rows[0]
    assert isinstance(row, dict)
    assert row["id"] == 1


@pytest.mark.parametrize(
    "test_model_inst",
    [
        Project(),
        Shot(name="test"),
        Shot(name="test", project=Project(id=1)),
    ],
)
def test_engine_create(engine: SgEngine, test_model_inst: SgBaseEntity) -> None:
    """Test create queries."""
    batch_query = SgBatchQuery(BatchRequestType.CREATE, test_model_inst)
    rows = engine.batch([batch_query])
    assert len(rows) == 1
    success, row = rows[0]
    assert isinstance(row, dict)
    assert success
    assert row["id"] == 1


@pytest.mark.parametrize(
    ("test_model_inst", "batch_request_type"),
    [
        (Project(), BatchRequestType.UPDATE),
        (Shot(name="shot1"), BatchRequestType.UPDATE),
        (Task(name="task1"), BatchRequestType.UPDATE),
        (Project(), BatchRequestType.DELETE),
        (Shot(name="shot1"), BatchRequestType.DELETE),
        (Task(name="task1"), BatchRequestType.DELETE),
    ],
)
def test_engine_batch_request(
    engine: SgEngine,
    test_model_inst: SgBaseEntity,
    batch_request_type: BatchRequestType,
) -> None:
    """Test update queries."""
    session = Session(engine)
    session.add(test_model_inst)
    session.commit()
    batch_query = SgBatchQuery(batch_request_type, test_model_inst)
    rows = engine.batch([batch_query])
    assert len(rows) == 1
    success, row = rows[0]
    assert isinstance(row, dict)
    assert success
    assert row["id"] == 1
