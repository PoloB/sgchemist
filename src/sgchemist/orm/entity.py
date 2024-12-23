"""Defines the base entity class."""

from __future__ import annotations

import inspect
import sys
from collections import defaultdict
from typing import Any
from typing import ClassVar
from typing import Generic
from typing import TypeVar
from typing import overload

from . import error
from . import field_info
from .annotation import FieldAnnotation
from .fields import AbstractField
from .fields import NumberField
from .fields import field_by_sg_type
from .typing_util import cleanup_mapped_str_annotation
from .typing_util import de_optionalize_union_types
from .typing_util import expand_unions
from .typing_util import get_annotations

T = TypeVar("T")
T_co = TypeVar("T_co", covariant=True)


class FieldProperty(Generic[T]):
    """A field descriptor wrapping the access data of fields."""

    def __init__(
        self,
        field: AbstractField[T],
        settable: bool = True,  # noqa: FBT001, FBT002
    ) -> None:
        """Initialize the field descriptor.

        Args:
            field: the field to wrap.
            settable: whether the attribute is settable or not.
        """
        self._field = field
        self._settable = settable

    @overload
    def __get__(self, instance: None, obj_type: SgEntityMeta) -> AbstractField[T]: ...

    @overload
    def __get__(self, instance: SgBaseEntity, obj_type: SgEntityMeta) -> T: ...

    def __get__(
        self,
        instance: SgBaseEntity | None,
        obj_type: SgEntityMeta,
    ) -> Any:
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
            error_message = f"{self._field} has not been queried"
            raise error.SgMissingFieldError(error_message)
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
            raise error.SgFieldNotSettableError(self._field)
        state = instance.__state__
        # Test against current value
        old_value = state.get_original_value(self._field)
        # Register state change
        if value != old_value:
            state.modified_fields.append(self._field)
        elif self._field in state.modified_fields:
            state.modified_fields.remove(self._field)
        instance.__state__.values[self._field] = value  # noqa: PD011


