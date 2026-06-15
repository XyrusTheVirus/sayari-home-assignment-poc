"""S3-compatible object-store adapter backed by MinIO locally."""

from typing import Any, cast
from urllib.parse import urlparse

import aioboto3
from botocore.exceptions import BotoCoreError, ClientError

from document_pipeline.config import Settings
from document_pipeline.errors import ObjectStoreUnavailableError


class MinioObjectStore:
    """Async object-store adapter using aioboto3 against MinIO/S3."""

    def __init__(self, settings: Settings) -> None:
        """Create an adapter configured from typed settings."""

        self._settings = settings
        self._session = aioboto3.Session()

    async def put_text(self, key: str, text: str, content_type: str = "text/plain") -> str:
        """Write UTF-8 text to S3 and return an `s3://bucket/key` URI."""

        try:
            async with self._client() as client:
                await client.put_object(
                    Bucket=self._settings.s3_bucket,
                    Key=key,
                    Body=text.encode("utf-8"),
                    ContentType=content_type,
                )
        except (BotoCoreError, ClientError) as exc:
            raise ObjectStoreUnavailableError("failed to write object") from exc
        return f"s3://{self._settings.s3_bucket}/{key}"

    async def get_text(self, uri: str) -> str:
        """Read UTF-8 text from S3 by immutable URI."""

        bucket, key = self._parse_uri(uri)
        try:
            async with self._client() as client:
                response = await client.get_object(Bucket=bucket, Key=key)
                async with response["Body"] as stream:
                    data = await stream.read()
        except (BotoCoreError, ClientError) as exc:
            raise ObjectStoreUnavailableError("failed to read object") from exc
        return cast(str, data.decode("utf-8"))

    async def exists(self, uri: str) -> bool:
        """Return true when the object exists and is accessible."""

        bucket, key = self._parse_uri(uri)
        try:
            async with self._client() as client:
                await client.head_object(Bucket=bucket, Key=key)
        except (BotoCoreError, ClientError):
            return False
        return True

    async def close(self) -> None:
        """No-op for aioboto3 session-backed clients."""

    def _client(self) -> Any:
        """Create a short-lived async S3 client."""

        return self._session.client(
            "s3",
            endpoint_url=self._settings.s3_endpoint_url,
            aws_access_key_id=self._settings.s3_access_key,
            aws_secret_access_key=self._settings.s3_secret_key,
            region_name=self._settings.s3_region,
        )

    def _parse_uri(self, uri: str) -> tuple[str, str]:
        """Parse an `s3://bucket/key` URI and reject unsupported public inputs."""

        parsed = urlparse(uri)
        if parsed.scheme != "s3" or not parsed.netloc or not parsed.path:
            raise ObjectStoreUnavailableError("invalid object URI")
        return parsed.netloc, parsed.path.lstrip("/")
