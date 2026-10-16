def test_database_connection(db_connection):
    """Verify the connection targets the isolated test database."""
    with db_connection.cursor() as cursor:
        cursor.execute(
            "SELECT current_database(), current_user, "
            "current_setting('server_version_num')"
        )
        database, username, version = cursor.fetchone()

    assert database == "retailflow_integration_test"
    assert username == "retailflow_test"
    assert int(version) >= 170000


def test_warehouse_schemas(db_connection):
    """Verify all required RetailFlow schemas exist."""
    expected = {"staging", "silver", "gold", "audit", "metadata"}

    with db_connection.cursor() as cursor:
        cursor.execute("""
            SELECT schema_name
            FROM information_schema.schemata
            WHERE schema_name = ANY(%s)
        """, (list(expected),))

        actual = {row[0] for row in cursor.fetchall()}

    assert actual == expected


def test_warehouse_table_counts(db_connection):
    """Verify the expected number of tables in each layer."""
    expected = {
        "metadata": 3,
        "audit": 3,
        "gold": 13,
        "silver": 13,
    }

    with db_connection.cursor() as cursor:
        cursor.execute("""
            SELECT table_schema, COUNT(*)
            FROM information_schema.tables
            WHERE table_schema = ANY(%s)
              AND table_type = 'BASE TABLE'
            GROUP BY table_schema
        """, (list(expected),))

        actual = dict(cursor.fetchall())

    assert actual == expected


def test_critical_warehouse_tables(db_connection):
    """Verify essential RetailFlow tables exist."""
    expected = {
        ("metadata", "pipeline_runs"),
        ("metadata", "pipeline_watermarks"),
        ("audit", "data_quality_results"),
        ("silver", "ecommerce_orders"),
        ("silver", "quarantine_records"),
        ("gold", "dim_product"),
        ("gold", "dim_customer"),
        ("gold", "fact_ecommerce_sales"),
        ("gold", "fact_inventory_snapshot"),
    }

    with db_connection.cursor() as cursor:
        cursor.execute("""
            SELECT table_schema, table_name
            FROM information_schema.tables
            WHERE table_schema IN (
                'metadata', 'audit', 'silver', 'gold'
            )
              AND table_type = 'BASE TABLE'
        """)

        actual = set(cursor.fetchall())

    assert expected.issubset(actual)
