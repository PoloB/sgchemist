"""Tests on entities."""

from __future__ import annotations

from typing import Any
from typing import ClassVar
from typing import Dict
from typing import List
from typing import Optional
from typing import Union

import pytest

from sgchemist.orm import error
from sgchemist.orm.entity import EntityState
from sgchemist.orm.entity import SgBaseEntity
from sgchemist.orm.field_info import get_types
from sgchemist.orm.fields import AbstractField
from sgchemist.orm.fields import AbstractValueField
from sgchemist.orm.fields import EntityField
from sgchemist.orm.fields import MultiEntityField
from sgchemist.orm.fields import NumberField
from sgchemist.orm.fields import TextField
from sgchemist.orm.fields import alias
from tests.classes import Asset
from tests.classes import Project
from tests.classes import Shot
from tests.classes import Task


@pytest.fixture()
def shot_entity() -> type[Shot]:
    """Returns the TestShot entity."""
    return Shot


@pytest.fixture()
def shot_not_commited(shot_entity: type[Shot]) -> Shot:
    """Returns a non commited TestShot instance."""
    return shot_entity(name="foo")


@pytest.fixture()
def shot_commited(shot_entity: type[Shot]) -> Shot:
    """Returns a commited TestShot instance."""
    return shot_entity(name="foo", id=42)


def test_entity_values(shot_entity: type[Shot]) -> None:
    """Tests the values of the fields."""
    assert shot_entity.__sg_type__ == "Shot"
    assert shot_entity.__fields__ == [
        shot_entity.id,
        shot_entity.name,
        shot_entity.description,
        shot_entity.project,
        shot_entity.parent_shots,
        shot_entity.tasks,
        shot_entity.assets,
    ]
    assert shot_entity.__attr_per_field_name__ == {
        "assets": "assets",
        "code": "name",
        "id": "id",
        "project": "project",
        "description": "description",
        "parent_shots": "parent_shots",
        "tasks": "tasks",
    }
    assert isinstance(shot_entity.id, AbstractValueField)


def test_model_creation_missing_sg_type() -> None:
    """Tests a missing __sg_type__ attribute raises an error."""

    class SgEntity(SgBaseEntity):
        pass

    with pytest.raises(error.SgEntityClassDefinitionError):

        class TestEntity1(SgEntity):
            pass


def test_model_creation_reserved_attributes() -> None:
    """Tests reserved attributes are protected against modifications."""

    class SgEntity(SgBaseEntity):
        pass

    # No reserved attributes
    with pytest.raises(error.SgEntityClassDefinitionError):

        class TestEntity1(SgEntity):
            __sg_type__ = "test"
            __fields_by_attr__ = "test"  # type: ignore[assignment]


def test_model_duplicate_field() -> None:
    """Tests it is not possible to duplicate a field."""

    class SgEntity(SgBaseEntity):
        pass

    with pytest.raises(error.SgEntityClassDefinitionError):

        class WeirdEntity(SgEntity):
            __sg_type__ = "test"
            test: NumberField = NumberField(name="id")


def test_model_entity_field_has_no_container() -> None:
    """Tests it is not possible to create an entity field with a container."""

    class SgEntity(SgBaseEntity):
        pass

    with pytest.raises(error.SgEntityClassDefinitionError):

        class TestEntityList(SgEntity):
            __sg_type__ = "test"
            entity_with_container: EntityField[list[SgBaseEntity]]

    with pytest.raises(error.SgEntityClassDefinitionError):

        class TestEntityListOld(SgEntity):
            __sg_type__ = "test"
            entity_with_container: EntityField[List[SgBaseEntity]]  # noqa: UP006

    with pytest.raises(error.SgEntityClassDefinitionError):

        class TestEntityDict(SgEntity):
            __sg_type__ = "test"
            entity_with_container: EntityField[dict[str, SgBaseEntity]]

    with pytest.raises(error.SgEntityClassDefinitionError):

        class TestEntityDictOld(SgEntity):
            __sg_type__ = "test"
            entity_with_container: EntityField[Dict[str, SgBaseEntity]]  # noqa: UP006


def test_model_multi_entity_field_has_no_container() -> None:
    """Tests it is not possible to create a multi-entity field with a container."""

    class SgEntity(SgBaseEntity):
        pass

    with pytest.raises(error.SgEntityClassDefinitionError):

        class TestEntity1(SgEntity):
            __sg_type__ = "test"
            multi_entity_container: MultiEntityField[list[SgBaseEntity]]


