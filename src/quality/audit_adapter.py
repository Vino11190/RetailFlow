"""
RetailFlow quality audit adapter.

Persists quality results using the existing SQLAlchemy warehouse
engine and psycopg2-based audit writer.

Each invocation owns an independent database transaction.
"""

from sqlalchemy.engine import Engine

from src.quality.audit import save_quality_audit
from src.quality.scoring import QualityScore
from src.quality.thresholds import (
    DEFAULT_THRESHOLDS,
    QualityThresholds,
)


def persist_quality_audit(
    engine: Engine,
    source_system: str,
    dataset_name: str,
    metrics: dict,
    score: QualityScore,
    thresholds: QualityThresholds = DEFAULT_THRESHOLDS,
) -> int:
    """
    Persist four quality check results in an independent transaction.

    The audit transaction is committed only when all inserts succeed.

    pipeline_run_id remains NULL until its existence in
    metadata.pipeline_runs can be guaranteed.
    """

    connection = engine.raw_connection()

    try:
        inserted = save_quality_audit(
            connection=connection,
            source_system=source_system,
            dataset_name=dataset_name,
            metrics=metrics,
            score=score,
            pipeline_run_id=None,
            thresholds=thresholds,
        )

        connection.commit()
        return inserted

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()