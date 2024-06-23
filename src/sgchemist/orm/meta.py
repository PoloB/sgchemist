"""Defines the metaclass for any entity."""

from __future__ import annotations

import dataclasses
import inspect
import sys
from typing import TYPE_CHECKING
from typing import Any
from typing import ClassVar
from typing import Dict
from typing import Generic
from typing import List
from typing import Optional
from typing import Set
from typing import Tuple
from typing import Type
from typing import TypeVar

from typing_extensions import get_origin

from . import error
from .field import AbstractEntityField
from .field import AbstractField
from .field_descriptor import FieldAnnotation
from .field_descriptor import MappedColumn
from .field_descriptor import MappedField
from .field_descriptor import Relationship
from .field_descriptor import extract_annotation_info
from .instrumentation import InstrumentedAttribute
from .typing_util import de_stringify_annotation
from .typing_util import get_annotations

T = TypeVar("T")

if TYPE_CHECKING:
    from .entity import SgEntity
    from .session import Session


@dataclasses.dataclass
class FieldSlot:
    """A container for field value."""

    value: Any
    available: bool


class FieldDescriptor(Generic[T]):
    """A field descriptor wrapping the access data of fields."""

    def __init__(
        self,
        instrumented_attribute: InstrumentedAttribute[T],
        attr_name: str,
        settable: bool = True,
    ) -> None:
        """Initialize the field descriptor.

        Args:
            instrumented_attribute (InstrumentedAttribute[T]): the instrumented
                attribute to wrap.
            attr_name (str): the name of the attribute.
            settable (bool): whether the attribute is settable or not.
        """
        self._field = instrumented_attribute
        self._attr_name = attr_name
        self._settable = settable

    def __get__(self, instance: Optional[SgEntity], obj_type: Any = None) -> Any:
        """Return the value of the attribute from the internal state of the instance.

        From the class itself, it returns the wrapped instrumented attribute.

        Args:
            instance (Optional[SgEntity]): the instance of the attribute.
            obj_type (Any): the type of the attribute.

        Returns:
            Any: the value of the attribute or the instrumented attribute.
        """
        if instance is None:
            return self._field
        slot = instance.__state__.get_slot(self._attr_name)
        if not slot.available:
            raise error.SgMissingFieldError(f"{self._field} has not been queried")
        return slot.value

    def __set__(self, instance: SgEntity, value: T) -> None:
        """Set the state internal value of the instance.

        Args:
            instance (Optional[SgEntity]): the instance of the attribute.
            value (T): the value to set.

        Raises:
            ValueError: raised when the attribute is not settable.
        """
        if not self._settable:
            raise ValueError(f"Field {self._field} is not settable")
        state = instance.__state__
        # Test against current value
        old_value = state.get_original_value(self._attr_name)
        # Register state change
        if value != old_value:
            state.modified_fields.append(self._field)
        else:
            if self._field in state.modified_fields:
                state.modified_fields.remove(self._field)
        instance.__state__.get_slot(self._attr_name).value = value


class AliasFieldDescriptor(FieldDescriptor[T]):
    """Defines an alias field descriptor."""

    def __get__(self, instance: Optional[SgEntity], obj_type: Any = None) -> Any:
        """Return the value of the targeted field.

        Args:
            instance (Optional[SgEntity]): the instance of the field.
            obj_type (Any): the type of the field.

        Returns:
            Any: the value of the targeted field.
        """
        if instance is None:
            return self._field
        # Get the aliased field
        target_field_name = self._field.get_name()
        class_ = self._field.get_parent_class()
        target_attr_name = class_.__attr_per_field_name__[target_field_name]
        target_value = instance.__state__.get_slot(target_attr_name).value
        if target_value is None:
            return None
        expected_target_class = self._field.get_types()
        if not isinstance(target_value, expected_target_class):
            return None
        return target_value


