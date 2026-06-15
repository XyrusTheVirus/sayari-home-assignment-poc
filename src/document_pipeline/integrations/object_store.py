"""Provider-neutral object-store interface."""

from typing import Protocol


class ObjectStore(Protocol):
    """Minimal async S3-compatible operations used by services and activities."""

    async def put_text(self, key: str, text: str, content_type: str = "text/plain") -> str:
        """Persist UTF-8 text and return an immutable object URI."""

    async def get_text(self, uri: str) -> str:
        """Load UTF-8 text from an object URI."""

    async def exists(self, uri: str) -> bool:
        """Return whether an object URI is readable."""

    async def close(self) -> None:
        """Release any provider resources."""
