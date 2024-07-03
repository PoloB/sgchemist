"""Definition of all the fields used by Shotgrid entities.

The main function of these fields is to provide the correct type annotations.
Internally, only the classes inheriting from InstrumentedAttribute are used.
"""

from __future__ import annotations

import abc
from datetime import date
from datetime import datetime
from typing import TYPE_CHECKING
from typing import Any
from typing import Callable
from typing import Dict
from typing import Generic
from typing import Iterator
from typing import List
from typing import Optional
from typing import Tuple
from typing import Type
from typing import TypeVar
from typing import Union
from typing import overload

from typing_extensions import Self

from . import error
from .annotation import FieldAnnotation
from .annotation import LazyEntityClassEval
from .annotation import LazyEntityCollectionClassEval
from .constant import DateType
from .constant import Operator
from .queryop import SgFieldCondition

if TYPE_CHECKING:
    from .entity import SgEntity
    from .meta import SgEntityMeta

T = TypeVar("T")
T2 = TypeVar("T2")


class FieldInfo(Generic[T]):
    """Field information."""

    annotation: FieldAnnotation
    entity: SgEntityMeta
    default_value: T

    def __init__(
        self,
        field: AbstractField[T],
        name: Optional[str] = None,
        name_in_relation: Optional[str] = None,
        default_value: Optional[T] = None,
        alias_field: Optional[AbstractField[Any]] = None,
        parent_field: Optional[AbstractField[Any]] = None,
        primary: bool = False,
    ) -> None:
        """Initialize the field info."""
        self.field = field
        self.field_name = name or ""
        self.name_in_relation = name_in_relation or self.field_name
        self.default_value = (
            default_value if default_value is not None else field.default_value
        )
        self.alias_field = alias_field
        self.parent_field = parent_field
        self.primary = primary

    def copy(self) -> FieldInfo[T]:
        """Returns a copy of the info."""
        new_info = self.__class__(
            field=self.field,
            name=self.field_name,
            name_in_relation=self.name_in_relation,
            default_value=self.default_value,
            alias_field=self.alias_field,
            parent_field=self.parent_field,
            primary=self.primary,
        )
        new_info.entity = self.entity
        new_info.annotation = self.annotation
        return new_info

    def initialize_from_annotation(
        self,
        parent_class: SgEntityMeta,
        annotation: FieldAnnotation,
        attribute_name: str,
    ) -> None:
        """Create a field from a descriptor."""
        if annotation.field_type is not self.field.__class__:
            raise error.SgInvalidAnnotationError(
                f"Cannot initialize field of type {self.field.__class__.__name__} "
                f"with a {annotation.field_type.__name__}"
            )
        if self.alias_field:
            if len(annotation.entities) != 1:
                raise error.SgInvalidAnnotationError(
                    "A alias field shall target a single entity"
                )
            # Make sure the entity type in annotation is in the target annotation
            target_entity = annotation.entities[0]
            target_annotation = self.alias_field.__info__.annotation
            if target_entity not in target_annotation.entities:
                raise error.SgInvalidAnnotationError(
                    "An alias field must target a multi target field containing "
                    "its entity"
                )
            # An alias field use the same name as its target
            self.field_name = self.alias_field.__info__.field_name
        self.entity = parent_class
        self.annotation = annotation
        self.field_name = self.field_name or attribute_name
        self.name_in_relation = self.name_in_relation or self.field_name

    def is_alias(self) -> bool:
        """Return whether the attribute is an alias.

        Returns:
            bool: whether the attribute is an alias
        """
        return self.alias_field is not None

    def get_hash(
        self,
    ) -> Tuple[AbstractField[Any], ...]:
        """Return the hash of the attribute."""
        parent_hash = (
            self.parent_field.__info__.get_hash() if self.parent_field else tuple()
        )
        field_hash = (*parent_hash, self.field)
        return field_hash


