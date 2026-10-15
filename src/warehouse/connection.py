
import os

import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.engine import URL


# ============================================================
# RetailFlow
# PostgreSQL Analytical Warehouse Connection
# ============================================================

load_dotenv()


def create_warehouse_engine() -> Engine:
    """
    Create a SQLAlchemy engine for the analytical warehouse.

    Connection settings are loaded from environment variables.
    """

    username = os.getenv("WAREHOUSE_POSTGRES_USER")
    password = os.getenv("WAREHOUSE_POSTGRES_PASSWORD")
    database = os.getenv("WAREHOUSE_POSTGRES_DB")

    host = os.getenv("WAREHOUSE_POSTGRES_HOST", "localhost")
    port = int(os.getenv("WAREHOUSE_POSTGRES_PORT", "5433"))

    if not all([username, password, database]):
        raise ValueError(
            "Missing warehouse database configuration. "
            "Check your .env file."
        )

    database_url = URL.create(
        drivername="postgresql+psycopg2",
        username=username,
        password=password,
        host=host,
        port=port,
        database=database,
    )

    engine = create_engine(
        database_url,
        pool_pre_ping=True,
        pool_size=5,
        max_overflow=10,
        pool_timeout=30,
        connect_args={
            "connect_timeout": 10,
        },
    )

    return engine


def test_warehouse_connection() -> dict:
    """
    Test the warehouse connection and return database details.
    """

    engine = create_warehouse_engine()

    try:
        with engine.connect() as connection:
            result = connection.execute(
                text(
                    """
                    SELECT
                        current_database() AS database_name,
                        current_user AS database_user,
                        current_schema() AS default_schema,
                        version() AS postgres_version
                    """
                )
            )

            row = result.mappings().one()

            return dict(row)

    finally:
        engine.dispose()


def execute_warehouse_query(
    query: str,
    parameters: dict | None = None,
) -> pd.DataFrame:
    """
    Execute a read-only SQL query and return a DataFrame.

    Use this helper for SELECT queries and validation.
    Warehouse writes will use explicit transactions later.
    """

    engine = create_warehouse_engine()

    try:
        with engine.connect() as connection:
            return pd.read_sql_query(
                sql=text(query),
                con=connection,
                params=parameters,
            )

    finally:
        engine.dispose()
