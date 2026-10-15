
"""
RetailFlow Gold Fact Loader.

Loads seven fact tables from the Silver warehouse.

Strategy:
- Transactional full-snapshot replacement
- Deterministic dimension lookups
- Unknown dimension fallback (key 0)
- Source business-key preservation
- Record-count reconciliation

Important:
Historical transactions currently resolve products
to their current observed dimension version.
True event-time SCD2 resolution is deferred until
historical product change data is available.
"""

from sqlalchemy import text

from src.warehouse.connection import create_warehouse_engine


FACT_LOADS = {
    "fact_ecommerce_sales": """
        SELECT
            oi.order_item_id,
            oi.order_id,
            COALESCE(dc.customer_key, 0) AS customer_key,
            COALESCE(dp.product_key, 0) AS product_key,
            COALESCE(dd.date_key, 0) AS date_key,
            COALESCE(ch.channel_key, 0) AS channel_key,
            o.order_timestamp,
            o.status AS order_status,
            o.currency,
            oi.quantity,
            oi.unit_price,
            oi.discount,
            oi.line_total
        FROM silver.ecommerce_order_items oi
        JOIN silver.ecommerce_orders o
          ON o.order_id = oi.order_id
        LEFT JOIN gold.dim_customer dc
          ON dc.customer_id = o.customer_id
        LEFT JOIN gold.dim_product dp
          ON dp.product_id = oi.product_id
         AND dp.is_current = TRUE
        LEFT JOIN gold.dim_date dd
          ON dd.full_date = (o.order_timestamp AT TIME ZONE 'UTC')::date
        LEFT JOIN gold.dim_channel ch
          ON ch.channel_name = o.channel
    """,

    "fact_pos_sales": """
        SELECT
            p.transaction_id,
            COALESCE(dp.product_key, 0) AS product_key,
            COALESCE(ds.store_key, 0) AS store_key,
            COALESCE(dd.date_key, 0) AS date_key,
            COALESCE(ch.channel_key, 0) AS channel_key,
            p.transaction_timestamp,
            p.payment_method,
            p.quantity,
            p.unit_price,
            p.discount,
            p.total_amount
        FROM silver.pos_transactions p
        LEFT JOIN gold.dim_product dp
          ON dp.product_id = p.product_id
         AND dp.is_current = TRUE
        LEFT JOIN gold.dim_store ds
          ON ds.store_id = p.store_id
        LEFT JOIN gold.dim_date dd
          ON dd.full_date = (
              p.transaction_timestamp AT TIME ZONE 'UTC'
          )::date
        LEFT JOIN gold.dim_channel ch
          ON ch.channel_name = 'POS'
    """,

    "fact_payments": """
        SELECT
            p.payment_id,
            p.order_id,
            COALESCE(dd.date_key, 0) AS date_key,
            p.payment_timestamp,
            p.amount,
            p.currency,
            p.status,
            p.payment_method
        FROM silver.payments_payments p
        LEFT JOIN gold.dim_date dd
          ON dd.full_date = (
              p.payment_timestamp AT TIME ZONE 'UTC'
          )::date
    """,

    "fact_returns": """
        SELECT
            r.return_id,
            r.order_id,
            COALESCE(dc.customer_key, 0) AS customer_key,
            COALESCE(dp.product_key, 0) AS product_key,
            COALESCE(dd.date_key, 0) AS date_key,
            r.quantity,
            r.reason,
            r.refund_amount
        FROM silver.returns_returns r
        LEFT JOIN gold.dim_customer dc
          ON dc.customer_id = r.customer_id
        LEFT JOIN gold.dim_product dp
          ON dp.product_id = r.product_id
         AND dp.is_current = TRUE
        LEFT JOIN gold.dim_date dd
          ON dd.full_date = r.return_date
    """,

    "fact_inventory_snapshot": """
        SELECT
            CURRENT_TIMESTAMP AS snapshot_timestamp,
            COALESCE(dd.date_key, 0) AS snapshot_date_key,
            COALESCE(dp.product_key, 0) AS product_key,
            COALESCE(ds.store_key, 0) AS store_key,
            i.quantity_on_hand,
            i.reorder_level
        FROM silver.inventory_inventory i
        LEFT JOIN gold.dim_product dp
          ON dp.product_id = i.product_id
         AND dp.is_current = TRUE
        LEFT JOIN gold.dim_store ds
          ON ds.store_id = i.store_id
        LEFT JOIN gold.dim_date dd
          ON dd.full_date = (
              CURRENT_TIMESTAMP AT TIME ZONE 'UTC'
          )::date
    """,

    "fact_inventory_movements": """
        SELECT
            m.movement_id,
            COALESCE(dp.product_key, 0) AS product_key,
            COALESCE(ds.store_key, 0) AS store_key,
            COALESCE(dd.date_key, 0) AS date_key,
            m.movement_timestamp,
            m.movement_type,
            m.quantity
        FROM silver.inventory_inventory_movements m
        LEFT JOIN gold.dim_product dp
          ON dp.product_id = m.product_id
         AND dp.is_current = TRUE
        LEFT JOIN gold.dim_store ds
          ON ds.store_id = m.store_id
        LEFT JOIN gold.dim_date dd
          ON dd.full_date = (
              m.movement_timestamp AT TIME ZONE 'UTC'
          )::date
    """,

    "fact_supplier_deliveries": """
        SELECT
            d.delivery_id,
            COALESCE(ds.supplier_key, 0) AS supplier_key,
            COALESCE(dp.product_key, 0) AS product_key,
            COALESCE(de.date_key, 0) AS expected_date_key,
            CASE
                WHEN d.actual_date IS NULL THEN NULL
                ELSE COALESCE(da.date_key, 0)
            END AS actual_date_key,
            d.quantity,
            d.status AS delivery_status,
            CASE
                WHEN d.actual_date IS NULL
                  OR d.expected_date IS NULL
                THEN NULL
                ELSE d.actual_date - d.expected_date
            END AS delivery_delay_days
        FROM silver.suppliers_deliveries d
        LEFT JOIN gold.dim_supplier ds
          ON ds.supplier_id = d.supplier_id
        LEFT JOIN gold.dim_product dp
          ON dp.product_id = d.product_id
         AND dp.is_current = TRUE
        LEFT JOIN gold.dim_date de
          ON de.full_date = d.expected_date
        LEFT JOIN gold.dim_date da
          ON da.full_date = d.actual_date
    """,
}


