"""Definition of all the fields used by Shotgrid entities.

The main function of these fields is to provide the correct type annotations.
Internally, only the classes inheriting from InstrumentedAttribute are used.
"""

from __future__ import annotations

import abc
from collections.abc import Collection
from datetime import date
from datetime import datetime
from typing import TYPE_CHECKING
from typing import Any
from typing import Callable
from typing import ClassVar
from typing import Dict
from typing import Generic
from typing import Iterable
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
from .descriptor import FieldDescriptor
from .queryop import SgFieldCondition
from .row import SgRow

if TYPE_CHECKING:
    from .entity import SgEntity
    from .meta import SgEntityMeta

T = TypeVar("T")
T2 = TypeVar("T2")


class AbstractField(Generic[T], metaclass=abc.ABCMeta):
    """Definition of an abstract field."""

    cast_type: Type[T]
    default_value: ClassVar
    __sg_type__: str = ""

    @classmethod
    @abc.abstractmethod
    def create_from_annotation(
        cls,
        field_annotation: FieldAnnotation,
        descriptor: FieldDescriptor,
    ) -> Self:
        """Create a field from a descriptor."""

    def __init__(
        self,
        source_class: SgEntityMeta,
        class_: SgEntityMeta,
        field_annotation: FieldAnnotation[T],
        attr_name: str,
        name: str,
        default_value: T,
        primary: bool,
    ):
        """Initialize an instrumented attribute.

        Args:
            source_class (SgEntityMeta): the original class for this attribute
            class_ (SgEntityMeta): the class the instrumented attribute belongs to
            field_annotation (FieldAnnotation): the field annotation
            attr_name (str): the Python attribute name.
            name (str): the name of the field
            default_value (T): the default value of the attribute
            primary (bool): whether the attribute is primary or not
        """
        self._attr_name = attr_name
        self._name = name or attr_name
        self._src_class = source_class
        self._class = class_
        self._field_annotation = field_annotation
        self._default_value = default_value
        self._primary = primary

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

    # TODO: could we remove the need for the attribute name?
    def get_attribute_name(self) -> str:
        """Return the attribute name.

        Returns:
            str: the attribute name
        """
        return self._attr_name

    def get_source_class(self) -> SgEntityMeta:
        """Return the source class.

        Returns:
            SgEntityMeta: the source class
        """
        return self._src_class

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

    def is_primary(self) -> bool:
        """Return whether the attribute is primary.

        Returns:
            bool: True if the attribute is primary, False otherwise.
        """
        return self._primary

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
    def _relative_to(self, relative_attribute: AbstractField[Any]) -> Self:
        """Build a new attribute relative to the given attribute.

        Args:
            relative_attribute (InstrumentedAttribute[T]): the relative attribute

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


T_field = TypeVar("T_field", bound=AbstractField[Any])


class AbstractValueField(AbstractField[T], metaclass=abc.ABCMeta):
    """Definition of an abstract value field."""

    @classmethod
    def create_from_annotation(
        cls,
        annotation: FieldAnnotation,
        descriptor: FieldDescriptor,
    ) -> Self:
        """Create a field from a descriptor."""
        return cls(
            source_class=annotation.entity_class,
            class_=annotation.entity_class,
            field_annotation=annotation,
            attr_name=annotation.attribute_name,
            name=descriptor.name,
            default_value=descriptor.default,
            name_in_relation=descriptor.name_in_relation,
            primary=descriptor.primary,
        )

    def __init__(
        self,
        source_class: SgEntityMeta,
        class_: SgEntityMeta,
        field_annotation: FieldAnnotation[T],
        attr_name: str,
        name: str,
        default_value: T,
        name_in_relation: str = "",
        primary: bool = False,
    ):
        """Initialize an instrumented field.

        Args:
            source_class (SgEntityMeta): the class of the source entity
            class_ (SgEntityMeta): the class the instrumented attribute belongs to
            field_annotation (FieldAnnotation): the field annotation
            attr_name (str): the Python attribute name.
            name (str): the name of the field
            default_value (T): the default value of the attribute
            name_in_relation (str): the name of the attribute in the relationship
            primary (bool): if True the attribute is primary (True) or not (False)
        """
        super().__init__(
            source_class,
            class_,
            field_annotation,
            attr_name,
            name,
            default_value,
            primary,
        )
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
        return (self.cast_type,)

    def _relative_to(self, relative_attribute: AbstractField[Any]) -> Self:
        """Build a new instrumented field relative to the given attribute.

        Args:
            relative_attribute (InstrumentedAttribute[T]): the relative attribute

        Returns:
            InstrumentedField[T]: the attribute relative to the given attribute
        """
        new_field_name = ".".join(
            [
                relative_attribute.get_name(),
                self.get_parent_class().__sg_type__,
                self.get_name(),
            ]
        )
        return self.__class__(
            relative_attribute.get_source_class(),
            self._class,
            self._field_annotation,
            self.get_attribute_name(),
            new_field_name,
            default_value=self.get_default_value(),
            name_in_relation=self.get_name_in_relation(),
            primary=self._primary,
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

    cast_type: Type[int] = int
    __sg_type__: str = "number"
    default_value: ClassVar[Optional[int]] = None

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
    default_value: ClassVar[Optional[float]] = None

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
    default_value: ClassVar[Optional[str]] = None

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

    def __init__(
        self,
        source_class: SgEntityMeta,
        class_: SgEntityMeta,
        field_annotation: FieldAnnotation[T],
        attr_name: str,
        name: str,
        default_value: T,
        lazy_collection: LazyEntityCollectionClassEval,
        alias: bool,
    ):
        """Initialize an instrumented relationship field.

        Args:
            source_class (SgEntityMeta): the source class of this attribute
            class_ (SgEntityMeta): the class the instrumented attribute belongs to
            field_annotation (FieldAnnotation): the field annotation
            attr_name (str): the Python attribute name.
            name (str): the name of the field
            default_value (T): the default value of the attribute
            lazy_collection (LazyEntityCollectionClassEval): the lazy entity collection
                used to get the target entity
            alias (bool): whether this field is an alias for another field
        """
        super().__init__(
            source_class,
            class_,
            field_annotation,
            attr_name,
            name,
            default_value,
            False,
        )
        self._lazy_collection = lazy_collection
        self._alias = alias

    def is_alias(self) -> bool:
        """Return whether the attribute is an alias.

        Always return False.

        Returns:
            bool: always False
        """
        return self._alias

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

    def f(self, field: T_field) -> T_field:
        """Return the given field in relation to the given field."""
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


class EntityField(AbstractEntityField[T]):
    """Definition a field targeting a single entity."""

    __sg_type__: str = "entity"
    default_value = None
    cast_type: Type[T]

    @classmethod
    def create_from_annotation(
        cls,
        field_annotation: FieldAnnotation,
        descriptor: FieldDescriptor,
    ) -> Self:
        """Creates an entity field from a field annotation."""
        entities = field_annotation.entities
        container_class = field_annotation.container_class
        entity_class = field_annotation.entity_class
        # Make some checks
        if len(entities) == 0:
            raise error.SgInvalidAnnotationError(
                "An entity field must provide a target entity"
            )
        aliased_field = descriptor.aliased_field
        if aliased_field:
            if len(field_annotation.entities) != 1:
                raise error.SgInvalidAnnotationError(
                    "A alias field shall target a single entity"
                )
            # Make sure the entity type in annotation is in the target annotation
            target_entity = field_annotation.entities[0]
            # Find the target mapped annotation
            target_instrumentation = field_annotation.entity_class.__fields__[
                aliased_field.attr_name
            ]
            target_annotation = target_instrumentation.get_field_annotation()
            if target_entity not in target_annotation.entities:
                raise error.SgInvalidAnnotationError(
                    "An alias field must target a multi target field containing "
                    "its entity"
                )
        if container_class:
            raise error.SgInvalidAnnotationError(
                "An entity field shall not have a container annotation"
            )
        # Construct a multi target entity
        lazy_evals = [
            LazyEntityClassEval(entity, entity_class.__registry__)
            for entity in entities
        ]
        lazy_collection = LazyEntityCollectionClassEval(lazy_evals)
        return cls(
            source_class=entity_class,
            class_=entity_class,
            field_annotation=field_annotation,
            attr_name=field_annotation.attribute_name,
            name=descriptor.name,
            default_value=descriptor.default,
            lazy_collection=lazy_collection,
            alias=descriptor.aliased_field is not None,
        )

    def _relative_to(self, relative_attribute: AbstractField[Any]) -> EntityField[T]:
        """Build a new instrumented relationship relative to the given attribute.

        Args:
            relative_attribute (InstrumentedAttribute[T]): the relative attribute

        Returns:
            InstrumentedMultiTargetSingleRelationship[T]: the attribute relative to
                the given attribute
        """
        new_field_name = ".".join(
            [
                relative_attribute.get_name(),
                self.get_parent_class().__sg_type__,
                self.get_name(),
            ]
        )
        return self.__class__(
            relative_attribute.get_source_class(),
            self._class,
            self._field_annotation,
            new_field_name,
            new_field_name,
            self._default_value,
            self._lazy_collection,
            self._alias,
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

    if TYPE_CHECKING:

        @overload
        def __get__(self, instance: None, owner: Any) -> EntityField[T]: ...

        @overload
        def __get__(self, instance: Any, owner: Any) -> Optional[T]: ...

        def __get__(
            self, instance: Optional[Any], owner: Any
        ) -> Union[Optional[T], EntityField[T]]:
            """Return the value of the field."""


class MultiEntityField(AbstractEntityField[T]):
    """Definition a field targeting multiple entities."""

    __sg_type__: str = "multi_entity"
    default_value: ClassVar[List[Any]] = []

    @classmethod
    def create_from_annotation(cls, annotation: FieldAnnotation,
                               descriptor: FieldDescriptor) -> Self:
        """Create an instance of a field from a field annotation."""
        entities = annotation.entities
        container_class = annotation.container_class
        entity_class = annotation.entity_class
        # Make some checks
        if len(entities) == 0:
            raise error.SgInvalidAnnotationError(
                "An entity field must provide a target entity"
            )
        if container_class is not list:
            raise error.SgInvalidAnnotationError(
                "A multi entity field requires a list annotation"
            )
        # Construct a multi target entity
        lazy_evals = [
            LazyEntityClassEval(entity, entity_class.__registry__)
            for entity in entities
        ]
        lazy_collection = LazyEntityCollectionClassEval(lazy_evals)
        return cls(
            source_class=entity_class,
            class_=entity_class,
            field_annotation=annotation,
            attr_name=annotation.attribute_name,
            name=descriptor.name,
            default_value=descriptor.default,
            lazy_collection=lazy_collection,
            alias=False,
        )

    def _relative_to(
        self, relative_attribute: AbstractField[Any]
    ) -> MultiEntityField[T]:
        """Build a new instrumented relationship relative to the given attribute.

        Args:
            relative_attribute (InstrumentedAttribute[T]): the relative attribute

        Returns:
            MultiEntityField[T]: the attribute relative to the given attribute
        """
        new_field_name = ".".join(
            [
                relative_attribute.get_name(),
                self.get_parent_class().__sg_type__,
                self.get_name(),
            ]
        )
        return self.__class__(
            relative_attribute.get_source_class(),
            self._class,
            self._field_annotation,
            new_field_name,
            new_field_name,
            self._default_value,
            self._lazy_collection,
            self._alias,
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
    default_value: ClassVar[Optional[bool]] = None

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
    default_value: ClassVar[Optional[date]] = None

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
    default_value: ClassVar[Optional[datetime]] = None

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
    default_value: ClassVar[Optional[str]] = None

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
    default_value: ClassVar[Optional[List[str]]] = None

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
    default_value: ClassVar[Optional[Dict[str, Any]]] = None

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
    default_value: ClassVar[str]

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
    default_value: ClassVar[Optional[str]] = None

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