class FieldCaster(Generic[T]):
    """Responsible for casting values in and out of a field."""

    def __init__(
        self,
        field: AbstractField[T],
        is_relationship: bool,
        is_list: bool,
        lazy_collection: LazyEntityCollectionClassEval,
    ) -> None:
        """Initialize the field caster."""
        self.field = field
        self.lazy_collection = lazy_collection
        self.is_relationship = is_relationship
        self.is_list = is_list

    def copy(self) -> FieldCaster[T]:
        """Returns a copy of the field caster."""
        return self.__class__(
            self.field,
            is_relationship=self.is_relationship,
            is_list=self.is_list,
            lazy_collection=self.lazy_collection,
        )

    def initialize_from_annotation(
        self,
        parent_class: SgEntityMeta,
        annotation: FieldAnnotation,
    ) -> None:
        """Create a field from a descriptor."""
        entities = annotation.entities
        # Make some checks
        if self.is_relationship and len(entities) == 0:
            raise error.SgInvalidAnnotationError("Expected at least one entity field")
        # Construct a multi target entity
        lazy_evals = [
            LazyEntityClassEval(entity, parent_class.__registry__)
            for entity in entities
        ]
        self.lazy_collection = LazyEntityCollectionClassEval(lazy_evals)

    def get_types(self) -> Tuple[Type[SgEntity], ...]:
        """Return the Python types of the attribute.

        Returns:
            tuple[Type[Any], ...]: Python types of the attribute
        """
        return tuple(self.lazy_collection.get_all())

    def update_entity_from_row_value(self, entity: SgEntity, field_value: Any) -> None:
        """Update an entity from a row value.

        Used by the Session to convert the value returned by an update back to the
        entity field.

        Args:
            entity (SgEntity): the entity to update
            field_value: the row value
        """
        if self.is_relationship:
            return
        entity.__state__.set_value(self.field, field_value)

    def iter_entities_from_field_value(self, field_value: Any) -> Iterator[SgEntity]:
        """Iterate entities from a field value.

        Used by the Session to get the entities within the field values if any.

        Args:
            field_value: Any

        Returns:
            Iterator[SgEntity]: the entities within the field value
        """
        if not self.is_relationship:
            return
        if self.is_list:
            for value in field_value:
                yield value
            return
        if field_value is None:
            return
        yield field_value

    def cast_value_over(
        self,
        func: Callable[[Any], Any],
        value: Any,
    ) -> Any:
        """Apply the given function to the given value.

        Used by the Engine to organize the result of its query.

        Args:
            func (Callable[[Any], Any]): the function to apply
            value (Any): the value on which to apply the function

        Returns:
            Any: result of the applied function
        """
        if self.is_relationship:
            if self.is_list:
                return [func(v) for v in value]
            else:
                return func(value)
        return value

    def cast_column(
        self,
        column_value: Any,
        model_factory: Callable[[Type[SgEntity], Dict[str, Any]], Any],
    ) -> Any:
        """Cast the given row value to be used for instancing the entity.

        Used by the session to convert the column value to a value for instantiating
        the entity.
        The model_factory is a function that takes an entity class and a row as
        argument. Use this factory if the instrumented attribute is representing another
        entity that you need to be instantiated.

        Args:
            column_value (Any): the column value to cast
            model_factory (Callable[[Type[SgEntity], SgRow[T]], T]): the function to
                call for instantiating an entity from a row.

        Returns:
            Any: result of the applied function
        """
        if not self.is_relationship:
            return column_value

        if not self.is_list and column_value is None:
            return None

        def _cast_column(col: Dict[str, Any]) -> Any:
            return model_factory(self.lazy_collection.get_by_type(col["type"]), col)

        return self.cast_value_over(_cast_column, column_value)


