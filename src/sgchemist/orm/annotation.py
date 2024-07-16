"""Annotation utility for sgchemist."""

from __future__ import absolute_import
from __future__ import annotations

from typing import Any

from .fields import AbstractField


class FieldAnnotation:
    """A well-defined field annotation."""

    __slots__ = ("_field_type", "_entities")

    def __init__(self, field_type: type[Any], entities: tuple[str, ...]) -> None:
        """Initialize an instance of field annotation."""
        self._field_type = field_type
        self._entities = entities

    @property
    def field_type(self) -> type[Any]:
        """Return the field type."""
        return self._field_type

    @property
    def entities(self) -> tuple[str, ...]:
        """Return the entities."""
        return self._entities

    def is_field(self) -> bool:
        """Return True if the annotation is a field annotation."""
        return isinstance(self._field_type, type) and issubclass(
            self._field_type, AbstractField
        )
