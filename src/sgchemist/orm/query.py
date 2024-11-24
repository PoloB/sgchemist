"""Defines elements for creating queries."""

from __future__ import annotations

from typing import Any
from typing import Generic
from typing import TypeVar

from typing_extensions import Self

from . import error
from . import field_info
from .constant import BatchRequestType
from .constant import Order
from .entity import SgBaseEntity
from .entity import SgEntityMeta
from .field_info import get_hash
from .field_info import get_types
from .field_info import is_alias
from .fields import AbstractEntityField
from .fields import AbstractField
from .queryop import SgFilterObject
from .queryop import SgNullCondition

T_meta = TypeVar("T_meta", bound=SgEntityMeta)
OrderField = tuple[AbstractField[Any], Order]


class SgFindQueryData(Generic[T_meta]):
    """Defines a data container for find query data.

    It is transferred between different SgFindQuery objects.
    """

    __slots__ = (
        "_additional_filter_presets",
        "_condition",
        "_entity",
        "_fields",
        "_include_archived_projects",
        "_limit",
        "_loading_fields",
        "_order_fields",
        "_page",
        "_retired_only",
    )

    def __init__(  # noqa: PLR0913
        self,
        entity: T_meta,
        fields: tuple[AbstractField[Any], ...],
        condition: SgFilterObject | None = None,
        order_fields: tuple[OrderField, ...] = (),
        limit: int = 0,
        retired_only: bool = False,  # noqa: FBT001, FBT002
        page: int = 0,
        include_archived_projects: bool = True,  # noqa: FBT001, FBT002
        additional_filter_presets: list[dict[str, Any]] | None = None,
        loading_fields: tuple[AbstractField[Any], ...] = (),
    ) -> None:
        """Initializes a find query data object."""
        self._entity = entity
        self._fields = fields
        self._condition = condition or SgNullCondition()
        self._order_fields = order_fields
        self._limit = limit
        self._retired_only = retired_only
        self._page = page
        self._include_archived_projects = include_archived_projects
        self._additional_filter_presets = additional_filter_presets or []
        self._loading_fields = loading_fields

    def copy(  # noqa: PLR0913
        self,
        entity: T_meta | None = None,
        fields: tuple[AbstractField[Any], ...] | None = None,
        condition: SgFilterObject | None = None,
        order_fields: tuple[OrderField, ...] | None = None,
        limit: int | None = None,
        retired_only: bool | None = None,
        page: int | None = None,
        include_archived_projects: bool | None = None,
        additional_filter_presets: list[dict[str, Any]] | None = None,
        loading_fields: tuple[AbstractField[Any], ...] | None = None,
    ) -> SgFindQueryData[T_meta]:
        """Returns a copy of the object with the given modified attributes."""
        entity = entity if entity is not None else self._entity
        fields = fields if fields is not None else self._fields
        condition = condition if condition is not None else self._condition
        order_fields = order_fields if order_fields is not None else self._order_fields
        limit = limit if limit is not None else self._limit
        retired_only = retired_only if retired_only is not None else self._retired_only
        page = page if page is not None else self._page
        include_archived_projects = (
            include_archived_projects
            if include_archived_projects is not None
            else self._include_archived_projects
        )
        additional_filter_presets = additional_filter_presets or []
        loading_fields = (
            loading_fields if loading_fields is not None else self._loading_fields
        )
        return SgFindQueryData(
            entity=entity,
            fields=fields,
            condition=condition,
            order_fields=order_fields,
            limit=limit,
            retired_only=retired_only,
            page=page,
            include_archived_projects=include_archived_projects,
            additional_filter_presets=additional_filter_presets,
            loading_fields=loading_fields,
        )

    @property
    def entity(self) -> T_meta:
        """Return on which the query applies."""
        return self._entity

    @property
    def fields(self) -> tuple[AbstractField[Any], ...]:
        """Return the fields of the query."""
        return self._fields

    @property
    def condition(self) -> SgFilterObject:
        """Return the condition of the query."""
        return self._condition

    @property
    def order_fields(self) -> tuple[OrderField, ...]:
        """Return the order fields of the query."""
        return self._order_fields

    @property
    def limit(self) -> int:
        """Return the limit."""
        return self._limit

    @property
    def retired_only(self) -> bool:
        """Return the retired only."""
        return self._retired_only

    @property
    def page(self) -> int:
        """Return the page."""
        return self._page

    @property
    def include_archived_projects(self) -> bool:
        """Return the include_archived_projects."""
        return self._include_archived_projects

    @property
    def additional_filter_presets(self) -> list[dict[str, Any]]:
        """Return the additional_filter_presets."""
        return self._additional_filter_presets

    @property
    def loading_fields(self) -> tuple[AbstractField[Any], ...]:
        """Return the loading_fields."""
        return self._loading_fields


