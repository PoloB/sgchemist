"""Tests for entity generation."""

from __future__ import annotations

import pathlib
from unittest import mock

import pytest

from sgchemist.schema import generate
from sgchemist.schema import parse


@pytest.fixture()
def output_script_path(tmp_path: pathlib.Path) -> str:
    """Return a temporary output script path."""
    return str(tmp_path / "models.py")


@pytest.fixture()
def cli_args(schema_paths: tuple[str, str], output_script_path: str) -> list[str]:
    """Return test cli arguments for the given schema paths and output script path."""
    return [
        "--in-schema",
        schema_paths[0],
        "--in-schema-entity",
        schema_paths[1],
        "--out",
        output_script_path,
        "--skip-field-patterns",
        ".*sg_.*",
        ".*image_.*",
        "--skip-entities",
        "AppWelcome",
        "Banner",
        "Contract",
        "--include-connections",
    ]


def test_generate_python_script_models(schema_paths: tuple[str, str]) -> None:
    """Test the python script generation."""
    entities = parse.load_entities(*schema_paths)
    # Test with standard arguments
    exec(generate.generate_python_script_models(entities), globals())  # noqa: S102
    # Test skipping entities
    exec(  # noqa: S102
        generate.generate_python_script_models(
            entities,
            skip_entities=["Asset", "Shot"],
        ),
        globals(),
    )
    # Test skipping field pattern
    exec(  # noqa: S102
        generate.generate_python_script_models(
            entities,
            skip_field_patterns=[".*sg_.*"],
        ),
        globals(),
    )
    # Test including connections
    exec(  # noqa: S102
        generate.generate_python_script_models(entities, include_connections=True),
        globals(),
    )
    # Test creating field aliases
    exec(  # noqa: S102
        generate.generate_python_script_models(entities, create_field_aliases=True),
        globals(),
    )
    # Test combination
    exec(  # noqa: S102
        generate.generate_python_script_models(
            entities,
            skip_entities=["Asset", "Shot"],
            skip_field_patterns=[".*sg_.*"],
            include_connections=True,
            create_field_aliases=True,
        ),
        globals(),
    )


def test_main(cli_args: list[str], output_script_path: str) -> None:
    """Test the main function of the module."""
    generate.main(cli_args)
    with pathlib.Path(output_script_path).open() as f:
        python_script = f.read()
    exec(python_script, globals())  # noqa: S102


def test_cli(cli_args: list[str]) -> None:
    """Test the cli function of the module."""
    cli_args = ["testProg", *cli_args]
    with mock.patch("sys.argv", cli_args):
        generate.cli()
