"""Defines elements for creating queries."""

from __future__ import annotations

import dataclasses
from typing import Any
from typing import Dict
from typing import Generic
from typing import List
from typing import Optional
from typing import Tuple
from typing import TypeVar
from typing import Union

from . import error
from .constant import BatchRequestType
from .constant import GroupingType
from .constant import Order
from .entity import SgEntity
from .instrumentation import InstrumentedAttribute
from .meta import SgEntityMeta
from .queryop import SgFilterObject
from .queryop import SgNullCondition
from .typing_alias import GroupingField
from .typing_alias import OrderField

T_meta = TypeVar("T_meta", bound=SgEntityMeta)


@dataclasses.dataclass
class SgFindQueryData(Generic[T_meta]):
    """Defines a data container for find query data.

    It is transferred between different SgFindQuery objects.
    """

    model: T_meta
    fields: Tuple[InstrumentedAttribute[Any], ...]
    condition: SgFilterObject = dataclasses.field(default_factory=SgNullCondition)
    order_fields: Tuple[OrderField, ...] = tuple()
    limit: int = 0
    retired_only: bool = False
    page: int = 0
    include_archived_projects: bool = True
    additional_filter_presets: List[Dict[str, Any]] = dataclasses.field(
        default_factory=list
    )


class SgFindQuery(Generic[T_meta]):
    """Defines a query."""

    def __init__(self, query_data: SgFindQueryData[T_meta]):
        """Initializes a query transformer.

        Args:
            query_data (SgFindQueryData[T_meta]): the query data to modify.
        """
        self._data = query_data

    def get_data(self) -> SgFindQueryData[T_meta]:
        """Returns the query data managed by the query.

        Returns:
            SgFindQueryData[T_meta]: the query data managed by the query.
        """
        return dataclasses.replace(self._data)

    def where(self, condition: SgFilterObject) -> SgFindQuery[T_meta]:
        """Filters the query result to the given condition.

        Args:
            condition (SgFilterObject): the condition to add to the query.

        Returns:
            SgFindQuery[T_meta]: a new query with the condition added.
        """
        new_condition = self._data.condition & condition
        new_state = dataclasses.replace(self._data, condition=new_condition)
        return self.__class__(new_state)

    def order_by(
        self,
        field: InstrumentedAttribute[Any],
        direction: Union[Order, str] = Order.ASC,
    ) -> SgFindQuery[T_meta]:
        """Orders the query results by the given field.

        Args:
            field (InstrumentedAttribute[Any]): the field to order from.
            direction (Union[Order, str]): the direction to order by.

        Returns:
            SgFindQuery[T_meta]: a new query with the ordering added.
        """
        if isinstance(direction, str):
            direction = Order(direction)
        new_state = dataclasses.replace(self._data)
        # Concat ordered fields
        new_state.order_fields = (
            *new_state.order_fields,
            (field, direction),
        )
        return self.__class__(new_state)

    def limit(self, limit: int) -> SgFindQuery[T_meta]:
        """Limit the query to the given number of records.

        Args:
            limit (int): the maximum number of records to query.

        Returns:
            SgFindQuery[T_meta]: a new query with the limit added.
        """
        new_state = dataclasses.replace(self._data)
        new_state.limit = limit
        return self.__class__(new_state)

    def retired_only(self) -> SgFindQuery[T_meta]:
        """Limit the query to retired entities only.

        Returns:
            SgFindQuery[T_meta]: a new query with the retired only added.
        """
        new_state = dataclasses.replace(self._data, retired_only=True)
        return self.__class__(new_state)

    def page(self, page_number: int) -> SgFindQuery[T_meta]:
        """Specify the page to query.

        Args:
            page_number (int): the page number to query.

        Returns:
            SgFindQuery[T_meta]: a new query limited to the given page.
        """
        new_state = dataclasses.replace(self._data, page=page_number)
        return self.__class__(new_state)

    def reject_archived_projects(self) -> SgFindQuery[T_meta]:
        """Reject archived projects from the queried records.

        Returns:
            SgFindQuery[T_meta]: a new query with rejected archived projects.
        """
        new_state = dataclasses.replace(self._data, include_archived_projects=False)
        return self.__class__(new_state)

    def filter_preset(
        self, preset_name: str, **preset_kwargs: Any
    ) -> SgFindQuery[T_meta]:
        """Filters the query results using the given preset.

        Args:
            preset_name (str): the preset name to filter by.
            preset_kwargs (Any): the preset keyword arguments to filter by.

        Returns:
            SgFindQuery[T_meta]: a new query with the filter preset added.
        """
        preset = {"preset_name": preset_name}
        preset.update(preset_kwargs)
        new_state = dataclasses.replace(self._data)
        # To avoid side effects we copy the previous presets
        new_preset = [
            preset_dict.copy() for preset_dict in new_state.additional_filter_presets
        ]
        new_preset.append(preset)
        new_state.additional_filter_presets = new_preset
        return self.__class__(new_state)


