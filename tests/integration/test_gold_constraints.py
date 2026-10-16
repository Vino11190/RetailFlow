import pytest
import psycopg2


def test_ecommerce_sales_rejects_missing_dimensions(db_connection):
    """A sale must reference existing dimension records."""

    with db_connection.cursor() as cursor:
        with pytest.raises(psycopg2.errors.ForeignKeyViolation):
            cursor.execute("""
                INSERT INTO gold.fact_ecommerce_sales (
                    sales_key,
                    order_item_id,
                    order_id,
                    customer_key,
                    product_key,
                    date_key,
                    channel_key
                )
                VALUES (
                    -900001,
                    'INTEGRATION-FK-001',
                    'INTEGRATION-ORDER-001',
                    -900001,
                    -900001,
                    -900001,
                    -900001
                )
            """)

    db_connection.rollback()


def test_product_rejects_invalid_effective_dates(db_connection):
    """A product history period cannot end before it starts."""

    with db_connection.cursor() as cursor:
        with pytest.raises(psycopg2.errors.CheckViolation):
            cursor.execute("""
                INSERT INTO gold.dim_product (
                    product_key,
                    product_id,
                    effective_from,
                    effective_to,
                    is_current,
                    attribute_hash
                )
                VALUES (
                    -900002,
                    'INTEGRATION-PRODUCT-DATES',
                    '2026-01-10 00:00:00+00',
                    '2026-01-05 00:00:00+00',
                    FALSE,
                    'integration-test-hash'
                )
            """)

    db_connection.rollback()


def test_product_rejects_overlapping_scd2_periods(db_connection):
    """Two versions of one product cannot overlap in time."""

    with db_connection.cursor() as cursor:
        cursor.execute("""
            INSERT INTO gold.dim_product (
                product_key,
                product_id,
                effective_from,
                effective_to,
                is_current,
                attribute_hash
            )
            VALUES (
                -900003,
                'INTEGRATION-PRODUCT-SCD2',
                '2026-01-01 00:00:00+00',
                '2026-02-01 00:00:00+00',
                FALSE,
                'integration-hash-v1'
            )
        """)

        with pytest.raises(psycopg2.errors.ExclusionViolation):
            cursor.execute("""
                INSERT INTO gold.dim_product (
                    product_key,
                    product_id,
                    effective_from,
                    effective_to,
                    is_current,
                    attribute_hash
                )
                VALUES (
                    -900004,
                    'INTEGRATION-PRODUCT-SCD2',
                    '2026-01-15 00:00:00+00',
                    '2026-03-01 00:00:00+00',
                    FALSE,
                    'integration-hash-v2'
                )
            """)

    db_connection.rollback()
