
"""
RetailFlow Phase 8.2:
Bronze-to-Silver Extraction Audit.
"""

from src.config.transformation_config import (
    list_transformations,
)
from src.transformations.silver.bronze_reader import (
    read_bronze_dataset,
)


EXPECTED_RECORD_COUNTS = {
    ("ecommerce", "customers"): 5000,
    ("ecommerce", "orders"): 25000,
    ("ecommerce", "order_items"): 66442,

    ("products", "products"): 500,
    ("products", "categories"): 8,

    ("pos", "transactions"): 20000,

    ("inventory", "inventory"): 6000,
    ("inventory", "inventory_movements"): 50000,

    ("suppliers", "suppliers"): 50,
    ("suppliers", "deliveries"): 5000,

    ("payments", "payments"): 25000,
    ("returns", "returns"): 2000,
}


REQUIRED_LINEAGE_COLUMNS = {
    "_pipeline_run_id",
    "_batch_id",
    "_ingestion_timestamp",
    "_source_system",
    "_source_dataset",
}


def main():
    print("RetailFlow Phase 8.2 Bronze Reader Audit")
    print("=" * 50)

    total_records = 0

    for definition in list_transformations():

        key = (
            definition.source_system,
            definition.dataset_name,
        )

        extracted = read_bronze_dataset(*key)

        frame = extracted["dataframe"]

        expected_count = EXPECTED_RECORD_COUNTS[key]

        assert len(frame) == expected_count, (
            f"{key}: expected {expected_count}, "
            f"found {len(frame)}"
        )

        assert REQUIRED_LINEAGE_COLUMNS.issubset(
            frame.columns
        ), f"Missing lineage columns: {key}"

        assert (
            frame["_pipeline_run_id"]
            .astype(str)
            .nunique()
            == 1
        ), f"Multiple pipeline runs found: {key}"

        assert set(
            frame["_source_system"].astype(str)
        ) == {definition.source_system}, (
            f"Incorrect source lineage: {key}"
        )

        assert set(
            frame["_source_dataset"].astype(str)
        ) == {definition.dataset_name}, (
            f"Incorrect dataset lineage: {key}"
        )

        total_records += len(frame)

        print(
            f"PASS | {definition.source_system}."
            f"{definition.dataset_name} "
            f"| {len(frame):,} records "
            f"| {extracted['parquet_files_read']} files"
        )

    assert total_records == 205000, (
        f"Expected 205,000 records; "
        f"found {total_records:,}"
    )

    print()
    print("Datasets validated: 12")
    print(f"Total extracted records: {total_records:,}")
    print()
    print("PHASE 8.2 AUDIT RESULT: PASS")


if __name__ == "__main__":
    main()
