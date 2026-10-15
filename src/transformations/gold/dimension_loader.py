
"""
RetailFlow Gold Dimension Loader.

Loads six shared analytical dimensions from Silver.

Strategies:
- Customer: Type 1
- Product: Type 2
- Date: deterministic calendar keys
- Store: Type 1
- Supplier: Type 1
- Channel: Type 1

Uses a single transaction for the dimension load.
"""

import hashlib
import json
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import text

from src.warehouse.connection import create_warehouse_engine


PRODUCT_ATTRIBUTES = (
    "sku",
    "product_name",
    "category_id",
    "category_name",
    "brand",
    "unit_price",
    "currency",
    "active",
)


def scalar(connection, sql):
    return connection.execute(text(sql)).scalar_one()


def canonical_value(value):
    if isinstance(value, Decimal):
        return str(value.quantize(Decimal("0.01")))

    if isinstance(value, (date, datetime)):
        return value.isoformat()

    return value


def product_hash(product):
    payload = {
        column: canonical_value(product[column])
        for column in PRODUCT_ATTRIBUTES
    }

    encoded = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    ).encode("utf-8")

    return hashlib.sha256(encoded).hexdigest()


def load_customers(connection):
    connection.execute(
        text(
            """
            INSERT INTO gold.dim_customer (
                customer_id,
                city,
                postcode,
                country,
                created_at,
                updated_at
            )
            SELECT
                customer_id,
                city,
                postcode,
                country,
                created_at,
                updated_at
            FROM silver.ecommerce_customers
            ON CONFLICT (customer_id)
            DO UPDATE SET
                city = EXCLUDED.city,
                postcode = EXCLUDED.postcode,
                country = EXCLUDED.country,
                created_at = EXCLUDED.created_at,
                updated_at = EXCLUDED.updated_at
            """
        )
    )


def load_stores(connection):
    connection.execute(
        text(
            """
            INSERT INTO gold.dim_store (store_id)
            SELECT DISTINCT store_id
            FROM (
                SELECT store_id
                FROM silver.pos_transactions

                UNION

                SELECT store_id
                FROM silver.inventory_inventory

                UNION

                SELECT store_id
                FROM silver.inventory_inventory_movements
            ) s
            WHERE store_id IS NOT NULL
              AND BTRIM(store_id) <> ''
            ON CONFLICT (store_id) DO NOTHING
            """
        )
    )


def load_suppliers(connection):
    connection.execute(
        text(
            """
            INSERT INTO gold.dim_supplier (
                supplier_id,
                supplier_name,
                country,
                lead_time_days,
                active
            )
            SELECT
                supplier_id,
                supplier_name,
                country,
                lead_time_days,
                active
            FROM silver.suppliers_suppliers
            ON CONFLICT (supplier_id)
            DO UPDATE SET
                supplier_name = EXCLUDED.supplier_name,
                country = EXCLUDED.country,
                lead_time_days = EXCLUDED.lead_time_days,
                active = EXCLUDED.active
            """
        )
    )


def load_channels(connection):
    connection.execute(
        text(
            """
            INSERT INTO gold.dim_channel (channel_name)
            SELECT DISTINCT channel_name
            FROM (
                SELECT channel
                AS channel_name
                FROM silver.ecommerce_orders

                UNION

                SELECT 'POS'
                AS channel_name
                FROM silver.pos_transactions
            ) channels
            WHERE channel_name IS NOT NULL
              AND BTRIM(channel_name) <> ''
            ON CONFLICT (channel_name) DO NOTHING
            """
        )
    )


def load_dates(connection):
    """
    Populate calendar dates from 2020 through 2035.

    Key 0 remains the unknown date member.
    """

    connection.execute(
        text(
            """
            WITH calendar AS (
                SELECT
                    day::date AS full_date
                FROM generate_series(
                    DATE '2020-01-01',
                    DATE '2035-12-31',
                    INTERVAL '1 day'
                ) AS day
            )
            INSERT INTO gold.dim_date (
                date_key,
                full_date,
                year,
                quarter,
                month,
                month_name,
                day,
                day_of_week,
                day_name,
                is_weekend
            )
            SELECT
                TO_CHAR(full_date, 'YYYYMMDD')::INTEGER,
                full_date,
                EXTRACT(YEAR FROM full_date)::INTEGER,
                EXTRACT(QUARTER FROM full_date)::INTEGER,
                EXTRACT(MONTH FROM full_date)::INTEGER,
                TO_CHAR(full_date, 'FMMonth'),
                EXTRACT(DAY FROM full_date)::INTEGER,
                EXTRACT(ISODOW FROM full_date)::INTEGER,
                TO_CHAR(full_date, 'FMDay'),
                EXTRACT(ISODOW FROM full_date) IN (6, 7)
            FROM calendar
            ON CONFLICT (date_key) DO NOTHING
            """
        )
    )


