"""A custom engine using the REST API of Shotgrid.

This an alternative to the shotgun_api3 engine with better performance.
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from typing import Any
from typing import TypedDict
from typing import TypeVar

import requests

from sgchemist.error import SgEngineError
from sgchemist.orm import SgBaseEntity
from sgchemist.orm import field_info
from sgchemist.orm.constant import BatchRequestType
from sgchemist.orm.engine import SgEngine
from sgchemist.orm.queryop import SgFieldCondition
from sgchemist.orm.queryop import SgFilterOperation
from sgchemist.orm.queryop import SgNullCondition
from sgchemist.orm.queryop import SgSerializable

if TYPE_CHECKING:
    from sgchemist.orm.fields import AbstractField
    from sgchemist.orm.query import SgBatchQuery
    from sgchemist.orm.query import SgFindQueryData
    from sgchemist.orm.typing_alias import SerializedEntity

T = TypeVar("T", bound=SgBaseEntity)


class RestEngineError(SgEngineError):
    """Generic errors for rest engine."""


class FindQueryRestEngineError(RestEngineError):
    """Raises when an error occurs during find queries."""


class BatchQueryRestEngineError(RestEngineError):
    """Raises when an error occurs during find queries."""


def _serialize_entity(entity: SgBaseEntity) -> SerializedEntity:
    """Serialize the given sgchemist entity to shotgun-api3 entity.

    Args:
        entity: sgchemist entity to serialize

    Returns:
        serialized entity
    """
    assert entity.id is not None
    return {"id": entity.id, "type": entity.__sg_type__}


def _serialize_condition(
    condition: SgFieldCondition,
) -> dict[str, Any]:
    """Serialize the given sgchemist condition to shotgun-api3 filter condition.

    Args:
        condition: sgchemist condition to serialize

    Returns:
        serialized condition
    """
    right = condition.op.serialize()
    if isinstance(right, SgBaseEntity):
        right = _serialize_entity(right)
    return {
        "path": field_info.get_name(condition.field),
        "relation": condition.op.__sg_op__,
        "values": right if isinstance(right, list) else [right],
    }


def _serialize_filter(
    sg_object: SgSerializable | SgBaseEntity,
) -> SerializedEntity | _SerializedOperator | list[Any] | dict[str, Any]:
    """Returns filters for shotgun-api3 from the given sgchemist object.

    Args:
        sg_object: sgchemist object to serialize

    Returns:
        list of serialized objects
    """
    if isinstance(sg_object, SgNullCondition):
        return {"logical_operator": "and", "conditions": []}
    if isinstance(sg_object, SgFieldCondition):
        return {"logical_operator": "and", "conditions": [_serialize_object(sg_object)]}
    return _serialize_object(sg_object)


def _serialize_object(
    sg_object: SgSerializable | SgBaseEntity,
) -> SerializedEntity | _SerializedOperator | list[Any] | dict[str, Any]:
    """Serialize the given sgchemist object to shotgun-api3 object.

    Args:
        sg_object: sgchemist object to serialize

    Returns:
        serialized object
    """
    if isinstance(sg_object, SgFieldCondition):
        return _serialize_condition(sg_object)
    if isinstance(sg_object, SgBaseEntity):
        return _serialize_entity(sg_object)
    if isinstance(sg_object, SgFilterOperation):
        return _serialize_operation(sg_object)

    error = f"Cannot serialize object of type {type(sg_object)}"  # pragma: no cover
    raise AssertionError(error)  # pragma: no cover


class _SerializedOperator(TypedDict):
    """Defines a serialized operator dict."""

    logical_operator: str
    conditions: list[Any]


def _serialize_operation(
    filter_operator: SgFilterOperation,
) -> _SerializedOperator:
    """Serialize the given sgchemist operation to shotgun-api3 logical operator.

    Args:
        filter_operator: sgchemist operator to serialize

    Returns:
        serialized operator
    """
    return {
        "logical_operator": filter_operator.operator.value,
        "conditions": [_serialize_object(obj) for obj in filter_operator.sg_objects],
    }


def _serialize_entity_for_batch(
    entity: SgBaseEntity,
    fields: list[AbstractField[Any]],
) -> list[dict[str, Any]]:
    """Serialize the given sgchemist entity for batching."""
    model_data = []
    for field in fields:
        value = entity.__state__.get_value(field)
        if isinstance(value, SgBaseEntity):
            value = {
                "type": value.__sg_type__,
                "id": value.id,
            }
        model_data.append(
            {
                "field_name": field_info.get_name(field),
                "value": value,
            },
        )
    return model_data


class RestEngine(SgEngine):
    """A custom engine using the REST API of Shotgrid."""

    def __init__(
        self,
        url: str,
        script_name: str,
        script_key: str,
        entities_per_page: int = 500,
        timeout: int = 60,
    ) -> None:
        """Initialize the mock engine."""
        self._url = url.removesuffix("/")
        self._read_url = f"{self._url}/api3/json"
        self._read_headers = {
            "connection": "keep-alive",
            "user-agent": "shotgun-json (3.5.1); Python 3.11 (Linux); "
            "ssl OpenSSL 3.0.13 30 Jan 2024 (validate)",
        }
        self._timeout = timeout
        self._script_name = script_name
        self._script_key = script_key
        self._entities_per_page = entities_per_page
        self._session = requests.Session()

    def _build_payload(
        self,
        method_name: str,
        params: dict[str, Any] | list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Build a payload for requesting Shotgrid."""
        return {
            "method_name": method_name,
            "params": [
                {
                    "script_name": self._script_name,
                    "script_key": self._script_key,
                },
                params,
            ],
        }

    def find(self, query: SgFindQueryData[type[T]]) -> list[dict[str, Any]]:
        """Get the result of the given query using the REST API."""
        limit = query.limit
        if query.page:
            limit = self._entities_per_page
        current_page = query.page or 1
        paging = {
            "current_page": current_page,
            "entities_per_page": self._entities_per_page,
        }
        params = {
            "type": query.entity.__sg_type__,
            "return_fields": [
                field_info.get_name(field)
                for field in query.fields + query.loading_fields
            ],
            "filters": _serialize_filter(query.condition),
            "return_only": "active",
            "paging": paging,
            "api_return_image_urls": True,
            "return_paging_info_without_counts": True,
        }
        payload = self._build_payload("read", params)

        all_records = []
        # Make the request
        result = self._session.post(
            self._read_url,
            json=payload,
            headers=self._read_headers,
            timeout=self._timeout,
        )
        result.raise_for_status()
        json_result = result.json()["results"]

        if json_result.get("exception"):
            raise FindQueryRestEngineError(json_result["message"])

        entities = json_result.get("entities")

        while entities:
            all_records.extend(json_result["entities"])

            if limit and len(all_records) >= limit:
                all_records = all_records[:limit]
                break

            if not json_result["paging_info"]["has_next_page"]:
                break

            paging["current_page"] += 1

            result = self._session.post(
                self._read_url,
                json=payload,
                headers=self._read_headers,
                timeout=self._timeout,
            )
            result.raise_for_status()
            json_result = result.json()["results"]

            if json_result.get("exception"):
                raise FindQueryRestEngineError(json_result["message"])

            entities = json_result.get("entities")

        # Reorganize the row contents
        for field in query.loading_fields:
            key = field_info.get_name(field)
            column_name, _, target_key = key.split(".")
            for row in all_records:
                row[column_name][target_key] = row.pop(key)

        return all_records

    def batch(
        self,
        batch_queries: list[SgBatchQuery],
    ) -> list[tuple[bool, dict[str, Any]]]:
        """Execute the batch queries and return the results."""
        batch_payload_by_query = {}
        for query in batch_queries:
            entity = query.entity
            request_params: dict[str, Any] = {
                "request_type": query.request_type.value,
                "type": entity.__sg_type__,
            }
            if query.request_type == BatchRequestType.DELETE:
                request_params["id"] = entity.id
                batch_payload_by_query[query] = request_params
                continue

            state = entity.__state__
            request_params["fields"] = _serialize_entity_for_batch(
                entity,
                state.modified_fields,
            )

            if query.request_type == BatchRequestType.UPDATE:
                request_params["id"] = entity.id

            batch_payload_by_query[query] = request_params

        if not batch_payload_by_query:
            return []

        request_payload = self._build_payload(
            "batch",
            list(batch_payload_by_query.values()),
        )
        response = self._session.post(
            self._read_url,
            json=request_payload,
            headers=self._read_headers,
            timeout=self._timeout,
        )
        response.raise_for_status()
        json_result = response.json()

        if json_result.get("exception"):
            raise BatchQueryRestEngineError(json_result["message"])

        parsed_records = []
        results: list[dict[str, Any] | bool] = json_result["results"]
        for k, query in enumerate(batch_payload_by_query):
            result = results[k]
            if query.request_type == BatchRequestType.DELETE:
                assert isinstance(result, bool)
                success: bool = result
                row: dict[str, Any] = {}
            else:
                success = True
                assert isinstance(result, dict)
                row = result
            parsed_records.append((success, row))

        return parsed_records