class AliasFieldProperty(FieldProperty[T]):
    """Defines an alias field descriptor."""

    def __get__(
        self,
        instance: SgBaseEntity | None,
        owner: SgEntityMeta,
    ) -> Any:  # noqa: ANN401
        """Return the value of the targeted field.

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


class EntityState(Generic[T_co]):
    """Defines the internal state of the instance field values."""

    __slots__ = (
        "_available",
        "_entity",
        "_original_values",
        "deleted",
        "modified_fields",
        "pending_add",
        "pending_deletion",
        "values",
    )

    def __init__(
        self,
        instance: SgBaseEntity,
        values_per_field: dict[AbstractField[T_co], T_co],
    ) -> None:
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
        self.values: dict[AbstractField[T_co], T_co] = values_per_field
        self._available: dict[AbstractField[T_co], bool] = defaultdict(lambda: True)
        self.modified_fields: list[AbstractField[Any]] = list(
            filter(lambda f: not field_info.is_primary(f), values_per_field),
        )
        self._original_values: dict[AbstractField[T_co], T_co] = {}

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

    def get_original_value(self, field: AbstractField[T_co]) -> T_co | None:
        """Return the entity initial value of the given attribute.

        Args:
            field: the name of the attribute.

        Returns:
            the entity initial value of the given attribute.
        """
        return self._original_values.get(field)

    def get_value(self, field: AbstractField[T_co]) -> T_co:
        """Return the value of the field."""
        return self.values.get(field, field_info.get_default_value(field))

    def set_value(self, field: AbstractField[Any], value: Any) -> None:  # noqa: ANN401
        """Sets the value of the field."""
        self.values[field] = value

    def is_available(self, field: AbstractField[Any]) -> bool:
        """Return True if the field is available."""
        return self._available[field]

    def set_unavailable(self, field: AbstractField[T_co]) -> None:
        """Sets the field as unavailable."""
        self._available[field] = False

    def set_as_original(self) -> None:
        """Set the current state of the entity as its original state."""
        self._original_values = self.values.copy()
        self.modified_fields = []


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
    ) -> SgEntityMeta:
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
            },
        )
        if field_intersect and bases:
            error_message = f"Attributes {field_intersect} are reserved."
            raise error.SgEntityClassDefinitionError(error_message)
        return type.__new__(cls, class_name, bases, dict_)

    def __init__(  # noqa: C901, PLR0915
        cls,
        class_name: str,
        bases: tuple[type[Any], ...],
        dict_: dict[str, Any],
    ) -> None:
        """Initialize the entity class."""
        super().__init__(class_name, bases, dict_)
        # Get the registry back from parent class
        cls.__sg_type__: str = dict_.get("__sg_type__", "")
        cls.__instance_state__: EntityState[Any]  # noqa: B032
        cls.__is_root__: bool = len(bases) == 0
        cls.__is_base__: bool = bases[0].__is_root__ if bases else False
        if cls.__is_root__:
            return
        # Check if we are initializing a base class
        if cls.__is_base__:
            cls.__registry__: dict[str, SgEntityMeta] = {}
            return
        # We are initializing subclass of base
        if not cls.__sg_type__:
            error_message = f"Missing __sg_type__ attribute in {class_name}"
            raise error.SgEntityClassDefinitionError(error_message)
        other_entity_by_type = {
            entity.__sg_type__: entity for entity in cls.__registry__.values()
        }
        other_entity = other_entity_by_type.get(cls.__sg_type__)
        if other_entity:
            other_file = inspect.getfile(other_entity)
            cls_file = inspect.getfile(cls)
            error_message = (
                f"Entity {class_name} defined at {cls_file} uses "
                f"__sg_type__ = {cls.__sg_type__} which is already used by "
                f"{other_entity.__name__} defined at {other_file}."
            )
            raise error.SgEntityClassDefinitionError(error_message)

        # Prepare global variables for evaluating the annotations
        cls_namespace = dict(cls.__dict__)
        cls_namespace.setdefault(cls.__name__, cls)
        original_scope = sys.modules[cls.__module__].__dict__.copy()
        original_scope.update(cls_namespace)
        original_scope.update(cls.__registry__)
        original_scope.update(
            {
                field_type.__name__: field_type
                for field_type in field_by_sg_type.values()
            },
        )

        # Add the common id field
        field_id = NumberField()
        initialize_from_annotation(
            field_id,
            FieldAnnotation(NumberField, ()),
            "id",
        )
        field_id.__info__["primary"] = True
        add_field_to_entity(cls, field_id)
        cls.__fields__: list[AbstractField[Any]] = [field_id]
        cls.__fields_by_attr__: dict[str, AbstractField[Any]] = {"id": field_id}
        cls.__attr_per_field_name__: dict[str, str] = {"id": "id"}
        field_names = {"id"}
        all_fields: dict[str, AbstractField[Any]] = {"id": field_id}

        # Add the field args from the class we are building
        for attr_name, annot in get_annotations(cls).items():
            # Extract entity information from annotation
            try:
                field_annot = extract_field_annotation(annot, original_scope)
            except error.SgInvalidAnnotationError as e:
                error_message = (
                    f"Cannot extract annotation information for field "
                    f"{class_name}.{attr_name}"
                )
                raise error.SgEntityClassDefinitionError(error_message) from e
            if not field_annot.is_field():
                continue

            # Build the field if it is not already declared
            field = dict_.get(attr_name, field_annot.field_type(name=attr_name))
            if not isinstance(field, AbstractField):
                error_message = (
                    f"{class_name}.{attr_name} is not initialized with a field."
                )
                raise error.SgEntityClassDefinitionError(error_message)

            try:
                initialize_from_annotation(field, field_annot, attr_name)
            except error.SgInvalidAnnotationError as e:
                error_message = (
                    f"Cannot build instrumentation for field {class_name}.{attr_name}"
                )
                raise error.SgEntityClassDefinitionError(error_message) from e
            add_field_to_entity(cls, field)
            field_name = field_info.get_name(field)
            # Check we are not redefining a field
            if not field_info.is_alias(field):
                if field_name in field_names:
                    error_message = f"Field named '{field_name}' is already defined"
                    raise error.SgEntityClassDefinitionError(error_message)

                field_names.add(field_name)
                cls.__attr_per_field_name__[field_name] = attr_name
                # Add to the class
                cls.__fields_by_attr__[attr_name] = field
                cls.__fields__.append(field)
            # Create field descriptors
            all_fields[attr_name] = field
        for attr_name, field in all_fields.items():
            prop = AliasFieldProperty if field_info.is_alias(field) else FieldProperty
            setattr(cls, attr_name, prop(field, not field_info.is_primary(field)))

        cls.__registry__[cls.__name__] = cls


class SgBaseEntity(metaclass=SgEntityMeta):
    """Base class for any Shotgrid entity.

    When implementing a new model, you shall subclass this class.
    It provides only the "id" field which is common to all Shotgrid entities.
    """

    id: NumberField
    __sg_type__: str
    __fields__: ClassVar[list[AbstractField[Any]]]
    __fields_by_attr__: ClassVar[dict[str, AbstractField[Any]]]
    __attr_per_field_name__: ClassVar[dict[str, str]]
    __state__: ClassVar[EntityState[Any]]

    def __init_subclass__(cls, **kwargs: Any) -> None:  # noqa: ANN401
        """Initialize the entity subclass."""
        # If we are directly subclassing, we shall not have any __sg_type__
        if SgBaseEntity in cls.__bases__ and "__sg_type__" in cls.__dict__:
            error_message = (
                "Cannot subclass SgBaseEntity directly to create an entity. "
                "Please subclass SgBaseEntity in your own base class.",
            )
            raise error.SgEntityClassDefinitionError(error_message)
        cls.__is_base__ = True
        super().__init_subclass__(**kwargs)

    def __init__(self: Any, **kwargs: Any) -> None:  # noqa: ANN401
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

    def get_value(self, field: AbstractField[Any]) -> Any:  # noqa: ANN401
        """Return the value of the given field.

        Args:
            field: the field for which to get the value.

        Raises:
            error.SgMissingFieldError: the value is not available because it has never
                been queried.
            error.SgInvalidFieldError: raised if the given field is not a field of the
                entity.
        """
        all_fields = field_info.get_field_hierarchy(field)
        if all_fields[0].__info__["entity"] is not self.__class__:
            error_message = f"{field} is not a field of {self.__class__}"
            raise error.SgInvalidFieldError(error_message)
        # Get the fields in order
        value = self.__state__.get_value(all_fields[0])
        for ordered_field in all_fields[1:]:
            value = value.__state__.get_value(ordered_field)
        return value

    def as_dict(self) -> dict[str, Any]:
        """Return the entity as dict."""
        data = {"id": self.id, "type": self.__sg_type__}

        for field in self.__fields__:
            value = self.__state__.get_value(field)
            if isinstance(value, SgBaseEntity):
                value = value.as_dict()
            data[field_info.get_name(field)] = value

        return data


def extract_field_annotation(annotation: str, scope: dict[str, Any]) -> FieldAnnotation:
    """Attempt to extract information from the given annotation.

    This is where all the `magic` really happen but also where it is
    the most dangerous. Annotations behave very differently between
    python <3.10 et later.
    For example, it is not possible to declare specified builtin types
    like `tuple[str] or dict[str, Any]`.
    This method tries its best to keep an agnostic approach across
    all python 3.7+ versions until their EOL.
    Global and local variables are used to evaluate some of the content of the
    annotation.

    Args:
        annotation: the annotation string to extract information from.
        scope: the variables in the same scope as the annotation.

    Returns:
        the extracted field information

    Raises:
        error.SgInvalidAnnotationError: when the reliable information
            couldn't be extracted from the annotation.
    """
    # Check annotation are as string
    # Otherwise it probably means annotations are not from __future__
    if not isinstance(annotation, str):
        error_message = (
            "sgchemist does not support non string annotations. "
            "If you are using python <3.10, please add "
            "`from __future__ import annotations` to your imports.",
        )
        raise error.SgInvalidAnnotationError(error_message)

    # String un-stringifying the annotation as much as possible.
    # At least we need to extract the main outer type to check it is a field kind.
    try:
        outer_type, cleaned_annot = cleanup_mapped_str_annotation(annotation, scope)
    except Exception as e:
        error_message = f"Cannot evaluate annotation {annotation}"
        raise error.SgInvalidAnnotationError(error_message) from e

    # We never care about anything but AbstractField
    if not isinstance(outer_type, type) or not issubclass(outer_type, AbstractField):
        return FieldAnnotation(outer_type, ())

    # Evaluate full annotation
    # Add ForwardRef in the scope to make sure we can evaluate what was not yet
    # defined in the scope already
    annot_eval = eval(cleaned_annot, scope)  # noqa: S307

    # Extract entity information from the evaluated annotation
    if not hasattr(annot_eval, "__args__"):
        return FieldAnnotation(outer_type, ())

    inner_annotation = annot_eval.__args__[0]
    inner_annotation = de_optionalize_union_types(inner_annotation)
    # Get the container type
    if hasattr(inner_annotation, "__origin__"):
        arg_origin = inner_annotation.__origin__
        if isinstance(arg_origin, type):
            error_message = "No container class expected"
            raise error.SgInvalidAnnotationError(error_message)
    # Unpack the unions
    entities = expand_unions(inner_annotation)
    # Try to evaluate the entities right away to check the type of the entity if they
    # are not lazy
    return FieldAnnotation(outer_type, tuple(entities))


def initialize_from_annotation(
    field: AbstractField[Any],
    annotation: FieldAnnotation,
    attribute_name: str,
) -> None:
    """Create a field from a descriptor."""
    if annotation.field_type is not field.__class__:
        error_message = (
            f"Cannot initialize field of type {field.__class__.__name__} "
            f"with a {annotation.field_type.__name__}"
        )
        raise error.SgInvalidAnnotationError(error_message)

    info = field.__info__
    if info["alias_field"]:
        if len(annotation.entities) != 1:
            error_message = "A alias field shall target a single entity"
            raise error.SgInvalidAnnotationError(error_message)

        # Make sure the entity type in annotation is in the target annotation
        target_entity = annotation.entities[0]
        target_annotation = info["alias_field"].__info__["annotation"]

        if target_entity not in target_annotation.entities:
            error_message = (
                "An alias field must target a multi target field containing its entity"
            )
            raise error.SgInvalidAnnotationError(error_message)

        # An alias field use the same name as its target
        info["name"] = info["alias_field"].__info__["name"]

    info["annotation"] = annotation
    info["name"] = info["name"] or attribute_name
    info["name_in_relation"] = info["name_in_relation"] or info["name"]

    # Make some checks
    if info["is_relationship"] and len(annotation.entities) == 0:
        error_message = "Expected at least one entity field"
        raise error.SgInvalidAnnotationError(error_message)
    # Construct a multi target entity
    lazy_evals = [LazyEntityClassEval(entity, {}) for entity in annotation.entities]
    info["lazy_collection"] = LazyEntityCollectionClassEval(lazy_evals)
    if "default_value" not in info:
        info["default_value"] = field.default_value


def add_field_to_entity(entity: SgEntityMeta, field: AbstractField[Any]) -> None:
    """Add the field to the given entity."""
    info = field.__info__
    info["entity"] = entity
    for lazy_col in info["lazy_collection"].lazy_entities:
        lazy_col.registry = entity.__registry__


class LazyEntityClassEval:
    """Defers the evaluation of a class name used in annotation."""

    _entity: type[SgBaseEntity]

    def __init__(self, class_: str, registry: dict[str, SgEntityMeta]) -> None:
        """Initialize an instance.

        Args:
            class_: the name of the class
            registry: registry where all classes are defined
        """
        self._resolved: bool = False
        self.class_name = class_
        self.registry = registry

    def get(self) -> type[SgBaseEntity]:
        """Return the entity class after evaluation.

        Returns:
            the entity class
        """
        if not self._resolved:
            try:
                entity = eval(self.class_name, {}, self.registry)  # noqa: S307
            except NameError as e:
                error_message = (
                    f"{self.class_name} is not defined in the registry of base class"
                )
                raise error.SgEntityClassDefinitionError(error_message) from e
            if not issubclass(entity, SgBaseEntity):
                error_message = (
                    f"Lazy class {self.class_name} is not an entity. "
                    f"Please check the target of your entities."
                )
                raise error.SgEntityClassDefinitionError(error_message)
            self._entity = entity
            self._resolved = True
        return self._entity


class LazyEntityCollectionClassEval:
    """A collection of lazy entity classes."""

    def __init__(self, lazy_entities: list[LazyEntityClassEval]) -> None:
        """Initialize an instance.

        Args:
            lazy_entities: list of lazy entity classes
        """
        self.lazy_entities = lazy_entities
        self._resolved_by_name: dict[str, type[SgBaseEntity]] = {}
        self._resolved_entities: list[type[SgBaseEntity]] = []
        self._resolved = False

    def _fill(self) -> None:
        """Evaluates all the lazy entity classes and fill internal cache."""
        for lazy in self.lazy_entities:
            entity = lazy.get()
            self._resolved_by_name[entity.__sg_type__] = entity
        self._resolved_entities = list(self._resolved_by_name.values())
        self._resolved = True

    def get_by_type(self, entity_type: str) -> type[SgBaseEntity]:
        """Return the entity class for its Shotgrid type.

        Args:
            entity_type: the entity type

        Returns:
            the entity class
        """
        if not self._resolved:
            self._fill()
        return self._resolved_by_name[entity_type]

    def get_all(self) -> list[type[SgBaseEntity]]:
        """Return all the evaluated entity classes."""
        if not self._resolved:
            self._fill()
        return self._resolved_entities
