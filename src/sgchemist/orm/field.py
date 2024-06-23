"""Definition of all the fields used by Shotgrid entities.

The main function of these fields is to provide the correct type annotations.
Internally, only the classes inheriting from InstrumentedAttribute are used.
"""

from __future__ import annotations

from datetime import date
from datetime import datetime
from typing import TYPE_CHECKING
from typing import Any
from typing import ClassVar
from typing import Dict
from typing import Generic
from typing import List
from typing import Optional
from typing import Type
from typing import TypeVar
from typing import Union
from typing import overload

from .constant import DateType
from .instrumentation import InstrumentedField
from .instrumentation import InstrumentedMultiTargetRelationship
from .instrumentation import InstrumentedRelationship
from .queryop import SgFieldCondition

if TYPE_CHECKING:
    from .entity import SgEntity
    from .meta import SgEntityMeta

T = TypeVar("T")


class AbstractField(Generic[T]):
    """Definition of an abstract field."""

    cast_type: Type[T]
    default_value: ClassVar
    __sg_type__: str = ""

    if TYPE_CHECKING:

        def eq(self, value: T) -> SgFieldCondition:
            """Filter entities where this field is equal to the given value.

            This is the equivalent of the "is" filter of Shotgrid.

            Args:
                value: The value to compare the field against

            Returns:
                SgFieldCondition: The field condition
            """

        def neq(self, value: T) -> SgFieldCondition:
            """Filter entities where this field is not equal to the given value.

            This is the equivalent of the "is_not" filter of Shotgrid.

            Args:
                value: The value to compare the field against

            Returns:
                SgFieldCondition: The field condition
            """


class AbstractValueField(AbstractField[T]):
    """Definition of an abstract value field."""

    if TYPE_CHECKING:

        @overload
        def __get__(self, instance: None, owner: Any) -> InstrumentedField[T]:
            ...

        @overload
        def __get__(self, instance: Any, owner: Any) -> Optional[T]:
            ...

        def __get__(
            self, instance: Optional[Any], owner: Any
        ) -> Union[Optional[T], InstrumentedField[T]]:
            """Return the value of the field."""


class NumericField(AbstractValueField[T]):
    """Definition of an abstract numerical field."""

    cast_type: Type[T]

    if TYPE_CHECKING:

        def gt(self, value: T) -> SgFieldCondition:
            """Filter entities where this field is greater than the given value.

            This is the equivalent of the "greater_than" filter of Shotgrid.

            Args:
                value: The value to compare the field against

            Returns:
                SgFieldCondition: The field condition
            """

        def lt(self, value: T) -> SgFieldCondition:
            """Filter entities where this field is less than the given value.

            This is the equivalent of the "less_than" filter of Shotgrid.

            Args:
                value: The value to compare the field against

            Returns:
                SgFieldCondition: The field condition
            """

        def between(self, low: Optional[T], high: Optional[T]) -> SgFieldCondition:
            """Filter entities where this field is between the low and high values.

            This is the equivalent of the "between" filter of Shotgrid.

            Args:
                low: low value of the range
                high: high value of the range

            Returns:
                SgFieldCondition: The field condition.
            """

        def not_between(self, low: Optional[T], high: Optional[T]) -> SgFieldCondition:
            """Filter entities where this field is not between the low and high values.

            This is the equivalent of the "not_between" filter of Shotgrid.

            Args:
                low: low value of the range
                high: high value of the range

            Returns:
                SgFieldCondition: The field condition.
            """

        def is_in(self, values: List[T]) -> SgFieldCondition:
            """Filter entities where this field is within the given list of values.

            This is the equivalent of the "in" filter of Shotgrid.

            Args:
                values (list): values to test

            Returns:
                SgFieldCondition: The field condition.
            """

        def is_not_in(self, values: List[T]) -> SgFieldCondition:
            """Filter entities where this field is not within the given list of values.

            This is the equivalent of the "not_in" filter of Shotgrid.

            Args:
                values (list): values to test

            Returns:
                SgFieldCondition: The field condition.
            """


