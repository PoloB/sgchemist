"""Definition of engines to communicate with the Shotgrid instance.

The engine is responsible for connecting to the Shotgrid instance and executing
the queries given by the Session object.

The engine ShotgunAPIEngine uses the python shotgun-api3 package.
You can reimplement a new engine using, for example, the REST api by subclassing the
SgEngine abstract class.
"""

from __future__ import annotations

import abc
from typing import Any
from typing import Type
from typing import TypeVar

from .entity import SgBaseEntity
from .query import SgBatchQuery
from .query import SgFindQueryData

T = TypeVar("T", bound=SgBaseEntity)


class SgEngine:
    """Abstract definition of an engine to communicate with Shotgun."""

    __metaclass__ = abc.ABCMeta

    @abc.abstractmethod
    def find(self, query: SgFindQueryData[Type[T]]) -> list[dict[str, Any]]:
        """Execute a find query and return the rows.

        Each row is referring to a single Shotgrid entity.
        If an entity is referencing other nested entities, these entities are also
        returned as rows.

        Args:
            query: query state to execute.
        """

    @abc.abstractmethod
    def batch(
        self, batch_queries: list[SgBatchQuery]
    ) -> list[tuple[bool, dict[str, Any]]]:
        """Execute a batch query and return the rows.

        Each row is referring to a single Shotgrid entity.
        If an entity is referencing other nested entities, these entities are also
        returned as rows.

        Args:
            batch_queries: query state to execute.
        """
