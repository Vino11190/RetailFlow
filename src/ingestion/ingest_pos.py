
from pathlib import Path

from src.ingestion.bronze_writer import write_to_bronze
from src.ingestion.file_extractor import discover_files, extract_csv
from src.ingestion.run_tracker import start_run, complete_run, fail_run


# ============================================================
# RetailFlow
# POS CSV → Bronze with Run Tracking
# ============================================================

POS_SOURCE_DIRECTORY = Path("sources/pos/outbound")


def main() -> None:
    run = start_run("pos")
    pipeline_run_id = run["pipeline_run_id"]
    total_records = 0
    files_processed = 0

    print("RetailFlow POS Ingestion")
    print("========================")
    print(f"Pipeline run ID: {pipeline_run_id}")

    try:
        files = discover_files(
            POS_SOURCE_DIRECTORY,
            "csv",
        )

        if not files:
            raise FileNotFoundError(
                "No POS CSV files were found."
            )

        print(f"Files discovered: {len(files)}")

        for file_path in files:
            print(f"Processing {file_path.name}...")

            dataframe = extract_csv(file_path)

            result = write_to_bronze(
                dataframe=dataframe,
                source_system="pos",
                source_dataset="transactions",
                source_file_name=file_path.name,
                pipeline_run_id=pipeline_run_id,
            )

            total_records += result["record_count"]
            files_processed += 1

            print(
                f"Written: {result['record_count']:,} records"
            )

        complete_run(run, total_records)

        print()
        print("POS ingestion complete.")
        print(f"Status: {run['status']}")
        print(f"Files processed: {files_processed}")
        print(f"Records: {total_records:,}")
        print(f"Duration: {run['duration_seconds']} seconds")

    except Exception as error:
        fail_run(run, error)
        print(f"POS ingestion FAILED: {error}")
        raise


if __name__ == "__main__":
    main()