class NumberField(NumericField[Optional[int]]):
    """An integer field."""

    cast_type: Type[int] = int
    __sg_type__: str = "number"
    default_value: ClassVar[Optional[int]] = None


class FloatField(NumericField[Optional[float]]):
    """A float field."""

    cast_type: Type[float] = float
    __sg_type__: str = "float"
    default_value: ClassVar[Optional[float]] = None


class TextField(AbstractValueField[Optional[str]]):
    """A text field."""

    cast_type: Type[str] = str
    __sg_type__: str = "text"
    default_value: ClassVar[Optional[str]] = None

    if TYPE_CHECKING:

        def contains(self, text: str) -> SgFieldCondition:
            """Filter entities where this text field contains the given string.

            This is the equivalent of the "contains" filter of Shotgrid.

            Args:
                text (str): text to check

            Returns:
                SgFieldCondition: The field condition.
            """

        def not_contains(self, text: str) -> SgFieldCondition:
            """Filter entities where this text field does not contain the given string.

            This is the equivalent of the "not_contains" filter of Shotgrid.

            Args:
                text (str): text to check

            Returns:
                SgFieldCondition: The field condition.
            """

        def is_in(self, texts: List[str]) -> SgFieldCondition:
            """Filter entities where this text field is within the given texts.

            This is the equivalent of the "in" filter of Shotgrid.

            Args:
                texts (list[str]): texts to check

            Returns:
                SgFieldCondition: The field condition.
            """

        def is_not_in(self, texts: List[str]) -> SgFieldCondition:
            """Filter entities where this text field is not within the given texts.

            This is the equivalent of the "not_in" filter of Shotgrid.

            Args:
                texts (list[str]): texts to check

            Returns:
                SgFieldCondition: The field condition.
            """

        def startswith(self, text: str) -> SgFieldCondition:
            """Filter entities where this text field starts with the given text.

            This is the equivalent of the "start_with" filter of Shotgrid.

            Args:
                text (str): text to check

            Returns:
                SgFieldCondition: The field condition.
            """

        def endswith(self, text: str) -> SgFieldCondition:
            """Filter entities where this text field ends with the given text.

            This is the equivalent of the "end_with" filter of Shotgrid.

            Args:
                text (str): text to check

            Returns:
                SgFieldCondition: The field condition.
            """


class AbstractEntityField(AbstractField[T]):
    """Definition a field targeting an entity."""

    __sg_type__: str
    cast_type: Type[T]

    if TYPE_CHECKING:

        def type_is(self, entity_cls: SgEntityMeta) -> SgFieldCondition:
            """Filter entities where this entity is of the given type.

            This is the equivalent of the "type_is" filter of Shotgrid.

            Args:
                entity_cls (SgEntityMeta): entity to test

            Returns:
                SgFieldCondition: The field condition.
            """

        def type_is_not(self, entity_cls: SgEntityMeta) -> SgFieldCondition:
            """Filter entities where this entity is not of the given type.

            This is the equivalent of the "type_is_not" filter of Shotgrid.

            Args:
                entity_cls (SgEntityMeta): entity to test

            Returns:
                SgFieldCondition: The field condition.
            """

        def name_contains(self, text: str) -> SgFieldCondition:
            """Filter entities where this entity name contains the given text.

            This is the equivalent of the "name_contains" filter of Shotgrid.

            Args:
                text (str): text to test

            Returns:
                SgFieldCondition: The field condition.
            """

        def name_not_contains(self, text: str) -> SgFieldCondition:
            """Filter entities where this entity name does not contain the given text.

            This is the equivalent of the "name_contains" filter of Shotgrid.

            Args:
                text (str): text to test

            Returns:
                SgFieldCondition: The field condition.
            """

        def name_is(self, text: str) -> SgFieldCondition:
            """Filter entities where this entity name is the given text.

            This is the equivalent of the "name_is" filter of Shotgrid.

            Args:
                text (str): text to test

            Returns:
                SgFieldCondition: The field condition.
            """

        def is_in(self, entities: List[SgEntity]) -> SgFieldCondition:
            """Filter entities where this entity name is within the given entities.

            This is the equivalent of the "in" filter of Shotgrid.

            Args:
                entities (list[SgEntity]): entities to test

            Returns:
                SgFieldCondition: The field condition.
            """

        def is_not_in(self, entities: List[SgEntity]) -> SgFieldCondition:
            """Filter entities where this entity name is not within the given entities.

            This is the equivalent of the "not_in" filter of Shotgrid.

            Args:
                entities (list[SgEntity]): entities to test

            Returns:
                SgFieldCondition: The field condition.
            """


