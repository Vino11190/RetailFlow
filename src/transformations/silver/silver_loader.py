
"""
RetailFlow Silver full-snapshot loader.

Uses PostgreSQL temporary tables and a single transaction
per dataset. Reprocessing a snapshot replaces, rather
than duplicates, the previously committed records.
"""

import json
import uuid
from datetime import date, datetime
from decimal import Decimal

import pandas as pd
from sqlalchemy import text

from src.config.transformation_config import get_transformation
from src.transformations.silver.bronze_reader import (
    read_bronze_dataset,
)
from src.transformations.silver.cleaner import (
    clean_bronze_dataframe,
)
from src.quality.audit_adapter import persist_quality_audit
from src.quality.gate import evaluate_quality_gate
from src.quality.scoring import calculate_quality_score
from src.warehouse.connection import create_warehouse_engine


LINEAGE_COLUMNS = [
    "_pipeline_run_id",
    "_batch_id",
    "_ingestion_timestamp",
    "_source_system",
    "_source_dataset",
    "_source_file_name",
    "_source_record_number",
]


def json_safe(value):
    if value is None:
        return None

    if isinstance(value, Decimal):
        return str(value)

    if isinstance(value, (pd.Timestamp, datetime, date)):
        if pd.isna(value):
            return None
        return value.isoformat()

    if isinstance(value, uuid.UUID):
        return str(value)

    if isinstance(value, float) and pd.isna(value):
        return None

    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass

    return value


