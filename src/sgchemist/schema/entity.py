"""Low level abstract of the schema structure provided by Shotgrid."""

from __future__ import annotations

import dataclasses
import pickle
from typing import Any
from typing import Dict
from typing import Generic
from typing import TypeVar

from typing_extensions import TypedDict

T = TypeVar("T")


class ValueSchemaInfo(TypedDict, Generic[T], total=True):
    """A value schema generic dict."""
    value: T
    editable: bool


class FieldSchemaInfo(TypedDict, Generic[T], total=True):
    """A field schema generic dict."""
    name: ValueSchemaInfo[str]
    entity_type: ValueSchemaInfo[str]
    data_type: ValueSchemaInfo[str]
    properties: Dict[str, ValueSchemaInfo[Any]]


@dataclasses.dataclass
class ValueSchema(Generic[T]):
    """Defines a value within a schema."""

    value: T
    editable: bool

    @classmethod
    def from_schema(cls, schema: ValueSchemaInfo[T]) -> ValueSchema[T]:
        """Instantiate a value from a schema dictionary.

        Args:
            schema (ValueSchemaInfo): A schema dictionary.

        Returns:
            Self: A value schema instance.
        """
        return cls(**schema)


@dataclasses.dataclass
class FieldSchema:
    """Defines a field within a schema."""

    field_name: str
    name: ValueSchema[str]
    entity_type: ValueSchema[str]
    data_type: ValueSchema[str]
    properties: dict[str, ValueSchema[Any]]

    @classmethod
    def from_schema(cls, field_name: str, schema: FieldSchemaInfo[Any]) -> FieldSchema:
        """Instantiate a field from a schema dictionary.

        Args:
            field_name (str): The name of the field.
            schema (FieldSchema): A schema dictionary.

        Returns:
            Self: A field schema instance.
        """
        return cls(
            field_name=field_name,
            name=ValueSchema.from_schema(schema["name"]),
            entity_type=ValueSchema.from_schema(schema["entity_type"]),
            data_type=ValueSchema.from_schema(schema["data_type"]),
            properties={
                key: ValueSchema.from_schema(prop)
                for key, prop in schema["properties"].items()
            },
        )


@dataclasses.dataclass
class EntitySchema(object):
    """Defines an entity within a schema."""

    entity_type: str
    entity_name: ValueSchema[str]
    visible: ValueSchema[bool]
    fields: list[FieldSchema]


def load_entities(schema_path: str, schema_entity_path: str) -> list[EntitySchema]:
    """Load entities from a schema file and schema entity file.

    Schema files can be generated using shotgun-api3 mockgun using the following script:
    ```python
    from shotgun_api3 import Shotgun
    from shotgun_api3.lib import mockgun

    sg = Shotgun("https://url.shotgrid.autodesk.com", script_name="api", api_key="abc")
    mockgun.generate_schema(sg, "schema", "entity_schema")

    ```

    Args:
        schema_path (str): The path to the schema file.
        schema_entity_path (str): The path to the entity file.

    Returns:
        list[EntitySchema]: A list of schema entities.
    """
    entities = []

    # Load all the entity data
    field_data = pickle.load(open(schema_path, "rb"))

    # Create the entities first
    entity_data = pickle.load(open(schema_entity_path, "rb"))
    for entity_type, schema in entity_data.items():
        name_schema = ValueSchema[str].from_schema(schema["name"])
        visible_schema = ValueSchema[bool].from_schema(schema["visible"])
        entity = EntitySchema(entity_type, name_schema, visible_schema, [])

        # Add the fields
        for field_name, field_schema in field_data[entity_type].items():
            entity.fields.append(FieldSchema.from_schema(field_name, field_schema))
        entities.append(entity)

    return entities
