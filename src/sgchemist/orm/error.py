"""Errors used in the orm package."""

from __future__ import annotations

from typing import TYPE_CHECKING
from typing import Any

if TYPE_CHECKING:
    from sgchemist.orm.fields import AbstractField


class SgError(Exception):
    """Base class for exceptions in orm package."""


class SgEntityClassDefinitionError(SgError):
    """Raised when an entity class is not well-defined."""


class SgInvalidAttributeError(SgError):
    """Raised when an attribute is invalid."""


class SgRelationshipNotCommitedError(SgError):
    """Raised when the relationship of an entity is not commited."""


class SgAddEntityError(SgError):
    """Raised when an entity cannot be added to the session."""


class SgDeleteEntityError(SgError):
    """Raised when an entity cannot be deleted in the session."""


class SgInvalidAnnotationError(SgError):
    """Raised when an annotation is invalid."""


class SgQueryError(SgError):
    """Raised when doing an invalid query."""


class SgFieldConstructionError(SgError):
    """Raised when a field cannot be constructed."""


class SgInvalidFieldError(SgError):
    """Raised when doing operation on an invalid field."""


class SgMissingFieldError(SgError):
    """Raised when trying to get a field that was not queried."""


class SgFieldNotSettableError(SgError):
    """Raised when trying to set a field that is not settable."""

    def __init__(self, field: AbstractField[Any]) -> None:
        """Initialize the exception."""
        super().__init__(f"Field {field} is not settable.")
        self.field = field
