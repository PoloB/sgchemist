"""Annotation utility for sgchemist."""

from __future__ import absolute_import
from __future__ import annotations

from typing import TYPE_CHECKING
from typing import Any
from typing import Dict
from typing import List
from typing import Tuple
from typing import Type
from typing import TypeVar

if TYPE_CHECKING:
    from sgchemist.orm import SgEntity
    from sgchemist.orm.fields import AbstractField

T = TypeVar("T")


class LazyEntityClassEval:
    """Defers the evaluation of a class name used in annotation."""

    _entity: Type[SgEntity]

    def __init__(self, class_name: str, registry: Dict[str, Type[SgEntity]]) -> None:
        """Initialize an instance.

        Args:
            class_name: the name of the class
            registry: registry where all classes are defined
        """
        self.class_name = class_name
        self.registry = registry
        self._resolved: bool = False

    def get(self) -> Type[SgEntity]:
        """Return the entity class after evaluation.

        Returns:
            SgEntityMeta: the entity class
        """
        if not self._resolved:
            self._entity = eval(self.class_name, {}, self.registry)
            self._resolved = True
        return self._entity


class LazyEntityCollectionClassEval:
    """A collection of lazy entity classes."""

    def __init__(self, lazy_entities: List[LazyEntityClassEval]) -> None:
        """Initialize an instance.

        Args:
            lazy_entities: list of lazy entity classes
        """
        self._lazy_entities = lazy_entities
        self._resolved_by_name: Dict[str, Type[SgEntity]] = {}
        self._resolved_entities: list[Type[SgEntity]] = []
        self._resolved = False

    def _fill(self) -> None:
        """Evaluates all the lazy entity classes and fill internal cache."""
        for lazy in self._lazy_entities:
            entity = lazy.get()
            self._resolved_by_name[entity.__sg_type__] = entity
        self._resolved_entities = list(self._resolved_by_name.values())
        self._resolved = True

    def get_by_type(self, entity_type: str) -> Type[SgEntity]:
        """Return the entity class for its Shotgrid type.

        Args:
            entity_type: the entity type

        Returns:
            the entity class
        """
        if not self._resolved:
            self._fill()
        return self._resolved_by_name[entity_type]

    def get_all(self) -> List[Type[SgEntity]]:
        """Return all the evaluated entity classes."""
        if not self._resolved:
            self._fill()
        return self._resolved_entities


class FieldAnnotation:
    """A well-defined field annotation."""

    __slots__ = ("_field_type", "_entities")

    def __init__(
        self, field_type: Type[AbstractField[Any]], entities: Tuple[str, ...]
    ) -> None:
        """Initialize an instance of field annotation."""
        self._field_type = field_type
        self._entities = entities

    @property
    def field_type(self) -> Type[AbstractField[Any]]:
        """Return the field type."""
        return self._field_type

    @property
    def entities(self) -> Tuple[str, ...]:
        """Return the entities."""
        return self._entities
