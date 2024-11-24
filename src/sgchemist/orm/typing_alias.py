"""Defines multiple typing alias used across sgchemist."""

from __future__ import annotations

from typing import TYPE_CHECKING
from typing import Any
from typing import ClassVar

from typing_extensions import Protocol
from typing_extensions import TypedDict

if TYPE_CHECKING:
    from sgchemist.orm import NumberField
    from sgchemist.orm.entity import EntityState
    from sgchemist.orm.fields import AbstractField

EntityHash = tuple[str, int]


class SerializedEntity(TypedDict, total=False):
    """Defines a serialized entity dict."""

    id: int
    type: str


class EntityProtocol(Protocol):
    """Entity protocol."""

    id: NumberField
    __sg_type__: str
    __fields__: ClassVar[list[AbstractField[Any]]]
    __fields_by_attr__: ClassVar[dict[str, AbstractField[Any]]]
    __attr_per_field_name__: ClassVar[dict[str, str]]
    __state__: ClassVar[EntityState[Any]]

    def __init__(self: Any, **kwargs: Any) -> None:  # noqa: ANN401
        """Initializes the entity from keyword arguments."""

    def __repr__(self) -> str:
        """Returns a string representation of the entity."""

    def get_value(self, field: AbstractField[Any]) -> Any:  # noqa: ANN401
        """Return the value of the given field."""

    def as_dict(self) -> dict[str, Any]:
        """Return the entity as dict."""
