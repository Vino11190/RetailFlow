"""
RetailFlow advanced data quality configuration.

Defines reusable quality thresholds for dataset evaluation.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class QualityThresholds:
    completeness_min: float = 0.98
    validity_min: float = 0.99
    uniqueness_min: float = 0.995
    quarantine_max: float = 0.02

    def __post_init__(self) -> None:
        for name in (
            "completeness_min",
            "validity_min",
            "uniqueness_min",
            "quarantine_max",
        ):
            value = getattr(self, name)

            if not 0.0 <= value <= 1.0:
                raise ValueError(
                    f"{name} must be between 0 and 1; got {value}"
                )


DEFAULT_THRESHOLDS = QualityThresholds()