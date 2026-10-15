
import os

from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL

from src.config.source_registry import SOURCE_REGISTRY
from src.warehouse.connection import create_warehouse_engine


# ============================================================
# RetailFlow
# Phase 6: Analytical Warehouse Foundation Audit
# ============================================================

load_dotenv()

EXPECTED_SCHEMAS = {
    "staging",
    "silver",
    "gold",
    "audit",
    "metadata",
}

EXPECTED_TABLES = {
    ("metadata", "pipeline_runs"),
    ("metadata", "pipeline_watermarks"),
    ("metadata", "dataset_registry"),
    ("audit", "data_quality_results"),
    ("audit", "reconciliation_results"),
    ("audit", "pipeline_errors"),
}

EXPECTED_DATASETS = {
    (source, dataset)
    for source, definition in SOURCE_REGISTRY.items()
    for dataset in definition.datasets
}

failures = []


def check(condition, description):
    status = "PASS" if condition else "FAIL"
    print(f"{status} | {description}")

    if not condition:
        failures.append(description)


def create_role_engine(username, password):
    url = URL.create(
        "postgresql+psycopg2",
        username=username,
        password=password,
        host=os.getenv(
            "WAREHOUSE_POSTGRES_HOST", "localhost"
        ),
        port=int(
            os.getenv("WAREHOUSE_POSTGRES_PORT", "5433")
        ),
        database=os.getenv("WAREHOUSE_POSTGRES_DB"),
    )

    return create_engine(
        url,
        pool_pre_ping=True,
        connect_args={"connect_timeout": 10},
    )


def test_constraint(connection):
    """
    Test that invalid pipeline status values are rejected.

    A SAVEPOINT ensures the failed INSERT does not
    invalidate the surrounding transaction.
    """

    nested = connection.begin_nested()

    try:
        connection.execute(
            text(
                """
                INSERT INTO metadata.pipeline_runs (
                    pipeline_run_id,
                    pipeline_name,
                    status
                )
                VALUES (
                    '00000000-0000-0000-0000-000000000001',
                    'constraint_validation',
                    'INVALID_STATUS'
                )
                """
            )
        )

        nested.rollback()
        return False

    except Exception:
        nested.rollback()
        return True


