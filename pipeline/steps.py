"""Pipeline steps: live API -> DuckLake on PostgreSQL -> dbt -> Metabase."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from urllib.request import Request, urlopen

import duckdb

from pipeline.config import settings
from pipeline.extract_api import ingest
from pipeline.lake import attach_lake

REPO_ROOT = Path(__file__).resolve().parent.parent
SERIES_ID = 'PSAVERT' # just used as a freshness test

def check_source_freshness() -> None:
    """Make a real request to the upstream API before starting the pipeline."""

    if not settings.api_token:
        raise ValueError("FRED_API_KEY environment variable is not set.")

    # FRED API requires the key as a query parameter (and file_type=json if you want JSON)
    url = f"{settings.api_base_url}?series_id={SERIES_ID}&api_key={settings.api_token}&file_type=json"
    print(f"sending request to {url}")
    request = Request(url, headers={"User-Agent": "de_fed_project/1.0"})
    with urlopen(request, timeout=15) as response:
        if response.status != 200:
            raise ConnectionError(f"upstream API returned HTTP {response.status}")


def extract_source_data() -> dict[str, int]:
    """Fetch info from the live API and store in S3-compatible storage."""
    return ingest()

def load_raw() -> dict[str, int]:
    """Load landed API JSON from S3-compatible storage
         into raw DuckLake tables without business transforms."""
    con = duckdb.connect()
    series_ids = settings.series_ids
    non_empty_tables = 0
    try:
        attach_lake(con)
        con.execute("CREATE SCHEMA IF NOT EXISTS raw")
        # Load observation data (fact tables)
        for id in series_ids:
            con.execute(
                f"CREATE OR REPLACE TABLE raw.{id} AS SELECT * FROM read_json_auto('s3://{settings.bucket}/{id}.json')"
            )
            rowcount = con.execute(f"SELECT count(*) FROM raw.{id}").fetchone()[0]
            if rowcount > 0:
                non_empty_tables+=1
        # Load series metadata (dimension table)
        con.execute(
                f"CREATE OR REPLACE TABLE raw.series_metadata AS SELECT * FROM read_json_auto('s3://{settings.bucket}/series_metadata.json')"
            )
        rowcount = con.execute("SELECT count(*) FROM raw.series_metadata").fetchone()[0]
        if rowcount > 0:
            non_empty_tables+=1

        return non_empty_tables
    finally:
        con.close()


def dbt_build() -> None:
    """Run dbt models and tests against the shared DuckLake."""
    dbt = Path(sys.executable).parent / "dbt"
    result = subprocess.run([str(dbt), "build"], cwd=REPO_ROOT, check=False)
    if result.returncode != 0:
        raise RuntimeError("dbt build failed - see dbt output above")
