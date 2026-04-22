"""Response normalization for TAGO API.

TAGO services use inconsistent key casing across endpoints (소문자 vs 카멜케이스).
All responses must pass through ``normalize_keys`` before downstream parsing so
that field access is case-stable.
"""

from __future__ import annotations

from typing import Any


def normalize_keys(obj: Any) -> Any:
    """Recursively lowercase every dict key. Lists are traversed; scalars pass through.

    TAGO 응답은 서비스별로 키 케이스가 다르다 (nodeid vs gpsLati vs arrTime 등).
    수집 직후 한 번 통과시키면 이후 파싱은 소문자 키 기준으로 단일화된다.
    """
    if isinstance(obj, dict):
        return {str(k).lower(): normalize_keys(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [normalize_keys(x) for x in obj]
    return obj


def coerce_numeric(row: dict, fields: dict[str, type]) -> dict:
    """Cast specified fields to a numeric type in-place (on a copy).

    Parameters
    ----------
    row
        Single normalized record (dict with lowercase keys).
    fields
        Mapping ``{field_name: int|float}`` — target type per field.

    Returns
    -------
    dict
        Shallow copy of ``row`` with coerced fields. On failure, the field is
        set to ``None`` (lossy preservation — downstream treats NaN/None).
    """
    out = dict(row)
    for field, target_type in fields.items():
        value = out.get(field)
        if value is None or value == "":
            out[field] = None
            continue
        try:
            out[field] = target_type(value)
        except (TypeError, ValueError):
            out[field] = None
    return out


def extract_items(body: dict) -> list[dict]:
    """Pull the ``items.item`` list out of a normalized TAGO body.

    TAGO returns either:
        body.items.item = [ {...}, {...}, ... ]   # multiple rows
        body.items.item = { ... }                  # single row (dict, not list)
        body.items = ""                            # empty (literal empty string)

    This helper flattens all three into ``list[dict]``.
    """
    items = body.get("items")
    if not items or not isinstance(items, dict):
        return []
    item = items.get("item")
    if item is None:
        return []
    if isinstance(item, dict):
        return [item]
    if isinstance(item, list):
        return item
    return []
