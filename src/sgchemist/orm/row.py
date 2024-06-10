"""Defines the low level row object."""

from __future__ import annotations

from typing import TYPE_CHECKING
from typing import Any
from typing import Dict
from typing import Generic
from typing import TypeVar

if TYPE_CHECKING:
    from .typing_alias import EntityHash

T = TypeVar("T")


class SgRow(Generic[T]):
    """Defines a row as returned by the engine."""

    def __init__(
        self, entity_type: str, entity_id: int, success: bool, content: Dict[str, Any]
    ):
        """Initialize the row.

        Args:
            entity_type (str): The entity type.
            entity_id (int): The entity id.
            success (bool): Whether the row was successfully created.
            content (dict[str, Any]): The content of the row.
        """
        self._entity_type = entity_type
        self._entity_id = entity_id
        self._success = success
        self._content = content

    @property
    def entity_type(self) -> str:
        """Return the entity type.

        Returns:
            str: The entity type.
        """
        return self._entity_type

    @property
    def entity_id(self) -> int:
        """Return the entity id.

        Returns:
            int: The entity id.
        """
        return self._entity_id

    @property
    def success(self) -> bool:
        """Return whether the row is the result of a successful query.

        Returns:
            bool: Whether the row is the result of a successful query.
        """
        return self._success

    @property
    def content(self) -> Dict[str, Any]:
        """Return the content of the row.

        Returns:
            dict[str, Any]: The content of the row.
        """
        return self._content

    @property
    def entity_hash(self) -> EntityHash:
        """Return the entity hash.

        Returns:
            EntityHash: The entity hash.
        """
        return self.entity_type, self.entity_id
