
"""
RetailFlow Bronze-to-Silver Reader.

Reads the latest successful full-snapshot ingestion
for a registered source dataset.

Preserves Bronze metadata for lineage.
"""

import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import pyarrow.parquet as pq

from src.config.bronze_config import (
    BRONZE_DIRECTORY,
    BRONZE_METADATA_DIRECTORY,
)
from src.config.transformation_config import (
    get_transformation,
)


RUNS_DIRECTORY = BRONZE_METADATA_DIRECTORY / "runs"


def _parse_timestamp(value):
    """Convert run-tracking timestamps to UTC."""

    if not value:
        raise ValueError("Missing run start timestamp")

    if isinstance(value, datetime):
        parsed = value
    else:
        parsed = datetime.fromisoformat(
            str(value).replace("Z", "+00:00")
        )

    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)

    return parsed.astimezone(timezone.utc)


def get_latest_successful_run(source_system):
    """
    Find the latest successful ingestion run
    for a source system.
    """

    if not RUNS_DIRECTORY.exists():
        raise FileNotFoundError(
            f"Run metadata directory missing: {RUNS_DIRECTORY}"
        )

    successful_runs = []

    for metadata_file in RUNS_DIRECTORY.glob("*.json"):

        with metadata_file.open(
            "r",
            encoding="utf-8-sig",
        ) as file:
            run = json.load(file)

        if (
            run.get("source_system") == source_system
            and run.get("status") == "SUCCESS"
        ):
            successful_runs.append(run)

    if not successful_runs:
        raise RuntimeError(
            f"No successful ingestion run for {source_system}"
        )

    return max(
        successful_runs,
        key=lambda run: _parse_timestamp(
            run["started_at"]
        ),
    )


def read_bronze_dataset(
    source_system,
    dataset_name,
):
    """
    Return the latest successful Bronze snapshot.

    Only records whose _pipeline_run_id matches
    the selected successful ingestion run are returned.
    """

    # Ensure the dataset is registered.
    definition = get_transformation(
        source_system,
        dataset_name,
    )

    latest_run = get_latest_successful_run(
        source_system
    )

    run_id = str(latest_run["pipeline_run_id"])

    dataset_directory = (
        Path(BRONZE_DIRECTORY)
        / definition.source_system
        / definition.dataset_name
    )

    if not dataset_directory.exists():
        raise FileNotFoundError(
            f"Bronze dataset missing: {dataset_directory}"
        )

    parquet_files = sorted(
        dataset_directory.rglob("*.parquet")
    )

    if not parquet_files:
        raise FileNotFoundError(
            f"No Parquet files found: {dataset_directory}"
        )

    matching_frames = []
    matching_files = 0

    for parquet_path in parquet_files:

        parquet_file = pq.ParquetFile(
            parquet_path
        )

        if (
            "_pipeline_run_id"
            not in parquet_file.schema_arrow.names
        ):
            raise ValueError(
                "Missing _pipeline_run_id in "
                f"{parquet_path}"
            )

        frame = pd.read_parquet(parquet_path)

        matching_rows = frame[
            frame["_pipeline_run_id"].astype(str)
            == run_id
        ].copy()

        if matching_rows.empty:
            continue

        matching_frames.append(matching_rows)
        matching_files += 1

    if not matching_frames:
        raise RuntimeError(
            "No Bronze records matched the latest "
            f"successful run {run_id} for "
            f"{source_system}.{dataset_name}"
        )

    result = pd.concat(
        matching_frames,
        ignore_index=True,
    )

    # Guard against accidentally mixing runs.
    observed_run_ids = set(
        result["_pipeline_run_id"].astype(str)
    )

    if observed_run_ids != {run_id}:
        raise RuntimeError(
            "Bronze lineage validation failed"
        )

    return {
        "source_system": source_system,
        "dataset_name": dataset_name,
        "pipeline_run_id": run_id,
        "record_count": len(result),
        "parquet_files_read": matching_files,
        "dataframe": result,
    }
