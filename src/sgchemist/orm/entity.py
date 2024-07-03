"""Defines the base entity class."""

from __future__ import absolute_import
from __future__ import annotations

from typing import Any
from typing import ClassVar
from typing import Dict
from typing import List
from typing import Type
from typing import TypeVar

from sgchemist.orm import error

from .fields import AbstractField
from .fields import NumberField
from .meta import EntityState
from .meta import SgEntityMeta

T = TypeVar("T")


class SgEntity(metaclass=SgEntityMeta):
    """Base class for any Shotgrid entity.

    When implementing a new model, you shall subclass this class.
    It provides only the "id" field which is common to all Shotgrid entities.
    """

    __abstract__: ClassVar[bool] = True
    __sg_type__: ClassVar[str]
    __registry__: ClassVar[Dict[str, Type[SgEntity]]]
    __fields__: ClassVar[List[AbstractField[Any]]]
    __fields_by_attr__: ClassVar[Dict[str, AbstractField[Any]]]
    __attr_per_field_name__: ClassVar[Dict[str, str]]
    __state__: ClassVar[EntityState]

    id: NumberField = NumberField(name="id")
    id.__info__.primary = True

    def __init_subclass__(cls, **kwargs: Any) -> None:
        """Adds the subclass to the global entity registry."""
        if cls.__name__ in cls.__registry__:
            return
        # Set the
        cls.__registry__[cls.__name__] = cls
        cls.__registry__ = cls.__registry__

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
            value_per_field = {
                self.__fields_by_attr__[k]: v for k, v in kwargs.items()
            }
        except KeyError as e:
            raise error.SgInvalidAttributeError(e.args) from e
        # We set the values directly in the state to avoid the cost of using the
        # properties.
        self.__state__ = EntityState(self, value_per_field)

    def __repr__(self) -> str:
        """Returns a string representation of the entity.

        Returns:
            str: representation of the entity.
        """
        return f"{self.__class__.__name__}(id={self.id})"
