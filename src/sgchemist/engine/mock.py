"""Definition of a mock engine that can be used for testing."""
#
# from __future__ import annotations
#
# import collections
# from typing import Any
# from typing import TypeVar
#
# from sgchemist.orm import SgBaseEntity
# from sgchemist.orm.engine import SgEngine
# from sgchemist.orm.entity import SgEntityMeta
# from sgchemist.orm.query import SgBatchQuery
# from sgchemist.orm.query import SgFindQueryData
# from sgchemist.orm.query import SgSummarizeQueryData
#
# T = TypeVar("T")
#
#
# class MockEngine(SgEngine):
#     """A mock engine that can be used for testing."""
#
#     def __init__(self):
#         """Initialize the mock engine."""
#         self._entities: dict[str, SgEntityMeta] = {}
#         self._db: dict[str, dict[int, dict[str, SgBaseEntity]]] = (
#             collections.defaultdict(dict)
#         )
#
#     def register_entity(self, entity: SgEntityMeta) -> None:
#         """Register an entity."""
#         self._entities[entity.__sg_type__] = entity
#
#     def find(self, query: SgFindQueryData[type[T]]) -> list[dict[str, Any]]:
#         """Execute a find query."""
#
#     def summarize(self, query: SgSummarizeQueryData[type[T]]) -> dict[str, Any]:
#         """Execute a summary query."""
#
#     def batch(
#         self, batch_queries: list[SgBatchQuery]
#     ) -> list[tuple[bool, dict[str, Any]]]:
#         """Execute a batch query."""
#         pass