def test_right_mapped_field_per_annotation() -> None:
    """Tests the correct MappedColumn object is used for a given annotation."""

    class SgEntity(SgBaseEntity):
        pass

    with pytest.raises(error.SgEntityClassDefinitionError):

        class _TestEntity1(SgEntity):
            __sg_type__ = "test1"
            field: TextField = EntityField()  # type: ignore[assignment]

    with pytest.raises(error.SgEntityClassDefinitionError):

        class _TestEntity2(SgEntity):
            __sg_type__ = "test2"
            field: EntityField[_TestEntity2] = TextField()  # type: ignore[assignment]

    with pytest.raises(error.SgEntityClassDefinitionError):

        class _TestEntity3(SgEntity):
            __sg_type__ = "test3"
            field: MultiEntityField[_TestEntity2] = TextField()  # type: ignore[assignment]


def test_cannot_create_entity_directly_from_base() -> None:
    """Test we cannot directly subclass SgBaseEntity class."""
    with pytest.raises(error.SgEntityClassDefinitionError):

        class TestEntity(SgBaseEntity):
            __sg_type__ = "test1"


def test_cannot_create_twice_the_same_entity() -> None:
    """Test we cannot create an entity twice with the same base class."""

    class SgEntity(SgBaseEntity):
        pass

    class TestEntity1(SgEntity):
        __sg_type__ = "test"

    class TestEntity2(SgEntity):
        __sg_type__ = "test1"

    with pytest.raises(error.SgEntityClassDefinitionError):

        class TestEntity3(SgEntity):
            __sg_type__ = "test1"

    class OtherSgEntity(SgBaseEntity):
        pass

    class TestEntity4(OtherSgEntity):
        __sg_type__ = "test"


def test_union_entity_in_entity() -> None:
    """Tests a multi target entity always uses unions."""

    class SgEntity(SgBaseEntity):
        pass

    class TestEntity(SgEntity):
        __sg_type__ = "test"

    class TestWithUnion(SgEntity):
        __sg_type__ = "test_with_union"
        entity: EntityField[TestWithUnion | TestEntity]

    assert isinstance(TestWithUnion.entity, EntityField)
    assert set(get_types(TestWithUnion.entity)) == {TestEntity, TestWithUnion}

    class TestWithUnionOld(SgEntity):
        __sg_type__ = "test_with_union_old"
        entity: EntityField[Union[TestWithUnion, TestEntity]]  # noqa: UP007

    assert isinstance(TestWithUnionOld.entity, EntityField)
    assert set(get_types(TestWithUnionOld.entity)) == {TestEntity, TestWithUnion}

    # Test union and optional
    class TestWithUnionOptional(SgEntity):
        __sg_type__ = "test_with_union_optional"
        entity: EntityField[TestWithUnion | TestEntity | None]

    assert isinstance(TestWithUnionOptional.entity, EntityField)
    assert set(get_types(TestWithUnionOptional.entity)) == {TestWithUnion, TestEntity}

    class TestWithUnionOptionalOld(SgEntity):
        __sg_type__ = "test_with_union_optional_old"
        entity: EntityField[Optional[Union[TestWithUnion, TestEntity]]]  # noqa: UP007

    assert isinstance(TestWithUnionOptionalOld.entity, EntityField)
    assert set(get_types(TestWithUnionOptional.entity)) == {TestWithUnion, TestEntity}

    class TestWithUnionOptionalMixedUnion(SgEntity):
        __sg_type__ = "test_with_union_optional_mixed"
        entity: EntityField[Optional[TestWithUnion | TestEntity]]  # noqa: UP007

    assert isinstance(TestWithUnionOptionalMixedUnion.entity, EntityField)
    assert set(get_types(TestWithUnionOptional.entity)) == {TestWithUnion, TestEntity}

    class TestWithUnionOptionalMixedNone(SgEntity):
        __sg_type__ = "test_with_union_optional_mixed_none"
        entity: EntityField[Union[TestWithUnion, TestEntity] | None]  # noqa: UP007

    assert isinstance(TestWithUnionOptionalMixedNone.entity, EntityField)
    assert set(get_types(TestWithUnionOptional.entity)) == {TestWithUnion, TestEntity}


