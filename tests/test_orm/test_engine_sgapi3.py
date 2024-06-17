"""Tests for the shotgun-api3 engine."""

from typing import Type

import pytest
from classes import Project
from classes import Shot
from classes import Task

from sgchemist.orm import Session
from sgchemist.orm import select
from sgchemist.orm.constant import BatchRequestType
from sgchemist.orm.engine import SgEngine
from sgchemist.orm.entity import SgEntity
from sgchemist.orm.query import SgBatchQuery
from sgchemist.orm.row import SgRow


@pytest.fixture
def test_project() -> Project:
    """Return a TestProject instance."""
    return Project()


@pytest.fixture
def test_shot(test_project: Project) -> Shot:
    """Return a TestShot instance."""
    return Shot(name="shot1")


@pytest.fixture
def test_task(test_shot: Shot) -> Task:
    """Return a TestTask instance."""
    return Task(name="task1")


@pytest.fixture
def filled_engine(
    engine: SgEngine, test_project: Project, test_shot: Shot, test_task: Task
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


@pytest.mark.parametrize(
    "test_model",
    (
        Shot,
        Project,
        Task,
    ),
)
def test_engine_find(filled_engine: SgEngine, test_model: Type[SgEntity]) -> None:
    """Test find queries on a filled engine."""
    find_query_state = select(test_model).get_data()
    rows = filled_engine.find(find_query_state)
    assert len(rows) == 1
    row = rows[0]
    assert isinstance(row, SgRow)
    assert row.success
    assert row.entity_hash == (test_model.__sg_type__, 1)


@pytest.mark.parametrize(
    "test_model_inst",
    (
        Project(),
        Shot(name="test"),
        Shot(name="test", project=Project(id=1)),
    ),
)
def test_engine_create(engine: SgEngine, test_model_inst: SgEntity) -> None:
    """Test create queries."""
    batch_query = SgBatchQuery(BatchRequestType.CREATE, test_model_inst)
    rows = engine.batch([batch_query])
    assert len(rows) == 1
    row = rows[0]
    assert isinstance(row, SgRow)
    assert row.success
    assert row.entity_hash == (test_model_inst.__sg_type__, 1)


@pytest.mark.parametrize(
    "test_model_inst, batch_request_type",
    (
        (Project(), BatchRequestType.UPDATE),
        (Shot(name="shot1"), BatchRequestType.UPDATE),
        (Task(name="task1"), BatchRequestType.UPDATE),
        (Project(), BatchRequestType.DELETE),
        (Shot(name="shot1"), BatchRequestType.DELETE),
        (Task(name="task1"), BatchRequestType.DELETE),
    ),
)
def test_engine_batch_request(
    engine: SgEngine, test_model_inst: SgEntity, batch_request_type: BatchRequestType
) -> None:
    """Test update queries."""
    session = Session(engine)
    session.add(test_model_inst)
    session.commit()
    batch_query = SgBatchQuery(BatchRequestType.UPDATE, test_model_inst)
    rows = engine.batch([batch_query])
    assert len(rows) == 1
    row = rows[0]
    assert isinstance(row, SgRow)
    assert row.success
    assert row.entity_hash == (test_model_inst.__sg_type__, 1)
