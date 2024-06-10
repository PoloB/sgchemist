"""Collections of typing utility functions."""

from __future__ import annotations

import builtins
import re
import sys
from re import Match
from typing import Any
from typing import ClassVar
from typing import Dict
from typing import ForwardRef
from typing import Mapping
from typing import Optional
from typing import Tuple
from typing import Type
from typing import TypeVar
from typing import Union
from typing import _SpecialForm
from typing import cast

from typing_extensions import Literal
from typing_extensions import NewType
from typing_extensions import Protocol
from typing_extensions import TypeAliasType
from typing_extensions import TypeGuard
from typing_extensions import get_origin

_T = TypeVar("_T", bound=Any)

NoneType = Literal[None]
AnnotationScanType = Union[Type[Any], str, ForwardRef, NewType, TypeAliasType]
NoneFwd = ForwardRef("None")


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

    __args__: Tuple[AnnotationScanType, ...]


def is_fwd_ref(type_: AnnotationScanType) -> TypeGuard[ForwardRef]:
    """Returns ``True`` if ``type_`` is a forward reference, ``False`` otherwise.

    Args:
        type_: The type to check.

    Returns:
        bool: ``True`` if ``type_`` is a forward reference, ``False`` otherwise.
    """
    if isinstance(type_, ForwardRef):
        return True
    else:
        return False


def eval_expression(
    expression: str,
    module_name: str,
    in_class: Type[Any],
    locals_: Optional[Mapping[str, Any]] = None,
) -> Any:
    """Evaluates the given Python expression.

    Args:
        expression: The Python expression to evaluate.
        module_name: The name of the module in which the expression is defined.
        locals_: The local variables to evaluate the expression with.
        in_class: The class in which the expression is defined.

    Returns:
        Any: The result of the evaluated expression.

    Raises:
        NameError: the given module cannot be found in ``sys.modules``
    """
    base_globals: Dict[str, Any] = sys.modules[module_name].__dict__
    cls_namespace = dict(in_class.__dict__)
    cls_namespace.setdefault(in_class.__name__, in_class)
    cls_namespace.update(base_globals)
    return eval(expression, cls_namespace, locals_)


def eval_name_only(
    name: str,
    module_name: str,
) -> Any:
    """Evaluates the given Python variable and returns the result.

    Args:
        name: The name of the variable.
        module_name: The name of the module in which the variable is defined.

    Returns:
        Any: The result of the evaluated variable.

    Raises:
        NameError: the given module cannot be found in ``sys.modules`` or in the
            global variables.
    """
    base_globals: Dict[str, Any] = sys.modules[module_name].__dict__

    # name only, just look in globals.  eval() works perfectly fine here,
    # however we are seeking to have this be faster, as this occurs for
    # every Mapper[] keyword, etc. depending on configuration
    try:
        return base_globals[name]
    except KeyError:
        # check in builtins as well to handle `list`, `set` or `dict`, etc.
        return builtins.__dict__[name]


def _cleanup_mapped_str_annotation(
    annotation: str, originating_module: str
) -> Tuple[Any, str]:
    """Cleans the given annotation string to only keep the internal as strings.

    Args:
        annotation: The annotation string to clean.
        originating_module: The module where the annotation string is located.

    Returns:
        tuple[Any, str]: the top element of the annotation, the cleaned annotation.
    """
    # fix up an annotation that comes in as the form:
    # 'Container[List[Address]]'  so that it instead looks like:
    # 'Container[List["Address"]]' , which will allow us to get
    # "Address" as a string

    inner: Optional[Match[str]]
    annotation = annotation.strip("\"'")

    mm = re.match(r"^(.+?)\[(.+)]$", annotation)

    if not mm:
        return None, annotation

    # ticket #8759.  Resolve the Mapped name to a real symbol.
    # originally this just checked the name.
    obj = eval_name_only(mm.group(1), originating_module)

    if obj is ClassVar:
        real_symbol = "ClassVar"
    else:
        real_symbol = obj.__name__

    # note: if one of the code paths above didn't define real_symbol and
    # then didn't return, real_symbol raises UnboundLocalError
    # which is actually a NameError, and the calling routines don't
    # notice this since they are catching NameError anyway.   Just in case
    # this is being modified in the future, something to be aware of.

    stack = []
    inner = mm
    while True:
        stack.append(real_symbol if mm is inner else inner.group(1))
        g2 = inner.group(2)
        inner = re.match(r"^(.+?)\[(.+)]$", g2)
        if inner is None:
            stack.append(g2)
            break

    # stacks we want to rewrite, that is, quote the last entry which
    # we think is a relationship class name:
    #
    #   ['Mapped', 'List', 'Address']
    #   ['Mapped', 'A']
    #
    # stacks we don't want to rewrite, which are generally MappedColumn
    # use cases:
    #
    # ['Mapped', "'Optional[Dict[str, str]]'"]
    # ['Mapped', 'dict[str, str] | None']

    if (
        # avoid already quoted symbols such as
        # ['Mapped', "'Optional[Dict[str, str]]'"]
        not re.match(r"""^["'].*["']$""", stack[-1])
        # avoid further generics like Dict[] such as
        # ['Mapped', 'dict[str, str] | None']
        and not re.match(r".*\[.*]", stack[-1])
    ):
        strip_chars = "\"' "
        stack[-1] = ", ".join(
            f'"{elem.strip(strip_chars)}"' for elem in stack[-1].split(",")
        )

        annotation = "[".join(stack) + ("]" * (len(stack) - 1))

    return obj, annotation


