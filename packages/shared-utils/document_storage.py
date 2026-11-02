"""Shared encrypted-document access for local and S3-compatible storage."""

from __future__ import annotations

from dataclasses import dataclass, field
from urllib.parse import urlparse


@dataclass(frozen=True)
class S3DocumentStore:
    """Server-side S3 client for encrypted objects in a private bucket."""

    bucket: str
    endpoint: str
    access_key: str = field(repr=False)
    secret_key: str = field(repr=False)
    region: str = "ap-south-1"

    def __post_init__(self) -> None:
        parsed = urlparse(self.endpoint)
        if parsed.scheme != "https" or not parsed.netloc:
            raise ValueError("S3 storage requires a valid HTTPS endpoint")
        if not all((self.bucket, self.access_key, self.secret_key)):
            raise ValueError("S3 storage is not fully configured")

    def client(self):
        import boto3
        from botocore.config import Config

        return boto3.client(
            "s3",
            endpoint_url=self.endpoint.rstrip("/"),
            region_name=self.region,
            aws_access_key_id=self.access_key,
            aws_secret_access_key=self.secret_key,
            config=Config(s3={"addressing_style": "path"}, signature_version="s3v4"),
        )

    def key_for(self, storage_path: str) -> str:
        parsed = urlparse(storage_path)
        if parsed.scheme != "s3" or parsed.netloc != self.bucket:
            raise ValueError("Invalid document storage reference")
        key = parsed.path.lstrip("/")
        if not key or ".." in key.split("/"):
            raise ValueError("Invalid document storage reference")
        return key

    def read_encrypted(self, storage_path: str) -> bytes:
        try:
            response = self.client().get_object(
                Bucket=self.bucket, Key=self.key_for(storage_path)
            )
            return response["Body"].read()
        except ValueError:
            raise
        except Exception as exc:  # provider errors can include request details
            raise OSError("Document storage could not be read") from exc

    def exists(self, storage_path: str) -> bool:
        try:
            self.client().head_object(Bucket=self.bucket, Key=self.key_for(storage_path))
            return True
        except ValueError:
            return False
        except Exception as exc:
            if getattr(exc, "response", {}).get("ResponseMetadata", {}).get("HTTPStatusCode") == 404:
                return False
            raise OSError("Document storage could not be checked") from exc

    def write_encrypted(self, key: str, data: bytes) -> None:
        try:
            self.client().put_object(
                Bucket=self.bucket,
                Key=key,
                Body=data,
                ContentType="application/octet-stream",
            )
        except Exception as exc:
            raise OSError("Document storage could not be written") from exc

    def delete(self, storage_path: str) -> None:
        try:
            self.client().delete_object(
                Bucket=self.bucket, Key=self.key_for(storage_path)
            )
        except ValueError:
            raise
        except Exception as exc:
            raise OSError("Document storage could not be deleted") from exc
