"""DuckLake connection setup for the PostgreSQL + RustFS lakehouse."""

from __future__ import annotations

import os
from urllib.parse import quote_plus

import duckdb

LAKE_ALIAS = "lake"


def _required(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def configure_extensions(con: duckdb.DuckDBPyConnection) -> None:
    con.execute("INSTALL ducklake")
    con.execute("INSTALL postgres")
    con.execute("INSTALL httpfs")
    con.execute("LOAD ducklake")
    con.execute("LOAD postgres")
    con.execute("LOAD httpfs")


def configure_s3_secret(con: duckdb.DuckDBPyConnection) -> None:
    access_key = _required("S3_ACCESS_KEY").replace("'", "''")
    secret_key = _required("S3_SECRET_KEY").replace("'", "''")
    raw_endpoint = _required("S3_ENDPOINT_URL").replace("'", "''")
    # Strip protocol prefixes specifically for DuckDB's ENDPOINT block
    endpoint = raw_endpoint.replace("http://", "").replace("https://", "")
    region = os.getenv("S3_REGION", "us-east-1").replace("'", "''")
    bucket = os.getenv("S3_BUCKET", "feddatapipeline").replace("'", "''")

    con.execute(
        f"""
        CREATE OR REPLACE SECRET rustfs_storage (
            TYPE S3,
            PROVIDER config,
            KEY_ID '{access_key}',
            SECRET '{secret_key}',
            ENDPOINT '{endpoint}',
            REGION '{region}',
            USE_SSL FALSE,
            URL_STYLE 'path',
            SCOPE 's3://{bucket}/'
        )
        """
    )

def attach_lake(con: duckdb.DuckDBPyConnection) -> None:
    """Attach the shared DuckLake catalog and make it the default database."""
    configure_extensions(con)
    configure_s3_secret(con)

    host = _required("PGHOST").replace("'", "''")
    port = _required("PGPORT").replace("'", "''")
    database = _required("PGDATABASE").replace("'", "''")
    user = _required("PGUSER").replace("'", "''")
    password = _required("PGPASSWORD").replace("'", "''")
    data_path = _required("DATA_PATH").replace("'", "''")

    # Attach DuckLake catalog
    postgres_params = (
        f"dbname={database} host={host} port={port} "
        f"user={user} password={quote_plus(password)}"
    )
    con.execute(
        f"ATTACH 'ducklake:postgres:{postgres_params}' AS {LAKE_ALIAS} "
        f"(DATA_PATH '{data_path}', DATA_INLINING_ROW_LIMIT 0, OVERRIDE_DATA_PATH TRUE)"
    )
    con.execute(f"USE {LAKE_ALIAS}")
