"""Helpers to work with JSON payloads in views and wizards."""

from __future__ import annotations

import json
from typing import Any


def format_json_value(value: Any, *, indent: int = 2) -> str:
    """Return a human readable representation of ``value``.

    The helper is defensive and falls back to ``str`` when the value cannot be
    serialised by :mod:`json`. Empty mappings or sequences yield an empty
    string so that text areas stay uncluttered when no data is available.
    """

    if not value:
        return ""
    try:
        return json.dumps(value, indent=indent, sort_keys=True, ensure_ascii=False)
    except TypeError:
        return str(value)


def parse_json_text(text: str | None, *, empty_default: Any = None) -> Any:
    """Parse JSON ``text`` while accepting empty values.

    An empty string (or ``None``) returns ``empty_default`` which defaults to an
    empty dict. Any decoding error is propagated so that callers can decide how
    to surface the issue to the user.
    """

    if empty_default is None:
        empty_default = {}
    if not text or not text.strip():
        return empty_default
    return json.loads(text)
