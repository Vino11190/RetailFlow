"""Unit tests for the RetailFlow data quality scoring engine."""

import pytest

from src.quality.scoring import calculate_quality_score
from src.quality.thresholds import QualityThresholds


def make_metrics(
    total=1000,
    invalid=0,
    duplicates=0,
):
    return {
        "input_records": total,
        "clean_records": total - invalid - duplicates,
        "quarantined_records": invalid + duplicates,
        "invalid_records": invalid,
        "duplicate_records": duplicates,
    }


def test_perfect_dataset_passes():
    score = calculate_quality_score(make_metrics())

    assert score.passed is True
    assert score.completeness == 1.0
    assert score.validity == 1.0
    assert score.uniqueness == 1.0
    assert score.quarantine_rate == 0.0
    assert score.failed_checks == ()


def test_high_quality_dataset_passes():
    score = calculate_quality_score(
        make_metrics(total=1000, invalid=5, duplicates=2)
    )

    assert score.passed is True
    assert score.quarantine_rate == 0.007


def test_excessive_invalid_records_fail():
    score = calculate_quality_score(
        make_metrics(total=1000, invalid=50)
    )

    assert score.passed is False
    assert "completeness" in score.failed_checks
    assert "validity" in score.failed_checks
    assert "quarantine_rate" in score.failed_checks


def test_excessive_duplicates_fail():
    score = calculate_quality_score(
        make_metrics(total=1000, duplicates=30)
    )

    assert score.passed is False
    assert "uniqueness" in score.failed_checks
    assert "quarantine_rate" in score.failed_checks


def test_empty_dataset_fails():
    score = calculate_quality_score(
        make_metrics(total=0)
    )

    assert score.passed is False
    assert score.failed_checks == ("empty_dataset",)


def test_missing_metric_raises_error():
    metrics = make_metrics()
    del metrics["invalid_records"]

    with pytest.raises(ValueError, match="Missing quality metric"):
        calculate_quality_score(metrics)


def test_negative_metric_raises_error():
    metrics = make_metrics()
    metrics["duplicate_records"] = -1

    with pytest.raises(ValueError, match="non-negative integer"):
        calculate_quality_score(metrics)


def test_inconsistent_record_counts_raise_error():
    metrics = make_metrics()
    metrics["clean_records"] = 999

    with pytest.raises(ValueError, match="Record reconciliation"):
        calculate_quality_score(metrics)


def test_custom_thresholds():
    thresholds = QualityThresholds(
        completeness_min=0.90,
        validity_min=0.90,
        uniqueness_min=0.90,
        quarantine_max=0.10,
    )

    score = calculate_quality_score(
        make_metrics(total=1000, invalid=50),
        thresholds=thresholds,
    )

    assert score.passed is True


def test_score_serialization():
    score = calculate_quality_score(make_metrics())
    result = score.to_dict()

    assert result["passed"] is True
    assert result["failed_checks"] == []
    assert result["completeness"] == 1.0


def test_invalid_threshold_rejected():
    with pytest.raises(ValueError, match="between 0 and 1"):
        QualityThresholds(completeness_min=1.5)