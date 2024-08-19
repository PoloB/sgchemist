"""Configuration for pytest."""

from __future__ import annotations

from pathlib import Path

import pytest


@pytest.fixture(scope="session")
def schema_paths() -> tuple[str, str]:
    """Returns the test schema paths."""
    current_directory = Path(Path(__file__).resolve()).parent
    return (
        str(current_directory / "ressources/test_schema"),
        str(current_directory / "ressources/test_schema_entity"),
    )
