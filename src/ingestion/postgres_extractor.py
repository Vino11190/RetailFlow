import os

import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine


# ============================================================
# RetailFlow
# PostgreSQL Source Extractor
# ============================================================


load_dotenv()


def create_postgres_engine(
    database_name: str,
) -> Engine:
    """
    Create a SQLAlchemy connection engine
    for a RetailFlow PostgreSQL source database.
    """

    username = os.getenv("POSTGRES_USER")
    password = os.getenv("POSTGRES_PASSWORD")

    host = os.getenv(
        "POSTGRES_HOST",
        "localhost",
    )

    port = os.getenv(
        "POSTGRES_PORT",
        "5432",
    )

    if not username or not password:
        raise ValueError(
            "PostgreSQL credentials are missing "
            "from the environment."
        )

    connection_url = (
        f"postgresql+psycopg2://"
        f"{username}:{password}"
        f"@{host}:{port}/"
        f"{database_name}"
    )

    return create_engine(
        connection_url,
        pool_pre_ping=True,
    )


def extract_table(
    engine: Engine,
    table_name: str,
) -> pd.DataFrame:
    """
    Extract an entire source table
    into a pandas DataFrame.

    Full extraction is intentional at this stage.
    Incremental extraction will be introduced later.
    """

    query = (
        f'SELECT * FROM "{table_name}"'
    )

    dataframe = pd.read_sql(
        query,
        engine,
    )

    return dataframe