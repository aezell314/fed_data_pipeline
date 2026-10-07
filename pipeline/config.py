"""Application configuration loaded from environment variables."""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import boto3
from botocore.client import BaseClient
from botocore.config import Config
from dotenv import load_dotenv

# Load variables from a .env file in the project root, if present. Real
# environment variables always win over .env values.
load_dotenv()


@dataclass(frozen=True)
class Settings:
    # The source API
    api_base_url: str
    api_timeout_seconds: float
    data_path: Path
    file_type: str
    api_token: str
    series_ids: list[str]
    # The S3 raw landing zone
    endpoint_url: str
    access_key: str
    secret_key: str
    region: str
    bucket: str
    # The final data lake
    pgdatabase: str
    pguser: str
    pgpassword: str
    pghost: str
    pgport: float

@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Reads settings from the environment once and caches them."""
    return Settings(
        api_base_url=os.getenv(
                "API_BASE_URL", "https://api.stlouisfed.org/fred/series"
            ).rstrip("/"),
        api_timeout_seconds=float(os.getenv("API_TIMEOUT_SECONDS", "10")),
        data_path=os.getenv("DATA_PATH", "s3://fed_data_pipeline"),
        file_type=os.getenv("FILE_TYPE", "json"),
        api_token=os.getenv("API_TOKEN", ""),
        endpoint_url=os.getenv("S3_ENDPOINT_URL", "http://localhost:9000"),
        series_ids=os.getenv("LIST_IDS", ['PCPI','UR','RGSP']),
        access_key=os.getenv("S3_ACCESS_KEY", "rustfsadmin"),
        secret_key=os.getenv("S3_SECRET_KEY", "rustfsadmin"),
        region=os.getenv("S3_REGION", "us-east-1"),
        bucket=os.getenv("S3_BUCKET", "feddatapipeline"),
        pgdatabase=os.getenv("PGDATABASE", "fedproject_ducklake_catalog"),
        pguser=os.getenv("PGUSER", "ducklake"),
        pgpassword=os.getenv("PGPASSWORD", "ducklake"),
        pghost=os.getenv("PGHOST", "localhost"),
        pgport=os.getenv("PGPORT", "5432"),
    )


def get_s3_client() -> BaseClient:
    """Returns a boto3 S3 client configured for the local RustFS endpoint."""
    s = get_settings()
    return boto3.client(
        "s3",
        endpoint_url=s.endpoint_url,
        aws_access_key_id=s.access_key,
        aws_secret_access_key=s.secret_key,
        region_name=s.region,
        config=Config(
            signature_version="s3v4",
            s3={"addressing_style": "path"},
            connect_timeout=5,
            read_timeout=10,
            retries={"max_attempts": 2, "mode": "standard"},
        ),
    )


# Convenience singleton so callers can simply `from ... import settings`.
settings = get_settings()