class AbstractField(Generic[T], metaclass=abc.ABCMeta):
    """Definition of an abstract field."""

    cast_type: Type[T]
    default_value: T
    __sg_type__: str = ""
    __cast__: FieldCaster[T]
    __info__: FieldInfo[T]

    def __init__(
        self,
        name: Optional[str] = None,
        default_value: Optional[T] = None,
        name_in_relation: Optional[str] = None,
        alias_field: Optional[AbstractField[Any]] = None,
        parent_field: Optional[AbstractField[Any]] = None,
        primary: bool = False,
        as_list: bool = False,
        is_relationship: bool = False,
        lazy_collection: Optional[LazyEntityCollectionClassEval] = None,
    ) -> None:
        """Initialize an instrumented attribute.

        Args:
            name (str): the name of the field
            default_value (Any): the default value of the field
            name_in_relation (str): the name of the field in relationship
            alias_field (AbstractField[Any], optional): the alias field of the field
            parent_field (AbstractField[Any], optional): the parent field of the field
            primary (bool, optional): whether the field is primary or not
            as_list (bool, optional): whether the field is list or not
            is_relationship (bool, optional): whether the field is a relationship
            lazy_collection (Optional[LazyEntityCollectionClassEval], optional):
                the wrapped entities evaluator
        """
        self.__info__ = FieldInfo(
            field=self,
            name=name,
            name_in_relation=name_in_relation,
            default_value=default_value,
            alias_field=alias_field,
            parent_field=parent_field,
            primary=primary,
        )
        self.__cast__ = FieldCaster(
            self,
            is_relationship,
            as_list,
            lazy_collection or LazyEntityCollectionClassEval([]),
        )

    def __repr__(self) -> str:
        """Returns a string representation of the instrumented attribute.

        Returns:
            str: the instrumented attribute representation
        """
        return (
            f"{self.__class__.__name__}"
            f"({self.__info__.entity.__name__}.{self.__info__.field_name})"
        )

    def _relative_to(self, relative_attribute: AbstractField[Any]) -> Self:
        """Build a new instrumented field relative to the given attribute.

        Args:
            relative_attribute (InstrumentedAttribute[T]): the relative attribute

        Returns:
            InstrumentedField[T]: the attribute relative to the given attribute
        """
        field_info = self.__info__
        new_field_name = ".".join(
            [
                relative_attribute.__info__.field_name,
                field_info.entity.__sg_type__,
                field_info.field_name,
            ]
        )
        new_field = self.__class__()
        new_field_info = field_info.copy()
        new_field_info.field_name = new_field_name
        new_field_info.field = new_field
        new_field_info.parent_field = relative_attribute
        new_field.__info__ = new_field_info
        new_field.__cast__ = self.__cast__.copy()
        return new_field

    def eq(self, other: T) -> SgFieldCondition:
        """Filter entities where this field is equal to the given value.

        This is the equivalent of the "is" filter of Shotgrid.

        Args:
            other: The value to compare the field against

        Returns:
            SgFieldCondition: The field condition
        """
        return SgFieldCondition(self, Operator.IS, other)

    def neq(self, other: T) -> SgFieldCondition:
        """Filter entities where this field is not equal to the given value.

        This is the equivalent of the "is_not" filter of Shotgrid.

        Args:
            other: The value to compare the field against

        Returns:
            SgFieldCondition: The field condition
        """
        return SgFieldCondition(self, Operator.IS_NOT, other)


T_field = TypeVar("T_field", bound=AbstractField[Any])


class AbstractValueField(AbstractField[Optional[T]], metaclass=abc.ABCMeta):
    """Definition of an abstract value field."""

    def __init__(
        self,
        name: Optional[str] = None,
        default_value: Optional[T] = None,
        name_in_relation: Optional[str] = None,
    ):
        """Initialize an instrumented field.

        Args:
            name (str): the name of the field
            default_value: default value of the field
            name_in_relation (str): the name of the attribute in the relationship
        """
        super().__init__(
            name=name,
            default_value=default_value,
            name_in_relation=name_in_relation,
            is_relationship=False,
            as_list=False,
        )