def test_alias_field_construction() -> None:
    """Tests the construction of an alias field."""

    class SgEntity(SgBaseEntity):
        pass

    class TestEntity(SgEntity):
        __sg_type__ = "test"

    # An alias relationship must be a single entity field
    with pytest.raises(error.SgEntityClassDefinitionError):

        class TestWithAlias(SgEntity):
            __sg_type__ = "foo"
            entity: EntityField[TestWithAlias | TestEntity | None] = EntityField()
            alias: MultiEntityField[TestEntity] = alias(entity)  # type: ignore[assignment]

    # An alias relationship cannot target multiple entities
    with pytest.raises(error.SgEntityClassDefinitionError):

        class TestEntity1(SgEntity):
            __sg_type__ = "foo"
            entity: EntityField[TestEntity1 | TestEntity] = EntityField()
            alias: EntityField[TestEntity | TestEntity1] = alias(entity)

    class OutsideEntity(SgEntity):
        __sg_type__ = "outside"
        outside_field: EntityField[TestEntity]

    # An alias field must target an entity from the aliased field
    with pytest.raises(error.SgEntityClassDefinitionError):

        class _TestWithAlias(SgEntity):
            __sg_type__ = "foo"
            entity: EntityField[TestWithAlias | TestEntity] = EntityField()
            alias: EntityField[OutsideEntity] = alias(entity)


def test_not_none_annotation() -> None:
    """Tests None cannot be used with an entity field."""

    class SgEntity(SgBaseEntity):
        pass

    with pytest.raises(error.SgEntityClassDefinitionError):

        class TestEntity1(SgEntity):
            __sg_type__ = "test1"
            test: EntityField[Any] | None


def test_any_non_entity_is_valid() -> None:
    """Tests that an annotation not directly typed as EntityField is valid."""

    class SgEntity(SgBaseEntity):
        pass

    class TestEntity2(SgEntity):
        __sg_type__ = "test2"
        test: list[EntityField[Any]]


def test_classic_annotation_are_valid() -> None:
    """Tests that non field annotation are valid."""

    class SgEntity(SgBaseEntity):
        pass

    class TestEntity4(SgEntity):
        __sg_type__ = "test4"
        test: ClassVar[list[Any]]

    class TestEntity5(SgEntity):
        __sg_type__ = "test5"
        test: list[str]

    class Other:
        pass

    class TestEntity6(SgEntity):
        __sg_type__ = "test6"
        test: ClassVar[list[Other]]


def test_string_annotation() -> None:
    """Tests that string annotations are valid."""

    class SgEntity(SgBaseEntity):
        pass

    # String annotation
    class TestEntity1(SgEntity):
        __sg_type__ = "test1"
        test: TextField

    class TestEntity2(SgEntity):
        __sg_type__ = "test2"
        test: EntityField[TestEntity1]

    class TestEntity3(SgEntity):
        __sg_type__ = "test3"
        test: EntityField[TestEntity1]

    class TestEntity4(SgEntity):
        __sg_type__ = "test4"
        test: EntityField[TestEntity1 | None]


def test_targeting_invalid_entity_fails_lazily() -> None:
    """Test using invalid entity even lazily raises an error."""

    class SgEntity(SgBaseEntity):
        pass

    class TestEntity2(SgEntity):
        __sg_type__ = "test2"
        test: EntityField[OtherBaseEntity]

    class OtherBaseEntity(SgBaseEntity):
        pass

    with pytest.raises(error.SgEntityClassDefinitionError):
        get_types(TestEntity2.test)

    class TestEntity3(SgEntity):
        __sg_type__ = "test3"
        test: EntityField[Test]

    class Test:
        pass


def test_field_uses_field_as_initializer() -> None:
    """Make sure we can use many combination of optional and union types."""

    class SgEntity(SgBaseEntity):
        pass

    with pytest.raises(error.SgEntityClassDefinitionError):

        class TestEntity10(SgEntity):
            __sg_type__ = "test10"
            test: TextField = 5  # type: ignore[assignment]

    with pytest.raises(error.SgEntityClassDefinitionError):

        class TestEntity11(SgEntity):
            __sg_type__ = "test11"
            test: EntityField  # type: ignore[type-arg]


