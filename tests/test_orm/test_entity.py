"""Tests on entities."""

from __future__ import annotations

from typing import Any
from typing import ClassVar
from typing import Optional
from typing import Type
from typing import Union

import pytest
from classes import Asset
from classes import Project
from classes import Shot
from classes import Task
from typing_extensions import List

from sgchemist.orm import EntityField
from sgchemist.orm import MultiEntityField
from sgchemist.orm import NumberField
from sgchemist.orm import SgEntity
from sgchemist.orm import TextField
from sgchemist.orm import error
from sgchemist.orm import mapped_field
from sgchemist.orm.field_descriptor import alias_relationship
from sgchemist.orm.field_descriptor import relationship
from sgchemist.orm.instrumentation import InstrumentedField
from sgchemist.orm.instrumentation import InstrumentedMultiTargetSingleRelationship
from sgchemist.orm.meta import EntityState


@pytest.fixture
def shot_entity() -> Type[Shot]:
    """Returns the TestShot entity."""
    return Shot


@pytest.fixture
def shot_not_commited(shot_entity: Type[Shot]) -> Shot:
    """Returns a non commited TestShot instance."""
    return shot_entity(name="foo")


@pytest.fixture
def shot_commited(shot_entity: Type[Shot]) -> Shot:
    """Returns a commited TestShot instance."""
    return shot_entity(name="foo", id=42)


def test_entity_values(shot_entity: Type[Shot]) -> None:
    """Tests the values of the fields."""
    assert shot_entity.__sg_type__ == "Shot"
    assert list(shot_entity.__fields__.values()) == [
        SgEntity.id,
        shot_entity.name,
        shot_entity.description,
        shot_entity.project,
        shot_entity.parent_shots,
        shot_entity.tasks,
        shot_entity.assets,
    ]
    assert shot_entity.__abstract__ is False
    assert shot_entity.__attr_per_field_name__ == {
        "assets": "assets",
        "code": "name",
        "id": "id",
        "project": "project",
        "description": "description",
        "parent_shots": "parent_shots",
        "tasks": "tasks",
    }
    assert isinstance(shot_entity.id, InstrumentedField)


def test_model_creation_missing_sg_type() -> None:
    """Tests a missing __sg_type__ attribute raises an error."""
    with pytest.raises(error.SgEntityClassDefinitionError):

        class TestEntity1(SgEntity):
            pass


def test_model_creation_reserved_attributes() -> None:
    """Tests reserved attributes are protected against modifications."""
    # No reserved attributes
    with pytest.raises(error.SgEntityClassDefinitionError):

        class TestEntity1(SgEntity):
            __sg_type__ = "test"
            __fields__ = "test"  # type: ignore


def test_model_attribute_overlap() -> None:
    """Tests relationship attributes are protected against overlapping.

    Because we use a getattr to reference a relationship field, the field python
    attribute name cannot be one of the attribute of field of relationship classes.
    """
    with pytest.raises(error.SgEntityClassDefinitionError):

        class WeirdEntity(SgEntity):
            __sg_type__ = "test"
            get_name: TextField


def test_model_duplicate_field() -> None:
    """Tests it is not possible to duplicate a field."""
    with pytest.raises(error.SgEntityClassDefinitionError):

        class WeirdEntity(SgEntity):
            __sg_type__ = "test"
            id: NumberField


def test_model_entity_field_has_no_container() -> None:
    """Tests it is not possible to create an entity field with a container."""
    with pytest.raises(error.SgEntityClassDefinitionError):

        class TestEntity1(SgEntity):
            __sg_type__ = "test"
            entity_with_container: EntityField[List[SgEntity]]


def test_model_multi_entity_field_has_container() -> None:
    """Tests it is not possible to create a multi-entity field without a container."""
    with pytest.raises(error.SgEntityClassDefinitionError):

        class TestEntity1(SgEntity):
            __sg_type__ = "test"
            multi_entity_with_no_container: MultiEntityField[SgEntity]