class NumericField(AbstractValueField[T], metaclass=abc.ABCMeta):
    """Definition of an abstract numerical field."""

    cast_type: Type[T]

    def gt(self, other: T) -> SgFieldCondition:
        """Filter entities where this field is greater than the given value.

        This is the equivalent of the "greater_than" filter of Shotgrid.

        Args:
            other: The value to compare the field against

        Returns:
            SgFieldCondition: The field condition
        """
        return SgFieldCondition(self, Operator.GREATER_THAN, other)

    def lt(self, other: T) -> SgFieldCondition:
        """Filter entities where this field is less than the given value.

        This is the equivalent of the "less_than" filter of Shotgrid.

        Args:
            other: The value to compare the field against

        Returns:
            SgFieldCondition: The field condition
        """
        return SgFieldCondition(self, Operator.LESS_THAN, other)

    def between(self, low: T, high: T) -> SgFieldCondition:
        """Filter entities where this field is between the low and high values.

        This is the equivalent of the "between" filter of Shotgrid.

        Args:
            low: low value of the range
            high: high value of the range

        Returns:
            SgFieldCondition: The field condition.
        """
        return SgFieldCondition(self, Operator.BETWEEN, [low, high])

    def not_between(self, low: T, high: T) -> SgFieldCondition:
        """Filter entities where this field is not between the low and high values.

        This is the equivalent of the "not_between" filter of Shotgrid.

        Args:
            low: low value of the range
            high: high value of the range

        Returns:
            SgFieldCondition: The field condition.
        """
        return SgFieldCondition(self, Operator.NOT_BETWEEN, [low, high])

    def is_in(self, others: List[T]) -> SgFieldCondition:
        """Filter entities where this field is within the given list of values.

        This is the equivalent of the "in" filter of Shotgrid.

        Args:
            others (list): values to test

        Returns:
            SgFieldCondition: The field condition.
        """
        return SgFieldCondition(self, Operator.IN, others)

    def is_not_in(self, others: List[T]) -> SgFieldCondition:
        """Filter entities where this field is not within the given list of values.

        This is the equivalent of the "not_in" filter of Shotgrid.

        Args:
            others (list): values to test

        Returns:
            SgFieldCondition: The field condition.
        """
        return SgFieldCondition(self, Operator.NOT_IN, others)


class NumberField(NumericField[Optional[int]]):
    """An integer field."""

    __sg_type__: str = "number"
    cast_type: Type[int] = int
    default_value = None

    if TYPE_CHECKING:

        @overload
        def __get__(self, instance: None, owner: Any) -> NumberField: ...

        @overload
        def __get__(self, instance: Any, owner: Any) -> Optional[int]: ...

        def __get__(
            self, instance: Optional[Any], owner: Any
        ) -> Union[Optional[int], NumberField]:
            """Return the value of the field."""


class FloatField(NumericField[Optional[float]]):
    """A float field."""

    cast_type: Type[float] = float
    __sg_type__: str = "float"
    default_value = None

    if TYPE_CHECKING:

        @overload
        def __get__(self, instance: None, owner: Any) -> FloatField: ...

        @overload
        def __get__(self, instance: Any, owner: Any) -> Optional[float]: ...

        def __get__(
            self, instance: Optional[Any], owner: Any
        ) -> Union[Optional[float], FloatField]:
            """Return the value of the field."""


class TextField(AbstractValueField[Optional[str]]):
    """A text field."""

    cast_type: Type[str] = str
    __sg_type__: str = "text"
    default_value = None

    def contains(self, text: str) -> SgFieldCondition:
        """Filter entities where this text field contains the given string.

        This is the equivalent of the "contains" filter of Shotgrid.

        Args:
            text (str): text to check

        Returns:
            SgFieldCondition: The field condition.
        """
        return SgFieldCondition(self, Operator.CONTAINS, text)

    def not_contains(self, text: str) -> SgFieldCondition:
        """Filter entities where this text field does not contain the given string.

        This is the equivalent of the "not_contains" filter of Shotgrid.

        Args:
            text (str): text to check

        Returns:
            SgFieldCondition: The field condition.
        """
        return SgFieldCondition(self, Operator.NOT_CONTAINS, text)

    def is_in(self, others: List[T]) -> SgFieldCondition:
        """Filter entities where this field is within the given list of values.

        This is the equivalent of the "in" filter of Shotgrid.

        Args:
            others (list): values to test

        Returns:
            SgFieldCondition: The field condition.
        """
        return SgFieldCondition(self, Operator.IN, others)

    def is_not_in(self, others: List[T]) -> SgFieldCondition:
        """Filter entities where this field is not within the given list of values.

        This is the equivalent of the "not_in" filter of Shotgrid.

        Args:
            others (list): values to test

        Returns:
            SgFieldCondition: The field condition.
        """
        return SgFieldCondition(self, Operator.NOT_IN, others)

    def startswith(self, text: str) -> SgFieldCondition:
        """Filter entities where this text field starts with the given text.

        This is the equivalent of the "start_with" filter of Shotgrid.

        Args:
            text (str): text to check

        Returns:
            SgFieldCondition: The field condition.
        """
        return SgFieldCondition(self, Operator.STARTS_WITH, text)

    def endswith(self, text: str) -> SgFieldCondition:
        """Filter entities where this text field ends with the given text.

        This is the equivalent of the "end_with" filter of Shotgrid.

        Args:
            text (str): text to check

        Returns:
            SgFieldCondition: The field condition.
        """
        return SgFieldCondition(self, Operator.ENDS_WITH, text)

    if TYPE_CHECKING:

        @overload
        def __get__(self, instance: None, owner: Any) -> TextField: ...

        @overload
        def __get__(self, instance: Any, owner: Any) -> Optional[str]: ...

        def __get__(
            self, instance: Optional[Any], owner: Any
        ) -> Union[Optional[str], TextField]:
            """Return the value of the field."""


