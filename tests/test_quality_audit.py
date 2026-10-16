"""Unit tests for PostgreSQL data quality audit persistence."""

import json
from unittest.mock import MagicMock

import pytest

from src.quality.audit import save_quality_audit
from src.quality.scoring import calculate_quality_score
from src.quality.thresholds import QualityThresholds


def make_metrics(total=1000, invalid=0, duplicates=0):
    return {
        "input_records": total,
        "clean_records": total - invalid - duplicates,
        "quarantined_records": invalid + duplicates,
        "invalid_records": invalid,
        "duplicate_records": duplicates,
    }


def mock_connection():
    connection = MagicMock()
    cursor = MagicMock()
    connection.cursor.return_value.__enter__.return_value = cursor
    return connection, cursor


def audit_rows(cursor):
    return [
        call.args[1]
        for call in cursor.execute.call_args_list
    ]


def test_passing_quality_inserts_four_checks():
    connection, cursor = mock_connection()
    metrics = make_metrics()
    score = calculate_quality_score(metrics)

    inserted = save_quality_audit(
        connection, "ecommerce", "customers", metrics, score
    )

    assert inserted == 4
    assert cursor.execute.call_count == 4

    rows = audit_rows(cursor)
    assert {row[3] for row in rows} == {
        "completeness",
        "validity",
        "uniqueness",
        "quarantine_rate",
    }
    assert all(row[5] == "PASS" for row in rows)
    assert all(row[4] == "ADVANCED_QUALITY" for row in rows)


def test_failing_quality_records_failed_checks():
    connection, cursor = mock_connection()
    metrics = make_metrics(invalid=50, duplicates=30)
    score = calculate_quality_score(metrics)

    save_quality_audit(
        connection, "ecommerce", "customers", metrics, score
    )

    rows = {row[3]: row for row in audit_rows(cursor)}

    assert rows["completeness"][5] == "FAIL"
    assert rows["validity"][5] == "FAIL"
    assert rows["uniqueness"][5] == "FAIL"
    assert rows["quarantine_rate"][5] == "FAIL"

    assert rows["completeness"][7] == 50
    assert rows["uniqueness"][7] == 30
    assert rows["quarantine_rate"][7] == 80

    details = json.loads(rows["completeness"][8])
    assert details["overall_quality_passed"] is False


def test_custom_thresholds_are_applied():
    connection, cursor = mock_connection()
    metrics = make_metrics(invalid=50)

    thresholds = QualityThresholds(
        completeness_min=0.90,
        validity_min=0.90,
        uniqueness_min=0.90,
        quarantine_max=0.10,
    )

    score = calculate_quality_score(metrics, thresholds)

    save_quality_audit(
        connection,
        "ecommerce",
        "customers",
        metrics,
        score,
        thresholds=thresholds,
    )

    assert all(row[5] == "PASS" for row in audit_rows(cursor))


def test_empty_dataset_fails_all_checks():
    connection, cursor = mock_connection()
    metrics = make_metrics(total=0)
    score = calculate_quality_score(metrics)

    save_quality_audit(
        connection, "ecommerce", "customers", metrics, score
    )

    assert all(row[5] == "FAIL" for row in audit_rows(cursor))


@pytest.mark.parametrize(
    "source,dataset",
    [
        ("", "customers"),
        ("   ", "customers"),
        ("ecommerce", ""),
        ("ecommerce", "   "),
    ],
)
def test_missing_identifiers_rejected(source, dataset):
    connection, cursor = mock_connection()
    metrics = make_metrics()
    score = calculate_quality_score(metrics)

    with pytest.raises(ValueError):
        save_quality_audit(
            connection, source, dataset, metrics, score
        )

    cursor.execute.assert_not_called()


def test_sql_is_parameterized():
    connection, cursor = mock_connection()
    metrics = make_metrics()
    score = calculate_quality_score(metrics)

    save_quality_audit(
        connection,
        "source'; DROP TABLE audit.data_quality_results; --",
        "customers",
        metrics,
        score,
    )

    for call in cursor.execute.call_args_list:
        sql, params = call.args

        assert "%s" in sql
        assert "DROP TABLE" not in sql
        assert "DROP TABLE" in params[1]


def test_caller_controls_transactions():
    connection, _ = mock_connection()
    metrics = make_metrics()
    score = calculate_quality_score(metrics)

    save_quality_audit(
        connection, "ecommerce", "customers", metrics, score
    )

    connection.commit.assert_not_called()
    connection.rollback.assert_not_called()