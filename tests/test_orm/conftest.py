"""Configuration for pytest."""

from __future__ import annotations

import pytest

from sgchemist.engine.mock import MockEngine
from tests.classes import SgEntity


@pytest.fixture()
def engine() -> MockEngine:
    """Returns a ShotgunAPIEngine instance."""
    engine = MockEngine()
    engine.register_base(SgEntity)
    return engine
