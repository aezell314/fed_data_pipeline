"""Run with: uv run python -m pipeline.flow"""

from prefect import flow, task
from prefect.logging import get_run_logger

from pipeline import steps

@task(retries=3, retry_delay_seconds=5)
def check_source() -> None:
  logger = get_run_logger()

  try:
    steps.check_source_freshness()
    logger.info("upstream source: reachable")
  except Exception as exc:
    logger.warning(
        f"Flake detected in check_source_freshness. Retrying... Error: {exc}"
    )
    raise

@task
def extract() -> dict[str, int]:
    logger = get_run_logger()
    counts = steps.extract_source_data()
    logger.info(f"Number of datasets ingested from FRED API: {counts}")
    return counts

@task
def load() -> dict[str, int]:
    logger = get_run_logger()
    counts = steps.load_raw()
    logger.info(f"raw DuckLake tables loaded: {counts}")
    return counts

@task
def transform() -> None:
    logger = get_run_logger()
    steps.dbt_build()
    logger.info("dbt build complete: models + tests passed")

@flow(log_prints=True)
def run_pipeline() -> None:
    logger = get_run_logger()
    check_source()
    extract()
    load()
    transform()
    logger.info("pipeline complete - curated tables are stored once in DuckLake")


if __name__ == "__main__":
    run_pipeline.serve(name="nightly-data-load", cron="0 6 * * *")