FACT_COLUMNS = {
    "fact_ecommerce_sales": [
        "order_item_id", "order_id",
        "customer_key", "product_key",
        "date_key", "channel_key",
        "order_timestamp", "order_status",
        "currency", "quantity", "unit_price",
        "discount", "line_total",
    ],
    "fact_pos_sales": [
        "transaction_id", "product_key",
        "store_key", "date_key", "channel_key",
        "transaction_timestamp", "payment_method",
        "quantity", "unit_price", "discount",
        "total_amount",
    ],
    "fact_payments": [
        "payment_id", "order_id", "date_key",
        "payment_timestamp", "amount", "currency",
        "status", "payment_method",
    ],
    "fact_returns": [
        "return_id", "order_id",
        "customer_key", "product_key", "date_key",
        "quantity", "reason", "refund_amount",
    ],
    "fact_inventory_snapshot": [
        "snapshot_timestamp", "snapshot_date_key",
        "product_key", "store_key",
        "quantity_on_hand", "reorder_level",
    ],
    "fact_inventory_movements": [
        "movement_id", "product_key", "store_key",
        "date_key", "movement_timestamp",
        "movement_type", "quantity",
    ],
    "fact_supplier_deliveries": [
        "delivery_id", "supplier_key",
        "product_key", "expected_date_key",
        "actual_date_key", "quantity",
        "delivery_status", "delivery_delay_days",
    ],
}


EXPECTED_SOURCE_COUNTS = {
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


def load_fact(connection, table_name):
    if table_name not in FACT_LOADS:
        raise ValueError(
            f"Unknown fact table: {table_name}"
        )

    columns = FACT_COLUMNS[table_name]
    column_sql = ", ".join(
        f'"{column}"' for column in columns
    )

    source_count = connection.execute(
        text(EXPECTED_SOURCE_COUNTS[table_name])
    ).scalar_one()

    # Materialise the transformed source first.
    # This allows validation before replacing
    # the currently committed fact snapshot.
    temp_table = f"tmp_{table_name}"

    connection.execute(
        text(
            f"""
            CREATE TEMP TABLE {temp_table}
            (LIKE gold.{table_name}
             INCLUDING DEFAULTS
             INCLUDING IDENTITY
             INCLUDING CONSTRAINTS
             INCLUDING INDEXES)
            ON COMMIT DROP
            """
        )
    )

    connection.execute(
        text(
            f"""
            INSERT INTO {temp_table} ({column_sql})
            {FACT_LOADS[table_name]}
            """
        )
    )

    staged_count = connection.execute(
        text(
            f"SELECT COUNT(*) FROM {temp_table}"
        )
    ).scalar_one()

    if staged_count != source_count:
        raise RuntimeError(
            f"{table_name}: expected {source_count:,} "
            f"rows, staged {staged_count:,}"
        )

    # Transactional replacement.
    connection.execute(
        text(f"DELETE FROM gold.{table_name}")
    )

    connection.execute(
        text(
            f"""
            INSERT INTO gold.{table_name} ({column_sql})
            SELECT {column_sql}
            FROM {temp_table}
            """
        )
    )

    final_count = connection.execute(
        text(
            f"SELECT COUNT(*) FROM gold.{table_name}"
        )
    ).scalar_one()

    if final_count != source_count:
        raise RuntimeError(
            f"{table_name}: reconciliation failed"
        )

    return final_count


def load_all_facts():
    engine = create_warehouse_engine()

    try:
        with engine.begin() as connection:
            # Prevent concurrent full fact loads.
            connection.execute(
                text(
                    "SELECT pg_advisory_xact_lock(8106)"
                )
            )

            results = {}

            for table_name in FACT_LOADS:
                count = load_fact(
                    connection,
                    table_name,
                )

                results[table_name] = count

        print("RetailFlow Gold Fact Load")
        print("=" * 45)

        for table_name, count in results.items():
            print(
                f"PASS | gold.{table_name}: "
                f"{count:,} rows"
            )

        print()
        print(
            f"Total fact rows: {sum(results.values()):,}"
        )
        print("GOLD FACT LOAD RESULT: PASS")

    finally:
        engine.dispose()


if __name__ == "__main__":
    load_all_facts()
