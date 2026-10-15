
import json
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from src.config.bronze_config import (
    BRONZE_METADATA_DIRECTORY,
)


# ============================================================
# RetailFlow
# Ingestion Run Tracker
# ============================================================


RUNS_DIRECTORY = (
    BRONZE_METADATA_DIRECTORY / "runs"
)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def save_run(record: dict) -> Path:
    RUNS_DIRECTORY.mkdir(
        parents=True,
        exist_ok=True,
    )

    output_path = (
        RUNS_DIRECTORY
        / f"{record['pipeline_run_id']}.json"
    )

    # Write to a temporary file before replacing the
    # target, reducing the risk of partial JSON writes.
    temporary_path = output_path.with_suffix(".tmp")

    with temporary_path.open(
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            record,
            file,
            indent=4,
        )

    temporary_path.replace(output_path)

    return output_path


def start_run(source_system: str) -> dict:
    record = {
        "pipeline_run_id": str(uuid4()),
        "source_system": source_system,
        "status": "STARTED",
        "started_at": utc_now(),
        "finished_at": None,
        "duration_seconds": None,
        "record_count": 0,
        "error_message": None,
    }

    save_run(record)
    return record


def calculate_duration(record: dict) -> float:
    started_at = datetime.fromisoformat(
        record["started_at"]
    )

    finished_at = datetime.fromisoformat(
        record["finished_at"]
    )

    return round(
        (finished_at - started_at).total_seconds(),
        3,
    )


def complete_run(
    record: dict,
    record_count: int,
) -> dict:
    record["status"] = "SUCCESS"
    record["finished_at"] = utc_now()
    record["record_count"] = record_count
    record["duration_seconds"] = (
        calculate_duration(record)
    )
    record["error_message"] = None

    save_run(record)
    return record


def fail_run(
    record: dict,
    error: Exception,
) -> dict:
    record["status"] = "FAILED"
    record["finished_at"] = utc_now()
    record["duration_seconds"] = (
        calculate_duration(record)
    )
    record["error_message"] = str(error)

    save_run(record)
    return record
