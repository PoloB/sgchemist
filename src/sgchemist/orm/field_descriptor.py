"""Defines elements for mapping between annotations and instrumentation."""

from __future__ import annotations

import abc
from typing import TYPE_CHECKING
from typing import Any
from typing import Collection
from typing import Generic
from typing import Iterable
from typing import Optional
from typing import Tuple
from typing import Type
from typing import TypeVar

from . import error
from .field import AbstractEntityField
from .field import AbstractField
from .field import AbstractValueField
from .field import EntityField
from .field import MultiEntityField
from .instrumentation import InstrumentedAttribute
from .instrumentation import InstrumentedField
from .instrumentation import InstrumentedMultiRelationship
from .instrumentation import InstrumentedMultiTargetSingleRelationship
from .instrumentation import InstrumentedRelationship
from .instrumentation import LazyEntityClassEval
from .instrumentation import LazyEntityCollectionClassEval
from .typing_util import AnnotationScanType
from .typing_util import de_optionalize_union_types
from .typing_util import expand_unions

if TYPE_CHECKING:
    from .meta import SgEntityMeta


T = TypeVar("T")
It = TypeVar("It", bound=Iterable[Any])


class FieldAnnotation(Generic[T]):
    """A well-defined field annotation."""

    def __init__(
        self,
        entity_class: SgEntityMeta,
        field_type: Type[AbstractField[T]],
        annotated_entities: Tuple[str, ...],
        container_class: Optional[Type[T]] = None,
    ):
        """Initialize a FieldAnnotation.

        Args:
            entity_class (SgEntityMeta): the class of the entity
            field_type (Type[AbstractField[T]]): the type of the field
            annotated_entities (tuple[str, ...]): the annotated entities
            container_class (Optional[Type[T]], optional): the class of the container
        """
        self.entity_class = entity_class
        self.field_type = field_type
        self.entities = annotated_entities
        self.container_class = container_class


def extract_annotation_info(
    annotation: AnnotationScanType,
) -> Tuple[Tuple[str, ...], Optional[Type[Collection[Any]]]]:
    """Returns the information extracted from a given annotation.

    Args:
        annotation (AnnotationScanType): the annotation

    Returns:
        tuple[tuple[str, ...], Optional[Type[Collection[Any]]]]:
            a tuple of extracted entity types,
            the collection type wrapping the entities
    """
    if not hasattr(annotation, "__args__"):
        return tuple(), None
    inner_annotation = annotation.__args__[0]
    inner_annotation = de_optionalize_union_types(inner_annotation)
    # Get the container type
    container_class = None
    if hasattr(inner_annotation, "__origin__"):
        arg_origin = inner_annotation.__origin__
        if isinstance(arg_origin, type) and issubclass(arg_origin, Collection):
            container_class = arg_origin
            inner_annotation = inner_annotation.__args__[0]
    # Unpack the unions
    entities = expand_unions(inner_annotation)
    return entities, container_class


class MappedColumn(abc.ABC):
    """An abstract mapped column."""

    def __init__(
        self,
        name: str,
        is_alias: bool = False,
        primary: bool = False,
    ):
        """Initialize a MappedColumn.

        Args:
            name (str): the name of the column
            is_alias (bool): whether the column is alias or not
            primary (bool): whether the column is primary or not
        """
        self.name = name
        self.attr_name: str = self.name
        self.is_alias = is_alias
        self.primary = primary

    @abc.abstractmethod
    def get_instrumented(
        self, field_annotation: FieldAnnotation[T]
    ) -> InstrumentedAttribute[T]:
        """Returns the instrumented attribute for the given field annotation.

        Args:
            field_annotation (FieldAnnotation[T]): the field annotation

        Returns:
            InstrumentedAttribute[T]: the instrumented attribute
        """


class MappedField(MappedColumn):
    """Defines a mapped field."""

    def __init__(
        self,
        name: str,
        default: Any = None,
        primary: bool = False,
        name_in_relation: str = "",
    ):
        """Initialize a MappedField.

        Args:
            name (str): the name of the field
            default (Any): the default value
            primary (bool): whether the column is primary or not
            name_in_relation (str): the name inside the relation
        """
        super().__init__(name, primary=primary)
        self.default = default
        self.name_in_relation = name_in_relation

    def get_instrumented(
        self,
        field_annotation: FieldAnnotation[T],
    ) -> InstrumentedField[T]:
        """Returns the instrumented field for the given field annotation.

        Args:
            field_annotation (FieldAnnotation[T]): the field annotation

        Returns:
            InstrumentedField[T]: the instrumented field
        """
        if not issubclass(field_annotation.field_type, AbstractValueField):
            raise error.SgInvalidAnnotationError(
                "A MappedField should target an AbstractValueField annotation"
            )
        return InstrumentedField(
            source_class=field_annotation.entity_class,
            class_=field_annotation.entity_class,
            field_annotation=field_annotation,
            attr_name=self.attr_name,
            name=self.name,
            default_value=self.default,
            name_in_relation=self.name_in_relation,
            primary=self.primary,
        )


