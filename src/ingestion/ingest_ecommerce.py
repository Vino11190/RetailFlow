
from src.ingestion.bronze_writer import (
    write_to_bronze,
)

from src.ingestion.postgres_extractor import (
    create_postgres_engine,
    extract_table,
)

from src.ingestion.run_tracker import (
    start_run,
    complete_run,
    fail_run,
)


# ============================================================
# RetailFlow
# E-commerce PostgreSQL → Bronze
# With Ingestion Run Tracking
# ============================================================


ECOMMERCE_DATABASE = "retailflow_ecommerce"

ECOMMERCE_TABLES = [
    "customers",
    "orders",
    "order_items",
]


def main() -> None:

    run = start_run("ecommerce")

    pipeline_run_id = run["pipeline_run_id"]

    print("RetailFlow E-commerce Ingestion")
    print("================================")
    print(f"Pipeline run ID: {pipeline_run_id}")
    print()

    total_records = 0
    engine = None

    try:
        engine = create_postgres_engine(
            ECOMMERCE_DATABASE
        )

        for table_name in ECOMMERCE_TABLES:

            print(f"Extracting {table_name}...")

            dataframe = extract_table(
                engine=engine,
                table_name=table_name,
            )

            print(
                f"Extracted {len(dataframe):,} records."
            )

            result = write_to_bronze(
                dataframe=dataframe,
                source_system="ecommerce",
                source_dataset=table_name,
                pipeline_run_id=pipeline_run_id,
            )

            total_records += result["record_count"]

            print(
                f"Bronze write complete: "
                f"{result['output_path']}"
            )
            print()

        complete_run(
            record=run,
            record_count=total_records,
        )

        print("E-commerce ingestion complete.")
        print(f"Status: {run['status']}")
        print(f"Records: {total_records:,}")
        print(
            f"Duration: "
            f"{run['duration_seconds']} seconds"
        )

    except Exception as error:

        fail_run(
            record=run,
            error=error,
        )

        print()
        print("E-commerce ingestion FAILED.")
        print(f"Error: {error}")

        raise

    finally:
        if engine is not None:
            engine.dispose()


if __name__ == "__main__":
    main()
