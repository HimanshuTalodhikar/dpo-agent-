"""Amazon S3 client for document storage."""

from __future__ import annotations

from datetime import datetime
from pathlib import PurePosixPath
from typing import TYPE_CHECKING, Any

import boto3
import structlog

from ..config import S3Settings

if TYPE_CHECKING:
    from botocore.client import BaseClient

logger = structlog.get_logger(__name__)


class S3DocumentStore:
    """S3-backed document store for raw legal documents."""

    def __init__(
        self,
        bucket: str,
        region: str,
        *,
        aws_access_key_id: str | None = None,
        aws_secret_access_key: str | None = None,
        endpoint_url: str | None = None,
    ) -> None:
        self._bucket = bucket
        self._region = region
        self._client: BaseClient = boto3.client(
            "s3",
            region_name=region,
            aws_access_key_id=aws_access_key_id,
            aws_secret_access_key=aws_secret_access_key,
            endpoint_url=endpoint_url,
        )

    def _make_key(self, document_id: str, filename: str) -> str:
        """Build an S3 key for a document."""
        return str(PurePosixPath("legal-docs") / document_id / filename)

    async def upload_document(
        self,
        document_id: str,
        filename: str,
        content: bytes,
        content_type: str = "text/plain",
        metadata: dict[str, str] | None = None,
    ) -> str:
        """Upload a raw document to S3. Returns the S3 key."""
        key = self._make_key(document_id, filename)
        extra_args: dict[str, Any] = {
            "ContentType": content_type,
        }
        if metadata:
            extra_args["Metadata"] = metadata

        self._client.put_object(
            Bucket=self._bucket,
            Key=key,
            Body=content,
            **extra_args,
        )
        logger.info("s3.uploaded", bucket=self._bucket, key=key, size_bytes=len(content))
        return key

    async def download_document(self, key: str) -> bytes:
        """Download a document by S3 key."""
        response = self._client.get_object(Bucket=self._bucket, Key=key)
        return response["Body"].read()

    async def list_documents(self, document_id: str) -> list[str]:
        """List all S3 keys for a given document_id."""
        prefix = f"legal-docs/{document_id}/"
        response = self._client.list_objects_v2(Bucket=self._bucket, Prefix=prefix)
        return [obj["Key"] for obj in response.get("Contents", [])]

    async def delete_document(self, key: str) -> None:
        """Delete a document by S3 key."""
        self._client.delete_object(Bucket=self._bucket, Key=key)
        logger.info("s3.deleted", bucket=self._bucket, key=key)

    async def get_presigned_url(self, key: str, expires_seconds: int = 3600) -> str:
        """Generate a presigned URL for downloading a document."""
        return self._client.generate_presigned_url(
            "get_object",
            Params={"Bucket": self._bucket, "Key": key},
            ExpiresIn=expires_seconds,
        )
