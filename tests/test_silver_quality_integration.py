"""Integration tests for Silver cleaning and quality scoring."""

from unittest.mock import patch

import pandas as pd
import pytest

from src.quality.silver_quality import clean_and_assess_silver
from src.quality.thresholds import QualityThresholds


def customer_data():
    return pd.DataFrame(
        {
            "customer_id": [
                "C001", "C002", "C003", "C003", None
            ],
            "first_name": [
                "Alice", "James", "Mary", "Mary", "Peter"
            ],
            "last_name": [
                "Brown", "Wilson", "Jones", "Jones", "Smith"
            ],
        }
    )


def test_cleaning_scoring_and_quarantine():
    # Mock only the configuration lookup, not the cleaning engine.
    from types import SimpleNamespace

    definition = SimpleNamespace(
        primary_key=("customer_id",)
    )

    with (
        patch(
            "src.transformations.silver.cleaner.get_transformation",
            return_value=definition,
        ),
        patch(
            "src.transformations.silver.cleaner.REQUIRED_COLUMNS",
            {("test_source", "customers"): ("customer_id",)},
        ),
    ):
        result = clean_and_assess_silver(
            source_system="test_source",
            dataset_name="customers",
            dataframe=customer_data(),
        )

    assert len(result["clean"]) == 3
    assert len(result["quarantine"]) == 2

    metrics = result["metrics"]

    assert metrics["input_records"] == 5
    assert metrics["clean_records"] == 3
    assert metrics["quarantined_records"] == 2
    assert metrics["invalid_records"] == 1
    assert metrics["duplicate_records"] == 1

    quality = result["quality"]

    assert quality["completeness"] == 0.8
    assert quality["validity"] == 0.8
    assert quality["uniqueness"] == 0.75
    assert quality["quarantine_rate"] == 0.4
    assert quality["passed"] is False

    reasons = set(
        result["quarantine"]["_quarantine_reason"]
    )

    assert "missing_or_invalid_customer_id" in reasons
    assert "duplicate_business_key" in reasons


def test_permissive_thresholds_allow_dataset():
    from types import SimpleNamespace

    definition = SimpleNamespace(
        primary_key=("customer_id",)
    )

    thresholds = QualityThresholds(
        completeness_min=0.8,
        validity_min=0.8,
        uniqueness_min=0.75,
        quarantine_max=0.4,
    )

    with (
        patch(
            "src.transformations.silver.cleaner.get_transformation",
            return_value=definition,
        ),
        patch(
            "src.transformations.silver.cleaner.REQUIRED_COLUMNS",
            {("test_source", "customers"): ("customer_id",)},
        ),
    ):
        result = clean_and_assess_silver(
            "test_source",
            "customers",
            customer_data(),
            thresholds=thresholds,
        )

    assert result["quality"]["passed"] is True
    assert result["quality"]["failed_checks"] == []


def test_input_dataframe_is_not_modified():
    from types import SimpleNamespace

    dataframe = customer_data()
    original = dataframe.copy(deep=True)

    with (
        patch(
            "src.transformations.silver.cleaner.get_transformation",
            return_value=SimpleNamespace(
                primary_key=("customer_id",)
            ),
        ),
        patch(
            "src.transformations.silver.cleaner.REQUIRED_COLUMNS",
            {("test_source", "customers"): ("customer_id",)},
        ),
    ):
        clean_and_assess_silver(
            "test_source",
            "customers",
            dataframe,
        )

    pd.testing.assert_frame_equal(dataframe, original)