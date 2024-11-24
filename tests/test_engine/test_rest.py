"""Tests for the rest engine."""

from __future__ import annotations

import functools
import json
import random
from typing import TYPE_CHECKING
from typing import Any
from typing import TypeVar

import pytest
import requests_mock

from sgchemist.engine import rest
from sgchemist.orm import SgBaseEntity
from sgchemist.orm import field_info
from sgchemist.orm import select
from sgchemist.orm.query import SgFindQueryData
from tests.classes import Asset
from tests.classes import Project
from tests.classes import SgEntity
from tests.classes import Task

if TYPE_CHECKING:
    from requests_mock.request import _RequestObjectProxy
    from requests_mock.response import _Context

    from sgchemist.orm.fields import AbstractField


TEST_URL = "https://sgchemist.shotgrid.autodesk.com"
TEST_URL_POST = f"{TEST_URL}/api3/json"
ENTITIES_PER_PAGE = 10


def _build_random_database(
    base_entity: type[SgBaseEntity],
    count_per_entity: int,
    connection_ratio: float,
) -> dict[str, list[SgBaseEntity]]:
    """Build a random database with the entities in the given base entity."""
    assert 0.0 <= connection_ratio <= 1.0
    store: dict[str, list[SgBaseEntity]] = {}
    # Start by building all the independent entities
    for entity_cls in base_entity.__registry__.values():
        store[entity_cls.__sg_type__] = [
            entity_cls(id=k) for k in range(count_per_entity)
        ]

    # Create random links between all these entities
    all_entities = [entity for entities in store.values() for entity in entities]
    for entity in all_entities:
        for entity_field in entity.__fields__:
            if not entity_field.__info__["is_relationship"]:
                continue

            entity_types = field_info.get_types(entity_field)
            all_entities = [
                entity
                for entity_type in entity_types
                for entity in store[entity_type.__sg_type__]
            ]

            if entity_field.__info__["is_list"]:
                choice_entities = random.sample(
                    all_entities,
                    random.randint(1, int(count_per_entity * connection_ratio)),  # noqa: S311
                )
                entity.__state__.set_value(entity_field, choice_entities)
            else:
                choice_entity = random.choice(all_entities)  # noqa: S311
                entity.__state__.set_value(entity_field, choice_entity)

    return store


T_ent = TypeVar("T_ent", bound=SgBaseEntity)


def _serialize_entity_like_sg(
    entity: T_ent,
    fields: tuple[AbstractField[Any], ...] | None = None,
) -> dict[str, Any]:
    if fields is None:
        fields = ()
    entity_data = {"id": entity.id, "type": entity.__sg_type__}
    for field in fields:
        field_value = entity.get_value(field)
        field_value = field_info.cast_value_over(
            field.__info__,
            _serialize_entity_like_sg,
            field_value,
        )
        entity_data[field_info.get_name(field)] = field_value

    return entity_data


@pytest.fixture(scope="module")
def db() -> dict[str, list[SgBaseEntity]]:
    """Return a test database."""
    return _build_random_database(SgEntity, ENTITIES_PER_PAGE * 2, 0.1)


