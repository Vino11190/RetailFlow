"""Verify successful Silver loading after quality audit persistence."""

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pandas as pd

from src.transformations.silver.silver_loader import load_silver_dataset


def test_passing_quality_gate_proceeds_to_silver_transaction():
    clean = pd.DataFrame(
        {
            "customer_id": [1, 2],
            "email": ["one@example.com", "two@example.com"],
        }
    )

    metrics = {
        "input_records": 2,
        "clean_records": 2,
        "quarantined_records": 0,
        "invalid_records": 0,
        "duplicate_records": 0,
    }

    audit_engine = MagicMock()
    silver_engine = MagicMock()

    connection = silver_engine.begin.return_value.__enter__.return_value

    # The loader queries available target columns, staging counts,
    # and the final Silver row count.
    def execute_statement(statement, parameters=None):
        sql = str(statement)

        result = MagicMock()

        if "information_schema.columns" in sql:
            result.scalars.return_value = ["customer_id", "email"]
        elif "COUNT(*)" in sql:
            result.scalar_one.return_value = 2

        return result

    connection.execute.side_effect = execute_statement

    definition = SimpleNamespace(
        silver_table="customers",
        primary_key=["customer_id"],
    )

    events = []

    def persist_audit(**kwargs):
        events.append("audit")
        return 4

    def begin_transaction():
        events.append("silver_transaction")
        return silver_engine.begin.return_value

    silver_engine.begin.side_effect = begin_transaction

    with (
        patch(
            "src.transformations.silver.silver_loader.get_transformation",
            return_value=definition,
        ),
        patch(
            "src.transformations.silver.silver_loader.read_bronze_dataset",
            return_value={
                "dataframe": clean,
                "pipeline_run_id": "test-run-id",
            },
        ),
        patch(
            "src.transformations.silver.silver_loader.clean_bronze_dataframe",
            return_value={
                "clean": clean,
                "quarantine": pd.DataFrame(),
                "metrics": metrics,
            },
        ),
        patch(
            "src.transformations.silver.silver_loader.create_warehouse_engine",
            side_effect=[audit_engine, silver_engine],
        ) as mock_create_engine,
        patch(
            "src.transformations.silver.silver_loader.persist_quality_audit",
            side_effect=persist_audit,
        ) as mock_audit,
        patch.object(pd.DataFrame, "to_sql") as mock_to_sql,
    ):
        result = load_silver_dataset("ecommerce", "customers")

    assert events == ["audit", "silver_transaction"]

    assert mock_create_engine.call_count == 2
    mock_audit.assert_called_once()

    assert mock_audit.call_args.kwargs["engine"] is audit_engine
    assert mock_audit.call_args.kwargs["metrics"] == metrics

    audit_engine.dispose.assert_called_once()
    silver_engine.dispose.assert_called_once()

    silver_engine.begin.assert_called_once()
    mock_to_sql.assert_called_once()

    assert result["table"] == "silver.customers"
    assert result["clean_records"] == 2
    assert result["quarantined_records"] == 0