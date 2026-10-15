
import json
from pathlib import Path

import pandas as pd

from src.config.bronze_config import (
    BRONZE_DATASETS,
    BRONZE_DIRECTORY,
    BRONZE_METADATA_DIRECTORY,
)
from src.config.source_registry import (
    SOURCE_REGISTRY,
    get_enabled_sources,
    get_source,
)
from src.ingestion.run_ingestion import (
    INGESTION_MODULES,
    run_source,
)


# ============================================================
# RetailFlow
# Phase 5 Ingestion Framework Audit
# ============================================================


EXPECTED_RECORD_COUNTS = {
    "ecommerce": 96_442,
    "products": 508,
    "pos": 20_000,
    "inventory": 56_000,
    "suppliers": 5_050,
    "payments": 25_000,
    "returns": 2_000,
}

RUNS_DIRECTORY = (
    BRONZE_METADATA_DIRECTORY / "runs"
)

failures = []


def check(condition: bool, description: str) -> None:
    if condition:
        print(f"PASS | {description}")
    else:
        print(f"FAIL | {description}")
        failures.append(description)


def load_runs() -> list[dict]:
    if not RUNS_DIRECTORY.exists():
        return []

    runs = []

    for path in RUNS_DIRECTORY.glob("*.json"):
        with path.open("r", encoding="utf-8") as file:
            runs.append(json.load(file))

    return runs


def latest_successful_run(
    runs: list[dict],
    source: str,
) -> dict | None:
    matches = [
        run
        for run in runs
        if (
            run.get("source_system") == source
            and run.get("status") == "SUCCESS"
        )
    ]

    if not matches:
        return None

    return max(
        matches,
        key=lambda run: run["started_at"],
    )


def count_bronze_records_for_run(
    source: str,
    pipeline_run_id: str,
) -> int:
    total = 0

    for dataset in BRONZE_DATASETS[source]:
        dataset_path = (
            BRONZE_DIRECTORY / source / dataset
        )

        if not dataset_path.exists():
            continue

        for parquet_path in dataset_path.rglob("*.parquet"):
            frame = pd.read_parquet(parquet_path)

            if "_pipeline_run_id" not in frame.columns:
                continue

            total += int(
                (
                    frame["_pipeline_run_id"]
                    == pipeline_run_id
                ).sum()
            )

    return total


def main() -> None:
    print("RetailFlow Phase 5 Framework Audit")
    print("==================================")
    print()

    # --------------------------------------------------------
    # Source registry
    # --------------------------------------------------------

    check(
        len(SOURCE_REGISTRY) == 7,
        "Seven source systems registered",
    )

    check(
        sum(
            len(source.datasets)
            for source in SOURCE_REGISTRY.values()
        ) == 12,
        "Twelve datasets registered",
    )

    check(
        len(get_enabled_sources()) == 7,
        "All seven sources enabled",
    )

    check(
        set(SOURCE_REGISTRY)
        == set(BRONZE_DATASETS),
        "Registry matches Bronze source systems",
    )

    for source, definition in SOURCE_REGISTRY.items():
        check(
            set(definition.datasets)
            == set(BRONZE_DATASETS[source]),
            f"{source}: datasets match Bronze configuration",
        )

    # --------------------------------------------------------
    # Ingestion module registration
    # --------------------------------------------------------

    check(
        set(INGESTION_MODULES)
        == set(SOURCE_REGISTRY),
        "All ingestion modules registered",
    )

    # --------------------------------------------------------
    # Source lookup
    # --------------------------------------------------------

    check(
        get_source("ecommerce").source_type == "postgres",
        "E-commerce source lookup works",
    )

    try:
        get_source("nonexistent_source")
    except ValueError:
        check(True, "Unknown source rejected by registry")
    else:
        check(False, "Unknown source rejected by registry")

    check(
        run_source("nonexistent_source") is False,
        "Unknown source rejected by runner",
    )

    # --------------------------------------------------------
    # Run tracking
    # --------------------------------------------------------

    runs = load_runs()

    check(
        bool(runs),
        "Execution metadata files exist",
    )

    check(
        any(run.get("status") == "SUCCESS" for run in runs),
        "Successful executions recorded",
    )

    check(
        any(run.get("status") == "FAILED" for run in runs),
        "Failed executions recorded",
    )

    # --------------------------------------------------------
    # Tracked Bronze record counts
    # --------------------------------------------------------

    for source, expected_count in EXPECTED_RECORD_COUNTS.items():
        run = latest_successful_run(runs, source)

        if run is None:
            check(
                False,
                f"{source}: successful tracked run exists",
            )
            continue

        check(
            run.get("record_count") == expected_count,
            f"{source}: tracked record count correct",
        )

        actual_bronze_count = count_bronze_records_for_run(
            source,
            run["pipeline_run_id"],
        )

        check(
            actual_bronze_count == expected_count,
            f"{source}: Bronze records match tracked run",
        )

    # --------------------------------------------------------
    # Final result
    # --------------------------------------------------------

    print()
    print("Phase 5 Audit Summary")
    print("---------------------")
    print(f"Checks failed: {len(failures)}")

    if failures:
        print()
        print("PHASE 5 AUDIT RESULT: FAIL")
        raise SystemExit(1)

    print()
    print("PHASE 5 AUDIT RESULT: PASS")
    print("RetailFlow ingestion framework validated.")


if __name__ == "__main__":
    main()
