import os
from src.ingestion.api_extractor import (
    extract_json_endpoint,
    extract_paginated_products,
)

from src.ingestion.bronze_writer import (
    write_to_bronze,
)

from src.ingestion.run_tracker import (
    start_run,
    complete_run,
    fail_run,
)


# ============================================================
# RetailFlow
# Product REST API → Bronze
# With Ingestion Run Tracking
# ============================================================


PRODUCT_API_BASE_URL = os.getenv(
    "PRODUCT_API_BASE_URL",
    "http://127.0.0.1:8000",
)


def main() -> None:

    run = start_run("products")
    pipeline_run_id = run["pipeline_run_id"]

    print("RetailFlow Product API Ingestion")
    print("================================")
    print(f"Pipeline run ID: {pipeline_run_id}")
    print()

    total_records = 0

    try:
        # ----------------------------------------------------
        # Products: paginated endpoint
        # ----------------------------------------------------

        print("Extracting products...")

        products_dataframe = extract_paginated_products(
            base_url=PRODUCT_API_BASE_URL,
            page_size=100,
        )

        print(
            f"Extracted {len(products_dataframe):,} products."
        )

        result = write_to_bronze(
            dataframe=products_dataframe,
            source_system="products",
            source_dataset="products",
            pipeline_run_id=pipeline_run_id,
        )

        total_records += result["record_count"]

        print(f"Bronze write complete: {result['output_path']}")
        print()

        # ----------------------------------------------------
        # Categories: standard JSON endpoint
        # ----------------------------------------------------

        print("Extracting categories...")

        categories_dataframe = extract_json_endpoint(
            url=f"{PRODUCT_API_BASE_URL}/categories",
        )

        print(
            f"Extracted {len(categories_dataframe):,} categories."
        )

        result = write_to_bronze(
            dataframe=categories_dataframe,
            source_system="products",
            source_dataset="categories",
            pipeline_run_id=pipeline_run_id,
        )

        total_records += result["record_count"]

        print(f"Bronze write complete: {result['output_path']}")
        print()

        complete_run(
            record=run,
            record_count=total_records,
        )

        print("Product API ingestion complete.")
        print(f"Status: {run['status']}")
        print(f"Records: {total_records:,}")
        print(f"Duration: {run['duration_seconds']} seconds")

    except Exception as error:

        fail_run(
            record=run,
            error=error,
        )

        print()
        print("Product API ingestion FAILED.")
        print(f"Error: {error}")

        raise


if __name__ == "__main__":
    main()
