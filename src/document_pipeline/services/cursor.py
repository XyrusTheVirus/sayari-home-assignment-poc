"""Opaque keyset cursor encoding for token pagination."""

import base64
import json
from uuid import UUID

from document_pipeline.repositories.interfaces import TokenCursor


def encode_cursor(cursor: TokenCursor | None) -> str | None:
    """Encode a token cursor as URL-safe opaque text."""

    if cursor is None:
        return None
    payload = {
        "page_number": cursor.page_number,
        "start_offset": cursor.start_offset,
        "token_id": str(cursor.token_id),
    }
    raw = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    return base64.urlsafe_b64encode(raw).decode("ascii")


def decode_cursor(value: str | None) -> TokenCursor | None:
    """Decode an opaque cursor, raising ValueError for malformed input."""

    if not value:
        return None
    payload = json.loads(base64.urlsafe_b64decode(value.encode("ascii")).decode("utf-8"))
    return TokenCursor(
        payload["page_number"], int(payload["start_offset"]), UUID(payload["token_id"])
    )