def load_products(connection):
    """
    SCD Type 2 product loading.

    New product:
        Insert current version.

    Changed product:
        Close old version and insert new current version.

    Unchanged product:
        No action.

    Uses a deterministic, transaction-scoped change
    timestamp for all changes in this load.
    """

    load_timestamp = connection.execute(
        text("SELECT CURRENT_TIMESTAMP")
    ).scalar_one()

    products = connection.execute(
        text(
            """
            SELECT
                product_id,
                sku,
                product_name,
                category_id,
                category_name,
                brand,
                unit_price,
                currency,
                active
            FROM silver.products_products
            ORDER BY product_id
            """
        )
    ).mappings().all()

    inserted = 0
    changed = 0
    unchanged = 0

    for product in products:
        product_id = product["product_id"]
        new_hash = product_hash(product)

        current = connection.execute(
            text(
                """
                SELECT
                    product_key,
                    attribute_hash,
                    effective_from
                FROM gold.dim_product
                WHERE product_id = :product_id
                  AND is_current = TRUE
                FOR UPDATE
                """
            ),
            {"product_id": product_id},
        ).mappings().first()

        parameters = {
            **dict(product),
            "attribute_hash": new_hash,
            "effective_from": load_timestamp,
        }

        if current is None:
            connection.execute(
                text(
                    """
                    INSERT INTO gold.dim_product (
                        product_id,
                        sku,
                        product_name,
                        category_id,
                        category_name,
                        brand,
                        unit_price,
                        currency,
                        active,
                        effective_from,
                        effective_to,
                        is_current,
                        attribute_hash
                    )
                    VALUES (
                        :product_id,
                        :sku,
                        :product_name,
                        :category_id,
                        :category_name,
                        :brand,
                        :unit_price,
                        :currency,
                        :active,
                        :effective_from,
                        NULL,
                        TRUE,
                        :attribute_hash
                    )
                    """
                ),
                parameters,
            )

            inserted += 1
            continue

        if current["attribute_hash"] == new_hash:
            unchanged += 1
            continue

        # Avoid a zero-length historical period if
        # two updates occur in the same transaction
        # timestamp.
        if load_timestamp <= current["effective_from"]:
            raise RuntimeError(
                "SCD2 timestamp must be later than "
                f"existing version for {product_id}"
            )

        connection.execute(
            text(
                """
                UPDATE gold.dim_product
                SET effective_to = :effective_from,
                    is_current = FALSE
                WHERE product_key = :product_key
                """
            ),
            {
                "effective_from": load_timestamp,
                "product_key": current["product_key"],
            },
        )

        connection.execute(
            text(
                """
                INSERT INTO gold.dim_product (
                    product_id,
                    sku,
                    product_name,
                    category_id,
                    category_name,
                    brand,
                    unit_price,
                    currency,
                    active,
                    effective_from,
                    effective_to,
                    is_current,
                    attribute_hash
                )
                VALUES (
                    :product_id,
                    :sku,
                    :product_name,
                    :category_id,
                    :category_name,
                    :brand,
                    :unit_price,
                    :currency,
                    :active,
                    :effective_from,
                    NULL,
                    TRUE,
                    :attribute_hash
                )
                """
            ),
            parameters,
        )

        changed += 1

    return {
        "inserted": inserted,
        "changed": changed,
        "unchanged": unchanged,
    }


def validate_dimensions(connection):
    dimensions = {
        "dim_customer": "customer_key",
        "dim_product": "product_key",
        "dim_date": "date_key",
        "dim_store": "store_key",
        "dim_supplier": "supplier_key",
        "dim_channel": "channel_key",
    }

    counts = {}

    for table_name, key_column in dimensions.items():
        count = scalar(
            connection,
            f"SELECT COUNT(*) FROM gold.{table_name}",
        )

        unknown_count = scalar(
            connection,
            f"""
            SELECT COUNT(*)
            FROM gold.{table_name}
            WHERE {key_column} = 0
            """,
        )

        if unknown_count != 1:
            raise RuntimeError(
                f"Unknown member missing: {table_name}"
            )

        counts[table_name] = count

    duplicate_current = scalar(
        connection,
        """
        SELECT COUNT(*)
        FROM (
            SELECT product_id
            FROM gold.dim_product
            WHERE is_current = TRUE
            GROUP BY product_id
            HAVING COUNT(*) > 1
        ) duplicates
        """,
    )

    if duplicate_current:
        raise RuntimeError(
            "Duplicate current product versions found"
        )

    return counts


def load_all_dimensions():
    engine = create_warehouse_engine()

    try:
        with engine.begin() as connection:
            # Serialise concurrent dimension runs.
            connection.execute(
                text(
                    "SELECT pg_advisory_xact_lock(8105)"
                )
            )

            load_dates(connection)
            load_customers(connection)
            load_stores(connection)
            load_suppliers(connection)
            load_channels(connection)

            product_stats = load_products(connection)

            counts = validate_dimensions(connection)

        print("RetailFlow Gold Dimension Load")
        print("=" * 40)

        for table_name, count in counts.items():
            print(
                f"PASS | gold.{table_name}: {count:,} rows"
            )

        print()
        print(
            "Product SCD2 | "
            f"new={product_stats['inserted']} "
            f"changed={product_stats['changed']} "
            f"unchanged={product_stats['unchanged']}"
        )

        print()
        print("GOLD DIMENSION LOAD RESULT: PASS")

    finally:
        engine.dispose()


if __name__ == "__main__":
    load_all_dimensions()
