"""Tests typing module."""

from __future__ import annotations

from typing import Any
from typing import Tuple

import _testmod
import pytest

from sgchemist.orm import typing_util


def test_get_annotations() -> None:
    """Test get_annotations."""

    class Test:
        t_int: int
        t_int_str: "int"
        t_tup_int: tuple[int]
        t_tup_int_str: "tuple[int]"
        t_tup_int_str_part: tuple["int"]
        t_tup_old_int: Tuple[int]
        t_tup_old_int_str: "Tuple[int]"
        t_tup_old_int_str_part: Tuple["int"]
        t = 0

    annotation = typing_util.get_annotations(Test)
    assert annotation == {
        "t_int": "int",
        "t_int_str": "'int'",
        "t_tup_int": "tuple[int]",
        "t_tup_int_str": "'tuple[int]'",
        "t_tup_int_str_part": "tuple['int']",
        "t_tup_old_int": "Tuple[int]",
        "t_tup_old_int_str": "'Tuple[int]'",
        "t_tup_old_int_str_part": "Tuple['int']",
    }

    class TestNoAnnot:
        pass

    annotation = typing_util.get_annotations(TestNoAnnot)
    assert annotation == {}


class _InScopeTestClass:
    """Test class."""


def test_eval_name_only() -> None:
    """Test eval_name_only."""
    value = typing_util.eval_name_only("int", {"int": int})
    assert value == int
    value = typing_util.eval_name_only(
        "_InScopeTestClass", {"_InScopeTestClass": _InScopeTestClass}
    )
    assert value == _InScopeTestClass
    value = typing_util.eval_name_only("_TestModClass", _testmod.__dict__)
    assert value == _testmod._TestModClass

    with pytest.raises(NameError):
        typing_util.eval_name_only("_UnknownClass", _testmod.__dict__)


@pytest.mark.parametrize(
    "annotation, result",
    [
        ("int", (int, "int")),
        ("'int'", (int, "int")),
        ("tuple[int]", (tuple, "tuple[int]")),
        ("tuple['int']", (tuple, "tuple[int]")),
        ("'tuple[int]'", (tuple, "tuple[int]")),
        ('"tuple[int]"', (tuple, "tuple[int]")),
        ("tuple[_InScopeTestClass]", (tuple, "tuple[_InScopeTestClass]")),
        ('"tuple[_InScopeTestClass]"', (tuple, "tuple[_InScopeTestClass]")),
        ('tuple["_InScopeTestClass"]', (tuple, "tuple[_InScopeTestClass]")),
        ("tuple['_InScopeTestClass']", (tuple, "tuple[_InScopeTestClass]")),
        ("tuple[_Unknown]", (tuple, "tuple[ForwardRef('_Unknown')]")),
        ('"tuple[_Unknown]"', (tuple, "tuple[ForwardRef('_Unknown')]")),
        ('tuple["_Unknown"]', (tuple, "tuple[ForwardRef('_Unknown')]")),
        ("tuple['_Unknown']", (tuple, "tuple[ForwardRef('_Unknown')]")),
    ],
)
def test_cleanup_mapped_str_annotation(
    annotation: str, result: tuple[Any, str]
) -> None:
    """Test cleanup_mapped_str_annotation."""
    assert typing_util.cleanup_mapped_str_annotation(annotation, globals()) == result


def test_cleanup_mapped_int_annotation_out_of_scope() -> None:
    """Test cleanup_mapped_int_annotation with an out-of-scope class."""
    assert typing_util.cleanup_mapped_str_annotation(
        "_TestModClass", _testmod.__dict__
    ) == (_testmod._TestModClass, "_TestModClass")


def test_error_cleanup_mapped_str_annotation() -> None:
    """Test error when calling cleanup_mapped_str_annotation with undefined."""
    with pytest.raises(NameError):
        typing_util.cleanup_mapped_str_annotation("UnknownClass", globals())
