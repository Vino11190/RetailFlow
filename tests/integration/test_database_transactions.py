def test_insert_update_and_rollback(db_connection):
    """Verify inserts, updates, and transaction rollback."""

    with db_connection.cursor() as cursor:
        cursor.execute("""
            CREATE TEMP TABLE retailflow_transaction_test (
                id INTEGER PRIMARY KEY,
                status TEXT NOT NULL
            ) ON COMMIT DROP
        """)

        cursor.execute("""
            INSERT INTO retailflow_transaction_test (id, status)
            VALUES (1, 'pending')
        """)

        cursor.execute("""
            SELECT status
            FROM retailflow_transaction_test
            WHERE id = 1
        """)
        assert cursor.fetchone()[0] == "pending"

        cursor.execute("""
            UPDATE retailflow_transaction_test
            SET status = 'completed'
            WHERE id = 1
        """)

        cursor.execute("""
            SELECT status
            FROM retailflow_transaction_test
            WHERE id = 1
        """)
        assert cursor.fetchone()[0] == "completed"

    db_connection.rollback()

    with db_connection.cursor() as cursor:
        cursor.execute("""
            SELECT to_regclass('pg_temp.retailflow_transaction_test')
        """)
        assert cursor.fetchone()[0] is None


def test_transaction_atomicity(db_connection):
    """Verify a failed statement can roll back an entire transaction."""

    with db_connection.cursor() as cursor:
        cursor.execute("""
            CREATE TEMP TABLE retailflow_atomicity_test (
                id INTEGER PRIMARY KEY,
                amount NUMERIC NOT NULL CHECK (amount >= 0)
            ) ON COMMIT DROP
        """)

        cursor.execute("""
            INSERT INTO retailflow_atomicity_test (id, amount)
            VALUES (1, 100)
        """)

        cursor.execute("SAVEPOINT before_invalid_insert")

        try:
            cursor.execute("""
                INSERT INTO retailflow_atomicity_test (id, amount)
                VALUES (2, -50)
            """)
            assert False, "Expected PostgreSQL to reject negative amount"
        except Exception as exc:
            import psycopg2
            assert isinstance(exc, psycopg2.errors.CheckViolation)
            cursor.execute("ROLLBACK TO SAVEPOINT before_invalid_insert")

        cursor.execute("""
            SELECT COUNT(*)
            FROM retailflow_atomicity_test
        """)
        assert cursor.fetchone()[0] == 1

    db_connection.rollback()

    with db_connection.cursor() as cursor:
        cursor.execute("""
            SELECT to_regclass('pg_temp.retailflow_atomicity_test')
        """)
        assert cursor.fetchone()[0] is None
