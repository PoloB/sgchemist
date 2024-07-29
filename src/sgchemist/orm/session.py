"""Definition of the session mechanism.

The Session object implements the unit of work pattern.
It keeps tracks of the pending queries and objects to commit to Shotgrid.
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from typing import Any
from typing import Generic
from typing import Iterator
from typing import TypeVar

from . import error
from . import field_info
from .constant import BatchRequestType
from .engine import SgEngine
from .entity import SgBaseEntity
from .field_info import cast_column
from .field_info import iter_entities_from_field_value
from .fields import AbstractField
from .fields import update_entity_from_value
from .query import SgBatchQuery
from .query import SgFindQuery
from .query import SgSummarizeQuery
from .typing_alias import EntityHash

T = TypeVar("T", bound=SgBaseEntity)

if TYPE_CHECKING:
    from types import TracebackType


class SgFindResult(Generic[T]):
    """Defines the result of a query to Shotgrid."""

    def __init__(self, entities: list[T]) -> None:
        """Initializes the entity result of a query to Shotgrid.

        Args:
            entities: List of entities.
        """
        self._entities = entities

    def __iter__(self) -> Iterator[T]:
        """Returns an iter of the results.

        Returns:
            Iterator of results.
        """
        return iter(self._entities)

    def __len__(self) -> int:
        """Returns the number of entities in the result.

        Returns:
            Number of entities in the result.
        """
        return len(self._entities)

    def first(self) -> T:
        """Returns the first entity in the result.

        Returns:
            First entity in the result.
        """
        return next(iter(self._entities))

    def all(self) -> list[T]:
        """Returns all entities in the result.

        Returns:
            All entities in the result.
        """
        return self._entities


class SgFieldSummary:
    """A summary of a field."""

    __slots__ = ("_field", "_result")

    def __init__(self, field: AbstractField[Any], result: Any) -> None:
        """Initializes the summary of a field."""
        self._field = field
        self._result = result

    @property
    def field(self) -> AbstractField[Any]:
        """Return the field concerned by the summary."""
        return self._field

    @property
    def result(self) -> Any:
        """Return the result of the summary."""
        return self._result


class SgSummarizeGroup:
    """A group of summaries."""

    __slots__ = ("_name", "_value", "_summaries", "_groups")

    def __init__(
        self,
        name: str,
        value: Any,
        summaries: list[SgFieldSummary],
        groups: list[SgSummarizeGroup] | None = None,
    ) -> None:
        """Initializes the group of summaries."""
        self._name = name
        self._value = value
        self._summaries = summaries
        self._groups = groups or []

    @property
    def name(self) -> str:
        """Return the name of the group."""
        return self._name

    @property
    def value(self) -> Any:
        """Return the value of the group."""
        return self._value

    @property
    def summaries(self) -> list[SgFieldSummary]:
        """Return the summaries of the group."""
        return self._summaries

    @property
    def groups(self) -> list[SgSummarizeGroup]:
        """Return the groups of the group."""
        return self._groups


class SgSummarizeResult(Generic[T]):
    """Result of a summary query."""

    __slots__ = ("_groups", "_summaries")

    def __init__(
        self, groups: list[SgSummarizeGroup], summaries: list[SgFieldSummary]
    ) -> None:
        """Initializes the result of a query to Shotgrid."""
        self._groups = groups
        self._summaries = summaries

    @property
    def groups(self) -> list[SgSummarizeGroup]:
        """Return the groups of the query."""
        return self._groups

    @property
    def summaries(self) -> list[SgFieldSummary]:
        """Return the summaries of the query."""
        return self._summaries


class Session:
    """Defines the session object."""

    def __init__(self, engine: SgEngine):
        """Initializes the session object from an engine.

        Args:
            engine: engine to use.
        """
        self._engine: SgEngine = engine
        self._pending_queries: dict[SgBaseEntity, SgBatchQuery] = {}
        self._entity_map: dict[EntityHash, SgBaseEntity] = {}

    def __enter__(self) -> Session:
        """Starts the session context.

        Returns:
            Session context.
        """
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        """Ends the session context by commiting all the pending queries."""
        self.commit()

    def __iter__(self) -> Iterator[SgBaseEntity]:
        """Returns an iterator of all the entities currently managed by the session.

        Returns:
            Iterator of entities currently managed by the session.
        """
        return iter(self._pending_queries.keys())

    @property
    def pending_queries(self) -> list[SgBatchQuery]:
        """Returns the pending queries.

        Returns:
            List of pending queries.
        """
        return list(self._pending_queries.values())

    def _get_or_create_instance(
        self,
        entity_cls: type[SgBaseEntity],
        row: dict[str, Any],
    ) -> SgBaseEntity:
        """Gets or creates the entity from the given row.

        Args:
            entity_cls: Type of the entity.
            row: Row of the entity.

        Returns:
            Instance of the entity.
        """
        # We assume this is only called when dealing with relationships
        try:
            column_value = self._entity_map[(entity_cls.__sg_type__, row["id"])]
        except KeyError:
            column_value = self._build_instance_from_row(entity_cls, row, True)
        return column_value

    def _build_instance_from_row(
        self,
        entity_cls: type[T],
        row: dict[str, Any],
        is_relationship: bool = False,
    ) -> T:
        """Builds the entity from the given row.

        Args:
            entity_cls: Type of the entity.
            row: Row of the entity.
            is_relationship (bool, optional): Whether the entity part of a relationship.

        Returns:
            Instance of the entity.
        """
        inst_data = {}
        field_mapper = entity_cls.__attr_per_field_name__

        if is_relationship:
            # Shotgrid uses a different key for the same field when queried
            # from relationship.
            # We construct a new field mapper in this case
            field_mapper = {
                field_info.get_name_in_relation(field): field_mapper[
                    field_info.get_name(field)
                ]
                for field in entity_cls.__fields__
            }

        column_value_by_attr = {
            field_mapper[column_name]: column_value
            for column_name, column_value in row.items()
            if column_name != "type"
        }
        for attr_name, column_value in column_value_by_attr.items():
            field = entity_cls.__fields_by_attr__[attr_name]
            # Cast column value
            column_value = cast_column(
                field.__info__, column_value, self._get_or_create_instance
            )
            inst_data[attr_name] = column_value

        inst = entity_cls(**inst_data)
        state = inst.__state__
        # Mark all the fields that were not queried as not available
        for attr_name in set(entity_cls.__fields_by_attr__).difference(
            set(column_value_by_attr)
        ):
            state.set_available(entity_cls.__fields_by_attr__[attr_name], False)

        inst.__state__.set_as_original()
        self._entity_map[(entity_cls.__sg_type__, row["id"])] = inst
        return inst

    def exec(self, query: SgFindQuery[type[T]]) -> SgFindResult[T]:
        """Executes the find query and returns the results.

        Args:
            query: Query to execute.

        Returns:
            Result of the query.
        """
        query_state = query.get_data()
        rows = self._engine.find(query_state)
        model = query_state.entity

        # Create the instances
        queried_models = []
        for row in rows:
            # Create the instance data
            inst = self._build_instance_from_row(model, row)
            queried_models.append(inst)

        return SgFindResult(queried_models)

    def summarize(self, query: SgSummarizeQuery[type[T]]) -> SgSummarizeResult[T]:
        """Return the result of the query."""
        query_data = query.get_data()
        result = self._engine.summarize(query_data)
        field_by_name = {
            field_info.get_name(field): field for field in query_data.entity.__fields__
        }

        def _create_summary_group(group_dict: dict[str, Any]) -> SgSummarizeGroup:
            summaries = [
                SgFieldSummary(field_by_name[field_name], value)
                for field_name, value in group["summaries"].items()
            ]
            summary_group = SgSummarizeGroup(
                group["group_name"],
                group["group_value"],
                summaries,
                list(map(_create_summary_group, group_dict.get("groups", []))),
            )
            return summary_group

        summary_groups = []
        # Unpack th results
        for group in result.get("groups", []):
            summary_groups.append(_create_summary_group(group))

        global_summaries = [
            SgFieldSummary(field_by_name[field_name], value)
            for field_name, value in result["summaries"].items()
        ]
        return SgSummarizeResult(summary_groups, global_summaries)

    @staticmethod
    def _check_relationship_commited(entity: SgBaseEntity) -> None:
        """Asserts that a relationship has been commited.

        Raises:
            error.SgRelationshipNotCommitedError: the entity is not commited.
        """
        state = entity.__state__
        if not state.is_commited() or state.is_modified():
            raise error.SgRelationshipNotCommitedError(
                f"Cannot add relation {entity} because it is not committed"
            )

    def add(self, entity: SgBaseEntity) -> SgBatchQuery:
        """Adds the given entity to the session.

        An entity is added for creation if it is not commited (i.e. its id is None).
        Otherwise, it is added for update even if its fields are not yet modified.

        Args:
            entity: Entity to add.

        Returns:
            the batch query object.

        Raises:
            error.SgAddEntityError: the entity is already in a pending deletion state.
        """
        state = entity.__state__
        request_type = (
            BatchRequestType.UPDATE if state.is_commited() else BatchRequestType.CREATE
        )
        if state.pending_deletion:
            raise error.SgAddEntityError(
                f"Cannot add entity {entity} to session: "
                f"it is already pending for deletion."
            )
        if state.pending_add:
            return self._pending_queries[entity]

        # Add modified relationships in cascade
        for field in entity.__fields__:
            rel_value = state.get_value(field)
            for field_entity in iter_entities_from_field_value(
                field.__info__, rel_value
            ):
                self._check_relationship_commited(field_entity)

        query = SgBatchQuery(request_type, entity)
        self._pending_queries[entity] = query
        state.pending_add = request_type == BatchRequestType.CREATE
        return query

    def delete(self, entity: SgBaseEntity) -> SgBatchQuery:
        """Mark the given entity for deletion.

        Args:
            entity: Entity to delete on commit

        Returns:
            the batch query object.
        """
        state = entity.__state__

        if not state.is_commited():
            raise error.SgDeleteEntityError(
                f"Cannot delete {entity}: it is not committed"
            )
        if state.deleted:
            raise error.SgDeleteEntityError(f"{entity} is already deleted")

        query = SgBatchQuery(BatchRequestType.DELETE, entity)
        self._pending_queries[entity] = query
        state.pending_deletion = True
        return query

    def commit(self) -> None:
        """Commits the pending queries in one batch.

        If any query fails the full transaction is cancelled.
        """
        # Add a batch for each
        rows: list[tuple[bool, dict[str, Any]]] = self._engine.batch(
            list(self._pending_queries.values())
        )
        assert len(rows) == len(self._pending_queries)

        for k, query in enumerate(self._pending_queries.values()):
            success, row = rows[k]
            state = query.entity.__state__

            if query.request_type == BatchRequestType.DELETE:
                state.deleted = success
                state.pending_deletion = False
                continue

            original_model = query.entity
            field_mapper = original_model.__attr_per_field_name__

            for field_name, field_value in row.items():
                if field_name == "type":
                    continue
                # Do not set the relationship field
                field = original_model.__fields_by_attr__[field_mapper[field_name]]
                update_entity_from_value(field, original_model, field_value)
            # The entity has now an unmodified state
            state.set_as_original()
            state.pending_add = False
        self._pending_queries = {}

    def rollback(self) -> None:
        """Cancels the pending queries."""
        self._pending_queries = {}
