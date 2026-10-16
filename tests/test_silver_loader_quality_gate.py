"""Tests for Silver quality rejection and persistent audit integration."""

from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from src.transformations.silver.silver_loader import load_silver_dataset


@pytest.mark.parametrize(
    "invalid_records",
    [10, 20],
)
def test_failed_quality_gate_audits_without_silver_load(invalid_records):
    bronze_data = pd.DataFrame({"customer_id": [1, 2, 3]})

    cleaned_result = {
        "clean": bronze_data,
        "quarantine": pd.DataFrame(),
        "metrics": {
            "input_records": 100,
            "clean_records": 100 - invalid_records,
            "quarantined_records": invalid_records,
            "invalid_records": invalid_records,
            "duplicate_records": 0,
        },
    }

    audit_engine = MagicMock()

    with (
        patch(
            "src.transformations.silver.silver_loader.get_transformation"
        ),
        patch(
            "src.transformations.silver.silver_loader.read_bronze_dataset"
        ) as mock_reader,
        patch(
            "src.transformations.silver.silver_loader.clean_bronze_dataframe"
        ) as mock_cleaner,
        patch(
            "src.transformations.silver.silver_loader.create_warehouse_engine",
            return_value=audit_engine,
        ) as mock_engine,
        patch(
            "src.transformations.silver.silver_loader.persist_quality_audit",
            return_value=4,
        ) as mock_audit,
    ):
        mock_reader.return_value = {
            "dataframe": bronze_data,
            "pipeline_run_id": "test-run-id",
        }
        mock_cleaner.return_value = cleaned_result

        with pytest.raises(
            RuntimeError,
            match="Quality gate rejected ecommerce/customers",
        ):
            load_silver_dataset("ecommerce", "customers")

        # Only the independent audit engine was created.
        mock_engine.assert_called_once_with()

        # Four quality checks were persisted before rejection.
        mock_audit.assert_called_once()
        assert mock_audit.call_args.kwargs["engine"] is audit_engine
        assert mock_audit.call_args.kwargs["source_system"] == "ecommerce"
        assert mock_audit.call_args.kwargs["dataset_name"] == "customers"

        # The audit engine was disposed after persistence.
        audit_engine.dispose.assert_called_once()

        # No Silver loading transaction was started.
        audit_engine.begin.assert_not_called()


def test_audit_failure_blocks_silver_loading():
    bronze_data = pd.DataFrame({"customer_id": [1]})

    cleaned_result = {
        "clean": bronze_data,
        "quarantine": pd.DataFrame(),
        "metrics": {
            "input_records": 100,
            "clean_records": 100,
            "quarantined_records": 0,
            "invalid_records": 0,
            "duplicate_records": 0,
        },
    }

    audit_engine = MagicMock()

    with (
        patch(
            "src.transformations.silver.silver_loader.get_transformation"
        ),
        patch(
            "src.transformations.silver.silver_loader.read_bronze_dataset"
        ) as mock_reader,
        patch(
            "src.transformations.silver.silver_loader.clean_bronze_dataframe"
        ) as mock_cleaner,
        patch(
            "src.transformations.silver.silver_loader.create_warehouse_engine",
            return_value=audit_engine,
        ) as mock_engine,
        patch(
            "src.transformations.silver.silver_loader.persist_quality_audit",
            side_effect=RuntimeError("Audit database unavailable"),
        ),
    ):
        mock_reader.return_value = {
            "dataframe": bronze_data,
            "pipeline_run_id": "test-run-id",
        }
        mock_cleaner.return_value = cleaned_result

        with pytest.raises(
            RuntimeError,
            match="Audit database unavailable",
        ):
            load_silver_dataset("ecommerce", "customers")

        mock_engine.assert_called_once_with()
        audit_engine.dispose.assert_called_once()
        audit_engine.begin.assert_not_called()