class EntityState(object):
    """Defines the internal state of the instance field values."""

    def __init__(self, instance: SgEntity):
        """Initialize the internal state of the instance.

        Args:
            instance (SgEntity): the instance of the field.
        """
        self._model_instance = instance
        self.pending_add = False
        self.pending_deletion = False
        self.deleted = False
        self._original_values: Dict[str, Any] = {}
        self._slots: Dict[str, FieldSlot] = {
            attr_name: FieldSlot(None, available=True)
            for attr_name in instance.__fields__
        }
        self.modified_fields: List[InstrumentedAttribute[Any]] = []
        self.session: Optional[Session] = None

    def is_modified(self) -> bool:
        """Return whether the entity is modified for its initial state.

        Returns:
            bool: True if the entity is modified for its initial state.
                False otherwise.
        """
        return bool(self.modified_fields)

    def is_commited(self) -> bool:
        """Return whether the entity is already commited.

        Returns:
            bool: True if the entity is commited. False otherwise.
                Note this may not represent the known state of the entity.
                It may not match the current state of the entity in Shotgrid.
        """
        return self._model_instance.id is not None

    def get_original_value(self, attr_name: str) -> Any:
        """Return the entity initial value of the given attribute.

        Args:
            attr_name (str): the name of the attribute.

        Returns:
            Any: the entity initial value of the given attribute.
        """
        return self._original_values.get(attr_name)

    def get_slot(self, attr_name: str) -> FieldSlot:
        """Return the entity value of the given attribute (i.e. the current value).

        Args:
            attr_name (str): the name of the attribute.

        Returns:
            FieldSlot: the field slot for the given attribute
        """
        return self._slots[attr_name]

    def set_as_original(self) -> None:
        """Set the current state of the entity as its original state."""
        for key, slot in self._slots.items():
            self._original_values[key] = slot.value
        self.modified_fields = []


_all_fields = {
    name: field_cls
    for name, field_cls in inspect.getmembers(sys.modules[AbstractField.__module__])
    if isinstance(field_cls, type) and issubclass(field_cls, AbstractField)
}


