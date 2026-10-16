"""Verify PostgreSQL rollback protects an existing Silver snapshot."""

import psycopg2
from psycopg2 import errors


def test_failed_snapshot_replacement_preserves_existing_records(
    db_connection,
):
    # Create a temporary Silver-like table in the isolated test DB.
    with db_connection.cursor() as cursor:
        cursor.execute("""
            CREATE TEMP TABLE retailflow_silver_snapshot_test (
                customer_id INTEGER PRIMARY KEY,
                customer_name TEXT NOT NULL
            ) ON COMMIT PRESERVE ROWS
        """)

        cursor.execute("""
            INSERT INTO retailflow_silver_snapshot_test
                (customer_id, customer_name)
            VALUES
                (1, 'Original Customer'),
                (2, 'Existing Customer')
        """)

    # Establish the original snapshot as committed.
    db_connection.commit()

    try:
        with db_connection.cursor() as cursor:
            # Simulate the Silver loader replacing a snapshot.
            cursor.execute("""
                DELETE FROM retailflow_silver_snapshot_test
            """)

            cursor.execute("""
                INSERT INTO retailflow_silver_snapshot_test
                    (customer_id, customer_name)
                VALUES (3, 'New Customer')
            """)

            # Deliberately violate the primary-key constraint.
            cursor.execute("""
                INSERT INTO retailflow_silver_snapshot_test
                    (customer_id, customer_name)
                VALUES (3, 'Duplicate Customer')
            """)

        raise AssertionError(
            "Expected PostgreSQL to reject the duplicate key"
        )

    except errors.UniqueViolation:
        db_connection.rollback()

    # Verify the previously committed snapshot is unchanged.
    with db_connection.cursor() as cursor:
        cursor.execute("""
            SELECT customer_id, customer_name
            FROM retailflow_silver_snapshot_test
            ORDER BY customer_id
        """)

        records = cursor.fetchall()

    assert records == [
        (1, "Original Customer"),
        (2, "Existing Customer"),
    ]

    # Remove the temporary table explicitly.
    db_connection.rollback()

    with db_connection.cursor() as cursor:
        cursor.execute("""
            DROP TABLE IF EXISTS retailflow_silver_snapshot_test
        """)

    db_connection.commit()