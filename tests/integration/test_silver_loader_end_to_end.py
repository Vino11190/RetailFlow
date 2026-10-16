"""End-to-end Silver loader test against isolated PostgreSQL."""

import os
from unittest.mock import patch
from uuid import uuid4

import pandas as pd
import psycopg2
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL

from src.transformations.silver.silver_loader import load_silver_dataset


def test_silver_loader_end_to_end(db_connection):
    parameters = db_connection.get_dsn_parameters()

    assert parameters["dbname"] == "retailflow_integration_test"
    assert parameters["user"] == "retailflow_test"

    url = URL.create(
        "postgresql+psycopg2",
        username=parameters["user"],
        password=os.getenv(
            "RETAILFLOW_TEST_DB_PASSWORD",
            "retailflow_test_local_only",
        ),
        host=parameters.get("host", "127.0.0.1"),
        port=int(parameters.get("port", 5434)),
        database=parameters["dbname"],
    )

    engine = create_engine(url)

    run_id = str(uuid4())

    customers = pd.DataFrame(
        {
            "customer_id": ["TEST-001", "TEST-002"],
            "first_name": ["Alice", "Bob"],
            "last_name": ["Smith", "Jones"],
            "email": [
                "alice@example.com",
                "bob@example.com",
            ],
        }
    )

    metrics = {
        "input_records": 2,
        "clean_records": 2,
        "quarantined_records": 0,
        "invalid_records": 0,
        "duplicate_records": 0,
    }

    try:
        # Check the target database before allowing any writes.
        with engine.connect() as connection:
            identity = connection.execute(
                text("SELECT current_database(), current_user")
            ).one()

            assert identity[0] == "retailflow_integration_test"
            assert identity[1] == "retailflow_test"

            customer_count = connection.execute(
                text("SELECT COUNT(*) FROM silver.ecommerce_customers")
            ).scalar_one()

            audit_count = connection.execute(
                text("SELECT COUNT(*) FROM audit.data_quality_results")
            ).scalar_one()

            assert customer_count == 0, "Customer table must be empty"
            assert audit_count == 0, "Audit table must be empty"

        # Mock Bronze input and cleaning, but exercise the real
        # quality gate, audit adapter and Silver database SQL.
        with (
            patch(
                "src.transformations.silver.silver_loader.read_bronze_dataset",
                return_value={
                    "dataframe": customers,
                    "pipeline_run_id": run_id,
                },
            ),
            patch(
                "src.transformations.silver.silver_loader.clean_bronze_dataframe",
                return_value={
                    "clean": customers,
                    "quarantine": pd.DataFrame(),
                    "metrics": metrics,
                },
            ),
            patch(
                "src.transformations.silver.silver_loader.create_warehouse_engine",
                side_effect=lambda: engine,
            ),
        ):
            result = load_silver_dataset("ecommerce", "customers")

        assert result["clean_records"] == 2
        assert result["quarantined_records"] == 0

        with engine.connect() as connection:
            loaded = connection.execute(
                text(
                    """
                    SELECT customer_id
                    FROM silver.ecommerce_customers
                    ORDER BY customer_id
                    """
                )
            ).scalars().all()

            audit_rows = connection.execute(
                text(
                    """
                    SELECT check_name, status
                    FROM audit.data_quality_results
                    WHERE source_system = 'ecommerce'
                      AND dataset_name = 'customers'
                    """
                )
            ).all()

        assert loaded == ["TEST-001", "TEST-002"]
        assert len(audit_rows) == 4
        assert all(row.status == "PASS" for row in audit_rows)

    finally:
        # Clean up only records belonging to this test.
        with engine.begin() as connection:
            connection.execute(
                text(
                    """
                    DELETE FROM silver.ecommerce_customers
                    WHERE customer_id IN ('TEST-001', 'TEST-002')
                    """
                )
            )

            connection.execute(
                text(
                    """
                    DELETE FROM audit.data_quality_results
                    WHERE source_system = 'ecommerce'
                      AND dataset_name = 'customers'
                      AND check_type = 'ADVANCED_QUALITY'
                    """
                )
            )

        engine.dispose()