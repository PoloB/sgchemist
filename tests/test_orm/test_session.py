"""Tests the session module."""
from typing import List

import pytest

import sgchemist
from classes import Asset
from classes import Project
from classes import Shot
from classes import Task
from sgchemist.orm import SgEntity
from sgchemist.orm import ShotgunAPIEngine
from sgchemist.orm import error
from sgchemist.orm.constant import BatchRequestType
from sgchemist.orm.row import SgRow
from sgchemist.orm.session import SgFindResult


@pytest.fixture
def session(engine) -> sgchemist.orm.Session:
    """Returns a session object."""
    return sgchemist.orm.Session(engine)


@pytest.fixture
def test_project() -> Project:
    """Returns a project object."""
    return Project()


@pytest.fixture
def test_asset(test_project) -> Asset:
    """Returns an asset object."""
    return Asset(name="asset1", project=test_project)


@pytest.fixture
def test_shot(test_project) -> Shot:
    """Returns a shot object."""
    return Shot(name="shot1", project=test_project)


@pytest.fixture
def test_task_shot(test_shot) -> Task:
    """Returns a task associated to a shot."""
    return Task(name="task1", entity=test_shot)


@pytest.fixture
def test_task_asset(test_asset) -> Task:
    """Returns a task associated to an asset."""
    return Task(name="task1", entity=test_asset)


@pytest.fixture()
def test_db(
    test_project, test_shot, test_asset, test_task_shot, test_task_asset
) -> List[SgEntity]:
    """Returns a database content."""
    return [test_project, test_shot, test_asset, test_task_shot, test_task_asset]


@pytest.fixture
def filled_engine(session, engine, test_db) -> ShotgunAPIEngine:
    """Returns an engine filled with database content."""
    for inst in test_db:
        session.add(inst)
        session.commit()
    return engine


def test_find_result(session, test_shot):
    """Tests the find result object."""
    test_row1 = SgRow("test", 1, True, {})
    test_row2 = SgRow("test", 2, True, {})
    result = SgFindResult([test_row1, test_row2])
    assert list(result) == [test_row1, test_row2]
    assert result.first() is test_row1
    assert result.all() == [test_row1, test_row2]


def test_session_init(session):
    """Tests the session initialization state."""
    assert len(session.pending_queries) == 0


def test_add_new(session, test_project):
    """Tests adding new object to the session."""
    query = session.add(test_project)
    state = test_project.__state__
    assert len(session.pending_queries) == 1
    assert query.request_type == BatchRequestType.CREATE
    assert state.pending_add is True
    assert test_project in session


def test_add_new_commit(session, test_project):
    """Tests adding an already commited object to the session."""
    session.add(test_project)
    state = test_project.__state__
    session.commit()
    assert state.pending_add is False
    assert len(session.pending_queries) == 0
    assert len(state.modified_fields) == 0
    assert state.is_commited()
    assert test_project not in session


def test_add_new_twice(session, test_project):
    """Tests adding the same object twice to the session."""
    # Adding the same object twice has no effect
    query1 = session.add(test_project)
    query2 = session.add(test_project)
    assert test_project in session
    assert query1 is query2
    assert len(session.pending_queries) == 1


def test_add_new_deleted(session, test_project):
    """Tests adding an already deleted object to the session."""
    test_project.__state__.deleted = True
    # A deleted object can be added without error
    session.add(test_project)
    assert test_project in session


def test_add_new_pending_deleted(session, test_project):
    """Tests adding an already pending deleted object to the session."""
    test_project.__state__.pending_deletion = True
    # A deleted object cannot be added
    with pytest.raises(error.SgAddEntityError):
        session.add(test_project)


def test_add_commited_result_in_update(session):
    """Tests adding an already commited result object to the session."""
    project = Project(id=2)
    query = session.add(project)
    assert project in session
    assert query.request_type == BatchRequestType.UPDATE


def test_add_relationship_not_commited(session, test_shot):
    """Tests adding an entity with a non commited relationship object to the session."""
    with pytest.raises(error.SgRelationshipNotCommitedError):
        session.add(test_shot)


def test_update(session, test_project):
    """Tests adding object after commit results in update."""
    session.add(test_project)
    session.commit()
    session.add(test_project)
    assert len(session.pending_queries) == 1
    assert session.pending_queries[0].request_type == BatchRequestType.UPDATE


def test_rollback(session, test_project):
    """Tests rollback."""
    session.add(test_project)
    assert len(session.pending_queries) == 1
    session.rollback()
    assert len(session.pending_queries) == 0


def test_delete(session, test_project):
    """Tests deleting object."""
    session.add(test_project)
    session.commit()
    query = session.delete(test_project)
    assert query.request_type == BatchRequestType.DELETE
    assert not test_project.__state__.deleted
    assert test_project.__state__.pending_deletion
    session.commit()
    assert test_project.__state__.deleted
    assert not test_project.__state__.pending_deletion


def test_empty_commit(session):
    """Tests commiting with an empty session works."""
    session.commit()


def test_delete_uncommitted(session, test_project):
    """Tests that deleting non commited object raises an error."""
    with pytest.raises(error.SgDeleteEntityError):
        session.delete(test_project)


def test_delete_already_deleted(session, test_project):
    """Tests that deleting an already deleted object raises an error."""
    session.add(test_project)
    session.commit()
    session.delete(test_project)
    session.commit()
    with pytest.raises(error.SgDeleteEntityError):
        session.delete(test_project)


@pytest.mark.parametrize(
    "model, expected_count",
    [(Shot, 1), (Asset, 1), (Project, 1), (Task, 2)],
)
def test_execute_query_find(filled_engine, session, model, expected_count):
    """Tests query find returns the expected number of results."""
    result = session.exec(sgchemist.orm.select(model))
    assert len(result) == expected_count


def test_execute_query_find_shot_entity(
    filled_engine, session, test_task_shot, test_shot
):
    """Tests that the session fills the multi target objects correctly."""
    task_entity = test_task_shot.__class__
    task = session.exec(
        sgchemist.orm.select(task_entity).where(task_entity.id.eq(test_task_shot.id))
    ).first()
    assert task.entity.id == test_shot.id
    assert task.entity.__sg_type__ == test_shot.__sg_type__
    assert task.asset is None
    assert task.shot.id == test_shot.id
    assert task.shot.__sg_type__ == test_shot.__sg_type__


def test_context_manager(engine, test_project):
    """Tests the context manager behavior."""
    with sgchemist.orm.Session(engine) as session:
        session.add(test_project)

    assert len(session.pending_queries) == 0
    assert test_project.__state__.is_commited()