def test_undefined_fields() -> None:
    """Tests undefined fields raises an error."""

    class TestEntity(SgEntity):
        __sg_type__ = "test1"

    with pytest.raises(error.SgEntityClassDefinitionError):

        class _TestEntity2(SgEntity):
            __sg_type__ = "test2"
            entity: int = 3

    with pytest.raises(error.SgEntityClassDefinitionError):

        class _TestEntity3(SgEntity):
            __sg_type__ = "test2"
            entity: TestEntity


def test_right_mapped_field_per_annotation() -> None:
    """Tests the correct MappedColumn object is used for a given annotation."""
    with pytest.raises(error.SgEntityClassDefinitionError):

        class _TestEntity1(SgEntity):
            __sg_type__ = "test"
            field: TextField = relationship()

    with pytest.raises(error.SgEntityClassDefinitionError):

        class _TestEntity2(SgEntity):
            __sg_type__ = "test"
            field: EntityField[_TestEntity2] = mapped_field()

    with pytest.raises(error.SgEntityClassDefinitionError):

        class _TestEntity3(SgEntity):
            __sg_type__ = "test"
            field: MultiEntityField[_TestEntity2] = mapped_field()


def test_union_entity_is_multi_target() -> None:
    """Tests a multi target entity always uses unions."""

    class TestEntity(SgEntity):
        __sg_type__ = "test1"

    class TestWithUnion(SgEntity):
        __sg_type__ = "test"
        entity: EntityField[Union[SgEntity, TestEntity]]

    assert isinstance(TestWithUnion.entity, InstrumentedMultiTargetSingleRelationship)

    # Multi entity must be a list
    with pytest.raises(error.SgEntityClassDefinitionError):

        class TestEntity1(SgEntity):
            __sg_type__ = "test"
            entity: MultiEntityField[Union[SgEntity, TestEntity]]

    class TestEntity2(SgEntity):
        __sg_type__ = "test"
        entity: MultiEntityField[List[Union[SgEntity, TestEntity]]]


def test_alias_field_construction() -> None:
    """Tests the construction of an alias field."""

    class TestEntity(SgEntity):
        __sg_type__ = "test"

    # An alias relationship must be a single entity field
    with pytest.raises(error.SgEntityClassDefinitionError):

        class TestWithAlias(SgEntity):
            __sg_type__ = "foo"
            entity: EntityField[Union[TestWithAlias, TestEntity]] = relationship()
            alias: MultiEntityField[TestEntity] = alias_relationship(entity)

    # An alias relationship cannot target multiple entities
    with pytest.raises(error.SgEntityClassDefinitionError):

        class TestEntity1(SgEntity):
            __sg_type__ = "foo"
            entity: EntityField[Union[TestEntity1, TestEntity]] = relationship()
            alias: EntityField[Union[TestEntity, TestEntity1]] = alias_relationship(
                entity
            )

    class OutsideEntity(SgEntity):
        __sg_type__ = "outside"
        outside_field: EntityField[TestEntity]

    # An alias field must target an entity from the aliased field
    with pytest.raises(error.SgEntityClassDefinitionError):

        class _TestWithAlias(SgEntity):
            __sg_type__ = "foo"
            entity: EntityField[Union[TestWithAlias, TestEntity]] = relationship()
            alias: EntityField[OutsideEntity] = alias_relationship(entity)


def test_various_annotations() -> None:
    """Tests various annotations."""
    with pytest.raises(error.SgEntityClassDefinitionError):

        class TestEntity1(SgEntity):
            __sg_type__ = "test"
            test: Optional[EntityField[Any]]

    with pytest.raises(error.SgEntityClassDefinitionError):

        class TestEntity2(SgEntity):
            __sg_type__ = "test"
            test: List[EntityField[Any]]

    with pytest.raises(error.SgEntityClassDefinitionError):

        class TestEntity3(SgEntity):
            __sg_type__ = "test"
            test: List[Any] = relationship()

    class TestEntity4(SgEntity):
        __sg_type__ = "test"
        test: ClassVar[List[Any]]

    with pytest.raises(error.SgEntityClassDefinitionError):

        class TestEntity5(SgEntity):
            __sg_type__ = "test"
            test: List[str]

    class Other:
        pass

    class TestEntity6(SgEntity):
        __sg_type__ = "test"
        test: ClassVar[List[Other]]

    # String annotation
    class TestEntity7(SgEntity):
        __sg_type__ = "test"
        test: "TextField"

    class TestEntity8(SgEntity):
        __sg_type__ = "test"
        test: EntityField["SgEntity"]

    class TestEntity9(SgEntity):
        __sg_type__ = "test"
        test: "EntityField[SgEntity]"

    with pytest.raises(error.SgEntityClassDefinitionError):

        class TestEntity10(SgEntity):
            __sg_type__ = "test"
            test: TextField = 5  # type: ignore

    with pytest.raises(error.SgEntityClassDefinitionError):

        class TestEntity11(SgEntity):
            __sg_type__ = "test"
            test: EntityField  # type: ignore

    with pytest.raises(error.SgEntityClassDefinitionError):

        class TestEntity12(SgEntity):
            __sg_type__ = "test"
            test: "weird[UnknownField]"  # type: ignore # noqa: F821


