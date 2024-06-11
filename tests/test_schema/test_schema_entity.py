"""Tests for entity schema."""

from sgchemist.schema.parse import FieldSchema
from sgchemist.schema.parse import ValueSchema
from sgchemist.schema.parse import load_entities


def test_value_schema():
    """Tests the ValueSchema class."""
    value_schema = ValueSchema.from_schema({"value": "test", "editable": True})
    assert value_schema.value == "test"
    assert value_schema.editable is True


def test_field_schema():
    """Tests the FieldSchema class."""
    field_schema = FieldSchema.from_schema(
        "field",
        {
            "name": {"value": "test", "editable": True},
            "entity_type": {"value": "test", "editable": True},
            "data_type": {"value": "text", "editable": True},
            "properties": {"prop": {"value": "test", "editable": True}},
        },
    )
    assert field_schema.field_name == "field"
    assert field_schema.entity_type.value == "test"
    assert field_schema.entity_type.editable is True
    assert field_schema.data_type.value == "text"
    assert field_schema.data_type.editable is True
    assert field_schema.properties["prop"].value == "test"
    assert field_schema.properties["prop"].editable is True


def test_load_entities(schema_paths):
    """Tests the load_entities function."""
    load_entities(*schema_paths)
