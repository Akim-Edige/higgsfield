"""Keyset pagination utilities."""
import base64
import json
from typing import Any


def encode_cursor(values: dict[str, Any]) -> str:
    """Encode cursor values to base64 string."""
    json_str = json.dumps(values, default=str)
    return base64.urlsafe_b64encode(json_str.encode()).decode()


def decode_cursor(cursor: str) -> dict[str, Any]:
    """Decode cursor from base64 string."""
    try:
        json_str = base64.urlsafe_b64decode(cursor.encode()).decode()
        return json.loads(json_str)
    except Exception:
        return {}