class EntityField(AbstractEntityField[T]):
    """Definition a field targeting a single entity."""

    __sg_type__: str = "entity"
    default_value = None
    cast_type: Type[T]

    if TYPE_CHECKING:

        @overload
        def __get__(self, instance: None, owner: Any) -> InstrumentedRelationship[T]:
            ...

        @overload
        def __get__(self, instance: Any, owner: Any) -> Optional[T]:
            ...

        def __get__(
            self, instance: Optional[Any], owner: Any
        ) -> Union[Optional[T], InstrumentedRelationship[T]]:
            """Return the value of the field."""


class MultiEntityField(AbstractEntityField[T]):
    """Definition a field targeting multiple entities."""

    __sg_type__: str = "multi_entity"
    default_value: ClassVar[List[Any]] = []

    if TYPE_CHECKING:

        @overload
        def __get__(
            self, instance: None, owner: Any
        ) -> InstrumentedMultiTargetRelationship[T]:
            ...

        @overload
        def __get__(self, instance: Any, owner: Any) -> T:
            ...

        def __get__(
            self, instance: Optional[Any], owner: Any
        ) -> Union[T, InstrumentedMultiTargetRelationship[T]]:
            """Return the value of the field."""


class BooleanField(AbstractValueField[Optional[bool]]):
    """Definition a boolean field."""

    __sg_type__: str = "checkbox"
    default_value: ClassVar[Optional[bool]] = None


class AbstractDateField(NumericField[T]):
    """Definition an abstract date field."""

    if TYPE_CHECKING:

        def in_last(self, count: int, date_element: DateType) -> SgFieldCondition:
            """Filter entities where this date is within the last given quantities.

            This is the equivalent of the "in_last" filter of Shotgrid.

            Args:
                count (int): number of days/weeks/months/years
                date_element (DateType): duration type to consider

            Returns:
                SgFieldCondition: The field condition.
            """

        def not_in_last(self, count: int, date_element: DateType) -> SgFieldCondition:
            """Filter entities where this date is not within the last given quantities.

            This is the equivalent of the "not_in_last" filter of Shotgrid.

            Args:
                count (int): number of days/weeks/months/years
                date_element (DateType): duration type to consider

            Returns:
                SgFieldCondition: The field condition.
            """

        def in_next(self, count: int, date_element: DateType) -> SgFieldCondition:
            """Filter entities where this date is within the next given quantities.

            This is the equivalent of the "in_next" filter of Shotgrid.

            Args:
                count (int): number of days/weeks/months/years
                date_element (DateType): duration type to consider

            Returns:
                SgFieldCondition: The field condition.
            """

        def not_in_next(self, count: int, date_element: DateType) -> SgFieldCondition:
            """Filter entities where this date is not within the next given quantities.

            This is the equivalent of the "not_in_next" filter of Shotgrid.

            Args:
                count (int): number of days/weeks/months/years
                date_element (DateType): duration type to consider

            Returns:
                SgFieldCondition: The field condition.
            """

        def in_calendar_day(self, offset: int) -> SgFieldCondition:
            """Filter entities where this date is equal to the offset current day.

            This is the equivalent of the "in_calendar_day" filter of Shotgrid.

            Args:
                offset (int): offset (e.g. 0=today, 1=tomorrow, -1=yesterday)

            Returns:
                SgFieldCondition: The field condition.
            """

        def in_calendar_week(self, offset: int) -> SgFieldCondition:
            """Filter entities where this date is equal to the offset current week.

            This is the equivalent of the "in_calendar_week" filter of Shotgrid.

            Args:
                offset (int): offset (e.g. 0=this week, 1=next week, -1=last week)

            Returns:
                SgFieldCondition: The field condition.
            """

        def in_calendar_month(self, offset: int) -> SgFieldCondition:
            """Filter entities where this date is equal to the offset current month.

            This is the equivalent of the "in_calendar_month" filter of Shotgrid.

            Args:
                offset (int): offset (e.g. 0=this month, 1=next month, -1= last month)

            Returns:
                SgFieldCondition: The field condition.
            """

        def in_calendar_year(self, offset: int) -> SgFieldCondition:
            """Filter entities where this date is equal to the offset current year.

            This is the equivalent of the "in_calendar_year" filter of Shotgrid.

            Args:
                offset (int): offset (e.g. 0=this year, 1=next year, -1= last year)

            Returns:
                SgFieldCondition: The field condition.
            """


