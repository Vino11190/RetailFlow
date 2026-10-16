"""
RetailFlow Data Quality Scoring Engine.

Evaluates existing Silver cleaning metrics against
configurable quality thresholds.
"""

from dataclasses import asdict, dataclass

from src.quality.thresholds import (
    DEFAULT_THRESHOLDS,
    QualityThresholds,
)


@dataclass(frozen=True)
class QualityScore:
    completeness: float
    validity: float
    uniqueness: float
    quarantine_rate: float
    passed: bool
    failed_checks: tuple[str, ...]

    def to_dict(self) -> dict:
        result = asdict(self)
        result["failed_checks"] = list(self.failed_checks)
        return result


def calculate_quality_score(
    metrics: dict,
    thresholds: QualityThresholds = DEFAULT_THRESHOLDS,
) -> QualityScore:
    """Evaluate Silver cleaning metrics against quality thresholds."""

    required = (
        "input_records",
        "clean_records",
        "quarantined_records",
        "duplicate_records",
        "invalid_records",
    )

    for name in required:
        if name not in metrics:
            raise ValueError(f"Missing quality metric: {name}")

        value = metrics[name]

        if (
            isinstance(value, bool)
            or not isinstance(value, int)
            or value < 0
        ):
            raise ValueError(
                f"{name} must be a non-negative integer"
            )

    total = metrics["input_records"]
    clean = metrics["clean_records"]
    quarantined = metrics["quarantined_records"]
    duplicates = metrics["duplicate_records"]
    invalid = metrics["invalid_records"]

    if clean + quarantined != total:
        raise ValueError("Record reconciliation failed")

    if invalid + duplicates != quarantined:
        raise ValueError("Invalid and duplicate counts do not reconcile")

    if total == 0:
        return QualityScore(
            completeness=0.0,
            validity=0.0,
            uniqueness=0.0,
            quarantine_rate=0.0,
            passed=False,
            failed_checks=("empty_dataset",),
        )

    valid = total - invalid

    completeness = valid / total
    validity = valid / total
    uniqueness = (
        (valid - duplicates) / valid
        if valid > 0
        else 0.0
    )
    quarantine_rate = quarantined / total

    failed = []

    if completeness < thresholds.completeness_min:
        failed.append("completeness")

    if validity < thresholds.validity_min:
        failed.append("validity")

    if uniqueness < thresholds.uniqueness_min:
        failed.append("uniqueness")

    if quarantine_rate > thresholds.quarantine_max:
        failed.append("quarantine_rate")

    return QualityScore(
        completeness=round(completeness, 6),
        validity=round(validity, 6),
        uniqueness=round(uniqueness, 6),
        quarantine_rate=round(quarantine_rate, 6),
        passed=not failed,
        failed_checks=tuple(failed),
    )