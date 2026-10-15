
from sqlalchemy import text

from src.config.source_registry import SOURCE_REGISTRY
from src.warehouse.connection import create_warehouse_engine


# ============================================================
# RetailFlow
# Register Source Datasets in Analytical Warehouse
# ============================================================


INSERT_DATASET_SQL = """
INSERT INTO metadata.dataset_registry (
    source_system,
    dataset_name,
    source_type,
    target_schema,
    target_table,
    is_enabled,
    load_strategy
)
VALUES (
    :source_system,
    :dataset_name,
    :source_type,
    :target_schema,
    :target_table,
    :is_enabled,
    :load_strategy
)
ON CONFLICT (source_system, dataset_name)
DO UPDATE SET
    source_type = EXCLUDED.source_type,
    target_schema = EXCLUDED.target_schema,
    target_table = EXCLUDED.target_table,
    is_enabled = EXCLUDED.is_enabled,
    load_strategy = EXCLUDED.load_strategy,
    updated_at = NOW()
"""


def main() -> None:
    engine = create_warehouse_engine()

    print("RetailFlow Warehouse Dataset Registration")
    print("=========================================")

    try:
        with engine.begin() as connection:
            for source_name, definition in SOURCE_REGISTRY.items():
                for dataset_name in definition.datasets:
                    connection.execute(
                        text(INSERT_DATASET_SQL),
                        {
                            "source_system": source_name,
                            "dataset_name": dataset_name,
                            "source_type": definition.source_type,
                            "target_schema": "staging",
                            "target_table": (
                                f"{source_name}_{dataset_name}"
                            ),
                            "is_enabled": definition.enabled,
                            "load_strategy": "FULL",
                        },
                    )

                    print(
                        f"Registered: {source_name}.{dataset_name}"
                    )

            count = connection.execute(
                text(
                    "SELECT COUNT(*) "
                    "FROM metadata.dataset_registry"
                )
            ).scalar_one()

        print()
        print(f"Registered datasets in warehouse: {count}")

        if count != 12:
            raise ValueError(
                f"Expected 12 datasets, found {count}"
            )

        print("Dataset registration complete.")

    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
