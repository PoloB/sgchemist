"""Script generating an entity classes from a given set of schema json files."""

from __future__ import annotations

import contextlib
import logging
import re
import sys
from argparse import ArgumentParser
from argparse import RawTextHelpFormatter
from pathlib import Path
from typing import TYPE_CHECKING
from typing import Any

from sgchemist.orm.fields import AbstractEntityField
from sgchemist.orm.fields import EntityField
from sgchemist.orm.fields import field_by_sg_type

from .parse import EntitySchema
from .parse import FieldSchema
from .parse import ValueSchema
from .parse import load_entities

if TYPE_CHECKING:
    from collections.abc import Iterable

logger = logging.getLogger("model_generate")


def _generate_python_script_field(
    entity_schema: EntitySchema,
    field_schema: FieldSchema,
    skip_entities: list[str],
    create_aliases: bool = False,  # noqa: FBT001, FBT002
) -> list[str]:
    """Generate python script for a given field for the given entity schema.

    Args:
        entity_schema: entity schema the field belongs to
        field_schema: field schema to generate script for
        skip_entities: list of entities to skip
        create_aliases: create aliases for multi target fields

    Returns:
        list of generated python scripts, one for each field.
    """
    field_args = []
    field_data_type = field_schema.data_type.value
    field_type = field_by_sg_type.get(field_data_type)
    pretty_field_name = f"{entity_schema.entity_name.value}.{field_schema.field_name}"

    if field_type is None:
        logger.warning(
            "Cannot generate python field for '%s': type %s is not supported yet",
            pretty_field_name,
            field_data_type,
        )
        return []

    valid_types = field_schema.properties.get(
        "valid_types",
        ValueSchema([], False),  # noqa: FBT003
    ).value

    if issubclass(field_type, AbstractEntityField):
        remaining_types = set(valid_types).difference(set(skip_entities))
        if len(remaining_types) == 0:
            logger.warning(
                "Field '%s' will not be generated: its target(s) %s were skipped.",
                pretty_field_name,
                skip_entities,
            )
            return []
        valid_types = sorted(remaining_types)
    annotation = f"{field_type.__name__}"

    if valid_types:
        annotation += f"[{' | '.join(valid_types)}]"

    field_args.append(f'name="{field_schema.field_name}"')
    default = field_schema.properties.get(
        "default_value",
        ValueSchema(None, False),  # noqa: FBT003
    ).value

    if default is not None:
        default_str = f'"{default}"' if isinstance(default, str) else f"{default}"
        field_args.append(f"default_value={default_str}")
    fields_instructions = [
        f"{field_schema.field_name}: {annotation} = "
        f"{field_type.__name__}({', '.join(field_args)})",
    ]

    # Append alias relationship
    if create_aliases:
        fields_instructions += [
            f"{field_schema.field_name}_{valid_type.lower()}:"
            f"{EntityField.__name__}[{valid_type}] = "
            f"alias({field_schema.field_name})"
            for valid_type in valid_types
        ]

    return fields_instructions


def _generate_entity_script_from_schema(schema: EntitySchema) -> str:
    """Generates the script for the given entity schema.

    Args:
        schema: entity schema to generate script for

    Returns:
        str: the python script creating the entity class
    """
    model_def = f"class {schema.entity_type}(SgEntity):\n"
    model_def += f'\t__sg_type__ = "{schema.entity_type}"'
    return model_def


def _generate_header(
    entity_schemas: Iterable[EntitySchema],
    create_field_aliases: bool = False,  # noqa: FBT001, FBT002
) -> str:
    # Create the python header
    header = """
\"\"\"
Models generated automatically from schema definitions
Any changes made to this file may be lost.
\"\"\"

"""

    # Add the minimal required imports
    imports = [
        "from __future__ import annotations",
        "from sgchemist.orm import SgBaseEntity",
    ]
    if create_field_aliases:
        imports.append(
            "from sgchemist.orm import alias",
        )
    # Get all the field type used in the schemas to add the import
    field_types = set()

    for entity_schema in entity_schemas:
        for field in entity_schema.fields:
            field_types.add(field.data_type.value)

    for field_type in sorted(field_types):
        with contextlib.suppress(KeyError):
            imports.append(
                f"from sgchemist.orm import {field_by_sg_type[field_type].__name__}",
            )

    # Add all the imports to the header
    header += "\n".join(sorted(imports))
    header += "\n\n\n"
    return header