def test_default_init(shot_entity: Type[Shot]) -> None:
    """Tests the initialization of an entity."""
    inst = shot_entity(name="test")
    assert inst.name == "test"
    assert inst.id is None
    assert isinstance(inst.__state__, EntityState)

    with pytest.raises(error.SgInvalidAttributeError):
        shot_entity(foo="test")


def test_get_fields(shot_entity: Type[Shot], shot_not_commited: Shot) -> None:
    """Tests field getter method."""
    assert (
        shot_not_commited.__state__.get_current_value(
            shot_entity.name.get_attribute_name()
        )
        == "foo"
    )


def test_set_fields(shot_not_commited: Shot) -> None:
    """Tests field setter method."""
    model = shot_not_commited.__class__
    shot_not_commited.__state__.set_current_value(
        model.name.get_attribute_name(), "test"
    )
    assert shot_not_commited.name == "test"


def test_repr(shot_not_commited: Shot) -> None:
    """Tests repr method."""
    assert isinstance(repr(shot_not_commited), str)


def test_state_init(shot_not_commited: Shot) -> None:
    """Tests the initialized entity has the expected state."""
    state = shot_not_commited.__state__
    model = shot_not_commited.__class__
    assert not state.is_commited()
    assert state.pending_add is False
    assert state.pending_deletion is False
    assert state.deleted is False
    assert state.modified_fields == [model.name]
    assert state.is_modified() is True


def test_instance_with_primary_key_is_committed(shot_commited: Shot) -> None:
    """Tests a shot with a None id is considered commited."""
    state = shot_commited.__state__
    assert state.is_commited()


@pytest.mark.parametrize(
    "entity, expected_modified_fields",
    [
        (Project(name="test"), [Project.name]),
        (Project(id=1, name="test"), [Project.name]),
        (Project(id=1), []),
    ],
)
def test_entity_modified_fields(
    entity: SgEntity, expected_modified_fields: list[InstrumentedField[Any]]
) -> None:
    """Tests that initialized fields are considered modified expect id."""
    assert entity.__state__.modified_fields == expected_modified_fields


def test_field_descriptor(shot_not_commited: Shot) -> None:
    """Tests field descriptor behavior."""
    model = shot_not_commited.__class__
    state = shot_not_commited.__state__
    state.revert_changes()
    assert state.is_modified() is False
    shot_not_commited.name = "test"
    assert state.is_modified() is True
    assert state.get_original_value(model.name.get_attribute_name()) == "foo"
    shot_not_commited.name = "foo"
    assert state.is_modified() is False


def test_cannot_set_primary_key(shot_not_commited: Shot) -> None:
    """Tests the id cannot be modified."""
    with pytest.raises(ValueError):
        shot_not_commited.id = 1


def test_alias_field_descriptor() -> None:
    """Tests alias field descriptor behavior."""
    task = Task(name="test")
    assert task.entity is None
    assert task.shot is None
    assert task.asset is None
    # Test with shot
    shot = Shot(name="test")
    task_shot = Task(name="test", entity=shot)
    assert task_shot.entity is shot
    assert task_shot.shot is shot
    assert task_shot.asset is None
    # Test with asset
    asset = Asset(name="test")
    task_asset = Task(name="test", entity=asset)
    assert task_asset.entity is asset
    assert task_asset.shot is None
    assert task_asset.asset is asset