class DateField(AbstractDateField[Optional[date]]):
    """Definition of a date field."""

    cast_type: Type[date] = date
    __sg_type__: str = "date"
    default_value: ClassVar[Optional[date]] = None


class DateTimeField(AbstractDateField[Optional[datetime]]):
    """Definition of a date time field."""

    cast_type: Type[datetime] = datetime
    __sg_type__: str = "date_time"
    default_value: ClassVar[Optional[datetime]] = None


class DurationField(NumberField):
    """Definition of a duration field."""

    __sg_type__: str = "duration"


class ImageField(AbstractValueField[Optional[str]]):
    """Definition of an image field."""

    cast_type: Type[str] = str
    __sg_type__: str = "image"
    default_value: ClassVar[Optional[str]] = None

    if TYPE_CHECKING:

        def exists(self) -> SgFieldCondition:
            """Filter entities where this image exists.

            This is the equivalent of the "is" filter of Shotgrid.

            Returns:
                SgFieldCondition: The field condition.
            """

        def not_exists(self) -> SgFieldCondition:
            """Filter entities where this image does not exist.

            This is the equivalent of the "is_not" filter of Shotgrid.

            Returns:
                SgFieldCondition: The field condition.
            """


class ListField(AbstractValueField[Optional[List[str]]]):
    """Definition of a list field."""

    cast_type: Type[List[str]] = list
    __sg_type__: str = "list"
    default_value: ClassVar[Optional[List[str]]] = None

    if TYPE_CHECKING:

        def is_in(self, texts: List[str]) -> SgFieldCondition:
            """Filter entities where this entity name is within the given texts.

            This is the equivalent of the "in" filter of Shotgrid.

            Args:
                texts (list[str]): texts to test

            Returns:
                SgFieldCondition: The field condition.
            """

        def is_not_in(self, texts: List[str]) -> SgFieldCondition:
            """Filter entities where this entity name is not within the given texts.

            This is the equivalent of the "not_in" filter of Shotgrid.

            Args:
                texts (list[str]): texts to test

            Returns:
                SgFieldCondition: The field condition.
            """


class PercentField(FloatField):
    """Definition of a percent field."""

    __sg_type__: str = "percent"


class SerializableField(AbstractValueField[Optional[Dict[str, Any]]]):
    """Definition of a serializable field."""

    cast_type: Type[Dict[str, Any]] = dict
    __sg_type__: str = "serializable"
    default_value: ClassVar[Optional[Dict[str, Any]]] = None


class StatusField(AbstractValueField[str]):
    """Definition of a status field."""

    __sg_type__: str = "status_list"
    default_value: ClassVar[str]


class UrlField(AbstractValueField[Optional[str]]):
    """Definition of an url field."""

    cast_type: Type[str] = str
    __sg_type__: str = "url"
    default_value: ClassVar[Optional[str]] = None


# Expose all the available fields (intended for model generation)
field_by_sg_type: Dict[str, Type[AbstractField[Any]]] = {
    field_cls.__sg_type__: field_cls
    for name, field_cls in locals().items()
    if isinstance(field_cls, type)
    and issubclass(field_cls, AbstractField)
    and field_cls.__sg_type__ is not None
}
