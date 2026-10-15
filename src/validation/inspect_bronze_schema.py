
import json

import pyarrow.parquet as pq

from src.config.bronze_config import (
    BRONZE_DIRECTORY,
    BRONZE_METADATA_DIRECTORY,
)
from src.config.source_registry import SOURCE_REGISTRY


# ============================================================
# RetailFlow
# Phase 7.1: Inspect Source Data for Dimensional Modelling
# ============================================================

RUNS_DIRECTORY = BRONZE_METADATA_DIRECTORY / "runs"


def latest_successful_run(source_system):
    runs = []

    for path in RUNS_DIRECTORY.glob("*.json"):
        with path.open("r", encoding="utf-8") as file:
            run = json.load(file)

        if (
            run.get("source_system") == source_system
            and run.get("status") == "SUCCESS"
        ):
            runs.append(run)

    if not runs:
        raise RuntimeError(
            f"No successful run found for {source_system}"
        )

    return max(runs, key=lambda run: run["started_at"])


def inspect_dataset(source_system, dataset, run_id):
    dataset_path = (
        BRONZE_DIRECTORY / source_system / dataset
    )

    matched_files = []
    total_rows = 0
    schema = None

    for path in sorted(dataset_path.rglob("*.parquet")):
        parquet_file = pq.ParquetFile(path)
        arrow_schema = parquet_file.schema_arrow

        if "_pipeline_run_id" not in arrow_schema.names:
            continue

        # Inspect only the lineage column to avoid
        # loading every data column into memory.
        lineage = pq.read_table(
            path,
            columns=["_pipeline_run_id"],
        ).column("_pipeline_run_id")

        matches = lineage.to_pylist()

        matched_count = sum(
            value == run_id for value in matches
        )

        if matched_count == 0:
            continue

        matched_files.append(path)
        total_rows += matched_count

        if schema is None:
            schema = arrow_schema

    print()
    print(f"DATASET: {source_system}.{dataset}")
    print("-" * 60)
    print(f"Latest successful run ID: {run_id}")
    print(f"Records: {total_rows:,}")
    print(f"Parquet files: {len(matched_files)}")

    if schema is None:
        print("WARNING: No matching Bronze files found.")
        return

    print()
    print(f"{'COLUMN':<35} DATA TYPE")
    print("-" * 60)

    for field in schema:
        if field.name.startswith("_"):
            continue

        print(f"{field.name:<35} {field.type}")


def main():
    print("RetailFlow Bronze Schema Inspection")
    print("===================================")

    for source_system, definition in SOURCE_REGISTRY.items():
        run = latest_successful_run(source_system)

        for dataset in definition.datasets:
            inspect_dataset(
                source_system,
                dataset,
                run["pipeline_run_id"],
            )

    print()
    print("Source schema inspection complete.")


if __name__ == "__main__":
    main()