@dataclasses.dataclass
class SgSummarizeQueryData(Generic[T_meta]):
    """Defines a data container for summary query data."""

    model: SgEntityMeta
    condition: Optional[SgFilterObject] = None
    grouping: Tuple[GroupingField, ...] = tuple()
    include_archived_projects: bool = True


class SgSummarizeQuery(Generic[T_meta]):
    """Defines a summarize query."""

    def __init__(
        self,
        state: SgSummarizeQueryData[T_meta],
    ):
        """Initializes the summarize query.

        Args:
            state (SgSummarizeQueryData[T_meta]): the query state.
        """
        self._state = state

    def get_data(self) -> SgSummarizeQueryData[T_meta]:
        """Returns the query data managed by the query.

        Returns:
            SgSummarizeQueryData[T_meta]: the query data managed by the query.
        """
        return dataclasses.replace(self._state)

    def where(self, condition: SgFilterObject) -> SgSummarizeQuery[T_meta]:
        """Filters the query result to the given condition.

        Args:
            condition (SgFilterObject): the condition to add to the query.

        Returns:
            SgSummarizeQuery[T_meta]: a new query with the condition added.
        """
        if self._state.condition is None:
            new_condition = condition
        else:
            new_condition = self._state.condition & condition
        new_state = dataclasses.replace(self._state, condition=new_condition)
        return self.__class__(new_state)

    def group_by(
        self,
        field: InstrumentedAttribute[Any],
        group_type: GroupingType,
        direction: Union[Order, str] = Order.ASC,
    ) -> SgSummarizeQuery[T_meta]:
        """Groups the query results by the given field.

        Args:
            field (InstrumentedAttribute[Any]): the field to group by.
            group_type (GroupingType): the group type to group by.
            direction (Union[Order, str]): the direction to group by.

        Returns:
            SgSummarizeQuery[T_meta]: a new query with the group type added.
        """
        if isinstance(direction, str):
            direction = Order(direction)
        new_state = dataclasses.replace(self._state)
        # Concat ordered fields
        new_state.grouping = (
            *new_state.grouping,
            (field, group_type, direction),
        )
        return self.__class__(new_state)

    def reject_archived_projects(self) -> SgSummarizeQuery[T_meta]:
        """Rejects the archived projects from the query.

        Returns:
            SgSummarizeQuery[T_meta]: a new query with rejected archived projects.
        """
        new_state = dataclasses.replace(self._state, include_archived_projects=False)
        return self.__class__(new_state)


class SgBatchQuery(object):
    """Defines a batch query."""

    def __init__(self, request_type: BatchRequestType, entity: SgEntity):
        """Initializes the batch query.

        Args:
            request_type (BatchRequestType): the request type.
            entity (SgEntity): the entity to query on.
        """
        self._request_type = request_type
        self._entity = entity

    @property
    def request_type(self) -> BatchRequestType:
        """Returns the request type.

        Returns:
            BatchRequestType: the request type.
        """
        return self._request_type

    @property
    def entity(self) -> SgEntity:
        """Returns the entity to query on.

        Returns:
            SgEntity: the entity to query on.
        """
        return self._entity


def select(
    model: T_meta, *fields: InstrumentedAttribute[Any]
) -> SgFindQuery[T_meta]:
    """Returns a new query for the given entity class.

    Args:
        model (T_meta): the entity class.
        fields (InstrumentedAttribute): fields to query.
            Query all the fields of the entity by default.

    Returns:
        SgFindQuery[T_meta]: the query for the given entity.
    """
    if not fields:
        fields = tuple(model.__fields__.values())
    # Checking the given fields belong to the given model
    model_fields = list(model.__fields__.values())
    for field in fields:
        if field not in model_fields:
            raise error.SgQueryError(f"{field} is not a field of {model}")
    state = SgFindQueryData[T_meta](model, fields=fields, condition=SgNullCondition())
    return SgFindQuery[T_meta](state)


def summarize(model: T_meta) -> SgSummarizeQuery[T_meta]:
    """Returns a new summarize query for the given entity class.

    Args:
        model (T_meta): the entity class.

    Returns:
        SgSummarizeQuery[T_meta]: the query for the given entity.
    """
    state = SgSummarizeQueryData[T_meta](model)
    return SgSummarizeQuery[T_meta](state)
