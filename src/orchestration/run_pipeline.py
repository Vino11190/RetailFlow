
"""
RetailFlow End-to-End Pipeline Orchestrator.

Stages:
1. Bronze ingestion
2. Silver transformation/loading
3. Gold dimensions
4. Gold facts
5. dbt analytics build and tests

Provides:
- Sequential dependency execution
- Fail-fast behaviour
- JSON execution reporting
- Per-stage duration tracking
- Optional Bronze ingestion skip
- Automated dbt analytics and quality testing
"""

import argparse
import json
import subprocess
import sys
import time
import uuid

from datetime import datetime, timezone
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]

REPORT_DIRECTORY = (
    PROJECT_ROOT
    / "data"
    / "pipeline_reports"
)


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def run_stage(stage_name, command):
    print()
    print("=" * 60)
    print(f"STARTING: {stage_name}")
    print("=" * 60, flush=True)

    started_at = utc_now()
    start_time = time.perf_counter()

    try:
        result = subprocess.run(
            command,
            cwd=PROJECT_ROOT,
            check=False,
        )

        return_code = result.returncode

    except Exception as exc:
        duration = round(
            time.perf_counter() - start_time,
            2,
        )

        return {
            "stage": stage_name,
            "status": "FAILED",
            "started_at": started_at,
            "finished_at": utc_now(),
            "duration_seconds": duration,
            "return_code": None,
            "error": str(exc),
        }

    duration = round(
        time.perf_counter() - start_time,
        2,
    )

    status = (
        "SUCCESS"
        if return_code == 0
        else "FAILED"
    )

    print()
    print(
        f"{status}: {stage_name} "
        f"({duration:.2f} seconds)",
        flush=True,
    )

    return {
        "stage": stage_name,
        "status": status,
        "started_at": started_at,
        "finished_at": utc_now(),
        "duration_seconds": duration,
        "return_code": return_code,
    }


def save_report(report):
    REPORT_DIRECTORY.mkdir(
        parents=True,
        exist_ok=True,
    )

    path = (
        REPORT_DIRECTORY
        / f"{report['pipeline_run_id']}.json"
    )

    with path.open(
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            report,
            file,
            indent=2,
        )

    return path


def run_pipeline(skip_bronze=False):
    pipeline_run_id = str(uuid.uuid4())

    report = {
        "pipeline_run_id": pipeline_run_id,
        "started_at": utc_now(),
        "finished_at": None,
        "status": "RUNNING",
        "skip_bronze": skip_bronze,
        "stages": [],
    }

    python = sys.executable

    stages = []

    # --------------------------------------------------
    # STAGE 1: BRONZE INGESTION
    # --------------------------------------------------

    if not skip_bronze:
        stages.append(
            (
                "Bronze Ingestion",
                [
                    python,
                    "-m",
                    "src.ingestion.run_ingestion",
                    "all",
                ],
            )
        )

    # --------------------------------------------------
    # STAGES 2-5: SILVER, GOLD AND DBT
    # --------------------------------------------------

    stages.extend(
        [
            (
                "Silver Transformation",
                [
                    python,
                    "-m",
                    "src.transformations.silver.silver_loader",
                    "--source",
                    "all",
                ],
            ),
            (
                "Gold Dimensions",
                [
                    python,
                    "-m",
                    "src.transformations.gold.dimension_loader",
                ],
            ),
            (
                "Gold Facts",
                [
                    python,
                    "-m",
                    "src.transformations.gold.fact_loader",
                ],
            ),
            (
                "dbt Analytics Build",
                [
                    python,
                    "-m",
                    "orchestration.dbt_runner",
                ],
            ),
        ]
    )

    # --------------------------------------------------
    # EXECUTE PIPELINE STAGES
    # --------------------------------------------------

    try:
        for stage_name, command in stages:
            stage_result = run_stage(
                stage_name,
                command,
            )

            report["stages"].append(
                stage_result
            )

            if stage_result["status"] != "SUCCESS":
                report["status"] = "FAILED"
                break

        else:
            report["status"] = "SUCCESS"

    except Exception as exc:
        report["status"] = "FAILED"
        report["error"] = str(exc)

    finally:
        report["finished_at"] = utc_now()
        report_path = save_report(report)

    # --------------------------------------------------
    # PRINT PIPELINE SUMMARY
    # --------------------------------------------------

    print()
    print("=" * 60)
    print("RETAILFLOW PIPELINE SUMMARY")
    print("=" * 60)

    for stage in report["stages"]:
        print(
            f"{stage['status']:8} | "
            f"{stage['stage']:24} | "
            f"{stage['duration_seconds']:8.2f}s"
        )

    print()
    print(f"Pipeline status: {report['status']}")
    print(f"Report saved: {report_path}")

    return report


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--skip-bronze",
        action="store_true",
        help="Reuse existing Bronze ingestion snapshots",
    )

    args = parser.parse_args()

    report = run_pipeline(
        skip_bronze=args.skip_bronze
    )

    if report["status"] != "SUCCESS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
