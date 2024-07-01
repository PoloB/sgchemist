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
from typing import Tuple
from typing import Type
from typing import TypeVar

from typing_extensions import get_origin

from . import error
from .annotation import FieldAnnotation
from .fields import AbstractField
from .typing_util import AnnotationScanType
from .typing_util import de_optionalize_union_types
from .typing_util import de_stringify_annotation
from .typing_util import expand_unions
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


class FieldProperty(Generic[T]):
    """A field descriptor wrapping the access data of fields."""

    def __init__(
        self,
        field: AbstractField[T],
        settable: bool = True,
    ) -> None:
        """Initialize the field descriptor.

        Args:
            field (AbstractField[T]): the instrumented
                attribute to wrap.
            settable (bool): whether the attribute is settable or not.
        """
        self._field = field
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
        slot = instance.__state__.get_slot(self._field)
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
        old_value = state.get_original_value(self._field)
        # Register state change
        if value != old_value:
            state.modified_fields.append(self._field)
        else:
            if self._field in state.modified_fields:
                state.modified_fields.remove(self._field)
        instance.__state__.get_slot(self._field).value = value


class AliasFieldProperty(FieldProperty[T]):
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
        aliased_field = self._field.__info__.alias_field
        assert aliased_field is not None
        target_value = instance.__state__.get_slot(aliased_field).value
        if target_value is None:
            return None
        expected_target_class = self._field.__cast__.get_types()
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
        self._original_values: Dict[AbstractField[Any], Any] = {}
        self._slots: Dict[AbstractField[Any], FieldSlot] = {
            field: FieldSlot(None, available=True)
            for field in instance.__fields__.values()
        }
        self.modified_fields: List[AbstractField[Any]] = []
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

    def get_original_value(self, field: AbstractField[Any]) -> Any:
        """Return the entity initial value of the given attribute.

        Args:
            field (AbstractField): the name of the attribute.

        Returns:
            Any: the entity initial value of the given attribute.
        """
        return self._original_values.get(field)

    def get_slot(self, field: AbstractField[Any]) -> FieldSlot:
        """Return the entity value of the given attribute (i.e. the current value).

        Args:
            field (AbstractField): the name of the attribute.

        Returns:
            FieldSlot: the field slot for the given attribute
        """
        return self._slots[field]

    def set_as_original(self) -> None:
        """Set the current state of the entity as its original state."""
        for field, slot in self._slots.items():
            self._original_values[field] = slot.value
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
        cls.__fields__: Dict[str, AbstractField[Any]] = {}
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

        # Get all the fields of the parent class and create new ones
        base_fields: Dict[str, AbstractField[Any]] = {}
        for base in bases:
            base_fields = base.__fields__ if hasattr(base, "__fields__") else {}
            base_fields.update(base_fields)

        field_args_per_attr = {}
        for attr_name, field in base_fields.items():
            new_field = field.__class__()
            new_field.__info__ = field.__info__.copy()
            field_args_per_attr[attr_name] = (new_field, new_field.__info__.annotation)

        # Add the field args from the class we are building
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
            field = dict_.get(attr_name, field_type(name=attr_name))
            if not isinstance(field, AbstractField):
                raise error.SgEntityClassDefinitionError(
                    f"{class_name}.{attr_name} is not initialized with a field."
                )
            # Extract entity information from annotation
            try:
                field_annot = FieldAnnotation(
                    field_type, extract_annotation_info(annot)
                )
            except error.SgInvalidAnnotationError as e:
                raise error.SgEntityClassDefinitionError(
                    f"Cannot extract annotation information for field "
                    f"{class_name}.{attr_name}"
                ) from e
            field_args_per_attr[attr_name] = (field, field_annot)

        cls.__primaries__ = set()
        field_names = set()

        for attr_name, (field, annotation) in field_args_per_attr.items():
            try:
                field.__info__.initialize_from_annotation(cls, annotation, attr_name)
                field.__cast__.initialize_from_annotation(cls, annotation)
            except error.SgInvalidAnnotationError as e:
                raise error.SgEntityClassDefinitionError(
                    f"Cannot build instrumentation for field {class_name}.{attr_name}"
                ) from e
            field_info = field.__info__
            field_name = field_info.field_name
            # Add attribute to primaries if needed
            if field_info.primary:
                cls.__primaries__.add(attr_name)
            # Check we are not redefining a field
            if not field_info.is_alias():
                if field_name in field_names:
                    raise error.SgEntityClassDefinitionError(
                        f"Field named '{field_name}' is already defined"
                    )
                field_names.add(field_name)
                cls.__attr_per_field_name__[field_name] = attr_name
                # Add to the class
                cls.__fields__[attr_name] = field
            # Create field descriptors
            prop = AliasFieldProperty if field_info.is_alias() else FieldProperty
            setattr(cls, attr_name, prop(field, not field_info.primary))


def extract_annotation_info(
    annotation: AnnotationScanType,
) -> Tuple[str, ...]:
    """Returns the information extracted from a given annotation.

    Args:
        annotation (AnnotationScanType): the annotation

    Returns:
        tuple[tuple[str, ...], Optional[Type[Collection[Any]]]]:
            a tuple of extracted entity types,
            the collection type wrapping the entities
    """
    if not hasattr(annotation, "__args__"):
        return tuple()
    inner_annotation = annotation.__args__[0]
    inner_annotation = de_optionalize_union_types(inner_annotation)
    # Get the container type
    if hasattr(inner_annotation, "__origin__"):
        arg_origin = inner_annotation.__origin__
        if isinstance(arg_origin, type):
            raise error.SgInvalidAnnotationError("No container class expected")
    # Unpack the unions
    entities = expand_unions(inner_annotation)
    return entities
