
from pathlib import Path

from src.ingestion.bronze_writer import write_to_bronze
from src.ingestion.file_extractor import extract_csv, extract_json
from src.ingestion.run_tracker import start_run, complete_run, fail_run


# ============================================================
# RetailFlow
# Suppliers CSV/JSON → Bronze with Run Tracking
# ============================================================

SOURCE_DIRECTORY = Path("sources/suppliers/outbound")

SOURCE_FILES = [
    ("suppliers", SOURCE_DIRECTORY / "suppliers.csv", extract_csv),
    ("deliveries", SOURCE_DIRECTORY / "deliveries.json", extract_json),
]


def main() -> None:
    run = start_run("suppliers")
    pipeline_run_id = run["pipeline_run_id"]
    total_records = 0

    print("RetailFlow Suppliers Ingestion")
    print("==============================")
    print(f"Pipeline run ID: {pipeline_run_id}")

    try:
        for dataset, file_path, extractor in SOURCE_FILES:
            print(f"Processing {file_path.name}...")

            dataframe = extractor(file_path)

            result = write_to_bronze(
                dataframe=dataframe,
                source_system="suppliers",
                source_dataset=dataset,
                source_file_name=file_path.name,
                pipeline_run_id=pipeline_run_id,
            )

            total_records += result["record_count"]

            print(
                f"Written: {result['record_count']:,} records"
            )

        complete_run(run, total_records)

        print()
        print("Suppliers ingestion complete.")
        print(f"Status: {run['status']}")
        print(f"Records: {total_records:,}")
        print(f"Duration: {run['duration_seconds']} seconds")

    except Exception as error:
        fail_run(run, error)
        print(f"Suppliers ingestion FAILED: {error}")
        raise


if __name__ == "__main__":
    main()