def load_silver_dataset(source_system, dataset_name):
    definition = get_transformation(
        source_system,
        dataset_name,
    )

    extracted = read_bronze_dataset(
        source_system,
        dataset_name,
    )

    cleaned = clean_bronze_dataframe(
        source_system,
        dataset_name,
        extracted["dataframe"],
    )

    clean = cleaned["clean"]
    quarantine = cleaned["quarantine"]
    run_id = extracted["pipeline_run_id"]

    # Evaluate quality before opening the Silver load transaction.
    quality_score = calculate_quality_score(cleaned["metrics"])
    quality_gate = evaluate_quality_gate(quality_score)

    # Persist quality results before allowing or rejecting Silver loading.
    audit_engine = create_warehouse_engine()

    try:
        persist_quality_audit(
            engine=audit_engine,
            source_system=source_system,
            dataset_name=dataset_name,
            metrics=cleaned["metrics"],
            score=quality_score,
        )
    finally:
        audit_engine.dispose()

    if not quality_gate.allowed:
        raise RuntimeError(
            f"Quality gate rejected {source_system}/{dataset_name}: "
            f"{quality_gate.message}"
        )

    engine = create_warehouse_engine()

    target_table = definition.silver_table
    temporary_table = f"tmp_{target_table}"

    try:
        with engine.begin() as connection:
            # Temporary table has the same structure
            # as the target, including constraints.
            connection.execute(
                text(
                    f"""
                    CREATE TEMP TABLE {temporary_table}
                    (LIKE silver.{target_table}
                     INCLUDING DEFAULTS
                     INCLUDING CONSTRAINTS
                     INCLUDING INDEXES)
                    ON COMMIT DROP
                    """
                )
            )

            target_columns = set(
                connection.execute(
                    text(
                        """
                        SELECT column_name
                        FROM information_schema.columns
                        WHERE table_schema = 'silver'
                          AND table_name = :table_name
                        """
                    ),
                    {"table_name": target_table},
                ).scalars()
            )

            columns = [
                column
                for column in clean.columns
                if column in target_columns
            ]

            if not set(definition.primary_key).issubset(columns):
                raise RuntimeError(
                    f"Missing business keys for {target_table}"
                )

            # Convert missing pandas values to SQL NULL.
            records = clean[columns].astype(object)
            records = records.where(pd.notna(records), None)

            if not records.empty:
                records.to_sql(
                    temporary_table,
                    con=connection,
                    if_exists="append",
                    index=False,
                    method="multi",
                    chunksize=500,
                )

            staged_count = connection.execute(
                text(
                    f"SELECT COUNT(*) FROM {temporary_table}"
                )
            ).scalar_one()

            if staged_count != len(clean):
                raise RuntimeError(
                    f"Staging mismatch: {target_table}"
                )

            # Replace the target snapshot transactionally.
            connection.execute(
                text(f"DELETE FROM silver.{target_table}")
            )

            column_sql = ", ".join(
                f'"{column}"' for column in columns
            )

            connection.execute(
                text(
                    f"""
                    INSERT INTO silver.{target_table}
                    ({column_sql})
                    SELECT {column_sql}
                    FROM {temporary_table}
                    """
                )
            )

            # Replace the quarantine results for this
            # dataset and ingestion run.
            connection.execute(
                text(
                    """
                    DELETE FROM silver.quarantine_records
                    WHERE source_system = :source_system
                      AND dataset_name = :dataset_name
                      AND pipeline_run_id = :run_id
                    """
                ),
                {
                    "source_system": source_system,
                    "dataset_name": dataset_name,
                    "run_id": run_id,
                },
            )

            if not quarantine.empty:
                payloads = []

                for _, row in quarantine.iterrows():
                    payload = {
                        column: json_safe(value)
                        for column, value in row.items()
                        if column != "_quarantine_reason"
                    }

                    payloads.append(
                        {
                            "source_system": source_system,
                            "dataset_name": dataset_name,
                            "pipeline_run_id": run_id,
                            "source_record_number": json_safe(
                                row.get("_source_record_number")
                            ),
                            "quarantine_reason": row[
                                "_quarantine_reason"
                            ],
                            "record_payload": json.dumps(
                                payload,
                                default=str,
                            ),
                        }
                    )

                connection.execute(
                    text(
                        """
                        INSERT INTO silver.quarantine_records (
                            source_system,
                            dataset_name,
                            pipeline_run_id,
                            source_record_number,
                            quarantine_reason,
                            record_payload
                        )
                        VALUES (
                            :source_system,
                            :dataset_name,
                            :pipeline_run_id,
                            :source_record_number,
                            :quarantine_reason,
                            CAST(:record_payload AS JSONB)
                        )
                        """
                    ),
                    payloads,
                )

            final_count = connection.execute(
                text(
                    f"SELECT COUNT(*) FROM silver.{target_table}"
                )
            ).scalar_one()

            if final_count != len(clean):
                raise RuntimeError(
                    f"Silver count mismatch: {target_table}"
                )

        return {
            "source_system": source_system,
            "dataset_name": dataset_name,
            "table": f"silver.{target_table}",
            "pipeline_run_id": run_id,
            **cleaned["metrics"],
        }

    finally:
        engine.dispose()


def main():
    import argparse

    from src.config.transformation_config import (
        list_transformations,
    )

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--source",
        default="all",
        help="Source system or 'all'",
    )
    parser.add_argument(
        "--dataset",
        default=None,
        help="Dataset name for a single source",
    )

    args = parser.parse_args()

    definitions = [
        definition
        for definition in list_transformations()
        if (
            args.source == "all"
            or definition.source_system == args.source
        )
        and (
            args.dataset is None
            or definition.dataset_name == args.dataset
        )
    ]

    if not definitions:
        parser.error("No matching transformation definitions")

    total_clean = 0
    total_quarantine = 0

    for definition in definitions:
        result = load_silver_dataset(
            definition.source_system,
            definition.dataset_name,
        )

        total_clean += result["clean_records"]
        total_quarantine += result["quarantined_records"]

        print(
            f"PASS | {result['table']} "
            f"| clean={result['clean_records']:,} "
            f"| quarantine={result['quarantined_records']:,}"
        )

    print()
    print(f"Silver records loaded: {total_clean:,}")
    print(f"Quarantined records: {total_quarantine:,}")
    print("SILVER LOAD RESULT: PASS")


if __name__ == "__main__":
    main()
