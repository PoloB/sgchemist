"""Tests the row object."""
from typing import Any

import pytest

from sgchemist.orm.row import SgRow


@pytest.fixture
def row() -> SgRow[Any]:
    """Returns the sample row object."""
    return SgRow(
        entity_type="entity_name",
        entity_id=123,
        success=False,
        content={},
    )


def test_row_init(row: SgRow[Any]) -> None:
    """Tests the row initialization."""
    assert row.entity_type == "entity_name"
    assert row.entity_id == 123
    assert row.success is False
    assert row.content == {}


def test_row_entity_hash(row: SgRow[Any]) -> None:
    """Tests the row entity hash."""
    assert row.entity_hash == ("entity_name", 123)


def test_row_data_is_not_settable(row: SgRow[Any]) -> None:
    """Tests the row data is not settable."""
    with pytest.raises(AttributeError):
        row.entity_type = "nope"  # type: ignore
    with pytest.raises(AttributeError):
        row.entity_id = 0  # type: ignore
    with pytest.raises(AttributeError):
        row.success = True  # type: ignore
    with pytest.raises(AttributeError):
        row.content = None  # type: ignore
