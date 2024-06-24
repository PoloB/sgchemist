"""Defines elements for mapping between annotations and instrumentation."""

from __future__ import annotations

from typing import TYPE_CHECKING
from typing import Any
from typing import Collection
from typing import Iterable
from typing import Optional
from typing import Tuple
from typing import Type
from typing import TypeVar

from .typing_util import AnnotationScanType
from .typing_util import de_optionalize_union_types
from .typing_util import expand_unions

if TYPE_CHECKING:
    pass


T = TypeVar("T")
It = TypeVar("It", bound=Iterable[Any])


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


class FieldDescriptor:
    """Defines a mapped field."""

    def __init__(
        self,
        name: Optional[str] = None,
        default: Any = None,
        primary: bool = False,
        name_in_relation: Optional[str] = None,
        aliased_field: Optional[FieldDescriptor] = None,
    ):
        """Initialize a MappedField.

        Args:
            name (str, optional): the name of the field
            default (Any, optional): the default value
            primary (bool, optional): whether the column is primary or not
            name_in_relation (str, optional): the name inside the relation
            aliased_field (EntityField, optional): the field aliased by this field
        """
        self.name = name
        self.name_in_relation = name_in_relation
        self.default = default
        self.primary = primary
        self.aliased_field = aliased_field
        self.attr_name: str = ""


def relationship(name: str = "") -> Any:
    """Defines a field as a relationship.

    Use this field specifier if you want to use a different attribute name to target
    a given entity field.

    Args:
        name (str): the name of the field

    Returns:
        RelationshipDescriptor: the mapped relationship
    """
    return FieldDescriptor(name=name)


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
    return FieldDescriptor(aliased_field=target_relationship)


def field(
    name: Optional[str] = None,
    name_in_relation: Optional[str] = None,
) -> Any:
    """Defines a mapped field.

    Use this specifier to modify the behavior of the field.

    Args:
        name (str): the name of the field
        name_in_relation (str): the name inside the relation

    Returns:
        FieldDescriptor: a mapped field
    """
    return FieldDescriptor(name=name, name_in_relation=name_in_relation)