def test_misc_annotations() -> None:
    """Test other corner cases."""

    class SgEntity(SgBaseEntity):
        pass

    with pytest.raises(error.SgEntityClassDefinitionError):

        class TestEntity12(SgEntity):
            __sg_type__ = "test12"
            test: weird[UnknownField]  # type: ignore[name-defined]  # noqa: F821

    with pytest.raises(error.SgEntityClassDefinitionError):

        class TestEntity13(SgEntity):
            __sg_type__ = "test13"
            test: MultiEntityField  # type: ignore[type-arg]

    with pytest.raises(error.SgEntityClassDefinitionError):

        class TestEntity14(SgEntity):
            __sg_type__ = "test15"
            test: ""  # type: ignore[syntax]  # noqa: F722


def test_invalid_expression_in_annotations() -> None:
    """Test invalid expression in annotation."""

    class SgEntity(SgBaseEntity):
        pass

    with pytest.raises(error.SgEntityClassDefinitionError):

        class TestEntity14(SgEntity):
            __sg_type__ = "test14"
            test: EntityField[1 & 5]  # type: ignore[valid-type]


def test_explicit_target_is_entity() -> None:
    """Test that not using an explicit target raises a error during class init."""

    class SgEntity(SgBaseEntity):
        pass

    class TestEntity(SgEntity):
        __sg_type__ = "test"
        test: EntityField[int]

    with pytest.raises(error.SgEntityClassDefinitionError):
        get_types(TestEntity.test)


def test_default_init(shot_entity: type[Shot]) -> None:
    """Tests the initialization of an entity."""
    inst = shot_entity(name="test")
    assert inst.name == "test"
    assert inst.id is None
    assert isinstance(inst.__state__, EntityState)

    with pytest.raises(error.SgInvalidAttributeError):
        shot_entity(foo="test")


def test_get_fields(shot_entity: type[Shot], shot_not_commited: Shot) -> None:
    """Tests field getter method."""
    assert shot_not_commited.__state__.get_value(shot_entity.name) == "foo"


def test_set_fields(shot_not_commited: Shot) -> None:
    """Tests field setter method."""
    model = shot_not_commited.__class__
    shot_not_commited.__state__.set_value(model.name, "test")
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
    ("entity", "expected_modified_fields"),
    [
        (Project(name="test"), [Project.name]),
        (Project(id=1, name="test"), [Project.name]),
        (Project(id=1), []),
    ],
)
def test_entity_modified_fields(
    entity: SgBaseEntity,
    expected_modified_fields: list[AbstractField[Any]],
) -> None:
    """Tests that initialized fields are considered modified expect id."""
    assert entity.__state__.modified_fields == expected_modified_fields


def test_field_descriptor(shot_not_commited: Shot) -> None:
    """Tests field descriptor behavior."""
    model = shot_not_commited.__class__
    state = shot_not_commited.__state__
    state.set_as_original()
    assert state.is_modified() is False
    shot_not_commited.name = "test"
    assert state.is_modified() is True
    assert state.get_original_value(model.name) == "foo"
    shot_not_commited.name = "foo"
    assert state.is_modified() is False


def test_cannot_set_primary_key(shot_not_commited: Shot) -> None:
    """Tests the id cannot be modified."""
    with pytest.raises(error.SgFieldNotSettableError):
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


def test_get_value() -> None:
    """Test the get_value method."""
    project = Project(name="project")
    asset = Asset(name="asset", project=project)
    task = Task(name="task", entity=asset)
    assert project.get_value(Project.name) == "project"
    assert asset.get_value(Asset.name) == "asset"
    assert asset.get_value(Asset.project) is project
    assert asset.get_value(Asset.project.f(Project.name)) == "project"
    assert task.get_value(Task.name) == "task"
    assert task.get_value(Task.entity) is asset
    assert task.get_value(Task.entity.f(Asset.name)) == "asset"
    assert task.get_value(Task.entity.f(Asset.project).f(Project.name)) == "project"

    with pytest.raises(error.SgInvalidFieldError):
        task.get_value(Asset.project)


def test_as_dict() -> None:
    """Test as dict method."""
    project = Project(name="project")
    assert project.as_dict() == {"name": "project", "id": None, "type": "Project"}
    asset = Asset(name="asset", project=project)
    assert asset.as_dict() == {
        "code": "asset",
        "id": None,
        "project": {"name": "project", "id": None, "type": "Project"},
        "shots": [],
        "tasks": [],
        "type": "Asset",
    }