class AbstractEntityField(AbstractField[T], metaclass=abc.ABCMeta):
    """Definition a field targeting an entity."""

    __sg_type__: str
    cast_type: Type[T]

    def f(self, field: T_field) -> T_field:
        """Return the given field in relation to the given field."""
        if field.__info__.entity not in self.__cast__.get_types():
            raise error.SgFieldConstructionError(
                f"Cannot cast {self} as {field.__info__.entity.__name__}. "
                f"Expected types are {self.__cast__.get_types()}"
            )
        return field._relative_to(self)

    def type_is(self, entity_cls: Type[SgEntity]) -> SgFieldCondition:
        """Filter entities where this entity is of the given type.

        This is the equivalent of the "type_is" filter of Shotgrid.

        Args:
            entity_cls (SgEntityMeta): entity to test

        Returns:
            SgFieldCondition: The field condition.
        """
        return SgFieldCondition(self, Operator.TYPE_IS, entity_cls.__sg_type__)

    def type_is_not(self, entity_cls: Type[SgEntity]) -> SgFieldCondition:
        """Filter entities where this entity is not of the given type.

        This is the equivalent of the "type_is_not" filter of Shotgrid.

        Args:
            entity_cls (SgEntityMeta): entity to test

        Returns:
            SgFieldCondition: The field condition.
        """
        return SgFieldCondition(self, Operator.TYPE_IS_NOT, entity_cls.__sg_type__)

    def name_contains(self, text: str) -> SgFieldCondition:
        """Filter entities where this entity name contains the given text.

        This is the equivalent of the "name_contains" filter of Shotgrid.

        Args:
            text (str): text to test

        Returns:
            SgFieldCondition: The field condition.
        """
        return SgFieldCondition(self, Operator.NAME_CONTAINS, text)

    def name_not_contains(self, text: str) -> SgFieldCondition:
        """Filter entities where this entity name does not contain the given text.

        This is the equivalent of the "name_contains" filter of Shotgrid.

        Args:
            text (str): text to test

        Returns:
            SgFieldCondition: The field condition.
        """
        return SgFieldCondition(self, Operator.NAME_NOT_CONTAINS, text)

    def name_is(self, text: str) -> SgFieldCondition:
        """Filter entities where this entity name is the given text.

        This is the equivalent of the "name_is" filter of Shotgrid.

        Args:
            text (str): text to test

        Returns:
            SgFieldCondition: The field condition.
        """
        return SgFieldCondition(self, Operator.NAME_IS, text)

    def is_in(self, others: List[T]) -> SgFieldCondition:
        """Filter entities where this field is within the given list of values.

        This is the equivalent of the "in" filter of Shotgrid.

        Args:
            others (list): values to test

        Returns:
            SgFieldCondition: The field condition.
        """
        return SgFieldCondition(self, Operator.IN, others)

    def is_not_in(self, others: List[T]) -> SgFieldCondition:
        """Filter entities where this field is not within the given list of values.

        This is the equivalent of the "not_in" filter of Shotgrid.

        Args:
            others (list): values to test

        Returns:
            SgFieldCondition: The field condition.
        """
        return SgFieldCondition(self, Operator.NOT_IN, others)


class EntityField(AbstractEntityField[Optional[T]]):
    """Definition a field targeting a single entity."""

    __sg_type__: str = "entity"
    cast_type: Type[T]
    default_value = None

    def __init__(self, name: Optional[str] = None):
        """Initialise the field."""
        super().__init__(
            name=name, default_value=None, is_relationship=True, as_list=False
        )

    if TYPE_CHECKING:

        @overload
        def __get__(self, instance: None, owner: Any) -> EntityField[T]: ...

        @overload
        def __get__(self, instance: Any, owner: Any) -> Optional[T]: ...

        def __get__(
            self, instance: Optional[Any], owner: Any
        ) -> Union[Optional[T], EntityField[T]]:
            """Return the value of the field."""


