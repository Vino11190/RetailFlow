"""
RetailFlow Silver Data Quality Gate.

Evaluates quality scores before Silver snapshot replacement.
Does not perform database writes.
"""

from dataclasses import dataclass

from src.quality.scoring import QualityScore


@dataclass(frozen=True)
class QualityGateResult:
    allowed: bool
    status: str
    failed_checks: tuple[str, ...]
    message: str


def evaluate_quality_gate(score: QualityScore) -> QualityGateResult:
    """
    Determine whether a dataset can proceed to Silver loading.

    A failed quality score blocks the load.
    """

    if score.passed:
        return QualityGateResult(
            allowed=True,
            status="PASS",
            failed_checks=(),
            message="Dataset passed all quality thresholds.",
        )

    failed_checks = tuple(score.failed_checks)

    if not failed_checks:
        failed_checks = ("unspecified_quality_failure",)

    return QualityGateResult(
        allowed=False,
        status="FAIL",
        failed_checks=failed_checks,
        message=(
            "Silver load blocked by data quality gate: "
            + ", ".join(failed_checks)
        ),
    )