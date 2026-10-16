"""
Tests for the RetailFlow Silver Data Quality Gate.
"""

from src.quality.gate import evaluate_quality_gate
from src.quality.scoring import calculate_quality_score


def make_metrics(
    total=1000,
    invalid=0,
    duplicates=0,
):
    quarantined = invalid + duplicates

    return {
        "input_records": total,
        "clean_records": total - quarantined,
        "quarantined_records": quarantined,
        "invalid_records": invalid,
        "duplicate_records": duplicates,
    }


def test_good_dataset_allowed():
    score = calculate_quality_score(make_metrics())

    result = evaluate_quality_gate(score)

    assert result.allowed is True
    assert result.status == "PASS"
    assert result.failed_checks == ()


def test_invalid_records_block_load():
    score = calculate_quality_score(
        make_metrics(invalid=50)
    )

    result = evaluate_quality_gate(score)

    assert result.allowed is False
    assert result.status == "FAIL"
    assert "validity" in result.failed_checks
    assert "Silver load blocked" in result.message


def test_duplicate_records_block_load():
    score = calculate_quality_score(
        make_metrics(duplicates=30)
    )

    result = evaluate_quality_gate(score)

    assert result.allowed is False
    assert "uniqueness" in result.failed_checks


def test_empty_dataset_blocked():
    score = calculate_quality_score(
        make_metrics(total=0)
    )

    result = evaluate_quality_gate(score)

    assert result.allowed is False
    assert result.status == "FAIL"


def test_passing_message():
    score = calculate_quality_score(make_metrics())

    result = evaluate_quality_gate(score)

    assert result.message == (
        "Dataset passed all quality thresholds."
    )