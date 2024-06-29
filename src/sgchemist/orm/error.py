"""Errors used in the orm package."""

from __future__ import annotations


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


class SgMissingFieldError(SgError):
    """Raised when trying to get a field that was not queried."""
