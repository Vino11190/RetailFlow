
"""
RetailFlow Phase 8.3:
Silver Data Cleaning Audit.
"""

from src.config.transformation_config import list_transformations

from src.transformations.silver.bronze_reader import (
    read_bronze_dataset,
)

from src.transformations.silver.cleaner import (
    clean_bronze_dataframe,
)


def main():
    print("RetailFlow Phase 8.3 Cleaning Audit")
    print("=" * 48)

    total_input = 0
    total_clean = 0
    total_quarantine = 0

    for definition in list_transformations():

        extracted = read_bronze_dataset(
            definition.source_system,
            definition.dataset_name,
        )

        result = clean_bronze_dataframe(
            definition.source_system,
            definition.dataset_name,
            extracted["dataframe"],
        )

        metrics = result["metrics"]

        assert (
            metrics["clean_records"]
            + metrics["quarantined_records"]
            == metrics["input_records"]
        )

        assert not result["clean"].duplicated(
            subset=list(definition.primary_key)
        ).any(), (
            f"Duplicate business keys remain: "
            f"{definition.source_system}.{definition.dataset_name}"
        )

        total_input += metrics["input_records"]
        total_clean += metrics["clean_records"]
        total_quarantine += metrics["quarantined_records"]

        print(
            f"PASS | {definition.source_system}."
            f"{definition.dataset_name} "
            f"| input={metrics['input_records']:,} "
            f"| clean={metrics['clean_records']:,} "
            f"| quarantine={metrics['quarantined_records']:,}"
        )

    assert total_input == 205000

    assert (
        total_clean + total_quarantine
        == total_input
    )

    print()
    print(f"Input records: {total_input:,}")
    print(f"Clean records: {total_clean:,}")
    print(f"Quarantined records: {total_quarantine:,}")

    print()


if __name__ == "__main__":
    main()
