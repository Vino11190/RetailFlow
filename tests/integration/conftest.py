import os

import psycopg2
import pytest


TEST_DATABASE = "retailflow_integration_test"
TEST_USER = "retailflow_test"


@pytest.fixture
def db_connection():
    """Connect only to the dedicated RetailFlow integration database."""

    host = os.getenv("RETAILFLOW_TEST_DB_HOST", "127.0.0.1")
    port = int(os.getenv("RETAILFLOW_TEST_DB_PORT", "5434"))
    database = os.getenv("RETAILFLOW_TEST_DB_NAME", TEST_DATABASE)
    user = os.getenv("RETAILFLOW_TEST_DB_USER", TEST_USER)
    password = os.getenv(
        "RETAILFLOW_TEST_DB_PASSWORD",
        "retailflow_test_local_only",
    )

    ci_environment = os.getenv("GITHUB_ACTIONS") == "true"

    expected_port = 5432 if ci_environment else 5434

    if (
        host not in ("127.0.0.1", "localhost")
        or port != expected_port
        or database != TEST_DATABASE
        or user != TEST_USER
    ):
        pytest.fail(
            "Unsafe integration database configuration. "
            "Connection must target the dedicated test database."
        )

    connection = psycopg2.connect(
        host=host,
        port=port,
        dbname=database,
        user=user,
        password=password,
        connect_timeout=5,
    )

    try:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT current_database(), current_user"
            )
            actual_database, actual_user = cursor.fetchone()

        if (
            actual_database != TEST_DATABASE
            or actual_user != TEST_USER
        ):
            pytest.fail(
                "Connected to an unexpected PostgreSQL database."
            )

        yield connection

    finally:
        connection.rollback()
        connection.close()