class MultiEntityField(AbstractEntityField[List[T]]):
    """Definition a field targeting multiple entities."""

    __sg_type__: str = "multi_entity"

    def __init__(self, name: Optional[str] = None):
        """Initialize the field."""
        super().__init__(
            name=name, default_value=[], as_list=True, is_relationship=True
        )

    if TYPE_CHECKING:

        @overload
        def __get__(self, instance: None, owner: Any) -> MultiEntityField[T]: ...

        @overload
        def __get__(self, instance: Any, owner: Any) -> T: ...

        def __get__(
            self, instance: Optional[Any], owner: Any
        ) -> Union[T, MultiEntityField[T]]:
            """Return the value of the field."""


class BooleanField(AbstractValueField[Optional[bool]]):
    """Definition a boolean field."""

    __sg_type__: str = "checkbox"
    default_value: Optional[bool] = None

    if TYPE_CHECKING:

        @overload
        def __get__(self, instance: None, owner: Any) -> BooleanField: ...

        @overload
        def __get__(self, instance: Any, owner: Any) -> Optional[bool]: ...

        def __get__(
            self, instance: Optional[Any], owner: Any
        ) -> Union[Optional[bool], BooleanField]:
            """Return the value of the field."""


class AbstractDateField(NumericField[T]):
    """Definition an abstract date field."""

    def in_last(self, count: int, date_element: DateType) -> SgFieldCondition:
        """Filter entities where this date is within the last given quantities.

        This is the equivalent of the "in_last" filter of Shotgrid.

        Args:
            count (int): number of days/weeks/months/years
            date_element (DateType): duration type to consider

        Returns:
            SgFieldCondition: The field condition.
        """
        return SgFieldCondition(self, Operator.IN_LAST, [count, date_element])

    def not_in_last(self, count: int, date_element: DateType) -> SgFieldCondition:
        """Filter entities where this date is not within the last given quantities.

        This is the equivalent of the "not_in_last" filter of Shotgrid.

        Args:
            count (int): number of days/weeks/months/years
            date_element (DateType): duration type to consider

        Returns:
            SgFieldCondition: The field condition.
        """
        return SgFieldCondition(self, Operator.NOT_IN_LAST, [count, date_element])

    def in_next(self, count: int, date_element: DateType) -> SgFieldCondition:
        """Filter entities where this date is within the next given quantities.

        This is the equivalent of the "in_next" filter of Shotgrid.

        Args:
            count (int): number of days/weeks/months/years
            date_element (DateType): duration type to consider

        Returns:
            SgFieldCondition: The field condition.
        """
        return SgFieldCondition(self, Operator.IN_NEXT, [count, date_element])

    def not_in_next(self, count: int, date_element: DateType) -> SgFieldCondition:
        """Filter entities where this date is not within the next given quantities.

        This is the equivalent of the "not_in_next" filter of Shotgrid.

        Args:
            count (int): number of days/weeks/months/years
            date_element (DateType): duration type to consider

        Returns:
            SgFieldCondition: The field condition.
        """
        return SgFieldCondition(self, Operator.NOT_IN_NEXT, [count, date_element])

    def in_calendar_day(self, offset: int) -> SgFieldCondition:
        """Filter entities where this date is equal to the offset current day.

        This is the equivalent of the "in_calendar_day" filter of Shotgrid.

        Args:
            offset (int): offset (e.g. 0=today, 1=tomorrow, -1=yesterday)

        Returns:
            SgFieldCondition: The field condition.
        """
        return SgFieldCondition(self, Operator.IN_CALENDAR_DAY, offset)

    def in_calendar_week(self, offset: int) -> SgFieldCondition:
        """Filter entities where this date is equal to the offset current week.

        This is the equivalent of the "in_calendar_week" filter of Shotgrid.

        Args:
            offset (int): offset (e.g. 0=this week, 1=next week, -1=last week)

        Returns:
            SgFieldCondition: The field condition.
        """
        return SgFieldCondition(self, Operator.IN_CALENDAR_WEEK, offset)

    def in_calendar_month(self, offset: int) -> SgFieldCondition:
        """Filter entities where this date is equal to the offset current month.

        This is the equivalent of the "in_calendar_month" filter of Shotgrid.

        Args:
            offset (int): offset (e.g. 0=this month, 1=next month, -1= last month)

        Returns:
            SgFieldCondition: The field condition.
        """
        return SgFieldCondition(self, Operator.IN_CALENDAR_MONTH, offset)

    def in_calendar_year(self, offset: int) -> SgFieldCondition:
        """Filter entities where this date is equal to the offset current year.

        This is the equivalent of the "in_calendar_year" filter of Shotgrid.

        Args:
            offset (int): offset (e.g. 0=this year, 1=next year, -1= last year)

        Returns:
            SgFieldCondition: The field condition.
        """
        return SgFieldCondition(self, Operator.IN_CALENDAR_YEAR, offset)


