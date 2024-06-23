"""Definition of instrumented attributes.

They are used internally instead of fields and act as a translation layer between
the Shotgrid row content and entity objects.
"""

from __future__ import absolute_import
from __future__ import annotations

import abc
from typing import TYPE_CHECKING
from typing import Any
from typing import Callable
from typing import Collection
from typing import Dict
from typing import Generic
from typing import Iterable
from typing import Iterator
from typing import List
from typing import Optional
from typing import Tuple
from typing import Type
from typing import TypeVar

from .constant import DateType
from .constant import Operator
from .queryop import SgFieldCondition
from .row import SgRow

T = TypeVar("T")
T_entity = TypeVar("T_entity")
T2 = TypeVar("T2")

if TYPE_CHECKING:
    from .entity import SgEntity
    from .field_descriptor import FieldAnnotation
    from .meta import SgEntityMeta


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


class InstrumentedAttribute(Generic[T], metaclass=abc.ABCMeta):
    """An abstract instrumented attribute."""

    def __init__(
        self,
        class_: SgEntityMeta,
        field_annotation: FieldAnnotation[T],
        attr_name: str,
        name: str,
        default_value: T,
    ):
        """Initialize an instrumented attribute.

        Args:
            class_ (Type[SgEntityMeta]): the class the instrumented attribute belongs to
            field_annotation (FieldAnnotation): the field annotation
            attr_name (str): the Python attribute name.
            name (str): the name of the field
            default_value (T): the default value of the attribute
        """
        self._attr_name = attr_name
        self._name = name or attr_name
        self._class = class_
        self._field_annotation = field_annotation
        self._default_value = default_value

    def __repr__(self) -> str:
        """Returns a string representation of the instrumented attribute.

        Returns:
            str: the instrumented attribute representation
        """
        return f"<{self.__class__.__name__}({self._name})>"

    def get_field_annotation(self) -> FieldAnnotation[T]:
        """Return the field annotation.

        Returns:
            FieldAnnotation[T]: the field annotation
        """
        return self._field_annotation

    def get_name(self) -> str:
        """Return the name of the field.

        Returns:
            str: the name of the field
        """
        return self._name

    def get_attribute_name(self) -> str:
        """Return the attribute name.

        Returns:
            str: the attribute name
        """
        return self._attr_name

    def get_parent_class(self) -> SgEntityMeta:
        """Return the parent class of the attribute.

        Returns:
            SgEntityMeta: the parent class of the attribute
        """
        return self._class

    def get_default_value(self) -> T:
        """Return the default value of the attribute.

        Returns:
            T: the default value of the attribute
        """
        return self._default_value

    @abc.abstractmethod
    def is_alias(self) -> bool:
        """Return whether the attribute is an alias.

        Returns:
            bool: whether the attribute is an alias
        """

    @abc.abstractmethod
    def get_name_in_relation(self) -> str:
        """Return the name of the field when queried from a relationship.

        Returns:
            str: the name of the field when queried from a relationship.
        """

    @abc.abstractmethod
    def get_types(self) -> Tuple[Type[Any], ...]:
        """Return the Python types of the attribute.

        Returns:
            tuple[Type[Any], ...]: Python types of the attribute
        """

    @abc.abstractmethod
    def build_relative_to(
        self,
        relative_attribute: InstrumentedAttribute[Any],
        through_entity: Type[SgEntity],
    ) -> InstrumentedAttribute[T]:
        """Build a new attribute relative to the given attribute.

        Args:
            relative_attribute (InstrumentedAttribute[T]): the relative attribute
            through_entity (Type[SgEntity]): the traversed entity type

        Returns:
            InstrumentedAttribute[T]: the attribute relative to the given attribute
        """

    @abc.abstractmethod
    def update_entity_from_row_value(self, entity: SgEntity, field_value: Any) -> None:
        """Update an entity from a row value.

        Used by the Session to convert the value returned by an update back to the
        entity field.

        Args:
            entity (SgEntity): the entity to update
            field_value: the row value
        """

    @abc.abstractmethod
    def iter_entities_from_field_value(self, field_value: Any) -> Iterator[SgEntity]:
        """Iterate entities from a field value.

        Used by the Session to get the entities within the field values if any.

        Args:
            field_value: Any

        Returns:
            Iterator[SgEntity]: the entities within the field value
        """

    @abc.abstractmethod
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

    @abc.abstractmethod
    def cast_column(
        self,
        column_value: Any,
        model_factory: Callable[[Type[SgEntity], SgRow[T]], T],
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

        def __getattr__(self, item: str) -> InstrumentedAttribute[T]:
            """Returns an instrumented attribute from attribute name."""


class InstrumentedField(InstrumentedAttribute[T]):
    """An generic value field."""

    def __init__(
        self,
        class_: SgEntityMeta,
        field_annotation: FieldAnnotation[T],
        attr_name: str,
        name: str,
        default_value: T,
        name_in_relation: str = "",
    ):
        """Initialize an instrumented field.

        Args:
            class_ (Type[SgEntityMeta]): the class the instrumented attribute belongs to
            field_annotation (FieldAnnotation): the field annotation
            attr_name (str): the Python attribute name.
            name (str): the name of the field
            default_value (T): the default value of the attribute
            name_in_relation (str): the name of the attribute in the relationship
        """
        super().__init__(class_, field_annotation, attr_name, name, default_value)
        self._name_in_relation = name_in_relation

    def is_alias(self) -> bool:
        """Return False.

        An instrumented field is not meant to be aliased.

        Returns:
            bool: always False
        """
        return False

    def get_name_in_relation(self) -> str:
        """Return the name of the field when queried from a relationship.

        Returns:
            str: the name of the field when queried from a relationship.
        """
        return self._name_in_relation or self._name

    def get_types(self) -> Tuple[Type[Any],]:
        """Return the Python type of the attribute.

        It always returns a tuple with a single type.

        Returns:
            tuple[Type[Any]]: Python types of the attribute
        """
        return (self.get_field_annotation().field_type.cast_type,)

    def build_relative_to(
        self,
        relative_attribute: InstrumentedAttribute[T],
        through_entity: Type[SgEntity],
    ) -> InstrumentedField[T]:
        """Build a new instrumented field relative to the given attribute.

        Args:
            relative_attribute (InstrumentedAttribute[T]): the relative attribute
            through_entity (Type[SgEntity]): the traversed entity type

        Returns:
            InstrumentedField[T]: the attribute relative to the given attribute
        """
        new_field_name = ".".join(
            [
                relative_attribute.get_name(),
                through_entity.__sg_type__,
                self.get_name(),
            ]
        )
        return self.__class__(
            self._class,
            self._field_annotation,
            self.get_attribute_name(),
            new_field_name,
            default_value=self.get_default_value(),
            name_in_relation=self.get_name_in_relation(),
        )

    def update_entity_from_row_value(self, entity: SgEntity, field_value: T) -> None:
        """Update an entity from a row value.

        It simply sets the value of the entity with the given value.

        Args:
            entity (SgEntity): the entity to update
            field_value: the row value
        """
        entity.__state__.get_slot(self.get_attribute_name()).value = field_value

    def iter_entities_from_field_value(self, field_value: Any) -> Iterator[SgEntity]:
        """Iterate entities from a field value.

        It simply returns an empty iterator because instrumented field never refer to
        other entities.

        Args:
            field_value: Any

        Returns:
            Iterator[SgEntity]: the entities within the field value
        """
        return iter([])

    def cast_value_over(
        self,
        func: Callable[[T], T2],
        value: T,
    ) -> T:
        """Apply the given function to the given value.

        Instrumented field never cast the value and simply return the given value.

        Args:
            func (Callable[[Any], Any]): the function to apply
            value (Any): the value on which to apply the function

        Returns:
            Any: result of the applied function
        """
        return value

    def cast_column(
        self,
        column_value: T,
        model_factory: Callable[[Type[SgEntity], SgRow[T]], T],
    ) -> T:
        """Cast the given row value to be used for instancing the entity.

        Simply returns the given value as instrumented fields never refer to another
        entity.

        Args:
            column_value (Any): the column value to cast
            model_factory (Callable[[Type[SgEntity], SgRow[T]], T]): the function to
                call for instantiating an entity from a row.

        Returns:
            Any: result of the applied function
        """
        return column_value


class InstrumentedRelationship(InstrumentedAttribute[T]):
    """A generic field targeting another entity."""

    def __init__(
        self,
        class_: SgEntityMeta,
        field_annotation: FieldAnnotation[T],
        attr_name: str,
        name: str,
        default_value: T,
        lazy_entity: LazyEntityClassEval,
        is_alias: bool = False,
    ) -> None:
        """Initialize an instrumented relationship field.

        Args:
            class_ (Type[SgEntityMeta]): the class the instrumented attribute belongs to
            field_annotation (FieldAnnotation): the field annotation
            attr_name (str): the Python attribute name.
            name (str): the name of the field
            default_value (T): the default value of the attribute
            lazy_entity (LazyEntityClassEval): the lazy entity to get the target entity
                class from.
            is_alias (bool): True if this relationship field is an alias for another
                relationship field.
        """
        super().__init__(class_, field_annotation, attr_name, name, default_value)
        self._is_alias = is_alias
        self._lazy_entity = lazy_entity

    def is_alias(self) -> bool:
        """Return whether the attribute is an alias.

        Returns:
            bool: whether the attribute is an alias
        """
        return self._is_alias

    def __getattr__(self, item: str) -> InstrumentedAttribute[Any]:
        """Returns a new instrumented attribute of the field target entity class.

        Args:
            item (str): the attribute name

        Returns:
            InstrumentedAttribute[Any] or Any: an instrumented attribute or the
                field attribute
        """
        target_model = self._lazy_entity.get()
        try:
            target_field = target_model.__fields__[item]
        except KeyError as e:
            raise AttributeError(
                f"Target model {target_model} has not field {item}"
            ) from e
        return target_field.build_relative_to(self, target_model)

    def build_relative_to(
        self,
        relative_attribute: InstrumentedAttribute[Any],
        through_entity: Type[SgEntity],
    ) -> InstrumentedRelationship[T]:
        """Build a new instrumented relationship relative to the given attribute.

        Args:
            relative_attribute (InstrumentedAttribute[T]): the relative attribute
            through_entity (Type[SgEntity]): the traversed entity type

        Returns:
            InstrumentedRelationship[T]: the attribute relative to the given attribute
        """
        new_field_name = ".".join(
            [
                relative_attribute.get_name(),
                through_entity.__sg_type__,
                self.get_name(),
            ]
        )
        return self.__class__(
            self._class,
            self._field_annotation,
            new_field_name,
            new_field_name,
            self.get_default_value(),
            self._lazy_entity,
        )

    def get_name_in_relation(self) -> str:
        """Return the name of the field when queried from a relationship.

        It always returns the name of the relationship assuming Shotgrid does not
        change the field key for entities.

        Returns:
            str: the name of the field when queried from a relationship.
        """
        return self._name

    def get_types(self) -> Tuple[Type[Any]]:
        """Return the Python type of the attribute.

        It always returns a tuple with a single entity type.

        Returns:
            tuple[Type[Any]]: entity class targeted by the relationship
        """
        return (self._lazy_entity.get(),)

    def update_entity_from_row_value(self, entity: SgEntity, field_value: T) -> None:
        """Update an entity from a row value.

        Entity fields are never updated calling an update on Shotgrid.

        Args:
            entity (SgEntity): the entity to update
            field_value: the row value
        """
        return

    def iter_entities_from_field_value(self, field_value: Any) -> Iterator[SgEntity]:
        """Iterate entities from a field value.

        Iterator of none or a single entity.

        Args:
            field_value: Any

        Returns:
            Iterator[SgEntity]: the entities within the field value
        """
        if field_value is None:
            return
        yield field_value

    def cast_value_over(
        self,
        func: Callable[[T], T2],
        value: T,
    ) -> T2:
        """Apply the given function to the given value.

        Instrumented relationship simply call the given func with the given value as
        argument.

        Args:
            func (Callable[[Any], Any]): the function to apply
            value (Any): the value on which to apply the function

        Returns:
            Any: result of the applied function
        """
        return func(value)

    def cast_column(
        self,
        column_value: Optional[SgRow[T]],
        model_factory: Callable[[Type[SgEntity], SgRow[T]], T],
    ) -> Optional[T]:
        """Cast the given row value to be used for instancing the entity.

        Instrumented relationship calls the model_factory function with the given
        column value to instantiate the related entity.

        Args:
            column_value (Any): the column value to cast
            model_factory (Callable[[Type[SgEntity], SgRow[T]], T]): the function to
                call for instantiating an entity from a row.

        Returns:
            Any: result of the applied function
        """
        if column_value is None:
            return None
        return model_factory(self._lazy_entity.get(), column_value)


class TargetSelector:
    """Defines a target type selector when using multi target entity relationship."""

    def __init__(
        self,
        multi_target_instrumentation: InstrumentedMultiTargetRelationship[T],
        target_entity: Type[SgEntity],
    ):
        """Initialize a target selector object.

        Args:
            multi_target_instrumentation (InstrumentedMultiTargetRelationship[T]):
                the source multi target instrumentation.
            target_entity (Type[SgEntity]): the target model
        """
        self._instru = multi_target_instrumentation
        self._target_entity = target_entity

    def __getattr__(self, item: str) -> Any:
        """Returns the field of the targeted entity."""
        try:
            target_field = self._target_entity.__fields__[item]
        except KeyError as e:
            raise AttributeError(
                f"{item} is not a valid target for field "
                f"{self._instru.get_parent_class().__name__}."
                f"{self._instru.get_name()}."
                f"{self._target_entity.__name__}"
            ) from e
        return target_field.build_relative_to(self._instru, self._target_entity)


class InstrumentedMultiTargetRelationship(InstrumentedAttribute[T], abc.ABC):
    """Defines a generic multi target relationship."""

    def __init__(
        self,
        class_: SgEntityMeta,
        field_annotation: FieldAnnotation[T],
        attr_name: str,
        name: str,
        default_value: T,
        lazy_collection: LazyEntityCollectionClassEval,
    ):
        """Initialize an instrumented relationship field.

        Args:
            class_ (Type[SgEntityMeta]): the class the instrumented attribute belongs to
            field_annotation (FieldAnnotation): the field annotation
            attr_name (str): the Python attribute name.
            name (str): the name of the field
            default_value (T): the default value of the attribute
            lazy_collection (LazyEntityCollectionClassEval): the lazy entity collection
                used to get the target entity
        """
        super().__init__(class_, field_annotation, attr_name, name, default_value)
        self._lazy_collection = lazy_collection

    def is_alias(self) -> bool:
        """Return whether the attribute is an alias.

        Always return False.

        Returns:
            bool: always False
        """
        return False

    def get_name_in_relation(self) -> str:
        """Return the name of the field when queried from a relationship.

        It always returns the name of the relationship assuming Shotgrid does not
        change the field key for entities.

        Returns:
            str: the name of the field when queried from a relationship.
        """
        return self._name

    def get_types(self) -> Tuple[Type[SgEntity], ...]:
        """Return the Python types the field can target.

        Returns:
            tuple[Type[SgEntity]]: entity class targeted by the relationship
        """
        return tuple(self._lazy_collection.get_all())

    def update_entity_from_row_value(self, entity: SgEntity, field_value: T) -> None:
        """Update an entity from a row value.

        Entity fields are never updated calling an update on Shotgrid.

        Args:
            entity (SgEntity): the entity to update
            field_value: the row value
        """
        return

    def __getattr__(self, item: str) -> Any:
        """Returns the field of the target entity or a target selector.

        A target selector is returned if there are multiple possible target types.

        Args:
            item (str): the name of the attribute

        Returns:
            Any: the field of the target entity or a target selector.\
        """
        target_models = self._lazy_collection.get_all()
        if len(target_models) > 1:
            try:
                target_model = self._lazy_collection.get_by_type(item)
            except KeyError:
                try:
                    return self.__getattribute__(item)
                except AttributeError as e:
                    raise AttributeError(
                        f"{self.get_parent_class().__name__}.{self.get_name()} "
                        f"is a multi target relationship. "
                        f"You must provide a target entity in "
                        f"{[t.__sg_type__ for t in self._lazy_collection.get_all()]} "
                        f"or use an alias relationship"
                    ) from e
            return TargetSelector(self, target_model)
        target_model = target_models[0]
        try:
            target_field = target_model.__fields__[item]
        except KeyError:
            return self.__getattribute__(item)
        return target_field.build_relative_to(self, target_model)


class InstrumentedMultiTargetSingleRelationship(InstrumentedMultiTargetRelationship[T]):
    """Defines a field target a single but multi target entity relationship."""

    def build_relative_to(
        self,
        relative_attribute: InstrumentedAttribute[T],
        through_entity: Type[SgEntity],
    ) -> InstrumentedMultiTargetSingleRelationship[T]:
        """Build a new instrumented relationship relative to the given attribute.

        Args:
            relative_attribute (InstrumentedAttribute[T]): the relative attribute
            through_entity (Type[SgEntity]): the traversed entity type

        Returns:
            InstrumentedMultiTargetSingleRelationship[T]: the attribute relative to
                the given attribute
        """
        new_field_name = ".".join(
            [
                relative_attribute.get_name(),
                through_entity.__sg_type__,
                self.get_name(),
            ]
        )
        return self.__class__(
            self._class,
            self._field_annotation,
            new_field_name,
            new_field_name,
            self._default_value,
            self._lazy_collection,
        )

    def get_name_in_relation(self) -> str:
        """Return the name of the field when queried from a relationship.

        It always returns the name of the relationship assuming Shotgrid does not
        change the field key for entities.

        Returns:
            str: the name of the field when queried from a relationship.
        """
        return self._name

    def iter_entities_from_field_value(self, field_value: Any) -> Iterator[SgEntity]:
        """Iterate entities from a field value.

        Iterator of none or a single entity.

        Args:
            field_value: Any

        Returns:
            Iterator[SgEntity]: the entities within the field value
        """
        if field_value is None:
            return
        yield field_value

    def cast_value_over(
        self,
        func: Callable[[T], T2],
        value: T,
    ) -> T2:
        """Apply the given function to the given value.

        Instrumented relationship simply call the given func with the given value as
        argument.

        Args:
            func (Callable[[Any], Any]): the function to apply
            value (Any): the value on which to apply the function

        Returns:
            Any: result of the applied function
        """
        return func(value)

    def cast_column(
        self,
        column_value: Optional[SgRow[T]],
        model_factory: Callable[[Type[SgEntity], SgRow[T]], T],
    ) -> Optional[T]:
        """Cast the given row value to be used for instancing the entity.

        Instrumented relationship calls the model_factory function with the given
        column value to instantiate the related entity.

        Args:
            column_value (Any): the column value to cast
            model_factory (Callable[[Type[SgEntity], SgRow[T]], T]): the function to
                call for instantiating an entity from a row.

        Returns:
            Any: result of the applied function
        """
        if column_value is None:
            return None
        return model_factory(
            self._lazy_collection.get_by_type(column_value.entity_type),
            column_value,
        )


class InstrumentedMultiRelationship(InstrumentedMultiTargetRelationship[T]):
    """Defines a field that can target multiple entities."""

    def build_relative_to(
        self,
        relative_attribute: InstrumentedAttribute[T],
        through_entity: Type[SgEntity],
    ) -> InstrumentedMultiRelationship[T]:
        """Build a new instrumented relationship relative to the given attribute.

        Args:
            relative_attribute (InstrumentedAttribute[T]): the relative attribute
            through_entity (Type[SgEntity]): the traversed entity type

        Returns:
            InstrumentedRelationship[T]: the attribute relative to the given attribute
        """
        new_field_name = ".".join(
            [
                relative_attribute.get_name(),
                through_entity.__sg_type__,
                self.get_name(),
            ]
        )
        return self.__class__(
            self._class,
            self._field_annotation,
            new_field_name,
            new_field_name,
            self._default_value,
            self._lazy_collection,
        )

    def iter_entities_from_field_value(
        self, field_value: Collection[Any]
    ) -> Iterator[SgEntity]:
        """Iterate entities from a field value.

        Args:
            field_value: Any

        Returns:
            Iterator[SgEntity]: the entities within the field value
        """
        return iter(field_value)

    def cast_value_over(
        self,
        func: Callable[[T], T2],
        value: Iterable[T],
    ) -> List[T2]:
        """Apply the given function to the given value.

        Instrumented multi relationship calls map each element of value to the given
        function.

        Args:
            func (Callable[[Any], Any]): the function to apply
            value (Any): the value on which to apply the function

        Returns:
            list: result of the applied function to every element of value
        """
        return [func(v) for v in value]

    def cast_column(
        self,
        column_value: Collection[SgRow[T]],
        model_factory: Callable[[Type[SgEntity], SgRow[T]], T],
    ) -> List[T]:
        """Cast the given row value to be used for instancing the entity.

        The model_factory function is called for every row of in the given column_value.

        Args:
            column_value (Any): the column value to cast
            model_factory (Callable[[Type[SgEntity], SgRow[T]], T]): the function to
                call for instantiating an entity from a row.

        Returns:
            list: result of the applied model factory over every element of the given
            column value.
        """
        return [
            model_factory(self._lazy_collection.get_by_type(col.entity_type), col)
            for col in column_value
        ]
