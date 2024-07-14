"""Defines the base entity class."""

from __future__ import annotations

import inspect
import sys
from collections import defaultdict
from typing import Any
from typing import Generic
from typing import TypeVar

from . import error
from . import field_info
from .fields import AbstractField
from .fields import FieldAnnotation
from .fields import NumberField
from .fields import add_field_to_entity
from .fields import initialize_from_annotation
from .typing_util import get_annotations

T = TypeVar("T")


class FieldProperty(Generic[T]):
    """A field descriptor wrapping the access data of fields."""

    def __init__(
        self,
        field: AbstractField[T],
        settable: bool = True,
    ) -> None:
        """Initialize the field descriptor.

        Args:
            field: the field to wrap.
            settable: whether the attribute is settable or not.
        """
        self._field = field
        self._settable = settable

    def __get__(self, instance: SgBaseEntity | None, obj_type: Any = None) -> Any:
        """Return the value of the attribute from the internal state of the instance.

        From the class itself, it returns the wrapped instrumented attribute.

        Args:
            instance: the instance of the attribute.
            obj_type: the type of the attribute.

        Returns:
            the value of the attribute or the instrumented attribute.
        """
        if instance is None:
            return self._field
        state = instance.__state__
        if not state.is_available(self._field):
            raise error.SgMissingFieldError(f"{self._field} has not been queried")
        return state.get_value(self._field)

    def __set__(self, instance: SgBaseEntity, value: T) -> None:
        """Set the state internal value of the instance.

        Args:
            instance: the instance of the attribute.
            value: the value to set.

        Raises:
            ValueError: raised when the attribute is not settable.
        """
        if not self._settable:
            raise ValueError(f"Field {self._field} is not settable")
        state = instance.__state__
        # Test against current value
        old_value = state.get_original_value(self._field)
        # Register state change
        if value != old_value:
            state.modified_fields.append(self._field)
        else:
            if self._field in state.modified_fields:
                state.modified_fields.remove(self._field)
        instance.__state__.set_value(self._field, value)


class AliasFieldProperty(FieldProperty[T]):
    """Defines an alias field descriptor."""

    def __get__(self, instance: SgBaseEntity | None, obj_type: Any = None) -> Any:
        """Return the value of the targeted field.

        Args:
            instance: the instance of the field.
            obj_type: the type of the field.

        Returns:
            the value of the targeted field.
        """
        if instance is None:
            return self._field
        # Get the aliased field
        aliased_field = field_info.get_alias(self._field)
        assert aliased_field is not None
        target_value = instance.__state__.get_value(aliased_field)
        if target_value is None:
            return None
        expected_target_class = field_info.get_types(self._field)
        if not isinstance(target_value, expected_target_class):
            return None
        return target_value