def main():
    print("RetailFlow Phase 6 Warehouse Audit")
    print("==================================")

    engine = create_warehouse_engine()

    try:
        with engine.connect() as connection:

            # ----------------------------------------
            # Database identity
            # ----------------------------------------

            database_name = connection.execute(
                text("SELECT current_database()")
            ).scalar_one()

            check(
                database_name == "retailflow_warehouse",
                "Connected to analytical warehouse",
            )

            # ----------------------------------------
            # Schemas
            # ----------------------------------------

            schemas = set(
                connection.execute(
                    text(
                        """
                        SELECT schema_name
                        FROM information_schema.schemata
                        WHERE schema_name IN (
                            'staging',
                            'silver',
                            'gold',
                            'audit',
                            'metadata'
                        )
                        """
                    )
                ).scalars()
            )

            check(
                schemas == EXPECTED_SCHEMAS,
                "All five warehouse schemas exist",
            )

            # ----------------------------------------
            # Foundation tables
            # ----------------------------------------

            tables = set(
                connection.execute(
                    text(
                        """
                        SELECT table_schema, table_name
                        FROM information_schema.tables
                        WHERE table_schema IN (
                            'metadata', 'audit'
                        )
                        AND table_type = 'BASE TABLE'
                        """
                    )
                ).all()
            )

            check(
                EXPECTED_TABLES.issubset(tables),
                "All six foundation tables exist",
            )

            # ----------------------------------------
            # Dataset registry
            # ----------------------------------------

            datasets = set(
                connection.execute(
                    text(
                        """
                        SELECT source_system, dataset_name
                        FROM metadata.dataset_registry
                        """
                    )
                ).all()
            )

            check(
                datasets == EXPECTED_DATASETS,
                "Warehouse registry matches Python registry",
            )

            check(
                len(datasets) == 12,
                "Exactly twelve datasets registered",
            )

            source_count = connection.execute(
                text(
                    """
                    SELECT COUNT(DISTINCT source_system)
                    FROM metadata.dataset_registry
                    """
                )
            ).scalar_one()

            check(
                source_count == 7,
                "All seven source systems represented",
            )

            # ----------------------------------------
            # Primary key constraints
            # ----------------------------------------

            primary_keys = set(
                connection.execute(
                    text(
                        """
                        SELECT
                            n.nspname,
                            c.relname
                        FROM pg_constraint con
                        JOIN pg_class c
                            ON c.oid = con.conrelid
                        JOIN pg_namespace n
                            ON n.oid = c.relnamespace
                        WHERE con.contype = 'p'
                          AND n.nspname IN (
                              'metadata', 'audit'
                          )
                        """
                    )
                ).all()
            )

            check(
                EXPECTED_TABLES.issubset(primary_keys),
                "All foundation tables have primary keys",
            )

            # ----------------------------------------
            # Role privileges
            # ----------------------------------------

            permissions = connection.execute(
                text(
                    """
                    SELECT
                        has_schema_privilege(
                            'retailflow_etl_user',
                            'staging',
                            'USAGE'
                        ) AS etl_staging,
                        has_schema_privilege(
                            'retailflow_etl_user',
                            'silver',
                            'USAGE'
                        ) AS etl_silver,
                        has_schema_privilege(
                            'retailflow_analytics_user',
                            'gold',
                            'USAGE'
                        ) AS analytics_gold,
                        has_schema_privilege(
                            'retailflow_analytics_user',
                            'silver',
                            'USAGE'
                        ) AS analytics_silver,
                        has_schema_privilege(
                            'retailflow_analytics_user',
                            'metadata',
                            'USAGE'
                        ) AS analytics_metadata,
                        has_schema_privilege(
                            'retailflow_analytics_user',
                            'gold',
                            'CREATE'
                        ) AS analytics_create
                    """
                )
            ).mappings().one()

            check(
                permissions["etl_staging"]
                and permissions["etl_silver"],
                "ETL role can access staging and silver",
            )

            check(
                permissions["analytics_gold"],
                "Analytics role can access gold",
            )

            check(
                not permissions["analytics_silver"]
                and not permissions["analytics_metadata"]
                and not permissions["analytics_create"],
                "Analytics role has restricted privileges",
            )

        # --------------------------------------------
        # Constraint validation
        # --------------------------------------------

        with engine.connect() as connection:
            check(
                test_constraint(connection),
                "Invalid pipeline status is rejected",
            )

    finally:
        engine.dispose()

    # ------------------------------------------------
    # Actual analytics login test
    # ------------------------------------------------

    analytics_user = os.getenv(
        "WAREHOUSE_ANALYTICS_USER"
    )
    analytics_password = os.getenv(
        "WAREHOUSE_ANALYTICS_PASSWORD"
    )

    if not analytics_user or not analytics_password:
        check(
            False,
            "Analytics login credentials configured",
        )
    else:
        analytics_engine = create_role_engine(
            analytics_user,
            analytics_password,
        )

        try:
            with analytics_engine.connect() as connection:
                current_user = connection.execute(
                    text("SELECT current_user")
                ).scalar_one()

                check(
                    current_user == analytics_user,
                    "Analytics account authenticates",
                )

                # USAGE on Gold should allow schema
                # visibility even before Gold tables exist.
                check(
                    connection.execute(
                        text(
                            """
                            SELECT has_schema_privilege(
                                current_user,
                                'gold',
                                'USAGE'
                            )
                            """
                        )
                    ).scalar_one(),
                    "Analytics login has Gold schema access",
                )

        except Exception as error:
            check(
                False,
                f"Analytics login test: {error}",
            )

        finally:
            analytics_engine.dispose()

    # ------------------------------------------------
    # Final result
    # ------------------------------------------------

    print()
    print("Phase 6 Audit Summary")
    print("---------------------")
    print(f"Checks failed: {len(failures)}")

    if failures:
        print()
        print("PHASE 6 AUDIT RESULT: FAIL")
        raise SystemExit(1)

    print()
    print("PHASE 6 AUDIT RESULT: PASS")
    print("RetailFlow warehouse foundation validated.")


if __name__ == "__main__":
    main()