class SgFindQuery(Generic[T_meta]):
    """Defines a query."""

    def __init__(self, query_data: SgFindQueryData[T_meta]) -> None:
        """Initializes a query transformer.

        Args:
            query_data: the query data to modify.
        """
        self._data = query_data

    def get_data(self) -> SgFindQueryData[T_meta]:
        """Returns the query data managed by the query.

        Returns:
            the query data managed by the query.
        """
        return self._data

    def where(self, condition: SgFilterObject) -> Self:
        """Filters the query result to the given condition.

        Args:
            condition: the condition to add to the query.

        Returns:
            a new query with the condition added.
        """
        new_condition = self._data.condition & condition
        new_state = self._data.copy(condition=new_condition)
        return self.__class__(new_state)

    def order_by(
        self,
        field: AbstractField[Any],
        direction: Order | str = Order.ASC,
    ) -> Self:
        """Orders the query results by the given field.

        Args:
            field: the field to order from.
            direction: the direction to order by.

        Returns:
            a new query with the ordering added.
        """
        if isinstance(direction, str):
            direction = Order(direction)
        new_order = (*self._data.order_fields, (field, direction))
        new_state = self._data.copy(order_fields=new_order)
        # Concat ordered fields
        return self.__class__(new_state)

    def limit(self, limit: int) -> Self:
        """Limit the query to the given number of records.

        Args:
            limit: the maximum number of records to query.

        Returns:
            a new query with the limit added.
        """
        new_state = self._data.copy(limit=limit)
        return self.__class__(new_state)

    def retired_only(self) -> Self:
        """Limit the query to retired entities only.

        Returns:
            a new query with the retired only added.
        """
        new_state = self._data.copy(retired_only=True)
        return self.__class__(new_state)

    def page(self, page_number: int) -> Self:
        """Specify the page to query.

        Args:
            page_number: the page number to query.

        Returns:
            a new query limited to the given page.
        """
        new_state = self._data.copy(page=page_number)
        return self.__class__(new_state)

    def reject_archived_projects(self) -> Self:
        """Reject archived projects from the queried records.

        Returns:
            a new query with rejected archived projects.
        """
        new_state = self._data.copy(include_archived_projects=False)
        return self.__class__(new_state)

    def filter_preset(self, preset_name: str, **preset_kwargs: str | int) -> Self:
        """Filters the query results using the given preset.

        Args:
            preset_name: the preset name to filter by.
            preset_kwargs: the preset keyword arguments to filter by.

        Returns:
            a new query with the filter preset added.
        """
        preset: dict[str, str | int] = {"preset_name": preset_name}
        preset.update(preset_kwargs)
        # To avoid side effects we copy the previous presets
        new_preset = [
            preset_dict.copy() for preset_dict in self._data.additional_filter_presets
        ]
        new_preset.append(preset)
        new_state = self._data.copy(additional_filter_presets=new_preset)
        return self.__class__(new_state)

    def load(self, *fields: AbstractField[Any]) -> Self:
        """Adds the given fields to the query.

        The results will be nested into the object hierarchy.
        """
        # Check the given fields belongs to the relationships of the queried fields
        queried_relationship_paths = {
            get_hash(f)
            for f in self._data.fields
            if isinstance(f, AbstractEntityField) and not is_alias(f)
        }
        for field in fields:
            if field_info.is_primary(field):
                continue
            if get_hash(field)[:-1] not in queried_relationship_paths:
                error_message = (
                    f"Cannot load {field} because its entity is not queried."
                )
                raise error.SgQueryError(error_message)
        new_state = self._data.copy(
            loading_fields=(*self._data.loading_fields, *fields),
        )
        return self.__class__(new_state)

    def load_all(self, *relationship_fields: AbstractEntityField[Any]) -> Self:
        """Load all the fields of the given relationship fields."""
        if not relationship_fields:
            relationship_fields = tuple(
                field
                for field in self.get_data().fields
                if isinstance(field, AbstractEntityField) and not is_alias(field)
            )
        # Construct all the fields for the relationships
        all_fields = []
        for field in relationship_fields:
            for target_type in get_types(field):
                all_fields += [
                    field.f(target_field) for target_field in target_type.__fields__
                ]
        return self.load(*all_fields)


class SgBatchQuery:
    """Defines a batch query."""

    def __init__(self, request_type: BatchRequestType, entity: SgBaseEntity) -> None:
        """Initializes the batch query.

        Args:
            request_type: the request type.
            entity: the entity to query on.
        """
        self._request_type = request_type
        self._entity = entity

    @property
    def request_type(self) -> BatchRequestType:
        """Returns the request type."""
        return self._request_type

    @property
    def entity(self) -> SgBaseEntity:
        """Returns the entity to query on."""
        return self._entity


def select(entity: T_meta, *fields: AbstractField[Any]) -> SgFindQuery[T_meta]:
    """Returns a new query for the given entity class.

    Args:
        entity: the entity class.
        fields: fields to query. Query all the fields of the entity by default.

    Returns:
        the query for the given entity.
    """
    if not fields:
        fields = tuple(entity.__fields_by_attr__.values())

    # Checking the given fields belong to the given model
    entity_fields = list(entity.__fields_by_attr__.values())
    for field in fields:
        if field not in entity_fields:
            error_message = f"{field} is not a field of {entity}"
            raise error.SgQueryError(error_message)

    state = SgFindQueryData[T_meta](entity, fields=fields, condition=SgNullCondition())
    return SgFindQuery[T_meta](state)
