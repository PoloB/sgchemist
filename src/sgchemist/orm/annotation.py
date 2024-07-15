"""Annotation utility for sgchemist."""

from __future__ import absolute_import
from __future__ import annotations

from typing import TYPE_CHECKING
from typing import Any

from .fields import AbstractField

if TYPE_CHECKING:
    from .entity import SgBaseEntity
    from .entity import SgEntityMeta


class LazyEntityClassEval:
    """Defers the evaluation of a class name used in annotation."""

    _entity: type[SgBaseEntity]

    def __init__(
        self, class_: str | type[SgBaseEntity], registry: dict[str, SgEntityMeta]
    ) -> None:
        """Initialize an instance.

        Args:
            class_: the name of the class
            registry: registry where all classes are defined
        """
        self._resolved: bool = False
        if not isinstance(class_, str):
            self.class_name = class_.__name__
            self._entity = class_
            self._resolved = True
        else:
            self.class_name = class_
        self.registry = registry

    def get(self) -> type[SgBaseEntity]:
        """Return the entity class after evaluation.

        Returns:
            the entity class
        """
        if not self._resolved:
            self._entity = eval(self.class_name, {}, self.registry)
            self._resolved = True
        return self._entity


class LazyEntityCollectionClassEval:
    """A collection of lazy entity classes."""

    def __init__(self, lazy_entities: list[LazyEntityClassEval]) -> None:
        """Initialize an instance.

        Args:
            lazy_entities: list of lazy entity classes
        """
        self.lazy_entities = lazy_entities
        self._resolved_by_name: dict[str, type[SgBaseEntity]] = {}
        self._resolved_entities: list[type[SgBaseEntity]] = []
        self._resolved = False

    def _fill(self) -> None:
        """Evaluates all the lazy entity classes and fill internal cache."""
        for lazy in self.lazy_entities:
            entity = lazy.get()
            self._resolved_by_name[entity.__sg_type__] = entity
        self._resolved_entities = list(self._resolved_by_name.values())
        self._resolved = True

    def get_by_type(self, entity_type: str) -> type[SgBaseEntity]:
        """Return the entity class for its Shotgrid type.

        Args:
            entity_type: the entity type

        Returns:
            the entity class
        """
        if not self._resolved:
            self._fill()
        return self._resolved_by_name[entity_type]

    def get_all(self) -> list[type[SgBaseEntity]]:
        """Return all the evaluated entity classes."""
        if not self._resolved:
            self._fill()
        return self._resolved_entities


class FieldAnnotation:
    """A well-defined field annotation."""

    __slots__ = ("_field_type", "_entities")

    def __init__(
        self, field_type: type[Any], entities: tuple[str | SgEntityMeta, ...]
    ) -> None:
        """Initialize an instance of field annotation."""
        self._field_type = field_type
        self._entities = entities

    @property
    def field_type(self) -> type[Any]:
        """Return the field type."""
        return self._field_type

    @property
    def entities(self) -> tuple[str | SgEntityMeta, ...]:
        """Return the entities."""
        return self._entities

    def is_field(self) -> bool:
        """Return True if the annotation is a field annotation."""
        return isinstance(self._field_type, type) and issubclass(
            self._field_type, AbstractField
        )
