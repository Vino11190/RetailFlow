
"""
RetailFlow Phase 8.1:
Transformation Framework Configuration Audit.
"""

from src.config.source_registry import SOURCE_REGISTRY

from src.config.transformation_config import (
    PRIMARY_KEYS,
    TRANSFORMATION_REGISTRY,
    get_transformation,
    list_transformations,
)


def main():
    print("RetailFlow Transformation Configuration Audit")
    print("=" * 48)

    expected = {
        (source, dataset)
        for source, definition in SOURCE_REGISTRY.items()
        for dataset in definition.datasets
    }

    actual = set(TRANSFORMATION_REGISTRY)

    assert actual == expected, (
        f"Registry mismatch: {actual ^ expected}"
    )

    assert len(actual) == 12, (
        f"Expected 12 datasets, found {len(actual)}"
    )

    assert set(PRIMARY_KEYS) == expected, (
        "Primary-key configuration does not match sources"
    )

    table_names = set()

    for definition in list_transformations():

        assert definition.silver_schema == "silver"
        assert definition.load_strategy == "FULL"

        assert definition.primary_key, (
            f"Missing primary key: {definition}"
        )

        assert len(set(definition.primary_key)) == len(
            definition.primary_key
        ), f"Duplicate primary-key column: {definition}"

        assert definition.bronze_dataset == (
            f"{definition.source_system}/"
            f"{definition.dataset_name}"
        )

        assert definition.silver_table not in table_names, (
            f"Duplicate Silver table: {definition.silver_table}"
        )

        table_names.add(definition.silver_table)

        resolved = get_transformation(
            definition.source_system,
            definition.dataset_name,
        )

        assert resolved == definition

        print(
            "PASS | "
            f"{definition.bronze_dataset} "
            f"-> silver.{definition.silver_table} "
            f"| PK: {', '.join(definition.primary_key)}"
        )

    assert len(table_names) == 12

    print()
    print(f"Source systems: {len(SOURCE_REGISTRY)}")
    print(f"Registered datasets: {len(actual)}")
    print(f"Unique Silver tables: {len(table_names)}")
    print()
    print("PHASE 8.1 AUDIT RESULT: PASS")


if __name__ == "__main__":
    main()
