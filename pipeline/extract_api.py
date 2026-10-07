"""Extract US consumer financial health data from the Federal Reserve API."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime

import httpx
import polars as pl
from botocore.exceptions import ClientError
from loglyte import logger
from tenacity import (
    RetryCallState,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from pipeline.config import get_s3_client, settings

DEFAULT_TIMEOUT = httpx.Timeout(10.0)
MAX_ATTEMPTS = 6
STATES = ["AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "FL", "GA",
          "HI", "ID", "IL", "IN", "IA", "KS", "KY", "LA", "ME", "MD",
          "MA", "MI", "MN", "MS", "MO", "MT", "NE", "NV", "NH", "NJ",
          "NM", "NY", "NC", "ND", "OH", "OK", "OR", "PA", "RI", "SC",
          "SD", "TN", "TX", "UT", "VT", "VA", "WA", "WV", "WI", "WY", "DC"]


def log_retry(state: RetryCallState) -> None:
    logger.warning(
        "API request failed; retrying",
        attempt=state.attempt_number,
        error=str(state.outcome.exception()) if state.outcome else "unknown",
    )

class RateLimitError(Exception):
    """Raised when the API answers 429 (Too Many Requests).

    It carries the server's ``Retry-After`` value (seconds) when one was sent, so
    the retry logic can wait exactly as long as the server asked instead of
    guessing.
    """

    def __init__(self, retry_after: float | None = None) -> None:
        self.retry_after = retry_after
        super().__init__(f"rate limited (retry_after={retry_after})")

def build_client(
    *,
    base_url: str | None = settings.api_base_url,
    token: str | None = settings.api_token,
    transport: httpx.BaseTransport | None = None,
) -> httpx.Client:
    """Returns an ``httpx.Client`` pointed at the API.
    """
    client = httpx.Client()
    headers = {"User-Agent": "de_fed_project/1.0", "Accept": "application/json"}
    if token:
      headers["authorization"] = f"Bearer {token}"
    client = httpx.Client(headers=headers, timeout=DEFAULT_TIMEOUT, transport=transport)
    return client

def custom_wait_strategy(retry_state):
    """
    Honors the Retry-After header if present in RateLimitError;
    otherwise, falls back to exponential backoff.
    """
    # Check if the last failed attempt threw a RateLimitError
    if retry_state.outcome.failed:
        exception = retry_state.outcome.exception()
        if isinstance(exception, RateLimitError) and exception.retry_after:
            try:
                # Handle numeric seconds (e.g., "5" or "0")
                return float(exception.retry_after)
            except ValueError:
                # Handle HTTP-date headers (e.g., "Wed, 21 Oct 2015 07:28:00 GMT")
                try:
                    target_time = parsedate_to_datetime(exception.retry_after)
                    delay = (target_time - target_time.now(target_time.tzinfo)).total_seconds()
                    return max(0.0, delay)
                except Exception:
                    # Malformed header fallback
                    pass

    # Fallback to standard exponential backoff: 1s, 2s, 4s, ... capped at 30s
    fallback = wait_exponential(multiplier=1, min=1, max=30)
    return fallback(retry_state=retry_state)

@retry(
    retry=retry_if_exception_type((RateLimitError, httpx.TransportError)),
    stop=stop_after_attempt(MAX_ATTEMPTS),
    wait=custom_wait_strategy,
    before_sleep=log_retry,
    reraise=True
)
def fetch_single_series(session: httpx.Client, state_series_id: str, state_code: str, type: str) -> list[dict]:
    """Executes a single HTTP call with targeted retry backing."""

    # 1. Map paths relative to: https://api.stlouisfed.org/fred/series
    if type == 'observation':
        endpoint = "/observations"  # Resolves to: .../fred/series/observations
        json_key = "observations"
    elif type == 'series':
        endpoint = "."               # Resolves to: .../fred/series (Root metadata endpoint)
        json_key = "seriess"        # FRED metadata payload array wrapper key
    else:
        logger.error("Invalid type parameter provided", type=type)
        raise ValueError(f"Invalid type parameter: {type}")

    try:
        # 2. Execute request with the correctly resolved path
        response = session.get(
            endpoint,
            params={
                "series_id": state_series_id,
                "api_key": settings.api_token,
                "file_type": settings.file_type
            }
        )

        # Explicitly check for 429 status codes before raise_for_status()
        if response.status_code == 429:
            retry_after = response.headers.get("Retry-After")
            raise RateLimitError(retry_after=retry_after)

        response.raise_for_status()

        # 3. Dynamic lookup depending on the data type returned
        payload = response.json().get(json_key, [])

        # Ensure metadata dictionary is wrapped in a list if it comes back as a single object
        if isinstance(payload, dict):
            payload = [payload]

        # Append state field and series_id field to each JSON row
        for item in payload:
            item["state"] = state_code
            item["series_id"] = state_series_id

        return payload

    except httpx.HTTPStatusError as e:
        if e.response.status_code == 429:
            raise RateLimitError(retry_after=e.response.headers.get("Retry-After")) from None
        logger.error(
            "HTTP client error occurred", status_code=e.response.status_code, series=state_series_id
        )
        raise e

def fetch_data(*, client: httpx.Client | None = None) -> dict[str, list[dict]]:
    series_ids = settings.series_ids
    if not series_ids:
        logger.warning("No series IDs found in environment variables.")
        return {}

    payloads = {}

    # Establish a reliable HTTP session context
    session = client or httpx.Client(
        base_url=settings.api_base_url,
        timeout=httpx.Timeout(settings.api_timeout_seconds),
    )
    try:
        full_seriesinfo = []
        for series_id in series_ids:
            full_observations = []
            logger.info("Starting extraction loop", series_id=series_id)

            for state in STATES:
                state_series_id = f"{state}{series_id}"
                # Get observations for the given state series
                try:
                    state_data = fetch_single_series(
                        session, state_series_id, state, type='observation'
                        )
                    full_observations.extend(state_data)
                except Exception as e:
                    # Log failure but allow pipeline to check other states/series
                    logger.critical("Skipping series after maximum retries exhausted", series=state_series_id, error=str(e))
                    continue
                # Get metadata about the given state series
                try:
                    state_series_data = fetch_single_series(
                        session, state_series_id, state, type='series'
                        )
                    full_seriesinfo.extend(state_series_data)
                except Exception as e:
                    # Log failure but allow pipeline to check other states/series
                    logger.critical("Skipping series after maximum retries exhausted", series=state_series_id, error=str(e))
                    continue

            payloads[series_id] = full_observations
            payloads["series_metadata"] = full_seriesinfo
            logger.info("API extraction complete for series",
                        series_id=series_id,
                        records=len(full_observations))
    finally:
        if client is None:
            session.close()

    return payloads

def land_to_s3(records: list[dict],
                *,
                s3_client=None,
                key: str | None
                ) -> int:
    """Uploads payloads to S3 as individual JSON arrays, untransformed; returns the count.
    """
    if s3_client is None:
        s3_client = get_s3_client()

    bucket = settings.bucket

    try:
        s3_client.head_bucket(Bucket=bucket)
    except ClientError:
        s3_client.create_bucket(Bucket=bucket)
        print(f"created bucket '{bucket}'")

    json_string = json.dumps(records).encode('utf-8')
    s3_client.put_object(
      Bucket=bucket,
      Key=key,
      Body=json_string
    )
    return len(records)

def ingest(*, client: httpx.Client | None = None, s3_client=None) -> int:
    """Fetches all info from the source API and lands it raw in S3.
    """

    fulldata = fetch_data(client=client)
    # Land all data in S3
    for key, value in fulldata.items():
        land_to_s3(value, s3_client=s3_client, key=f"{key}.json")
    logger.info("All series data landed raw in S3.")
    return len(fulldata.items())

