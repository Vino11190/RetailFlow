import pandas as pd

from src.ingestion.bronze_writer import (
    write_to_bronze,
)


# ============================================================
# RetailFlow
# Manual Bronze Writer Test
# ============================================================


def main() -> None:

    test_dataframe = pd.DataFrame(
        [
            {
                "customer_id": "TEST001",
                "first_name": "Alice",
                "last_name": "Brown",
            },
            {
                "customer_id": "TEST002",
                "first_name": "James",
                "last_name": "Wilson",
            },
            {
                "customer_id": "TEST003",
                "first_name": "Sarah",
                "last_name": "Taylor",
            },
        ]
    )

    result = write_to_bronze(
        dataframe=test_dataframe,
        source_system="ecommerce",
        source_dataset="customers",
        pipeline_run_id="manual-test-run",
    )

    print(
        "RetailFlow Bronze Writer Test"
    )
    print(
        "============================="
    )

    print(
        f"Source: "
        f"{result['source_system']}"
    )

    print(
        f"Dataset: "
        f"{result['source_dataset']}"
    )

    print(
        f"Records: "
        f"{result['record_count']}"
    )

    print(
        f"Batch ID: "
        f"{result['batch_id']}"
    )

    print(
        f"Pipeline Run ID: "
        f"{result['pipeline_run_id']}"
    )

    print(
        f"Output: "
        f"{result['output_path']}"
    )


if __name__ == "__main__":
    main()