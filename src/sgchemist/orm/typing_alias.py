"""Defines multiple typing alias used across sgchemist."""

from __future__ import absolute_import
from __future__ import annotations

from typing import Tuple
from typing import TypedDict

EntityHash = Tuple[str, int]


class SerializedEntity(TypedDict, total=False):
    """Defines a serialized entity dict."""

    id: int
    type: str
