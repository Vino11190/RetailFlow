
from pathlib import Path

from src.ingestion.bronze_writer import write_to_bronze
from src.ingestion.file_extractor import extract_csv
from src.ingestion.run_tracker import start_run, complete_run, fail_run


# ============================================================
# RetailFlow
# Returns CSV → Bronze with Run Tracking
# ============================================================

RETURNS_SOURCE_FILE = Path(
    "sources/returns/outbound/returns.csv"
)


def main() -> None:
    run = start_run("returns")
    pipeline_run_id = run["pipeline_run_id"]

    print("RetailFlow Returns Ingestion")
    print("============================")
    print(f"Pipeline run ID: {pipeline_run_id}")

    try:
        dataframe = extract_csv(
            RETURNS_SOURCE_FILE
        )

        result = write_to_bronze(
            dataframe=dataframe,
            source_system="returns",
            source_dataset="returns",
            source_file_name=RETURNS_SOURCE_FILE.name,
            pipeline_run_id=pipeline_run_id,
        )

        complete_run(
            run,
            result["record_count"],
        )

        print("Returns ingestion complete.")
        print(f"Status: {run['status']}")
        print(f"Records: {run['record_count']:,}")
        print(f"Duration: {run['duration_seconds']} seconds")

    except Exception as error:
        fail_run(run, error)
        print(f"Returns ingestion FAILED: {error}")
        raise


if __name__ == "__main__":
    main()
