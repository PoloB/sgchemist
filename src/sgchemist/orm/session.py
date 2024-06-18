"""Definition of the session mechanism.

The Session object implements the unit of work pattern.
It keeps tracks of the pending queries and objects to commit to Shotgrid.
"""

from __future__ import annotations

from types import TracebackType
from typing import Dict
from typing import Generic
from typing import Iterator
from typing import List
from typing import Optional
from typing import Type
from typing import TypeVar

from . import error
from .constant import BatchRequestType
from .engine import SgEngine
from .entity import SgEntity
from .query import SgBatchQuery
from .query import SgFindQuery
from .row import SgRow
from .typing_alias import EntityHash

T = TypeVar("T", bound=SgEntity)


class SgFindResult(Generic[T]):
    """Defines the result of a query to Shotgrid."""

    def __init__(self, entities: List[T]) -> None:
        """Initializes the entity result of a query to Shotgrid.

        Args:
            entities (list[T]): List of entities.
        """
        self._entities = entities

    def __iter__(self) -> Iterator[T]:
        """Returns an iter of the results.

        Returns:
            Iterator[T]: Iterator of results.
        """
        return iter(self._entities)

    def __len__(self) -> int:
        """Returns the number of entities in the result.

        Returns:
            int: Number of entities in the result.
        """
        return len(self._entities)

    def first(self) -> T:
        """Returns the first entity in the result.

        Returns:
            T: First entity in the result.
        """
        return next(iter(self._entities))

    def all(self) -> List[T]:
        """Returns all entities in the result.

        Returns:
            list[T]: All entities in the result.
        """
        return self._entities


class Session:
    """Defines the session object."""

    def __init__(self, engine: SgEngine):
        """Initializes the session object from an engine.

        Args:
            engine (sgchemist.orm.engine.Engine): engine to use.
        """
        self._engine: SgEngine = engine
        self._pending_queries: Dict[SgEntity, SgBatchQuery] = {}
        self._entity_map: Dict[EntityHash, SgEntity] = {}

    def __enter__(self) -> Session:
        """Starts the session context.

        Returns:
            Session: Session context.
        """
        return self

    def __exit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc: Optional[BaseException],
        traceback: Optional[TracebackType],
    ) -> None:
        """Ends the session context by commiting all the pending queries."""
        self.commit()

    def __iter__(self) -> Iterator[SgEntity]:
        """Returns an iterator of all the entities currently managed by the session.

        Returns:
            Iterator[SgEntity]: Iterator of entities currently managed by the session.
        """
        return iter(self._pending_queries.keys())

    @property
    def pending_queries(self) -> List[SgBatchQuery]:
        """Returns the pending queries.

        Returns:
            list[SgBatchQuery]: List of pending queries.
        """
        return list(self._pending_queries.values())

    def _get_or_create_instance(
        self, entity_cls: Type[SgEntity], row: SgRow[SgEntity]
    ) -> SgEntity:
        """Gets or creates the entity from the given row.

        Args:
            entity_cls (Type[SgEntity]): Type of the entity.
            row (SgRow[SgEntity]): Row of the entity.

        Returns:
            SgEntity: Instance of the entity.
        """
        # We assume this is only called when dealing with relationships
        try:
            column_value = self._entity_map[row.entity_hash]
        except KeyError:
            column_value = self._build_instance_from_row(entity_cls, row, True)
        return column_value

    def _build_instance_from_row(
        self, entity_cls: Type[T], row: SgRow[T], is_relationship: bool = False
    ) -> T:
        """Builds the entity from the given row.

        Args:
            entity_cls (Type[T]): Type of the entity.
            row (SgRow[T]): Row of the entity.
            is_relationship (bool, optional): Whether the entity part of a relationship.

        Returns:
            T: Instance of the entity.
        """
        inst_data = {}
        field_mapper = entity_cls.__attr_per_field_name__

        if is_relationship:
            # Shotgrid uses a different key for the same field when queried
            # from relationship.
            # We construct a new field mapper in this case
            field_mapper = {
                field.get_name_in_relation(): field_mapper[field.get_name()]
                for field in entity_cls.__fields__.values()
            }

        column_value_by_attr = {
            field_mapper[column_name]: column_value
            for column_name, column_value in row.content.items()
        }
        for attr_name, column_value in column_value_by_attr.items():
            field = entity_cls.__fields__[attr_name]
            # Cast column value
            column_value = field.cast_column(column_value, self._get_or_create_instance)
            inst_data[attr_name] = column_value

        inst = entity_cls(**inst_data)
        state = inst.__state__
        # Mark all the fields that were not queried as not available
        for attr_name in set(entity_cls.__fields__).difference(
            set(column_value_by_attr)
        ):
            state.get_slot(attr_name).available = False

        inst.__state__.set_as_original()
        self._entity_map[row.entity_hash] = inst
        return inst

    def exec(self, query: SgFindQuery[Type[T]]) -> SgFindResult[T]:
        """Executes the find query and returns the results.

        Args:
            query (SgFindQuery[Type[T]]): Query to execute.

        Returns:
            SgFindResult[T]: Result of the query.
        """
        query_state = query.get_data()
        rows = self._engine.find(query_state)
        model = query_state.model

        # Create the instances
        queried_models = []
        for row in rows:
            # Create the instance data
            inst = self._build_instance_from_row(model, row)
            queried_models.append(inst)

        return SgFindResult(queried_models)

    @staticmethod
    def _check_relationship_commited(entity: SgEntity) -> None:
        """Asserts that a relationship has been commited.

        Raises:
            error.SgRelationshipNotCommitedError: the entity is not commited.
        """
        state = entity.__state__
        if not state.is_commited() or state.is_modified():
            raise error.SgRelationshipNotCommitedError(
                f"Cannot add relation {entity} because it is not committed"
            )

    def add(self, entity: SgEntity) -> SgBatchQuery:
        """Adds the given entity to the session.

        An entity is added for creation if it is not commited (i.e. its id is None).
        Otherwise, it is added for update even if its fields are not yet modified.

        Args:
            entity (SgEntity): Entity to add.

        Returns:
            SgBatchQuery: the batch query object.

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
        for attr_name, field in entity.__fields__.items():
            rel_value = state.get_slot(attr_name).value
            for field_entity in field.iter_entities_from_field_value(rel_value):
                self._check_relationship_commited(field_entity)

        query = SgBatchQuery(request_type, entity)
        self._pending_queries[entity] = query
        state.session = self
        state.pending_add = request_type == BatchRequestType.CREATE
        return query

    def delete(self, entity: SgEntity) -> SgBatchQuery:
        """Mark the given entity for deletion.

        Args:
            entity (SgEntity): Entity to delete on commit

        Returns:
            SgBatchQuery: the batch query object.
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
        rows: List[SgRow[SgEntity]] = self._engine.batch(
            list(self._pending_queries.values())
        )
        assert len(rows) == len(self._pending_queries)

        for k, query in enumerate(self._pending_queries.values()):
            row = rows[k]
            state = query.entity.__state__

            if query.request_type == BatchRequestType.DELETE:
                state.deleted = row.success
                state.pending_deletion = False
                continue

            original_model = query.entity
            field_mapper = original_model.__attr_per_field_name__

            for field_name, field_value in row.content.items():
                # Do not set the relationship field
                field = original_model.__fields__[field_mapper[field_name]]
                field.update_entity_from_row_value(original_model, field_value)
            # The entity has now an unmodified state
            state.set_as_original()
            state.pending_add = False
        self._pending_queries = {}

    def rollback(self) -> None:
        """Cancels the pending queries."""
        self._pending_queries = {}
