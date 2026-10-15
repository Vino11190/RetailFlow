
"""
RetailFlow Phase 8.8
End-to-End Data Reconciliation Audit.

Validates:
- Silver-to-Gold fact counts
- Financial totals
- Business-key uniqueness
- Unknown dimension references
- Referential integrity
- Product SCD Type 2 consistency
- Quarantine accounting
- Latest pipeline execution status

Writes a JSON audit report.
"""

import json
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

from sqlalchemy import text

from src.config.transformation_config import (
    list_transformations,
)
from src.warehouse.connection import (
    create_warehouse_engine,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]

REPORT_DIRECTORY = (
    PROJECT_ROOT / "data" / "validation_reports"
)

PIPELINE_REPORT_DIRECTORY = (
    PROJECT_ROOT / "data" / "pipeline_reports"
)


FACT_SOURCES = {
    "fact_ecommerce_sales": """
        SELECT COUNT(*)
        FROM silver.ecommerce_order_items oi
        JOIN silver.ecommerce_orders o
          ON o.order_id = oi.order_id
    """,
    "fact_pos_sales": """
        SELECT COUNT(*) FROM silver.pos_transactions
    """,
    "fact_payments": """
        SELECT COUNT(*) FROM silver.payments_payments
    """,
    "fact_returns": """
        SELECT COUNT(*) FROM silver.returns_returns
    """,
    "fact_inventory_snapshot": """
        SELECT COUNT(*) FROM silver.inventory_inventory
    """,
    "fact_inventory_movements": """
        SELECT COUNT(*)
        FROM silver.inventory_inventory_movements
    """,
    "fact_supplier_deliveries": """
        SELECT COUNT(*)
        FROM silver.suppliers_deliveries
    """,
}


FINANCIAL_CHECKS = {
    "ecommerce_sales": (
        """
        SELECT COALESCE(SUM(line_total), 0)
        FROM silver.ecommerce_order_items oi
        JOIN silver.ecommerce_orders o
          ON o.order_id = oi.order_id
        """,
        """
        SELECT COALESCE(SUM(line_total), 0)
        FROM gold.fact_ecommerce_sales
        """,
    ),
    "pos_sales": (
        """
        SELECT COALESCE(SUM(total_amount), 0)
        FROM silver.pos_transactions
        """,
        """
        SELECT COALESCE(SUM(total_amount), 0)
        FROM gold.fact_pos_sales
        """,
    ),
    "payments": (
        """
        SELECT COALESCE(SUM(amount), 0)
        FROM silver.payments_payments
        """,
        """
        SELECT COALESCE(SUM(amount), 0)
        FROM gold.fact_payments
        """,
    ),
    "refunds": (
        """
        SELECT COALESCE(SUM(refund_amount), 0)
        FROM silver.returns_returns
        """,
        """
        SELECT COALESCE(SUM(refund_amount), 0)
        FROM gold.fact_returns
        """,
    ),
}


BUSINESS_KEYS = {
    "fact_ecommerce_sales": "order_item_id",
    "fact_pos_sales": "transaction_id",
    "fact_payments": "payment_id",
    "fact_returns": "return_id",
    "fact_inventory_movements": "movement_id",
    "fact_supplier_deliveries": "delivery_id",
}


DIMENSION_REFERENCES = {
    "fact_ecommerce_sales": (
        "customer_key",
        "product_key",
        "date_key",
        "channel_key",
    ),
    "fact_pos_sales": (
        "product_key",
        "store_key",
        "date_key",
        "channel_key",
    ),
    "fact_payments": ("date_key",),
    "fact_returns": (
        "customer_key",
        "product_key",
        "date_key",
    ),
    "fact_inventory_snapshot": (
        "snapshot_date_key",
        "product_key",
        "store_key",
    ),
    "fact_inventory_movements": (
        "product_key",
        "store_key",
        "date_key",
    ),
    "fact_supplier_deliveries": (
        "supplier_key",
        "product_key",
        "expected_date_key",
    ),
}


