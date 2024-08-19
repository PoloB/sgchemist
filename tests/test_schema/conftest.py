"""Configuration for pytest."""

from __future__ import annotations

import os

import pytest


@pytest.fixture(scope="session")
def schema_paths() -> tuple[str, str]:
    """Returns the test schema paths."""
    current_directory = os.path.dirname(os.path.abspath(__file__))
    return (
        os.path.join(current_directory, "ressources/test_schema"),
        os.path.join(current_directory, "ressources/test_schema_entity"),
    )
