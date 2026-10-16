"""Unit tests for RetailFlow quality audit transaction handling."""

from unittest.mock import MagicMock, patch

import pytest

from src.quality.audit_adapter import persist_quality_audit


def test_successful_audit_commits_four_records():
    engine = MagicMock()
    connection = engine.raw_connection.return_value
    score = MagicMock()

    with patch(
        "src.quality.audit_adapter.save_quality_audit",
        return_value=4,
    ) as mock_save:
        result = persist_quality_audit(
            engine=engine,
            source_system="ecommerce",
            dataset_name="customers",
            metrics={"input_records": 100},
            score=score,
        )

    assert result == 4
    mock_save.assert_called_once()

    assert mock_save.call_args.kwargs["connection"] is connection
    assert mock_save.call_args.kwargs["pipeline_run_id"] is None

    connection.commit.assert_called_once()
    connection.rollback.assert_not_called()
    connection.close.assert_called_once()


def test_failed_audit_rolls_back_transaction():
    engine = MagicMock()
    connection = engine.raw_connection.return_value

    with patch(
        "src.quality.audit_adapter.save_quality_audit",
        side_effect=RuntimeError("Audit insert failed"),
    ):
        with pytest.raises(RuntimeError, match="Audit insert failed"):
            persist_quality_audit(
                engine=engine,
                source_system="ecommerce",
                dataset_name="customers",
                metrics={"input_records": 100},
                score=MagicMock(),
            )

    connection.commit.assert_not_called()
    connection.rollback.assert_called_once()
    connection.close.assert_called_once()


def test_adapter_closes_connection_after_success():
    engine = MagicMock()
    connection = engine.raw_connection.return_value

    with patch(
        "src.quality.audit_adapter.save_quality_audit",
        return_value=4,
    ):
        persist_quality_audit(
            engine=engine,
            source_system="pos",
            dataset_name="transactions",
            metrics={"input_records": 50},
            score=MagicMock(),
        )

    engine.raw_connection.assert_called_once()
    connection.close.assert_called_once()