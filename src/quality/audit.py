"""
RetailFlow PostgreSQL Data Quality Audit Persistence.

Persists quality assessments to the existing
audit.data_quality_results table.

The caller controls the database transaction.
"""

import json
from uuid import UUID

from src.quality.scoring import QualityScore
from src.quality.thresholds import (
    DEFAULT_THRESHOLDS,
    QualityThresholds,
)


QUALITY_CHECKS = (
    ("completeness", "completeness_min", ">="),
    ("validity", "validity_min", ">="),
    ("uniqueness", "uniqueness_min", ">="),
    ("quarantine_rate", "quarantine_max", "<="),
)


def save_quality_audit(
    connection,
    source_system: str,
    dataset_name: str,
    metrics: dict,
    score: QualityScore,
    pipeline_run_id: UUID | None = None,
    thresholds: QualityThresholds = DEFAULT_THRESHOLDS,
) -> int:
    """
    Insert four quality check results into PostgreSQL.

    Returns the number of inserted audit records.

    Does not commit or roll back the connection.
    """

    if not source_system or not source_system.strip():
        raise ValueError("source_system is required")

    if not dataset_name or not dataset_name.strip():
        raise ValueError("dataset_name is required")

    total = metrics["input_records"]
    invalid = metrics["invalid_records"]
    duplicates = metrics["duplicate_records"]
    quarantined = metrics["quarantined_records"]

    failed_counts = {
        "completeness": invalid,
        "validity": invalid,
        "uniqueness": duplicates,
        "quarantine_rate": quarantined,
    }

    checked_counts = {
        "completeness": total,
        "validity": total,
        "uniqueness": total - invalid,
        "quarantine_rate": total,
    }

    inserted = 0

    with connection.cursor() as cursor:
        for check_name, threshold_name, operator in QUALITY_CHECKS:
            measured = getattr(score, check_name)
            threshold = getattr(thresholds, threshold_name)

            if check_name == "quarantine_rate":
                passed = measured <= threshold
            else:
                passed = measured >= threshold

            # Empty datasets are not considered successful.
            if total == 0:
                passed = False

            details = json.dumps(
                {
                    "measured_score": measured,
                    "threshold": threshold,
                    "operator": operator,
                    "overall_quality_passed": score.passed,
                    "failed_checks": list(score.failed_checks),
                }
            )

            cursor.execute(
                """
                INSERT INTO audit.data_quality_results (
                    pipeline_run_id,
                    source_system,
                    dataset_name,
                    check_name,
                    check_type,
                    status,
                    records_checked,
                    records_failed,
                    failure_details
                )
                VALUES (
                    %s, %s, %s, %s, %s,
                    %s, %s, %s, %s
                )
                """,
                (
                    str(pipeline_run_id) if pipeline_run_id is not None else None,
                    source_system,
                    dataset_name,
                    check_name,
                    "ADVANCED_QUALITY",
                    "PASS" if passed else "FAIL",
                    checked_counts[check_name],
                    failed_counts[check_name],
                    details,
                ),
            )

            inserted += 1

    return inserted