def de_stringify_annotation(
    cls: Type[Any],
    annotation: AnnotationScanType,
    originating_module: str,
    locals_: Mapping[str, Any],
) -> Tuple[Optional[Type[Any]], AnnotationScanType]:
    """Resolve annotations that may be string based into real objects.

    This is particularly important if a module defines "from __future__ import
    annotations", as everything inside __annotations__ is a string. We want
    to at least have generic containers like ``Mapped``, ``Union``, ``List``,
    etc.

    Args:
        cls: The class in which the annotation is defined.
        annotation: The annotation string to resolve.
        originating_module: The module where the annotation string is located.
        locals_: The local variables to use for evaluating the annotation.

    Returns:
        tuple[Optional[Type[Any]], AnnotationScanType]: The top element of the
            annotation, the cleaned annotation.
    """
    obj = None
    if isinstance(annotation, str):
        obj, annotation = _cleanup_mapped_str_annotation(annotation, originating_module)
        try:
            annotation = eval_expression(
                annotation, originating_module, cls, locals_=locals_
            )
        except NameError:
            return None, annotation
    if not obj:
        obj = annotation
    return obj, annotation  # type: ignore


def make_union_type(*types: AnnotationScanType) -> Type[Any]:
    """Make a Union type.

    This is needed by :func:`.de_optionalize_union_types` which removes
    ``NoneType`` from a ``Union``.

    Args:
        types: The types to make a Union type.

    Returns:
        Type[Any]: The union type.
    """
    return cast(Any, Union).__getitem__(types)  # type: ignore


def is_origin_of(
    type_: Any, *types: _SpecialForm, module: Optional[str] = None
) -> bool:
    """Return True if the given type has an __origin__ with the given names.

    Args:
        type_: The type to check.
        types: The types to check.
        module: The module where the type is located.

    Returns:
        bool: True if the type has an __origin__ with the given names.
    """
    origin = get_origin(type_)
    if origin is None:
        return False

    return origin in types and (module is None or origin.__module__.startswith(module))


def is_optional(type_: Any) -> TypeGuard[ArgsTypeProtocol]:
    """Return True if the given type is an optional.

    Args:
        type_: The type to check.

    Returns:
        bool: True if the type is an optional.
    """
    return is_origin_of(
        type_,
        Optional,
        Union,
    )


def is_union(type_: Any) -> TypeGuard[ArgsTypeProtocol]:
    """Return True if the given type is union.

    Args:
        type_: The type to check.

    Returns:
        bool: True if the type is union.
    """
    return is_origin_of(type_, Union)


def expand_unions(type_: str) -> Tuple[str, ...]:
    """Returns a type as a tuple of individual types, expanding for ``Union`` types.

    Args:
        type_: The type to expand.

    Returns:
        tuple[str, ...]: The types expanded.
    """
    ret = tuple([type_])
    if is_fwd_ref(type_):
        return expand_unions(type_.__forward_arg__)
    if isinstance(type_, str):
        return tuple(re.split(r"\s*\|\s*", type_))
    if is_union(type_):
        typ = set(type_.__args__)
        ret = tuple(typ)
    return tuple(typ.__forward_arg__ if is_fwd_ref(typ) else typ for typ in ret)


def de_optionalize_union_types(
    type_: AnnotationScanType,
) -> AnnotationScanType:
    """Returns the annotation striping any optionals.

    Args:
        type_: The type to de-optionalize.

    Returns:
        AnnotationScanType: The annotation without any optionals.
    """
    if is_optional(type_):
        typ = set(type_.__args__)
        typ.discard(NoneFwd)
        typ.discard(type(None))

        return make_union_type(*typ)
    return type_
