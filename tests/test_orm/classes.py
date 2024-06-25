"""Define entity classes for tests."""

from __future__ import annotations

from typing import List
from typing import Optional
from typing import Union

from sgchemist.orm import alias
from sgchemist.orm.entity import SgEntity
from sgchemist.orm.fields import DateTimeField
from sgchemist.orm.fields import EntityField
from sgchemist.orm.fields import ImageField
from sgchemist.orm.fields import MultiEntityField
from sgchemist.orm.fields import TextField


class Project(SgEntity):
    """A test project entity."""

    __sg_type__ = "Project"
    name: TextField


class Shot(SgEntity):
    """A test shot entity."""

    __sg_type__ = "Shot"
    name: TextField = TextField("code", name_in_relation="name")
    description: TextField
    project: EntityField[Project]
    parent_shots: MultiEntityField[List[Shot]]
    tasks: MultiEntityField[List[Task]]
    assets: MultiEntityField[List[Asset]]


class Asset(SgEntity):
    """A test asset entity."""

    __sg_type__ = "Asset"
    name: TextField = TextField("code", name_in_relation="name")
    project: EntityField[Project]
    shots: MultiEntityField[List[Shot]]
    tasks: MultiEntityField[List[Task]]


class Task(SgEntity):
    """A test task entity."""

    __sg_type__ = "Task"
    name: TextField = TextField(name="content")
    entity: EntityField[Optional[Union[Asset, Shot]]] = EntityField()
    shot: EntityField[Optional[Shot]] = alias(entity)
    asset: EntityField[Optional[Asset]] = alias(entity)
    created_at: DateTimeField
    image: ImageField = ImageField()
