"""Configuration for pytest."""

import os
from typing import List
from typing import Tuple

import pytest

from sgchemist.engine.mock import MockEngine

from .classes import SgEntity


@pytest.fixture(scope="session")
def schema_paths() -> Tuple[str, str]:
    """Returns the test schema paths."""
    current_directory = os.path.dirname(os.path.abspath(__file__))
    return (
        os.path.join(current_directory, "ressources/test_schema"),
        os.path.join(current_directory, "ressources/test_schema_entity"),
    )


@pytest.fixture
def engine(schema_paths: List[str]) -> MockEngine:
    """Returns a ShotgunAPIEngine instance."""
    engine = MockEngine()
    engine.register_base(SgEntity)
    return engine