class EntityState(object):
    """Defines the internal state of the instance field values."""

    __slots__ = (
        "_entity",
        "pending_add",
        "pending_deletion",
        "deleted",
        "_values",
        "_available",
        "modified_fields",
        "_original_values",
    )

    def __init__(
        self, instance: SgBaseEntity, values_per_field: dict[AbstractField[T], T]
    ):
        """Initialize the internal state of the instance.

        Args:
            instance: the instance of the field.
            values_per_field: initialize the state with the given field values.
                These fields will be marked as modified (expect primary key).
                All other fields will be initialized to their default value.
        """
        self._entity = instance
        self.pending_add = False
        self.pending_deletion = False
        self.deleted = False
        self._values: dict[AbstractField[Any], T] = values_per_field
        self._available: dict[AbstractField[Any], bool] = defaultdict(lambda: True)
        self.modified_fields: list[AbstractField[Any]] = list(
            filter(lambda f: not field_info.is_primary(f), values_per_field)
        )
        self._original_values: dict[AbstractField[T], T] = {}

    def is_modified(self) -> bool:
        """Return whether the entity is modified for its initial state.

        Returns:
            True if the entity is modified for its initial state. False otherwise.
        """
        return bool(self.modified_fields)

    def is_commited(self) -> bool:
        """Return whether the entity is already commited.

        Returns:
            True if the entity is commited. False otherwise.
                Note this may not represent the known state of the entity.
                It may not match the current state of the entity in Shotgrid.
        """
        return self._entity.id is not None

    def get_original_value(self, field: AbstractField[T]) -> T | None:
        """Return the entity initial value of the given attribute.

        Args:
            field: the name of the attribute.

        Returns:
            the entity initial value of the given attribute.
        """
        return self._original_values.get(field)

    def get_value(self, field: AbstractField[T]) -> T:
        """Return the value of the field."""
        return self._values.get(field, field_info.get_default_value(field))

    def set_value(self, field: AbstractField[T], value: T) -> None:
        """Sets the value of the field."""
        self._values[field] = value

    def is_available(self, field: AbstractField[Any]) -> bool:
        """Return True if the field is available."""
        return self._available[field]

    def set_available(self, field: AbstractField[Any], available: bool) -> None:
        """Sets the availability of the field value."""
        self._available[field] = available

    def set_as_original(self) -> None:
        """Set the current state of the entity as its original state."""
        self._original_values = self._values.copy()
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
        cls,
        class_name: str,
        bases: tuple[type[Any], ...],
        dict_: dict[str, Any],
    ):
        """Initialize the new class.

        Args:
            class_name: the name of the class.
            bases: the base classes of the class.
            dict_: the attributes of the class.

        Raises:
            error.SgEntityClassDefinitionError: raised if the definition of the class
                is invalid.
        """
        field_intersect = set(dict_).intersection(
            {
                "__fields__",
                "__fields_by_attr__",
                "__instance_state__",
                "__attr_per_field_name__",
                "__registry__",
            }
        )
        if field_intersect and bases:
            raise error.SgEntityClassDefinitionError(
                f"Attributes {field_intersect} are reserved."
            )
        return type.__new__(cls, class_name, bases, dict_)

    def __init__(cls, class_name, bases, dict_):
        super().__init__(class_name, bases, dict_)
        # Get the registry back from parent class
        cls.__sg_type__: str = dict_.get("__sg_type__", "")
        cls.__instance_state__: EntityState  # noqa: B032
        cls.__is_root__: bool = len(bases) == 0
        if cls.__is_root__:
            return
        cls.__is_base__: bool = bases[0].__is_root__ if bases else False
        # Check if we are initializing a base class
        if cls.__is_base__:
            cls.__registry__: dict[str, SgEntityMeta] = {}
            return
        # We are initializing subclass of base
        if not cls.__sg_type__:
            raise error.SgEntityClassDefinitionError(
                f"Missing __sg_type__ attribute in {class_name}"
            )
        other_entity_by_type = {
            entity.__sg_type__: entity for entity in cls.__registry__.values()
        }
        other_entity = other_entity_by_type.get(cls.__sg_type__)
        if other_entity:
            other_file = inspect.getfile(other_entity)
            cls_file = inspect.getfile(cls)
            raise error.SgEntityClassDefinitionError(
                f"Entity {class_name} defined at {cls_file} uses "
                f'__sg_type__ = "{cls.__sg_type__}" which is already used by '
                f"{other_entity.__name__} defined at {other_file}."
            )
        # Prepare global variables for evaluating the annotations
        cls_namespace = dict(cls.__dict__)
        cls_namespace.setdefault(cls.__name__, cls)
        original_scope = sys.modules[cls.__module__].__dict__.copy()
        original_scope.update(cls_namespace)

        # Add the common id field
        field_id = NumberField()
        initialize_from_annotation(
            field_id, FieldAnnotation(NumberField, tuple()), "id"
        )
        field_id.__info__["primary"] = True
        add_field_to_entity(cls, field_id)
        cls.__fields__: list[AbstractField[Any]] = [field_id]
        cls.__fields_by_attr__: dict[str, AbstractField[Any]] = {"id": field_id}
        cls.__attr_per_field_name__: dict[str, str] = {"id": "id"}
        cls.id = FieldProperty(field_id, False)
        field_names = {"id"}

        # Add the field args from the class we are building
        for attr_name, annot in get_annotations(cls).items():
            # Extract entity information from annotation
            try:
                field_annot = FieldAnnotation.extract(annot, original_scope)
            except error.SgInvalidAnnotationError as e:
                raise error.SgEntityClassDefinitionError(
                    f"Cannot extract annotation information for field "
                    f"{class_name}.{attr_name}"
                ) from e
            if not field_annot.is_field():
                continue

            # Build the field if it is not already declared
            field = dict_.get(attr_name, field_annot.field_type(name=attr_name))
            if not isinstance(field, AbstractField):
                raise error.SgEntityClassDefinitionError(
                    f"{class_name}.{attr_name} is not initialized with a field."
                )

            try:
                initialize_from_annotation(field, field_annot, attr_name)
            except error.SgInvalidAnnotationError as e:
                raise error.SgEntityClassDefinitionError(
                    f"Cannot build instrumentation for field {class_name}.{attr_name}"
                ) from e
            add_field_to_entity(cls, field)
            field_name = field_info.get_name(field)
            # Check we are not redefining a field
            if not field_info.is_alias(field):
                if field_name in field_names:
                    raise error.SgEntityClassDefinitionError(
                        f"Field named '{field_name}' is already defined"
                    )
                field_names.add(field_name)
                cls.__attr_per_field_name__[field_name] = attr_name
                # Add to the class
                cls.__fields_by_attr__[attr_name] = field
                cls.__fields__.append(field)
            # Create field descriptors
            prop = AliasFieldProperty if field_info.is_alias(field) else FieldProperty
            setattr(cls, attr_name, prop(field, True))

        cls.__registry__[cls.__name__] = cls


class SgBaseEntity(metaclass=SgEntityMeta):
    """Base class for any Shotgrid entity.

    When implementing a new model, you shall subclass this class.
    It provides only the "id" field which is common to all Shotgrid entities.
    """

    def __init_subclass__(cls, **kwargs) -> None:
        """Initialize the entity subclass."""
        # If we are directly subclassing, we shall not have any __sg_type__
        if SgBaseEntity in cls.__bases__:
            if "__sg_type__" in cls.__dict__:
                raise error.SgEntityClassDefinitionError(
                    "Cannot subclass SgBaseEntity directly to create an entity. "
                    "Please subclass SgBaseEntity in your own base class."
                )
        else:
            # Check we are not defining a class in the same class container
            if cls.__name__ in cls.__registry__:
                module_file = inspect.getfile(cls)
                raise error.SgEntityClassDefinitionError(
                    f"Class {cls.__name__} already defined in module at {module_file}."
                )
        cls.__is_base__ = True
        super().__init_subclass__(**kwargs)

    def __init__(self: Any, **kwargs: Any) -> None:
        """Initializes the entity from keyword arguments.

        Args:
            kwargs: Keyword arguments.

        Raises:
            error.SgInvalidAttributeError: raised when a keyword argument is not a
                field of the entity.
        """
        # Compute the values per field
        try:
            value_per_field = {self.__fields_by_attr__[k]: v for k, v in kwargs.items()}
        except KeyError as e:
            raise error.SgInvalidAttributeError(e.args) from e
        # We set the values directly in the state to avoid the cost of using the
        # properties.
        self.__state__ = EntityState(self, value_per_field)

    def __repr__(self) -> str:
        """Returns a string representation of the entity."""
        return f"{self.__class__.__name__}(id={self.id})"