class DateField(AbstractDateField[Optional[date]]):
    """Definition of a date field."""

    cast_type: Type[date] = date
    __sg_type__: str = "date"
    default_value: Optional[date] = None

    if TYPE_CHECKING:

        @overload
        def __get__(self, instance: None, owner: Any) -> DateField: ...

        @overload
        def __get__(self, instance: Any, owner: Any) -> Optional[date]: ...

        def __get__(
            self, instance: Optional[Any], owner: Any
        ) -> Union[Optional[date], DateField]:
            """Return the value of the field."""


class DateTimeField(AbstractDateField[Optional[datetime]]):
    """Definition of a date time field."""

    cast_type: Type[datetime] = datetime
    __sg_type__: str = "date_time"
    default_value = None

    if TYPE_CHECKING:

        @overload
        def __get__(self, instance: None, owner: Any) -> DateTimeField: ...

        @overload
        def __get__(self, instance: Any, owner: Any) -> Optional[datetime]: ...

        def __get__(
            self, instance: Optional[Any], owner: Any
        ) -> Union[Optional[datetime], DateTimeField]:
            """Return the value of the field."""


class DurationField(NumberField):
    """Definition of a duration field."""

    __sg_type__: str = "duration"

    if TYPE_CHECKING:

        @overload
        def __get__(self, instance: None, owner: Any) -> DurationField: ...

        @overload
        def __get__(self, instance: Any, owner: Any) -> Optional[int]: ...

        def __get__(
            self, instance: Optional[Any], owner: Any
        ) -> Union[Optional[int], DurationField]:
            """Return the value of the field."""


class ImageField(AbstractValueField[Optional[str]]):
    """Definition of an image field."""

    cast_type: Type[str] = str
    __sg_type__: str = "image"
    default_value = None

    def exists(self) -> SgFieldCondition:
        """Filter entities where this image exists.

        This is the equivalent of the "is" filter of Shotgrid.

        Returns:
            SgFieldCondition: The field condition.
        """
        return SgFieldCondition(self, Operator.IS_NOT, None)

    def not_exists(self) -> SgFieldCondition:
        """Filter entities where this image does not exist.

        This is the equivalent of the "is_not" filter of Shotgrid.

        Returns:
            SgFieldCondition: The field condition.
        """
        return SgFieldCondition(self, Operator.IS, None)

    if TYPE_CHECKING:

        @overload
        def __get__(self, instance: None, owner: Any) -> ImageField: ...

        @overload
        def __get__(self, instance: Any, owner: Any) -> Optional[str]: ...

        def __get__(
            self, instance: Optional[Any], owner: Any
        ) -> Union[Optional[str], ImageField]:
            """Return the value of the field."""


