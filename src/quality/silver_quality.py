"""
RetailFlow Silver Data Quality Integration.

Combines the existing Bronze-to-Silver cleaning engine
with the advanced data quality scoring framework.

No database writes are performed.
"""

import pandas as pd

from src.quality.scoring import calculate_quality_score
from src.quality.thresholds import (
    DEFAULT_THRESHOLDS,
    QualityThresholds,
)
from src.transformations.silver.cleaner import (
    clean_bronze_dataframe,
)


def clean_and_assess_silver(
    source_system: str,
    dataset_name: str,
    dataframe: pd.DataFrame,
    thresholds: QualityThresholds = DEFAULT_THRESHOLDS,
) -> dict:
    """
    Clean a Bronze dataset and assess its data quality.

    Returns:
        clean: Cleaned DataFrame
        quarantine: Quarantined DataFrame
        metrics: Existing Silver cleaning metrics
        quality: Advanced quality assessment dictionary
    """

    result = clean_bronze_dataframe(
        source_system=source_system,
        dataset_name=dataset_name,
        dataframe=dataframe,
    )

    score = calculate_quality_score(
        metrics=result["metrics"],
        thresholds=thresholds,
    )

    return {
        "clean": result["clean"],
        "quarantine": result["quarantine"],
        "metrics": result["metrics"],
        "quality": score.to_dict(),
    }