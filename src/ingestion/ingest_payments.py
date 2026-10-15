
from pathlib import Path

from src.ingestion.bronze_writer import write_to_bronze
from src.ingestion.file_extractor import extract_json
from src.ingestion.run_tracker import start_run, complete_run, fail_run


# ============================================================
# RetailFlow
# Payments JSON → Bronze with Run Tracking
# ============================================================

PAYMENTS_SOURCE_FILE = Path(
    "sources/payments/outbound/payments.json"
)


def main() -> None:
    run = start_run("payments")
    pipeline_run_id = run["pipeline_run_id"]

    print("RetailFlow Payments Ingestion")
    print("=============================")
    print(f"Pipeline run ID: {pipeline_run_id}")

    try:
        dataframe = extract_json(
            PAYMENTS_SOURCE_FILE
        )

        result = write_to_bronze(
            dataframe=dataframe,
            source_system="payments",
            source_dataset="payments",
            source_file_name=PAYMENTS_SOURCE_FILE.name,
            pipeline_run_id=pipeline_run_id,
        )

        complete_run(
            run,
            result["record_count"],
        )

        print("Payments ingestion complete.")
        print(f"Status: {run['status']}")
        print(f"Records: {run['record_count']:,}")
        print(f"Duration: {run['duration_seconds']} seconds")

    except Exception as error:
        fail_run(run, error)
        print(f"Payments ingestion FAILED: {error}")
        raise


if __name__ == "__main__":
    main()