def generate_python_script_models(
    entity_schemas: Iterable[EntitySchema],
    skip_entities: list[str] | None = None,
    skip_field_patterns: list[str] | None = None,
    include_connections: bool = False,  # noqa: FBT001, FBT002
    create_field_aliases: bool = False,  # noqa: FBT001, FBT002
) -> str:
    """Generate python scripts for the given entity schemas.

    Args:
        entity_schemas (list[schema_entity.EntitySchema]): list of entity schemas to
            generate classes for
        skip_entities: list of entities to skip
        skip_field_patterns: list of field patterns to skip
        include_connections: create the connection classes
        create_field_aliases: create aliases for multi target fields

    Returns:
        str: the python script creating the entity classes
    """
    if not skip_field_patterns:
        skip_field_patterns = []

    if not skip_entities:
        skip_entities = []

    entity_scripts = [
        'class SgEntity(SgBaseEntity):\n\t"""Base class for all the entities."""',
    ]
    # Start generating the script for each entity
    for entity_schema in sorted(entity_schemas, key=lambda x: x.entity_name.value):
        if entity_schema.entity_type in skip_entities:
            continue

        if entity_schema.entity_type.endswith("Connection") and not include_connections:
            continue

        entity_script = _generate_entity_script_from_schema(entity_schema)
        entity_script += "\n\n"
        # Add a fields
        field_defs = []

        for field in sorted(entity_schema.fields, key=lambda x: x.field_name):
            if field.field_name == "id":
                continue

            field_pattern_test = f"{entity_schema.entity_type}.{field.field_name}"

            if any(
                re.match(pattern, field_pattern_test) for pattern in skip_field_patterns
            ):
                continue
            fields = _generate_python_script_field(
                entity_schema,
                field,
                skip_entities,
                create_field_aliases,
            )
            field_defs += [f"\t{field_def}" for field_def in fields]

        entity_script += "\n".join(field_defs)
        entity_scripts.append(entity_script)

    # Finalize the script
    header = _generate_header(entity_schemas, create_field_aliases)
    python_script = header + "\n\n\n".join(entity_scripts) + "\n"
    return python_script.replace("\t", "    ")


def get_cli_parser() -> ArgumentParser:
    """Creates the argument parser for the entity generation script.

    Returns:
        ArgumentParser: the argument parser for the entity generation script
    """
    parser = ArgumentParser(
        add_help=True,
        description="""
Generate a python script with all the sgchemist entities from the given schema files.
To generate these schema files, you can use the following python script:

###################################################################################

from shotgun_api3 import Shotgun
from shotgun_api3.lib import mockgun

sg = Shotgun('https://url.shotgrid.autodesk.com', script_name='api', api_key='abc')
mockgun.generate_schema(sg, 'schema', 'entity_schema')

###################################################################################

You can then pass these files to sg2python to create the python script.
""",
        formatter_class=RawTextHelpFormatter,
    )
    parser.add_argument(
        "--in-schema",
        help="path where to load the general schema",
        required=True,
        type=str,
    )
    parser.add_argument(
        "--in-schema-entity",
        help="path where to load the entity schema",
        required=True,
        type=str,
    )
    parser.add_argument(
        "--out",
        help="path where to save the python script for script models",
        required=False,
        default="models.py",
        type=str,
    )
    parser.add_argument(
        "--skip-field-patterns",
        type=str,
        nargs="+",
        help="skip the field if <EntityType>.<field_name> matches any of the given "
        "regex",
    )
    parser.add_argument(
        "--skip-entities",
        type=str,
        nargs="+",
        help="skip the given entities (and any field referencing it)",
        default=("AppWelcome", "Banner", "Contract"),
    )
    parser.add_argument(
        "--include-connections",
        action="store_true",
        default=False,
        help="do not generate classes for the connection tables. "
        "Shotgrid uses these tables to create the many to many relationships. "
        "Because sgchemist can create these relationships without an intermediate "
        "class, this is disabled by default.",
    )
    return parser


def main(argv: list[Any]) -> None:
    """Runs the command line from the given arguments.

    Args:
        argv: list of arguments
    """
    parser = get_cli_parser()
    args = parser.parse_args(argv)
    # Load the entities
    entities = load_entities(args.in_schema, args.in_schema_entity)
    python_script = generate_python_script_models(
        entities,
        skip_entities=args.skip_entities,
        skip_field_patterns=args.skip_field_patterns,
        include_connections=args.include_connections,
    )
    with Path(args.out).open("w") as f:
        f.write(python_script)


def cli() -> None:
    """Entry point for the console scripts."""
    main(sys.argv[1:])
