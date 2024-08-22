"""Defines multiple typing alias used across sgchemist."""

from __future__ import annotations

from typing import Tuple

from typing_extensions import TypedDict

EntityHash = Tuple[str, int]


class SerializedEntity(TypedDict, total=False):
    """Defines a serialized entity dict."""

    id: int
    type: str
