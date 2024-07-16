"""Collections of typing utility functions."""

from __future__ import absolute_import
from __future__ import annotations

import ast
import builtins
import re
import sys
from typing import Any
from typing import ForwardRef
from typing import Mapping
from typing import Optional
from typing import Type
from typing import TypeVar
from typing import Union
from typing import cast

from typing_extensions import NewType
from typing_extensions import Protocol
from typing_extensions import TypeAliasType
from typing_extensions import _SpecialForm
from typing_extensions import get_args
from typing_extensions import get_origin

_T = TypeVar("_T", bound=Any)

NoneFwd = ForwardRef("None")
AnnotationScanType = Union[
    Type[Any], str, ForwardRef, NewType, TypeAliasType, _SpecialForm
]


def get_annotations(obj: Any) -> Mapping[str, Any]:
    """Return the annotations of the given object.

    Compatibility function to `inspect.get_annotations`.
    """
    # https://docs.python.org/3/howto/annotations.html#annotations-howto
    ann = (
        obj.__dict__.get("__annotations__", None)
        if isinstance(obj, type)
        else getattr(obj, "__annotations__", None)
    )
    if ann is None:
        return {}
    else:
        return cast("Mapping[str, Any]", ann)


class ArgsTypeProtocol(Protocol):
    """Defines a Protocol for types that have ``__args__``."""

    __args__: tuple[AnnotationScanType, ...]


def eval_name_only(
    name: str,
    scope: dict[str, Any],
) -> Any:
    """Evaluates the given Python variable and returns the result.

    Args:
        name: name of the variable.
        scope: variables to use to evaluate the annotation.

    Returns:
        The result of the evaluated variable.

    Raises:
        NameError: the given module cannot be found in ``sys.modules`` or in the
            global variables.
    """
    for scope_ in [scope, builtins.__dict__]:
        try:
            return scope_[name]
        except KeyError:
            continue
    raise NameError(f"{name} is not defined.")


def stringify_ast(
    exp: ast.AST,
) -> str:
    """Convert the given subscript to a string."""
    if isinstance(exp, ast.BinOp):
        left = stringify_ast(exp.left).replace("'", "")
        op = stringify_ast(exp.op)
        right = stringify_ast(exp.right).replace("'", "")
        return f"'{left} {op} {right}'"
    elif isinstance(exp, ast.BitOr):
        return "|"
    elif isinstance(exp, ast.Subscript):
        value = stringify_ast(exp.value).replace("'", "")
        slice = stringify_ast(exp.slice)
        return f"{value}[{slice}]"
    elif isinstance(exp, ast.Name):
        return f"{exp.id!r}"
    elif isinstance(exp, (ast.Constant, ast.NameConstant)):
        return f"{exp.value!r}"
    elif isinstance(exp, ast.Tuple):
        return ", ".join(map(stringify_ast, exp.elts))
    elif isinstance(exp, ast.Index):
        return stringify_ast(exp.value)  # type: ignore # this is for python 3.7 compat
    raise TypeError(f"Cannot parse element {type(exp)}")


def cleanup_mapped_str_annotation(
    annotation: str,
    scope: dict[str, Any],
) -> tuple[Any, str]:
    """Cleans the given annotation string to only keep the internal as strings.

    Args:
        annotation: The annotation string to clean.
        scope: variables to use to evaluate the annotation.

    Returns:
        the top element of the annotation, the cleaned annotation.
    """
    annotation = annotation.replace('"', "").replace("'", "")
    expr_body = ast.parse(annotation).body
    if not expr_body:
        raise TypeError("No annotation found.")
    expr = expr_body[0]
    assert isinstance(expr, ast.Expr)
    subscript = expr.value
    # We only handle subscript
    if isinstance(subscript, ast.Name):
        return eval_name_only(subscript.id, scope), annotation
    if not isinstance(subscript, ast.Subscript):
        raise TypeError(
            f"Expected annotation {annotation} to be a subscript of field, "
            f"but got {type(subscript)}"
        )
    subscript_value = subscript.value
    assert isinstance(subscript_value, ast.Name)
    obj = eval_name_only(subscript_value.id, scope)
    annotation = stringify_ast(subscript.slice)
    return obj, f"{subscript_value.id}[{annotation}]"


def make_union_type(*types: AnnotationScanType) -> type[Any]:
    """Make a Union type.

    This is needed by :func:`.de_optionalize_union_types` which removes
    ``NoneType`` from a ``Union``.

    Args:
        types: The types to make a Union type.

    Returns:
        The union type.
    """
    return cast(Any, Union).__getitem__(types)  # type: ignore


def expand_unions(type_: Any) -> tuple[Any, ...]:
    """Returns a type as a tuple of individual types, expanding for ``Union`` types.

    Args:
        type_: The type to expand.

    Returns:
        The types expanded.
    """
    ret = tuple([type_])
    if isinstance(type_, ForwardRef):
        return expand_unions(type_.__forward_arg__)
    if isinstance(type_, str):
        return tuple(re.split(r"\s*\|\s*", type_))
    if get_origin(type_) is Union:
        ret = tuple(set(get_args(type_)))
    return tuple(
        typ.__forward_arg__ if isinstance(typ, ForwardRef) else typ for typ in ret
    )


if sys.version_info < (3, 10):
    TYPES_TO_DE_OPTIONALIZE = {Optional, Union}
else:
    from types import UnionType

    TYPES_TO_DE_OPTIONALIZE = {Optional, Union, UnionType}


def de_optionalize_union_types(
    type_: AnnotationScanType,
) -> AnnotationScanType:
    """Returns the annotation striping any optionals.

    Args:
        type_: The type to de-optionalize.

    Returns:
        The annotation without any optionals.
    """
    if isinstance(type_, ForwardRef):
        # Check for new style union using "|"
        splits = re.split(r"\s*\|\s*", type_.__forward_arg__)
        try:
            splits.remove("None")
        except ValueError:
            pass
        return " | ".join(splits)
    if get_origin(type_) in TYPES_TO_DE_OPTIONALIZE:
        typ = set(get_args(type_))
        typ.discard(NoneFwd)
        typ.discard(type(None))

        return make_union_type(*typ)
    return type_