@pytest.fixture
def engine() -> rest.RestEngine:
    """Returns a test engine instance."""
    return rest.RestEngine(
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


def _build_error() -> dict[str, Any]:
    return {
        "results": {
            "exception": "exception",
            "message": "ERROR",
        },
    }


def _mock_response(
    test_db: dict[str, list[SgBaseEntity]],
    query: SgFindQueryData[Any],
    request: _RequestObjectProxy,
    _context: _Context,
) -> dict[str, Any]:
    # Get the page requested by the query
    entities = test_db[query.entity.__sg_type__]
    # Filter the entities
    filtered_entities = [e for e in entities if query.condition.matches(e)]
    request = json.loads(request.text)["params"][1]
    page = request["paging"]["current_page"]
    entities_per_page = request["paging"]["entities_per_page"]
    last_index = page * entities_per_page
    page_entities = filtered_entities[last_index - entities_per_page : last_index]
    fields = query.fields + query.loading_fields
    serialized_entities = [_serialize_entity_like_sg(e, fields) for e in page_entities]
    has_next_page = last_index < (len(entities) - 1)
    return _build_result(serialized_entities, has_next_page)


def _mock_error(
    test_db: dict[str, list[SgBaseEntity]],
    query: SgFindQueryData[Any],
    on_page: int,
    request: _RequestObjectProxy,
    _context: _Context,
) -> dict[str, Any]:
    # Get the page requested by the query
    requested_page = json.loads(request.text)["params"][1]["paging"]["current_page"]
    if requested_page != on_page:
        return _mock_response(test_db, query, request, _context)
    return _build_error()


@pytest.mark.parametrize(
    "query",
    [
        select(Asset).get_data(),
        select(Project).get_data(),
        select(Task).get_data(),
    ],
)
def test_engine_find(
    query: SgFindQueryData[Any],
    db: dict[str, list[SgBaseEntity]],
    engine: rest.RestEngine,
) -> None:
    """Test find queries on a filled engine."""
    with requests_mock.Mocker() as mock:
        mock.post(
            TEST_URL_POST,
            json=functools.partial(_mock_response, db, query),
        )
        rows = engine.find(query)
    assert rows == [
        _serialize_entity_like_sg(e, query.fields + query.loading_fields)
        for e in db[query.entity.__sg_type__]
    ]


@pytest.mark.parametrize(
    ("query", "expected_results"),
    [
        (
            select(Asset, Asset.id).where(Asset.id.eq(1)).get_data(),
            [{"type": "Asset", "id": 1}],
        ),
    ],
)
def test_engine_find_filter(
    query: SgFindQueryData[Any],
    expected_results: list[dict[str, Any]],
    db: dict[str, list[SgBaseEntity]],
    engine: rest.RestEngine,
) -> None:
    """Test find queries on a filled engine."""
    with requests_mock.Mocker() as mock:
        mock.post(
            TEST_URL_POST,
            json=functools.partial(_mock_response, db, query),
        )
        rows = engine.find(query)
    assert rows == expected_results


@pytest.mark.parametrize(
    ("query", "indexes"),
    [
        (select(Asset).page(1).get_data(), [0, ENTITIES_PER_PAGE]),
        (select(Asset).page(2).get_data(), [ENTITIES_PER_PAGE, ENTITIES_PER_PAGE * 2]),
    ],
)
def test_engine_find_page(
    query: SgFindQueryData[Any],
    indexes: tuple[int, int],
    db: dict[str, list[SgBaseEntity]],
    engine: rest.RestEngine,
) -> None:
    """Test find queries on a filled engine."""
    with requests_mock.Mocker() as mock:
        mock.post(
            TEST_URL_POST,
            json=functools.partial(_mock_response, db, query),
        )
        rows = engine.find(query)

    entities = [
        _serialize_entity_like_sg(e, query.fields + query.loading_fields)
        for e in db[query.entity.__sg_type__][indexes[0] : indexes[1]]
    ]
    assert rows == entities


@pytest.mark.parametrize(
    "query",
    [
        select(Asset).limit(2).get_data(),
        select(Asset).limit(1).get_data(),
        select(Asset).limit(ENTITIES_PER_PAGE + 1).get_data(),
    ],
)
def test_engine_find_limit(
    query: SgFindQueryData[Any],
    db: dict[str, list[SgBaseEntity]],
    engine: rest.RestEngine,
) -> None:
    """Test find queries on a filled engine."""
    with requests_mock.Mocker() as mock:
        mock.post(
            TEST_URL_POST,
            json=functools.partial(_mock_response, db, query),
        )
        rows = engine.find(query)

    entities = [
        _serialize_entity_like_sg(e, query.fields + query.loading_fields)
        for e in db[query.entity.__sg_type__][: query.limit]
    ]
    assert rows == entities


@pytest.mark.parametrize(
    ("query", "error_on_page"),
    [
        (select(Asset).get_data(), 1),
        (select(Asset).get_data(), 2),
    ],
)
def test_engine_find_error(
    query: SgFindQueryData[Any],
    error_on_page: int,
    db: dict[str, list[SgBaseEntity]],
    engine: rest.RestEngine,
) -> None:
    """Test find queries on a filled engine."""
    find_query_state = SgFindQueryData(
        Asset,
        (Asset.id, Asset.name, Asset.project),
    )

    with requests_mock.Mocker() as mock:
        mock.post(
            TEST_URL_POST,
            json=functools.partial(_mock_error, db, query, error_on_page),
        )
        with pytest.raises(rest.FindQueryRestEngineError):
            _ = engine.find(find_query_state)
