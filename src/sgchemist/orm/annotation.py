"""Annotation utility for sgchemist."""

from __future__ import absolute_import
from __future__ import annotations

import dataclasses
from typing import TYPE_CHECKING
from typing import Any
from typing import Collection
from typing import Dict
from typing import List
from typing import Optional
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
            class_name (str): the name of the class
            registry (dict[str, Type[SgEntity]]): registry where all classes are defined
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
            lazy_entities (list[LazyEntityClassEval]): list of lazy entity classes
        """
        self._lazy_entities = lazy_entities
        self._resolved_by_name: Dict[str, Type[SgEntity]] = {}

    def _fill(self) -> None:
        """Evaluates all the lazy entity classes and fill internal cache."""
        if not self._resolved_by_name:
            for lazy in self._lazy_entities:
                entity = lazy.get()
                self._resolved_by_name[entity.__sg_type__] = entity

    def get_by_type(self, entity_type: str) -> Type[SgEntity]:
        """Return the entity class for its Shotgrid type.

        Args:
            entity_type (str): the entity type

        Returns:
            Type[SgEntity]: the entity class
        """
        self._fill()
        return self._resolved_by_name[entity_type]

    def get_all(self) -> List[Type[SgEntity]]:
        """Return all the evaluated entity classes.

        Returns:
            list[Type[SgEntity]]: list of entity classes
        """
        self._fill()
        return list(self._resolved_by_name.values())


@dataclasses.dataclass
class FieldAnnotation:
    """A well-defined field annotation."""

    field_type: Type[AbstractField[Any]]
    entities: Tuple[str, ...]
    container_class: Optional[Type[Collection[Any]]]
