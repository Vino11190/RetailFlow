"""Test Silver temporary-table staging against isolated PostgreSQL."""

import os
from uuid import uuid4

import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL


def test_silver_staging_with_pandas(db_connection):
    parameters = db_connection.get_dsn_parameters()

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

    # Use a unique temporary table, never the real Silver table.
    temporary_table = f"tmp_retailflow_{uuid4().hex[:12]}"

    customers = pd.DataFrame(
        {
            "customer_id": ["TEST-001", "TEST-002"],
            "first_name": ["Alice", "Bob"],
            "email": [
                "alice@example.com",
                "bob@example.com",
            ],
        }
    )

    try:
        with engine.begin() as connection:
            connection.execute(
                text(
                    f"""
                    CREATE TEMP TABLE {temporary_table}
                    (LIKE silver.ecommerce_customers
                     INCLUDING DEFAULTS
                     INCLUDING CONSTRAINTS
                     INCLUDING INDEXES)
                    ON COMMIT DROP
                    """
                )
            )

            customers.to_sql(
                temporary_table,
                con=connection,
                if_exists="append",
                index=False,
                method="multi",
            )

            staged_count = connection.execute(
                text(f"SELECT COUNT(*) FROM {temporary_table}")
            ).scalar_one()

            assert staged_count == 2

            print(
                f"\nSilver staging verified: {staged_count} records"
            )

        # PostgreSQL should drop the temporary table on commit.
        with engine.connect() as connection:
            remaining = connection.execute(
                text(
                    "SELECT to_regclass(:table_name)"
                ),
                {"table_name": f"pg_temp.{temporary_table}"},
            ).scalar_one()

            assert remaining is None

    finally:
        engine.dispose()