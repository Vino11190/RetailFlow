from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

import pandas as pd

from src.config.bronze_config import (
    BATCH_ID_TIMESTAMP_FORMAT,
    BRONZE_COMPRESSION,
    BRONZE_DATASETS,
    BRONZE_DIRECTORY,
    BRONZE_FILE_FORMAT,
    BRONZE_METADATA_COLUMNS,
    PARQUET_FILE_PREFIX,
)


# ============================================================
# RetailFlow
# Reusable Bronze Layer Writer
# ============================================================


def validate_source_dataset(
    source_system: str,
    source_dataset: str,
) -> None:
    """Validate that a source/dataset is registered."""

    if source_system not in BRONZE_DATASETS:
        raise ValueError(
            f"Unknown source system: {source_system}"
        )

    if (
        source_dataset
        not in BRONZE_DATASETS[source_system]
    ):
        raise ValueError(
            f"Dataset '{source_dataset}' "
            f"is not registered for source "
            f"'{source_system}'."
        )


def validate_metadata_collision(
    dataframe: pd.DataFrame,
) -> None:
    """
    Prevent source data from overwriting
    RetailFlow-controlled metadata columns.
    """

    collisions = [
        column
        for column in BRONZE_METADATA_COLUMNS
        if column in dataframe.columns
    ]

    if collisions:
        raise ValueError(
            "Source data contains reserved "
            f"Bronze metadata columns: {collisions}"
        )


def create_batch_id(
    source_system: str,
    source_dataset: str,
    ingestion_timestamp: datetime,
) -> str:
    """Create a human-readable unique batch ID."""

    timestamp = ingestion_timestamp.strftime(
        BATCH_ID_TIMESTAMP_FORMAT
    )

    suffix = uuid4().hex[:8]

    return (
        f"{source_system}_"
        f"{source_dataset}_"
        f"{timestamp}_"
        f"{suffix}"
    )


def add_bronze_metadata(
    dataframe: pd.DataFrame,
    source_system: str,
    source_dataset: str,
    batch_id: str,
    pipeline_run_id: str,
    ingestion_timestamp: datetime,
    source_file_name: str | None,
) -> pd.DataFrame:
    """Add standard RetailFlow Bronze metadata."""

    bronze_dataframe = dataframe.copy()

    bronze_dataframe[
        "_ingestion_timestamp"
    ] = ingestion_timestamp

    bronze_dataframe[
        "_source_system"
    ] = source_system

    bronze_dataframe[
        "_source_dataset"
    ] = source_dataset

    bronze_dataframe[
        "_batch_id"
    ] = batch_id

    bronze_dataframe[
        "_pipeline_run_id"
    ] = pipeline_run_id

    bronze_dataframe[
        "_source_file_name"
    ] = source_file_name

    bronze_dataframe[
        "_source_record_number"
    ] = range(
        1,
        len(bronze_dataframe) + 1,
    )

    return bronze_dataframe


def build_output_path(
    source_system: str,
    source_dataset: str,
    ingestion_timestamp: datetime,
    batch_id: str,
) -> Path:
    """Build the partitioned Bronze output path."""

    ingestion_date = (
        ingestion_timestamp.date().isoformat()
    )

    output_directory = (
        BRONZE_DIRECTORY
        / source_system
        / source_dataset
        / f"ingestion_date={ingestion_date}"
    )

    output_directory.mkdir(
        parents=True,
        exist_ok=True,
    )

    filename = (
        f"{PARQUET_FILE_PREFIX}-"
        f"{batch_id}."
        f"{BRONZE_FILE_FORMAT}"
    )

    return output_directory / filename


def write_to_bronze(
    dataframe: pd.DataFrame,
    source_system: str,
    source_dataset: str,
    source_file_name: str | None = None,
    pipeline_run_id: str | None = None,
) -> dict:
    """
    Write a source batch to the RetailFlow Bronze layer.

    Returns technical information about the written batch.
    """

    if dataframe.empty:
        raise ValueError(
            "Cannot write an empty DataFrame "
            "to Bronze."
        )

    validate_source_dataset(
        source_system,
        source_dataset,
    )

    validate_metadata_collision(
        dataframe
    )

    ingestion_timestamp = (
        datetime.now(timezone.utc)
    )

    if pipeline_run_id is None:
        pipeline_run_id = str(
            uuid4()
        )

    batch_id = create_batch_id(
        source_system,
        source_dataset,
        ingestion_timestamp,
    )

    bronze_dataframe = add_bronze_metadata(
        dataframe=dataframe,
        source_system=source_system,
        source_dataset=source_dataset,
        batch_id=batch_id,
        pipeline_run_id=pipeline_run_id,
        ingestion_timestamp=ingestion_timestamp,
        source_file_name=source_file_name,
    )

    output_path = build_output_path(
        source_system,
        source_dataset,
        ingestion_timestamp,
        batch_id,
    )

    bronze_dataframe.to_parquet(
        output_path,
        engine="pyarrow",
        compression=BRONZE_COMPRESSION,
        index=False,
    )

    return {
        "source_system": source_system,
        "source_dataset": source_dataset,
        "batch_id": batch_id,
        "pipeline_run_id": pipeline_run_id,
        "record_count": len(
            bronze_dataframe
        ),
        "ingestion_timestamp": (
            ingestion_timestamp.isoformat()
        ),
        "output_path": str(
            output_path
        ),
    }