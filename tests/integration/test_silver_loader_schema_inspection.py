"""Inspect the isolated test database's Silver customer table."""

def test_inspect_silver_customer_schema(db_connection):
    with db_connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT
                column_name,
                data_type,
                is_nullable,
                column_default
            FROM information_schema.columns
            WHERE table_schema = 'silver'
              AND table_name = 'ecommerce_customers'
            ORDER BY ordinal_position
            """
        )

        columns = cursor.fetchall()

    assert columns, "silver.ecommerce_customers table not found"

    print("\n=== SILVER ECOMMERCE CUSTOMERS COLUMNS ===")

    for name, data_type, nullable, default in columns:
        print(
            f"{name} | {data_type} | "
            f"nullable={nullable} | default={default}"
        )

    print(f"\nTotal columns: {len(columns)}")