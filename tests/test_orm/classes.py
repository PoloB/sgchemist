"""Define entity classes for tests."""

from __future__ import annotations

from typing import List
from typing import Optional
from typing import Union

from sgchemist.orm.entity import SgEntity
from sgchemist.orm.field import DateTimeField
from sgchemist.orm.field import EntityField
from sgchemist.orm.field import ImageField
from sgchemist.orm.field import MultiEntityField
from sgchemist.orm.field import TextField
from sgchemist.orm.field_descriptor import alias_relationship
from sgchemist.orm.field_descriptor import mapped_field
from sgchemist.orm.field_descriptor import relationship


class Project(SgEntity):
    """A test project entity."""

    __sg_type__ = "Project"
    name: TextField


class Shot(SgEntity):
    """A test shot entity."""

    __sg_type__ = "Shot"
    name: TextField = mapped_field("code", name_in_relation="name")
    description: TextField
    project: EntityField[Project]
    parent_shots: MultiEntityField[List[Shot]]
    tasks: MultiEntityField[List[Task]]
    assets: MultiEntityField[List[Asset]]


class Asset(SgEntity):
    """A test asset entity."""

    __sg_type__ = "Asset"
    name: TextField = mapped_field("code", name_in_relation="name")
    project: EntityField[Project]
    shots: MultiEntityField[List[Shot]]
    tasks: MultiEntityField[List[Task]]


class Task(SgEntity):
    """A test task entity."""

    __sg_type__ = "Task"
    name: TextField = mapped_field(name="content")
    entity: EntityField[Optional[Union[Asset, Shot]]] = relationship()
    shot: EntityField[Optional[Shot]] = alias_relationship(entity)
    asset: EntityField[Optional[Asset]] = alias_relationship(entity)
    created_at: DateTimeField
    image: ImageField = mapped_field()
