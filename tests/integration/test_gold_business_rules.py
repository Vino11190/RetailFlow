import psycopg2
import pytest


def test_duplicate_order_item_rejected(db_connection):
    """The same order item cannot appear twice in the sales fact."""

    with db_connection.cursor() as cursor:
        cursor.execute("""
            INSERT INTO gold.dim_customer (
                customer_key, customer_id
            )
            VALUES (-910001, 'TEST-CUSTOMER-910001')
        """)

        cursor.execute("""
            INSERT INTO gold.dim_product (
                product_key, product_id, effective_from,
                is_current, attribute_hash
            )
            VALUES (
                -910001, 'TEST-PRODUCT-910001',
                '2026-01-01 00:00:00+00',
                TRUE, 'test-product-hash'
            )
        """)

        cursor.execute("""
            INSERT INTO gold.dim_date (
                date_key
            )
            VALUES (19000101)
            ON CONFLICT (date_key) DO NOTHING
        """)

        cursor.execute("""
            INSERT INTO gold.dim_channel (
                channel_key
            )
            VALUES (-910001)
        """)

        cursor.execute("""
            INSERT INTO gold.fact_ecommerce_sales (
                sales_key, order_item_id, order_id,
                customer_key, product_key, date_key, channel_key
            )
            VALUES (
                -910001, 'TEST-ORDER-ITEM-910001', 'TEST-ORDER-910001',
                -910001, -910001, 19000101, -910001
            )
        """)

        with pytest.raises(psycopg2.errors.UniqueViolation):
            cursor.execute("""
                INSERT INTO gold.fact_ecommerce_sales (
                    sales_key, order_item_id, order_id,
                    customer_key, product_key, date_key, channel_key
                )
                VALUES (
                    -910002, 'TEST-ORDER-ITEM-910001', 'TEST-ORDER-910002',
                    -910001, -910001, 19000101, -910001
                )
            """)

    db_connection.rollback()


def test_valid_non_overlapping_scd2_history(db_connection):
    """Consecutive product versions with no overlap are valid."""

    with db_connection.cursor() as cursor:
        cursor.execute("""
            INSERT INTO gold.dim_product (
                product_key, product_id, effective_from,
                effective_to, is_current, attribute_hash
            )
            VALUES (
                -920001, 'TEST-PRODUCT-SCD2-920001',
                '2026-01-01 00:00:00+00',
                '2026-02-01 00:00:00+00',
                FALSE, 'test-hash-v1'
            )
        """)

        cursor.execute("""
            INSERT INTO gold.dim_product (
                product_key, product_id, effective_from,
                effective_to, is_current, attribute_hash
            )
            VALUES (
                -920002, 'TEST-PRODUCT-SCD2-920001',
                '2026-02-01 00:00:00+00',
                NULL,
                TRUE, 'test-hash-v2'
            )
        """)

        cursor.execute("""
            SELECT COUNT(*)
            FROM gold.dim_product
            WHERE product_id = 'TEST-PRODUCT-SCD2-920001'
        """)

        assert cursor.fetchone()[0] == 2

    db_connection.rollback()


def test_current_product_requires_null_end_date(db_connection):
    """A current product version cannot have an end date."""

    with db_connection.cursor() as cursor:
        with pytest.raises(psycopg2.errors.CheckViolation):
            cursor.execute("""
                INSERT INTO gold.dim_product (
                    product_key, product_id, effective_from,
                    effective_to, is_current, attribute_hash
                )
                VALUES (
                    -930001, 'TEST-PRODUCT-CURRENT-930001',
                    '2026-01-01 00:00:00+00',
                    '2026-03-01 00:00:00+00',
                    TRUE, 'test-hash-current'
                )
            """)

    db_connection.rollback()
