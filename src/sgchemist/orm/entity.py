"""Defines the base entity class."""

from __future__ import absolute_import
from __future__ import annotations

from typing import Any
from typing import ClassVar
from typing import Dict
from typing import Set
from typing import Type
from typing import TypeVar

from . import error
from .field import NumberField
from .field_descriptor import mapped_field
from .instrumentation import InstrumentedAttribute
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
    __fields__: ClassVar[Dict[str, InstrumentedAttribute[Any]]]
    __primaries__: ClassVar[Set[str]]
    __attr_per_field_name__: ClassVar[Dict[str, str]]
    __state__: ClassVar[EntityState]

    id: NumberField = mapped_field(primary=True)

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
        cls_ = type(self)
        self.__state__ = EntityState(self)
        # Init with field default value by setting its state
        for attr_name, field in self.__fields__.items():
            self.__state__.get_slot(attr_name).value = field.get_default_value()
        # Set with keyword arguments
        for k, v in kwargs.items():
            if not hasattr(cls_, k):
                raise error.SgInvalidAttributeError(
                    "%r is an invalid keyword argument for %s" % (k, cls_.__name__)
                )
            if k in self.__primaries__:
                self.__state__.get_slot(k).value = v
                continue
            setattr(self, k, v)

    def __repr__(self) -> str:
        """Returns a string representation of the entity.

        Returns:
            str: representation of the entity.
        """
        primary_fields = {
            field.get_name(): getattr(self, attr_name)
            for attr_name, field in self.__fields__.items()
            if attr_name in self.__primaries__
        }
        repr_str = ",".join(
            f"{field_name}={field_value}"
            for field_name, field_value in primary_fields.items()
        )
        return f"{self.__class__.__name__}({repr_str})"
