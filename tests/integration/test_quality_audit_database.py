"""PostgreSQL integration tests for advanced data quality auditing."""

import json
from uuid import uuid4

import psycopg2
import pytest

from src.quality.audit import save_quality_audit
from src.quality.scoring import calculate_quality_score


def make_metrics(total=1000, invalid=0, duplicates=0):
    return {
        "input_records": total,
        "clean_records": total - invalid - duplicates,
        "quarantined_records": invalid + duplicates,
        "invalid_records": invalid,
        "duplicate_records": duplicates,
    }


def test_audit_records_inserted(db_connection):
    metrics = make_metrics()
    score = calculate_quality_score(metrics)

    inserted = save_quality_audit(
        db_connection,
        "ecommerce",
        "customers",
        metrics,
        score,
    )

    assert inserted == 4

    with db_connection.cursor() as cursor:
        cursor.execute("""
            SELECT check_name, status
            FROM audit.data_quality_results
            WHERE source_system = %s
              AND dataset_name = %s
              AND check_type = %s
        """, ("ecommerce", "customers", "ADVANCED_QUALITY"))

        rows = cursor.fetchall()

    assert len(rows) == 4
    assert all(status == "PASS" for _, status in rows)

    db_connection.rollback()


def test_failed_quality_results_persist(db_connection):
    metrics = make_metrics(invalid=50, duplicates=30)
    score = calculate_quality_score(metrics)

    save_quality_audit(
        db_connection,
        "test_quality_failure",
        "customers",
        metrics,
        score,
    )

    with db_connection.cursor() as cursor:
        cursor.execute("""
            SELECT check_name, status, failure_details
            FROM audit.data_quality_results
            WHERE source_system = %s
        """, ("test_quality_failure",))

        rows = cursor.fetchall()

    assert len(rows) == 4
    assert all(status == "FAIL" for _, status, _ in rows)

    for _, _, details in rows:
        parsed = json.loads(details)
        assert parsed["overall_quality_passed"] is False

    db_connection.rollback()


def test_quality_audit_links_to_pipeline_run(db_connection):
    run_id = uuid4()

    with db_connection.cursor() as cursor:
        cursor.execute("""
            INSERT INTO metadata.pipeline_runs (
                pipeline_run_id,
                pipeline_name,
                source_system,
                status
            )
            VALUES (%s, %s, %s, %s)
        """, (
            str(run_id),
            "phase13_quality_integration_test",
            "ecommerce",
            "STARTED",
        ))

    metrics = make_metrics()
    score = calculate_quality_score(metrics)

    save_quality_audit(
        db_connection,
        "ecommerce",
        "customers",
        metrics,
        score,
        pipeline_run_id=run_id,
    )

    with db_connection.cursor() as cursor:
        cursor.execute("""
            SELECT COUNT(*)
            FROM audit.data_quality_results
            WHERE pipeline_run_id = %s
        """, (str(run_id),))

        assert cursor.fetchone()[0] == 4

    db_connection.rollback()


def test_invalid_pipeline_run_rejected(db_connection):
    metrics = make_metrics()
    score = calculate_quality_score(metrics)

    with pytest.raises(psycopg2.errors.ForeignKeyViolation):
        save_quality_audit(
            db_connection,
            "ecommerce",
            "customers",
            metrics,
            score,
            pipeline_run_id=uuid4(),
        )

    db_connection.rollback()


def test_quality_audit_transaction_rollback(db_connection):
    source = f"rollback_test_{uuid4().hex}"

    metrics = make_metrics()
    score = calculate_quality_score(metrics)

    save_quality_audit(
        db_connection,
        source,
        "customers",
        metrics,
        score,
    )

    with db_connection.cursor() as cursor:
        cursor.execute("""
            SELECT COUNT(*)
            FROM audit.data_quality_results
            WHERE source_system = %s
        """, (source,))

        assert cursor.fetchone()[0] == 4

    db_connection.rollback()

    with db_connection.cursor() as cursor:
        cursor.execute("""
            SELECT COUNT(*)
            FROM audit.data_quality_results
            WHERE source_system = %s
        """, (source,))

        assert cursor.fetchone()[0] == 0