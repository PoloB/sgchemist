"""A custom engine using the REST API of Shotgrid.

This an alternative to the shotgun_api3 engine with better performance.
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from typing import Any

from sgchemist.orm.engine import SgEngine
from sgchemist.orm.engine import T

if TYPE_CHECKING:
    from sgchemist.orm.query import SgBatchQuery
    from sgchemist.orm.query import SgFindQueryData


class RestEngine(SgEngine):
    """A custom engine using the REST API of Shotgrid."""

    def find(self, query: SgFindQueryData[type[T]]) -> list[dict[str, Any]]:
        """Get the result of the given query using the REST API."""

    def batch(
        self,
        batch_queries: list[SgBatchQuery],
    ) -> list[tuple[bool, dict[str, Any]]]:
        """Execute the batch queries and return the results."""
