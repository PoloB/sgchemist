"""Tests the session module."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from sgchemist import error
from sgchemist.orm import Session
from sgchemist.orm import SgBaseEntity
from sgchemist.orm import select
from sgchemist.orm.constant import BatchRequestType
from sgchemist.orm.session import SgFindResult
from tests.classes import Asset
from tests.classes import Project
from tests.classes import Shot
from tests.classes import Task

if TYPE_CHECKING:
    from sgchemist.orm.engine import SgEngine


@pytest.fixture
def shot_entity() -> type[Shot]:
    """Returns the Shot entity."""
    return Shot


@pytest.fixture
def session(engine: SgEngine) -> Session:
    """Returns a session object."""
    return Session(engine)


@pytest.fixture
def test_project() -> Project:
    """Returns a project object."""
    return Project(name="project")


@pytest.fixture
def test_asset(test_project: Project) -> Asset:
    """Returns an asset object."""
    return Asset(name="asset1", project=test_project)


@pytest.fixture
def test_shot(test_project: Project) -> Shot:
    """Returns a shot object."""
    return Shot(name="shot1", project=test_project)


@pytest.fixture
def test_task_shot(test_shot: Shot) -> Task:
    """Returns a task associated to a shot."""
    return Task(name="task1", entity=test_shot)


@pytest.fixture
def test_task_asset(test_asset: Asset) -> Task:
    """Returns a task associated to an asset."""
    return Task(name="task1", entity=test_asset)


@pytest.fixture
def test_db(
    test_project: Project,
    test_shot: Shot,
    test_asset: Asset,
    test_task_shot: Task,
    test_task_asset: Task,
) -> list[SgBaseEntity]:
    """Returns a database content."""
    return [test_project, test_shot, test_asset, test_task_shot, test_task_asset]


@pytest.fixture
def filled_engine(
    session: Session,
    engine: SgEngine,
    test_db: list[SgBaseEntity],
) -> SgEngine:
    """Returns an engine filled with database content."""
    for inst in test_db:
        session.add(inst)
        session.commit()
    return engine


def test_find_result(shot_entity: type[Shot]) -> None:
    """Tests the find result object."""
    test_shot1 = shot_entity()
    test_shot2 = shot_entity()
    result = SgFindResult([test_shot1, test_shot2])
    assert list(result) == [test_shot1, test_shot2]
    assert result.first() is test_shot1
    assert result.all() == [test_shot1, test_shot2]


def test_session_init(session: Session) -> None:
    """Tests the session initialization state."""
    assert len(session.pending_queries) == 0


def test_add_new(session: Session, test_project: Project) -> None:
    """Tests adding new object to the session."""
    query = session.add(test_project)
    state = test_project.__state__
    assert len(session.pending_queries) == 1
    assert query.request_type == BatchRequestType.CREATE
    assert state.pending_add is True
    assert test_project in session


def test_add_new_commit(session: Session, test_project: Project) -> None:
    """Tests adding an already commited object to the session."""
    session.add(test_project)
    state = test_project.__state__
    session.commit()
    assert state.pending_add is False
    assert len(session.pending_queries) == 0
    assert len(state.modified_fields) == 0
    assert state.is_commited()
    assert test_project not in session


def test_add_new_twice(session: Session, test_project: Project) -> None:
    """Tests adding the same object twice to the session."""
    # Adding the same object twice has no effect
    query1 = session.add(test_project)
    query2 = session.add(test_project)
    assert test_project in session
    assert query1 is query2
    assert len(session.pending_queries) == 1


def test_add_new_deleted(session: Session, test_project: Project) -> None:
    """Tests adding an already deleted object to the session."""
    test_project.__state__.deleted = True
    # A deleted object can be added without error
    session.add(test_project)
    assert test_project in session


def test_add_new_pending_deleted(session: Session, test_project: Project) -> None:
    """Tests adding an already pending deleted object to the session."""
    test_project.__state__.pending_deletion = True
    # A deleted object cannot be added
    with pytest.raises(error.SgAddEntityError):
        session.add(test_project)


def test_add_commited_result_in_update(session: Session) -> None:
    """Tests adding an already commited result object to the session."""
    project = Project(id=2)
    query = session.add(project)
    assert project in session
    assert query.request_type == BatchRequestType.UPDATE


def test_add_relationship_not_commited(session: Session, test_shot: Shot) -> None:
    """Tests adding an entity with a non commited relationship object to the session."""
    with pytest.raises(error.SgRelationshipNotCommitedError):
        session.add(test_shot)


def test_update(session: Session, test_project: Project) -> None:
    """Tests adding object after commit results in update."""
    session.add(test_project)
    session.commit()
    session.add(test_project)
    assert len(session.pending_queries) == 1
    assert session.pending_queries[0].request_type == BatchRequestType.UPDATE
    # An entity that is finally not modified should not be commited
    assert session.commit() == []


def test_rollback(session: Session, test_project: Project) -> None:
    """Tests rollback."""
    session.add(test_project)
    assert len(session.pending_queries) == 1
    session.rollback()
    assert len(session.pending_queries) == 0


def test_delete(session: Session, test_project: Project) -> None:
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


def test_empty_commit(session: Session) -> None:
    """Tests commiting with an empty session works."""
    assert session.commit() == []


def test_delete_uncommitted(session: Session, test_project: Project) -> None:
    """Tests that deleting non commited object raises an error."""
    with pytest.raises(error.SgDeleteEntityError):
        session.delete(test_project)


def test_delete_already_deleted(session: Session, test_project: Project) -> None:
    """Tests that deleting an already deleted object raises an error."""
    session.add(test_project)
    session.commit()
    session.delete(test_project)
    session.commit()
    with pytest.raises(error.SgDeleteEntityError):
        session.delete(test_project)


@pytest.mark.parametrize(
    ("model", "expected_count"),
    [(Shot, 1), (Asset, 1), (Project, 1), (Task, 2)],
)
def test_execute_query_find(
    filled_engine: SgEngine,  # noqa: ARG001
    session: Session,
    model: type[SgBaseEntity],
    expected_count: int,
) -> None:
    """Tests query find returns the expected number of results."""
    result = session.exec(select(model))
    assert len(result) == expected_count


def test_execute_query_find_shot_entity(
    filled_engine: SgEngine,  # noqa: ARG001
    session: Session,
    test_task_shot: Task,
    test_shot: Shot,
) -> None:
    """Tests that the session fills the multi target objects correctly."""
    task_entity = test_task_shot.__class__
    task = session.exec(
        select(task_entity).where(task_entity.id.eq(test_task_shot.id)),
    ).first()
    assert task.entity is not None
    assert task.entity.id == test_shot.id
    assert task.entity.__sg_type__ == test_shot.__sg_type__
    assert task.asset is None
    assert task.shot is not None
    assert task.shot.id == test_shot.id
    assert task.shot.__sg_type__ == test_shot.__sg_type__
    # Getting elements nested elements from shot should raise an error
    with pytest.raises(error.SgMissingFieldError):
        _ = task.shot.description


def test_execute_query_find_loading(
    filled_engine: SgEngine,  # noqa: ARG001
    session: Session,
    shot_entity: type[Shot],
    test_shot: Shot,
) -> None:
    """Test querying with loading option."""
    shot_fields = (shot_entity.id, shot_entity.project)
    query = select(shot_entity, *shot_fields).load(shot_entity.project.f(Project.name))
    shot = session.exec(query).first()
    assert shot.id == test_shot.id
    assert shot.project is not None
    assert test_shot.project is not None
    assert shot.project.id == test_shot.project.id
    assert shot.project.name == test_shot.project.name
    # Loading all with relationship
    query = select(shot_entity, *shot_fields).load_all(shot_entity.project)
    shot = session.exec(query).first()
    assert shot.id == test_shot.id
    assert shot.project is not None
    assert test_shot.project is not None
    assert shot.project.id == test_shot.project.id
    assert shot.project.name == test_shot.project.name
    # Loading all
    query = select(shot_entity, *shot_fields).load_all()
    shot = session.exec(query).first()
    assert shot.id == test_shot.id
    assert shot.project is not None
    assert test_shot.project is not None
    assert shot.project.id == test_shot.project.id
    assert shot.project.name == test_shot.project.name


def test_execute_query_select_any_fields(
    filled_engine: SgEngine,  # noqa: ARG001
    session: Session,
    shot_entity: type[Shot],
    test_shot: Shot,
) -> None:
    """Test querying only some fields."""
    shot = session.exec(select(shot_entity, shot_entity.id, shot_entity.name)).first()
    assert shot.id == test_shot.id
    assert shot.name == test_shot.name
    with pytest.raises(error.SgMissingFieldError):
        _ = shot.project


def test_context_manager(engine: SgEngine, test_project: Project) -> None:
    """Tests the context manager behavior."""
    with Session(engine) as session:
        session.add(test_project)

    assert len(session.pending_queries) == 0
    assert test_project.__state__.is_commited()
