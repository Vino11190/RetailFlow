"""Database integration test for the quality audit adapter."""

from uuid import uuid4

import pytest
from sqlalchemy import create_engine
from sqlalchemy.engine import URL

from src.quality.audit_adapter import persist_quality_audit
from src.quality.scoring import calculate_quality_score


def test_audit_adapter_commits_records_to_test_database(db_connection):
    # Reuse the verified, isolated PostgreSQL test database.
    parameters = db_connection.get_dsn_parameters()

    url = URL.create(
        "postgresql+psycopg2",
        username=parameters["user"],
        password="retailflow_test_local_only",
        host=parameters.get("host", "127.0.0.1"),
        port=int(parameters.get("port", 5434)),
        database=parameters["dbname"],
    )

    engine = create_engine(url)

    dataset_name = f"audit_adapter_{uuid4().hex[:12]}"

    metrics = {
        "input_records": 100,
        "clean_records": 100,
        "quarantined_records": 0,
        "invalid_records": 0,
        "duplicate_records": 0,
    }

    score = calculate_quality_score(metrics)

    try:
        inserted = persist_quality_audit(
            engine=engine,
            source_system="integration_test",
            dataset_name=dataset_name,
            metrics=metrics,
            score=score,
        )

        assert inserted == 4

        # Query through a fresh connection to verify the commit.
        with engine.connect() as connection:
            from sqlalchemy import text

            result = connection.execute(
                text(
                    """
                    SELECT check_name, status
                    FROM audit.data_quality_results
                    WHERE source_system = :source_system
                      AND dataset_name = :dataset_name
                    """
                ),
                {
                    "source_system": "integration_test",
                    "dataset_name": dataset_name,
                },
            ).fetchall()

        assert len(result) == 4
        assert all(row.status == "PASS" for row in result)

    finally:
        # Remove test records using a separate committed transaction.
        from sqlalchemy import text

        with engine.begin() as connection:
            connection.execute(
                text(
                    """
                    DELETE FROM audit.data_quality_results
                    WHERE source_system = :source_system
                      AND dataset_name = :dataset_name
                    """
                ),
                {
                    "source_system": "integration_test",
                    "dataset_name": dataset_name,
                },
            )

        engine.dispose()