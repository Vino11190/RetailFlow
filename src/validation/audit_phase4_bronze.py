from pathlib import Path

import pandas as pd

from src.config.bronze_config import (
    BRONZE_DIRECTORY,
    BRONZE_METADATA_COLUMNS,
)


# ============================================================
# RetailFlow
# Phase 4 Bronze Layer Audit
# ============================================================


EXPECTED_DATASETS = {
    ("ecommerce", "customers"): 5_000,
    ("ecommerce", "orders"): 25_000,
    ("ecommerce", "order_items"): 66_442,
    ("products", "products"): 500,
    ("products", "categories"): 8,
    ("pos", "transactions"): 20_000,
    ("inventory", "inventory"): 6_000,
    ("inventory", "inventory_movements"): 50_000,
    ("suppliers", "suppliers"): 50,
    ("suppliers", "deliveries"): 5_000,
    ("payments", "payments"): 25_000,
    ("returns", "returns"): 2_000,
}


EXPECTED_SOURCE_FILES = {
    ("pos", "transactions"): {
        f"pos_transactions_2026-09-{day:02d}.csv"
        for day in range(1, 31)
    },
    ("suppliers", "suppliers"): {
        "suppliers.csv"
    },
    ("suppliers", "deliveries"): {
        "deliveries.json"
    },
    ("payments", "payments"): {
        "payments.json"
    },
    ("returns", "returns"): {
        "returns.csv"
    },
}


def get_parquet_files(
    source_system: str,
    source_dataset: str,
) -> list[Path]:

    dataset_directory = (
        BRONZE_DIRECTORY
        / source_system
        / source_dataset
    )

    if not dataset_directory.exists():
        return []

    return sorted(
        dataset_directory.rglob("*.parquet")
    )


def select_latest_pipeline_run(
    dataframe: pd.DataFrame,
) -> pd.DataFrame:

    if "_pipeline_run_id" not in dataframe.columns:
        return dataframe

    if "_ingestion_timestamp" not in dataframe.columns:
        return dataframe

    run_summary = (
        dataframe.groupby(
            "_pipeline_run_id",
            dropna=False,
        )["_ingestion_timestamp"]
        .max()
        .sort_values()
    )

    latest_pipeline_run_id = (
        run_summary.index[-1]
    )

    return dataframe[
        dataframe["_pipeline_run_id"]
        == latest_pipeline_run_id
    ].copy()


def load_dataset(
    source_system: str,
    source_dataset: str,
) -> tuple[pd.DataFrame, int]:

    parquet_files = get_parquet_files(
        source_system,
        source_dataset,
    )

    if not parquet_files:
        return pd.DataFrame(), 0

    frames = []

    for parquet_file in parquet_files:

        dataframe = pd.read_parquet(
            parquet_file
        )

        frames.append(
            dataframe
        )

    combined_dataframe = pd.concat(
        frames,
        ignore_index=True,
    )

    latest_dataframe = (
        select_latest_pipeline_run(
            combined_dataframe
        )
    )

    return (
        latest_dataframe,
        len(parquet_files),
    )


