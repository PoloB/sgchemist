"""Benchmark sgchemist."""

from typing import Any

from sgchemist.orm import Session
from sgchemist.orm import select
from sgchemist.orm.engine import SgEngine

from .classes import Project
from .classes import Shot
from .classes import Task


def test_project_creation(benchmark: Any) -> None:
    """Test performance of instantiating a project."""
    benchmark(Project, name="project")


def test_shot_creation(benchmark: Any) -> None:
    """Test performance of instantiating a shot."""
    project = Project(name="project")
    benchmark(Shot, name="shot", project=project)


def test_task_creation(benchmark: Any) -> None:
    """Test performance of instantiating a task."""
    project = Project(name="project")
    shot = Shot(name="shot", project=project)
    benchmark(Task, name="task", entity=shot)


def test_query_builder(benchmark: Any) -> None:
    """Test performance of query builder."""

    def _build_query() -> None:
        select(Shot).where(Shot.project.f(Project.name).eq("project"))

    benchmark(_build_query)


def _fill_session(session: Session) -> None:
    """Fill the given session with some data."""
    project = Project(name="project")
    session.add(project)
    session.commit()
    session.add(Shot(name="shot", project=project))
    session.commit()


def test_session_commit(engine: SgEngine, benchmark: Any) -> None:
    """Test performance of adding stuff to session."""

    def _do_commit() -> None:
        with Session(engine) as session:
            _fill_session(session)

    benchmark(_do_commit)


def test_session_query(engine: SgEngine, benchmark: Any) -> None:
    """Test performance of querying from session."""
    # Add stuff to session
    session = Session(engine)
    _fill_session(session)
    query = select(Shot).where(Shot.project.f(Project.name).eq("project"))
    result = benchmark(session.exec, query)
    assert len(result.all()) == 1
