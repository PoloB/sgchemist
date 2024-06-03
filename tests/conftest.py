"""Configuration for pytest."""

import os
from typing import Tuple

import pytest
from shotgun_api3.lib import mockgun

from sgchemist.orm import ShotgunAPIEngine


@pytest.fixture(scope="session")
def schema_paths() -> Tuple[str, str]:
    """Returns the test schema paths."""
    current_directory = os.path.dirname(os.path.abspath(__file__))
    return (
        os.path.join(current_directory, "ressources/test_schema"),
        os.path.join(current_directory, "ressources/test_schema_entity"),
    )


@pytest.fixture
def engine(schema_paths) -> ShotgunAPIEngine:
    """Returns a ShotgunAPIEngine instance."""
    # Create a mockgun Shotgun instance
    mockgun.Shotgun.set_schema_paths(*schema_paths)
    sg = mockgun.Shotgun(
        "https://mysite.shotgunstudio.com", script_name="xyz", api_key="abc"
    )

    # We need to mock the find method of mockgun which does not supports all the
    # arguments of the original shotgrid object.
    def patch_find(func):
        def mock_find(*args, **kwargs):
            kwargs.pop("include_archived_projects")
            kwargs.pop("additional_filter_presets")
            return func(*args, **kwargs)

        return mock_find

    sg.find = patch_find(sg.find)  # type: ignore
    return ShotgunAPIEngine(sg)
