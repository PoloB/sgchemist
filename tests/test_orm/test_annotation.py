"""Test missing future annotation."""

import pytest

from sgchemist import error
from sgchemist.orm import NumberField
from sgchemist.orm import SgBaseEntity


def test_future_annotation_missing() -> None:
    """Test missing future annotation raises an error."""

    class SgEntity(SgBaseEntity):
        pass

    with pytest.raises(error.SgEntityClassDefinitionError):

        class TestEntity(SgEntity):
            __sg_type__ = "test"
            f: NumberField