class ReconciliationAudit:
    def __init__(self):
        self.results = []
        self.metrics = {}

    def record(self, name, passed, details=None):
        result = {
            "check": name,
            "status": "PASS" if passed else "FAIL",
            "details": details or {},
        }

        self.results.append(result)

        print(
            f"{result['status']:4} | {name}",
            flush=True,
        )

    def scalar(self, connection, query, parameters=None):
        return connection.execute(
            text(query),
            parameters or {},
        ).scalar_one()

    def check_fact_counts(self, connection):
        print("\nFACT COUNT RECONCILIATION")
        print("-" * 50)

        counts = {}

        for table_name, source_query in FACT_SOURCES.items():
            expected = self.scalar(
                connection, source_query
            )

            actual = self.scalar(
                connection,
                f"SELECT COUNT(*) FROM gold.{table_name}",
            )

            counts[table_name] = {
                "silver": expected,
                "gold": actual,
                "difference": actual - expected,
            }

            self.record(
                f"{table_name}: source-to-target count",
                expected == actual,
                counts[table_name],
            )

        self.metrics["fact_counts"] = counts

    def check_financial_totals(self, connection):
        print("\nFINANCIAL RECONCILIATION")
        print("-" * 50)

        financial_results = {}

        for name, (source_sql, target_sql) in (
            FINANCIAL_CHECKS.items()
        ):
            source_total = self.scalar(
                connection, source_sql
            )

            target_total = self.scalar(
                connection, target_sql
            )

            source_total = Decimal(str(source_total))
            target_total = Decimal(str(target_total))

            difference = target_total - source_total

            financial_results[name] = {
                "silver_total": str(source_total),
                "gold_total": str(target_total),
                "difference": str(difference),
            }

            self.record(
                f"{name}: financial total",
                difference == Decimal("0"),
                financial_results[name],
            )

        self.metrics["financial_totals"] = (
            financial_results
        )

    def check_business_keys(self, connection):
        print("\nBUSINESS-KEY UNIQUENESS")
        print("-" * 50)

        for table_name, key_column in BUSINESS_KEYS.items():
            duplicates = self.scalar(
                connection,
                f"""
                SELECT COUNT(*)
                FROM (
                    SELECT {key_column}
                    FROM gold.{table_name}
                    GROUP BY {key_column}
                    HAVING COUNT(*) > 1
                ) duplicate_keys
                """,
            )

            self.record(
                f"{table_name}: unique business keys",
                duplicates == 0,
                {"duplicate_keys": duplicates},
            )

        snapshot_duplicates = self.scalar(
            connection,
            """
            SELECT COUNT(*)
            FROM (
                SELECT
                    snapshot_timestamp,
                    product_key,
                    store_key
                FROM gold.fact_inventory_snapshot
                GROUP BY
                    snapshot_timestamp,
                    product_key,
                    store_key
                HAVING COUNT(*) > 1
            ) duplicate_snapshots
            """,
        )

        self.record(
            "inventory snapshot: unique grain",
            snapshot_duplicates == 0,
            {"duplicate_grains": snapshot_duplicates},
        )

    def check_unknown_keys(self, connection):
        print("\nUNKNOWN DIMENSION REFERENCES")
        print("-" * 50)

        unknowns = {}

        for table_name, columns in (
            DIMENSION_REFERENCES.items()
        ):
            unknowns[table_name] = {}

            for column in columns:
                count = self.scalar(
                    connection,
                    f"""
                    SELECT COUNT(*)
                    FROM gold.{table_name}
                    WHERE {column} = 0
                    """,
                )

                unknowns[table_name][column] = count

                # Unknown members are valid references.
                # Report them for investigation rather
                # than automatically failing the audit.
                print(
                    f"INFO | {table_name}.{column}: "
                    f"{count:,} unknown references"
                )

        self.metrics["unknown_dimension_keys"] = (
            unknowns
        )

    def check_foreign_keys(self, connection):
        print("\nFOREIGN-KEY VALIDATION")
        print("-" * 50)

        violations = self.scalar(
            connection,
            """
            SELECT COUNT(*)
            FROM pg_constraint c
            JOIN pg_class t
              ON t.oid = c.conrelid
            JOIN pg_namespace n
              ON n.oid = t.relnamespace
            WHERE n.nspname = 'gold'
              AND c.contype = 'f'
              AND NOT c.convalidated
            """,
        )

        self.record(
            "Gold foreign-key constraints validated",
            violations == 0,
            {"unvalidated_constraints": violations},
        )

        self.record(
            "Gold foreign-key constraints present",
            self.scalar(
                connection,
                """
                SELECT COUNT(*)
                FROM pg_constraint c
                JOIN pg_class t
                  ON t.oid = c.conrelid
                JOIN pg_namespace n
                  ON n.oid = t.relnamespace
                WHERE n.nspname = 'gold'
                  AND c.contype = 'f'
                """,
            ) == 22,
        )

    def check_product_history(self, connection):
        print("\nPRODUCT SCD TYPE 2")
        print("-" * 50)

        duplicate_current = self.scalar(
            connection,
            """
            SELECT COUNT(*)
            FROM (
                SELECT product_id
                FROM gold.dim_product
                WHERE is_current = TRUE
                GROUP BY product_id
                HAVING COUNT(*) > 1
            ) duplicates
            """,
        )

        self.record(
            "No duplicate current product versions",
            duplicate_current == 0,
        )

        invalid_periods = self.scalar(
            connection,
            """
            SELECT COUNT(*)
            FROM gold.dim_product
            WHERE
                (
                    effective_to IS NOT NULL
                    AND effective_to <= effective_from
                )
                OR (
                    is_current
                    AND effective_to IS NOT NULL
                )
                OR (
                    NOT is_current
                    AND effective_to IS NULL
                )
            """,
        )

        self.record(
            "Product effective periods valid",
            invalid_periods == 0,
        )

        overlapping = self.scalar(
            connection,
            """
            SELECT COUNT(*)
            FROM gold.dim_product a
            JOIN gold.dim_product b
              ON a.product_id = b.product_id
             AND a.product_key < b.product_key
             AND tstzrange(
                 a.effective_from,
                 a.effective_to,
                 '[)'
             ) && tstzrange(
                 b.effective_from,
                 b.effective_to,
                 '[)'
             )
            """,
        )

        self.record(
            "No overlapping product history",
            overlapping == 0,
        )

    def check_quarantine(self, connection):
        print("\nQUARANTINE ACCOUNTING")
        print("-" * 50)

        quarantine_summary = {}

        for definition in list_transformations():
            table_name = definition.silver_table

            silver_count = self.scalar(
                connection,
                f"""
                SELECT COUNT(*)
                FROM silver.{table_name}
                """,
            )

            run_ids = connection.execute(
                text(
                    f"""
                    SELECT DISTINCT _pipeline_run_id
                    FROM silver.{table_name}
                    WHERE _pipeline_run_id IS NOT NULL
                    """
                )
            ).scalars().all()

            # Each full-snapshot Silver table should
            # contain records from one ingestion run.
            self.record(
                f"{table_name}: single source run",
                len(run_ids) == 1,
                {"run_count": len(run_ids)},
            )

            quarantine_count = 0

            if len(run_ids) == 1:
                quarantine_count = self.scalar(
                    connection,
                    """
                    SELECT COUNT(*)
                    FROM silver.quarantine_records
                    WHERE source_system = :source
                      AND dataset_name = :dataset
                      AND pipeline_run_id = :run_id
                    """,
                    {
                        "source": definition.source_system,
                        "dataset": definition.dataset_name,
                        "run_id": run_ids[0],
                    },
                )

            quarantine_summary[table_name] = {
                "silver_records": silver_count,
                "quarantined_records": quarantine_count,
                "accounted_records": (
                    silver_count + quarantine_count
                ),
            }

            self.record(
                f"{table_name}: quarantine accounting",
                (
                    len(run_ids) == 1
                    and silver_count + quarantine_count > 0
                ),
                quarantine_summary[table_name],
            )

        self.metrics["quarantine"] = quarantine_summary

        # This checks Silver/quarantine accounting.
        # Exact Bronze row-count reconciliation is
        # a separate validation in Phase 11.

    def check_pipeline_report(self):
        print("\nPIPELINE EXECUTION REPORT")
        print("-" * 50)

        report_files = list(
            PIPELINE_REPORT_DIRECTORY.glob("*.json")
        ) if PIPELINE_REPORT_DIRECTORY.exists() else []

        if not report_files:
            self.record(
                "Latest pipeline execution successful",
                False,
                {"reason": "No pipeline reports found"},
            )
            return

        latest = max(
            report_files,
            key=lambda path: path.stat().st_mtime_ns,
        )

        with latest.open("r", encoding="utf-8") as file:
            report = json.load(file)

        stages = report.get("stages", [])

        expected_stages = {
            "Bronze Ingestion",
            "Silver Transformation",
            "Gold Dimensions",
            "Gold Facts",
        }

        observed_stages = {
            stage.get("stage")
            for stage in stages
        }

        passed = (
            report.get("status") == "SUCCESS"
            and observed_stages == expected_stages
            and all(
                stage.get("status") == "SUCCESS"
                for stage in stages
            )
        )

        self.record(
            "Latest full pipeline execution successful",
            passed,
            {
                "pipeline_run_id": report.get(
                    "pipeline_run_id"
                ),
                "status": report.get("status"),
                "stages": sorted(observed_stages),
            },
        )

    def save(self):
        REPORT_DIRECTORY.mkdir(
            parents=True,
            exist_ok=True,
        )

        passed = sum(
            result["status"] == "PASS"
            for result in self.results
        )

        failed = len(self.results) - passed

        report = {
            "audit_id": str(uuid.uuid4()),
            "audit_name": "phase8_reconciliation",
            "created_at": datetime.now(
                timezone.utc
            ).isoformat(),
            "status": "PASS" if failed == 0 else "FAIL",
            "checks_executed": len(self.results),
            "checks_passed": passed,
            "checks_failed": failed,
            "results": self.results,
            "metrics": self.metrics,
        }

        path = REPORT_DIRECTORY / (
            f"phase8_{report['audit_id']}.json"
        )

        with path.open("w", encoding="utf-8") as file:
            json.dump(
                report,
                file,
                indent=2,
                default=str,
            )

        return report, path


def main():
    audit = ReconciliationAudit()

    print("=" * 60)
    print("RETAILFLOW PHASE 8 RECONCILIATION AUDIT")
    print("=" * 60)

    engine = create_warehouse_engine()

    try:
        with engine.connect() as connection:
            audit.check_fact_counts(connection)
            audit.check_financial_totals(connection)
            audit.check_business_keys(connection)
            audit.check_unknown_keys(connection)
            audit.check_foreign_keys(connection)
            audit.check_product_history(connection)
            audit.check_quarantine(connection)

        audit.check_pipeline_report()

    finally:
        engine.dispose()

    report, path = audit.save()

    print()
    print("=" * 60)
    print("PHASE 8 AUDIT SUMMARY")
    print("=" * 60)

    print(
        f"Checks executed: {report['checks_executed']}"
    )
    print(
        f"Checks passed: {report['checks_passed']}"
    )
    print(
        f"Checks failed: {report['checks_failed']}"
    )

    print()
    print(
        f"PHASE 8 AUDIT RESULT: {report['status']}"
    )
    print(f"Report saved: {path}")

    if report["status"] != "PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