class ListField(AbstractValueField[Optional[List[str]]]):
    """Definition of a list field."""

    cast_type: Type[List[str]] = list
    __sg_type__: str = "list"
    default_value = None

    def is_in(self, others: List[str]) -> SgFieldCondition:
        """Filter entities where this field is within the given list of values.

        This is the equivalent of the "in" filter of Shotgrid.

        Args:
            others (list): values to test

        Returns:
            SgFieldCondition: The field condition.
        """
        return SgFieldCondition(self, Operator.IN, others)

    def is_not_in(self, others: List[str]) -> SgFieldCondition:
        """Filter entities where this field is not within the given list of values.

        This is the equivalent of the "not_in" filter of Shotgrid.

        Args:
            others (list): values to test

        Returns:
            SgFieldCondition: The field condition.
        """
        return SgFieldCondition(self, Operator.NOT_IN, others)

    if TYPE_CHECKING:

        @overload
        def __get__(self, instance: None, owner: Any) -> ListField: ...

        @overload
        def __get__(self, instance: Any, owner: Any) -> Optional[List[str]]: ...

        def __get__(
            self, instance: Optional[Any], owner: Any
        ) -> Union[Optional[List[str]], ListField]:
            """Return the value of the field."""


class PercentField(FloatField):
    """Definition of a percent field."""

    __sg_type__: str = "percent"

    if TYPE_CHECKING:

        @overload
        def __get__(self, instance: None, owner: Any) -> PercentField: ...

        @overload
        def __get__(self, instance: Any, owner: Any) -> Optional[float]: ...

        def __get__(
            self, instance: Optional[Any], owner: Any
        ) -> Union[Optional[float], PercentField]:
            """Return the value of the field."""


class SerializableField(AbstractValueField[Optional[Dict[str, Any]]]):
    """Definition of a serializable field."""

    cast_type: Type[Dict[str, Any]] = dict
    __sg_type__: str = "serializable"
    default_value = None

    if TYPE_CHECKING:

        @overload
        def __get__(self, instance: None, owner: Any) -> SerializableField: ...

        @overload
        def __get__(self, instance: Any, owner: Any) -> Optional[Dict[str, Any]]: ...

        def __get__(
            self, instance: Optional[Any], owner: Any
        ) -> Union[Optional[Dict[str, Any]], SerializableField]:
            """Return the value of the field."""


class StatusField(AbstractValueField[str]):
    """Definition of a status field."""

    __sg_type__: str = "status_list"
    default_value = "wtg"

    if TYPE_CHECKING:

        @overload
        def __get__(self, instance: None, owner: Any) -> StatusField: ...

        @overload
        def __get__(self, instance: Any, owner: Any) -> str: ...

        def __get__(
            self, instance: Optional[Any], owner: Any
        ) -> Union[str, StatusField]:
            """Return the value of the field."""


class UrlField(AbstractValueField[Optional[str]]):
    """Definition of an url field."""

    cast_type: Type[str] = str
    __sg_type__: str = "url"
    default_value = None

    if TYPE_CHECKING:

        @overload
        def __get__(self, instance: None, owner: Any) -> UrlField: ...

        @overload
        def __get__(self, instance: Any, owner: Any) -> Optional[str]: ...

        def __get__(
            self, instance: Optional[Any], owner: Any
        ) -> Union[Optional[str], UrlField]:
            """Return the value of the field."""


# Expose all the available fields (intended for model generation)
field_by_sg_type: Dict[str, Type[AbstractField[Any]]] = {
    field_cls.__sg_type__: field_cls
    for name, field_cls in locals().items()
    if isinstance(field_cls, type)
    and issubclass(field_cls, AbstractField)
    and field_cls.__sg_type__ is not None
}


def alias(target_relationship: AbstractEntityField[Any]) -> EntityField[Any]:
    """Defines a field as an alias relationship.

    Use this field specifier to target a specific entity type of the given multi target
    relationship:

    ```python
    from sgchemist.orm import alias_relationship
    from sgchemist.orm import EntityField
    from sgchemist.orm import SgEntity

    class Asset(SgEntity):
        __sg_type__ = "Asset"

    class Shot(SgEntity):
        __sg_type__ = "Shot"

    class Task(SgEntity):
        __sg_type__ = "Task"

        entity: EntityField[Optional[Asset | Shot]]
        asset: EntityField[Optional[Asset]] = alias_relationship(entity)
        shot: EntityField[Optional[Shot]] = alias_relationship(entity)

    # Create a filter using target selector
    filter = Task.entity.Shot.id.eq(123)
    # Create a filter using the alias
    filter = Task.shot.id.eq(123)
    ```
    """
    field: EntityField[Any] = EntityField()
    field.__info__.alias_field = target_relationship
    return field
