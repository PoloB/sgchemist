"""Tests for the rest engine."""

from __future__ import annotations

import functools
import json
import random
import string
from typing import TYPE_CHECKING
from typing import Any

import pytest
import requests_mock

from sgchemist.engine.rest import RestEngine
from sgchemist.orm.constant import BatchRequestType
from sgchemist.orm.entity import SgBaseEntity
from sgchemist.orm.query import SgBatchQuery
from sgchemist.orm.query import SgFindQueryData
from sgchemist.orm.session import Session
from tests.classes import Asset
from tests.classes import Project
from tests.classes import Shot
from tests.classes import Task

if TYPE_CHECKING:
    from sgchemist.orm.engine import SgEngine

TEST_URL = "https://sgchemist.shotgrid.autodesk.com"
TEST_URL_POST = f"{TEST_URL}/api3/json"
ENTITIES_PER_PAGE = 10


@pytest.fixture
def engine() -> RestEngine:
    """Returns a test engine instance."""
    return RestEngine(
        TEST_URL,
        script_name="script_name",
        script_key="123456789",
        entities_per_page=ENTITIES_PER_PAGE,
    )


def _build_result(
    entities: list[dict[str, Any]],
    has_next_page: bool = False,  # noqa: FBT001, FBT002
) -> dict[str, Any]:
    return {
        "results": {
            "entities": entities,
            "paging_info": {
                "has_next_page": has_next_page,
            },
        },
    }


def _build_random_string(character_count: int = 10) -> str:
    return "".join(
        random.choice(string.ascii_lowercase)  # noqa: S311
        for _ in range(character_count)
    )


def _build_random_entity(with_sub_entities: bool = True) -> dict[str, Any]:  # noqa: FBT001, FBT002
    entity = {
        "type": _build_random_string(),
        "id": random.randint(1, 100),  # noqa: S311
    }
    if with_sub_entities:
        for _ in range(random.randint(0, 2)):  # noqa: S311
            entity[_build_random_string()] = _build_random_entity(
                with_sub_entities=False,
            )
    return entity


def _build_random_entities(count: int) -> list[dict[str, Any]]:
    return [_build_random_entity() for _ in range(count)]


def _mock_response(entities, request, context) -> dict[str, Any]:
    # Get the page requested by the query
    request = json.loads(request.text)["params"][1]
    page = request["paging"]["current_page"]
    entities_per_page = request["paging"]["entities_per_page"]
    last_index = page * entities_per_page
    page_entities = entities[last_index - entities_per_page : last_index]
    has_next_page = last_index < (len(entities) - 1)
    return _build_result(page_entities, has_next_page)


@pytest.mark.parametrize(
    "entities",
    [
        _build_random_entities(ENTITIES_PER_PAGE),
        _build_random_entities(ENTITIES_PER_PAGE * 2),
    ],
)
def test_engine_find(entities: list[dict[str, Any]], engine: RestEngine) -> None:
    """Test find queries on a filled engine."""
    find_query_state = SgFindQueryData(Asset, (Asset.id, Asset.name, Asset.project))

    with requests_mock.Mocker() as mock:
        mock.post(
            TEST_URL_POST,
            json=functools.partial(_mock_response, entities),
        )
        rows = engine.find(find_query_state)
    assert rows == entities


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