class Relationship(MappedColumn):
    """A mapped relationship."""

    def _get_instrumented_attr_name(self) -> str:
        return self.name

    def get_instrumented(
        self,
        field_annotation: FieldAnnotation[T],
    ) -> InstrumentedAttribute[T]:
        """Returns the instrumented relationship for the given field annotation.

        Args:
            field_annotation (FieldAnnotation[T]): the field annotation

        Returns:
            InstrumentedAttribute[T]: the instrumented attribute

        Raises:
            error.SgInvalidAnnotation: the annotation is invalid
        """
        entities = field_annotation.entities
        multi_target = len(entities) > 1
        field_type = field_annotation.field_type
        container_class = field_annotation.container_class
        entity_class = field_annotation.entity_class
        # Make some checks
        if not issubclass(field_type, AbstractEntityField):
            raise error.SgInvalidAnnotationError(
                "A Relationship should target an AbstractEntityField annotation"
            )
        if len(entities) == 0:
            raise error.SgInvalidAnnotationError(
                "An entity field must provide a target entity"
            )
        if field_type is MultiEntityField and container_class is not list:
            raise error.SgInvalidAnnotationError(
                "A multi entity field requires a list annotation"
            )
        if field_type is EntityField and container_class:
            raise error.SgInvalidAnnotationError(
                "An entity field shall not have a container annotation"
            )
        # Construct a multi target entity
        lazy_evals = [
            LazyEntityClassEval(entity, entity_class.__registry__)
            for entity in entities
        ]
        lazy_collection = LazyEntityCollectionClassEval(lazy_evals)
        if multi_target:
            return InstrumentedMultiTargetSingleRelationship(
                entity_class,
                entity_class,
                field_annotation,
                self.attr_name,
                self._get_instrumented_attr_name(),
                field_type.default_value,
                lazy_collection,
            )
        if container_class is not None:
            return InstrumentedMultiRelationship(
                entity_class,
                entity_class,
                field_annotation,
                self.attr_name,
                self._get_instrumented_attr_name(),
                field_type.default_value,
                lazy_collection,
            )
        return InstrumentedRelationship(
            entity_class,
            entity_class,
            field_annotation,
            self.attr_name,
            self._get_instrumented_attr_name(),
            field_type.default_value,
            lazy_evals[0],
            self.is_alias,
        )


class AliasRelationship(Relationship):
    """Defines an alias relationship."""

    def __init__(self, target_relationship: Relationship):
        """Initialize a AliasRelationship.

        Args:
            target_relationship (Relationship): the target relationship
        """
        super().__init__("", is_alias=True)
        self._target_relationship = target_relationship

    def _get_instrumented_attr_name(self) -> str:
        return self._target_relationship.attr_name

    def get_instrumented(
        self,
        field_annotation: FieldAnnotation[T],
    ) -> InstrumentedAttribute[T]:
        """Returns the instrumented attribute for the given field annotation.

        Args:
            field_annotation (FieldAnnotation[T]): the field annotation

        Returns:
            InstrumentedAttribute[T]: the instrumented attribute

        Raises:
            error.SgInvalidAnnotation: the annotation is invalid
        """
        # Check the annotation
        if field_annotation.field_type is not EntityField:
            raise error.SgInvalidAnnotationError(
                "An alias field requires must be an EntityField"
            )
        if len(field_annotation.entities) != 1:
            raise error.SgInvalidAnnotationError(
                "A alias field shall target a single entity"
            )
        # Make sure the entity type in annotation is in the target annotation
        target_entity = field_annotation.entities[0]
        # Find the target mapped annotation
        target_attribute_name = self._target_relationship.attr_name
        target_instrumentation = field_annotation.entity_class.__fields__[
            target_attribute_name
        ]
        target_annotation = target_instrumentation.get_field_annotation()
        if target_entity not in target_annotation.entities:
            raise error.SgInvalidAnnotationError(
                "An alias field must target a multi target field containing its entity"
            )
        return super().get_instrumented(field_annotation)


def relationship(name: str = "") -> Any:
    """Defines a field as a relationship.

    Use this field specifier if you want to use a different attribute name to target
    a given entity field.

    Args:
        name (str): the name of the field

    Returns:
        Relationship: the mapped relationship
    """
    return Relationship(name)


def alias_relationship(target_relationship: Any) -> Any:
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
    return AliasRelationship(target_relationship)


def mapped_field(
    name: str = "",
    default: Optional[Any] = None,
    primary: bool = False,
    name_in_relation: str = "",
) -> Any:
    """Defines a mapped field.

    Use this specifier to modify the behavior of the field.

    Args:
        name (str): the name of the field
        default (Any): the default value
        primary (bool): whether the column is primary or not
        name_in_relation (str): the name inside the relation

    Returns:
        MappedField: a mapped field
    """
    return MappedField(name, default, primary, name_in_relation)