def validate_dataset(
    source_system: str,
    source_dataset: str,
    expected_records: int,
) -> list[str]:

    failures = []

    dataframe, parquet_file_count = (
        load_dataset(
            source_system,
            source_dataset,
        )
    )

    dataset_name = (
        f"{source_system}.{source_dataset}"
    )

    if parquet_file_count == 0:

        failures.append(
            f"{dataset_name}: "
            f"no Parquet files found."
        )

        return failures

    # --------------------------------------------------------
    # Record count
    # --------------------------------------------------------

    actual_records = len(
        dataframe
    )

    if actual_records != expected_records:

        failures.append(
            f"{dataset_name}: "
            f"expected {expected_records:,} "
            f"records but found "
            f"{actual_records:,}."
        )

    # --------------------------------------------------------
    # Required Bronze metadata
    # --------------------------------------------------------

    missing_metadata = [
        column
        for column in BRONZE_METADATA_COLUMNS
        if column not in dataframe.columns
    ]

    if missing_metadata:

        failures.append(
            f"{dataset_name}: "
            f"missing metadata columns "
            f"{missing_metadata}."
        )

        return failures

    # --------------------------------------------------------
    # Metadata source-system consistency
    # --------------------------------------------------------

    source_system_values = set(
        dataframe[
            "_source_system"
        ]
        .dropna()
        .astype(str)
        .unique()
    )

    if source_system_values != {
        source_system
    }:

        failures.append(
            f"{dataset_name}: "
            f"unexpected _source_system "
            f"values "
            f"{source_system_values}."
        )

    # --------------------------------------------------------
    # Metadata dataset consistency
    # --------------------------------------------------------

    source_dataset_values = set(
        dataframe[
            "_source_dataset"
        ]
        .dropna()
        .astype(str)
        .unique()
    )

    if source_dataset_values != {
        source_dataset
    }:

        failures.append(
            f"{dataset_name}: "
            f"unexpected _source_dataset "
            f"values "
            f"{source_dataset_values}."
        )

    # --------------------------------------------------------
    # Required technical metadata cannot be null
    # --------------------------------------------------------

    required_non_null_metadata = [
        "_ingestion_timestamp",
        "_source_system",
        "_source_dataset",
        "_batch_id",
        "_pipeline_run_id",
        "_source_record_number",
    ]

    for column in required_non_null_metadata:

        if dataframe[
            column
        ].isna().any():

            failures.append(
                f"{dataset_name}: "
                f"{column} contains "
                f"null values."
            )

    # --------------------------------------------------------
    # Record numbers must be positive
    # --------------------------------------------------------

    if (
        dataframe[
            "_source_record_number"
        ]
        <= 0
    ).any():

        failures.append(
            f"{dataset_name}: "
            "_source_record_number "
            "contains non-positive values."
        )

    # --------------------------------------------------------
    # Ingestion timestamps must be valid
    # --------------------------------------------------------

    ingestion_timestamps = pd.to_datetime(
        dataframe[
            "_ingestion_timestamp"
        ],
        errors="coerce",
        utc=True,
    )

    if ingestion_timestamps.isna().any():

        failures.append(
            f"{dataset_name}: "
            "invalid ingestion timestamps "
            "detected."
        )

    # --------------------------------------------------------
    # File lineage checks
    # --------------------------------------------------------

    dataset_key = (
        source_system,
        source_dataset,
    )

    if dataset_key in EXPECTED_SOURCE_FILES:

        expected_files = (
            EXPECTED_SOURCE_FILES[
                dataset_key
            ]
        )

        actual_files = set(
            dataframe[
                "_source_file_name"
            ]
            .dropna()
            .astype(str)
            .unique()
        )

        if actual_files != expected_files:

            missing_files = (
                expected_files
                - actual_files
            )

            unexpected_files = (
                actual_files
                - expected_files
            )

            if missing_files:

                failures.append(
                    f"{dataset_name}: "
                    f"missing source files "
                    f"{sorted(missing_files)}."
                )

            if unexpected_files:

                failures.append(
                    f"{dataset_name}: "
                    f"unexpected source files "
                    f"{sorted(unexpected_files)}."
                )

    return failures


def main() -> None:

    print(
        "RetailFlow Phase 4 Bronze Audit"
    )
    print(
        "==============================="
    )
    print()

    all_failures = []

    total_expected_records = 0
    total_audited_records = 0

    for (
        source_system,
        source_dataset,
    ), expected_records in (
        EXPECTED_DATASETS.items()
    ):

        dataset_name = (
            f"{source_system}."
            f"{source_dataset}"
        )

        print(
            f"Auditing {dataset_name}..."
        )

        dataframe, parquet_file_count = (
            load_dataset(
                source_system,
                source_dataset,
            )
        )

        actual_records = len(
            dataframe
        )

        total_expected_records += (
            expected_records
        )

        total_audited_records += (
            actual_records
        )

        failures = validate_dataset(
            source_system,
            source_dataset,
            expected_records,
        )

        if failures:

            print(
                f"  FAIL | "
                f"Files: {parquet_file_count} | "
                f"Records: {actual_records:,}"
            )

            for failure in failures:

                print(
                    f"       - {failure}"
                )

            all_failures.extend(
                failures
            )

        else:

            print(
                f"  PASS | "
                f"Files: {parquet_file_count} | "
                f"Records: {actual_records:,}"
            )

    print()
    print(
        "Phase 4 Audit Summary"
    )
    print(
        "---------------------"
    )

    print(
        f"Datasets expected: "
        f"{len(EXPECTED_DATASETS)}"
    )

    print(
        f"Datasets failed: "
        f"{len(set(all_failures))}"
    )

    print(
        f"Expected records: "
        f"{total_expected_records:,}"
    )

    print(
        f"Audited records: "
        f"{total_audited_records:,}"
    )

    print()

    if all_failures:

        print(
            "PHASE 4 AUDIT RESULT: FAIL"
        )

        raise SystemExit(1)

    print(
        "PHASE 4 AUDIT RESULT: PASS"
    )

    print(
        "RetailFlow Bronze layer is ready."
    )


if __name__ == "__main__":
    main()