class SgEntityMeta(type):
    """Base metaclass for all entity types.

    It is responsible for:
    - checking the validity of the class definition,
    - extracting information from the field annotations,
    - constructing the instrumented attributes,
    - wrapping instrumented attributes in field descriptors
    """

    def __new__(
        cls, name: str, bases: Tuple[Type[Any], ...], attrs: Dict[str, Any]
    ) -> SgEntityMeta:
        """Creates a new entity class.

        It makes sure that no reserved attributes are defined within the class to
        create.

        Args:
            name (str): the name of the entity class.
            bases (tuple[type[Any], ...]): the base classes of the entity class.
            attrs (dict[str, Any]): the attributes of the entity class.

        Returns:
            SgEntityMeta: the new entity class.

        Raises:
            error.SgEntityClassDefinitionError: raised if the definition of the class
                is invalid.
        """
        field_intersect = set(attrs).intersection(
            {
                "__fields__",
                "__instance_state__",
                "__attr_per_field_name__",
                "__primaries__",
                "__registry__",
            }
        )
        is_abstract = attrs.get("__abstract__", False)
        if field_intersect and not is_abstract:
            raise error.SgEntityClassDefinitionError(
                f"Attributes {field_intersect} are reserved."
            )
        return type.__new__(cls, name, bases, attrs)

    def __init__(
        cls,
        class_name: str,
        bases: Tuple[Type[Any], ...],
        dict_: Dict[str, Any],
    ):
        """Initialize the new class.

        Args:
            class_name (str): the name of the class.
            bases (tuple[type[Any], ...]): the base classes of the class.
            dict_ (dict[str, Any]): the attributes of the class.

        Raises:
            error.SgEntityClassDefinitionError: raised if the definition of the class
                is invalid.
        """
        super().__init__(class_name, bases, dict_)
        cls.__fields__: Dict[str, InstrumentedAttribute[Any]] = {}
        cls.__sg_type__: str = dict_.get("__sg_type__", "")
        cls.__abstract__ = dict_.get("__abstract__", False)
        cls.__instance_state__: EntityState  # noqa: B032
        cls.__attr_per_field_name__ = {}
        # Get the registry back from parent class
        cls.__registry__ = {}
        for base in bases:
            registry = base.__dict__.get("__registry__")
            if registry:
                cls.__registry__ = registry
                break

        # Check the basic attributes
        if not cls.__abstract__ and not cls.__sg_type__:
            raise error.SgEntityClassDefinitionError(
                f"Missing __sg_type__ attribute in model {class_name}"
            )

        # Get all the fields from the parent classes
        all_fields: Dict[str, InstrumentedAttribute[Any]] = {}
        all_primaries: Set[str] = set()
        for base in bases:
            base_fields = base.__fields__ if hasattr(base, "__fields__") else {}
            all_primaries.update(
                base.__primaries__ if hasattr(base, "__primaries__") else {}
            )
            all_fields.update(base_fields)
        cls.__fields__ = all_fields
        cls.__attr_per_field_name__ = {
            field.get_name(): attr_name for attr_name, field in all_fields.items()
        }
        cls.__primaries__ = all_primaries
        field_names = set(field.get_name() for field in all_fields.values())

        # Name and store new fields
        for attr_name, annot in get_annotations(cls).items():
            try:
                field_type, annot = de_stringify_annotation(
                    cls, annot, cls.__module__, _all_fields
                )
            except Exception as e:
                raise error.SgEntityClassDefinitionError(
                    f"Cannot destringify annotation {annot} "
                    f"for field {class_name}.{attr_name}"
                ) from e

            # We shall never care about ClassVar
            if get_origin(annot) is ClassVar:
                continue

            if not isinstance(field_type, type) or not issubclass(
                field_type, AbstractField
            ):
                raise error.SgEntityClassDefinitionError(
                    f"{class_name}.{attr_name} is not a field annotation."
                )
            # Check we are not overlapping attributes over relationship
            if attr_name in InstrumentedAttribute.__dict__:
                raise error.SgEntityClassDefinitionError(
                    f"Attribute {attr_name} overlap with instrumented attributes. "
                    f"Please use other variable names for your fields"
                )
            map_field = dict_.get(attr_name)
            if not map_field:
                map_type = (
                    Relationship
                    if issubclass(field_type, AbstractEntityField)
                    else MappedField
                )
                map_field = map_type(attr_name)
            if not isinstance(map_field, MappedColumn):
                raise error.SgEntityClassDefinitionError(
                    f"{class_name}.{attr_name} is not a mapped column."
                )
            # Extract entity information from annotation
            entities, container_class = extract_annotation_info(annot)
            entity_annot = FieldAnnotation(cls, field_type, entities, container_class)
            map_field.attr_name = attr_name
            # Build the instrumented attribute
            try:
                field = map_field.get_instrumented(entity_annot)
            except error.SgInvalidAnnotationError as e:
                raise error.SgEntityClassDefinitionError(
                    f"Cannot build instrumentation for field {class_name}.{attr_name}"
                ) from e
            field_name = field.get_name()
            # Add attribute to primaries if needed
            if map_field.primary:
                cls.__primaries__.add(attr_name)
            # Check we are not redefining a field
            if not field.is_alias():
                if field_name in field_names:
                    raise error.SgEntityClassDefinitionError(
                        f"Field named '{field_name}' is already defined"
                    )
                field_names.add(field_name)
                cls.__attr_per_field_name__[field_name] = attr_name
                # Add to the class
                cls.__fields__[attr_name] = field
            # Create field descriptors
            descriptor = AliasFieldDescriptor if field.is_alias() else FieldDescriptor
            setattr(cls, attr_name, descriptor(field, attr_name, not map_field.primary))
