
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from src.warehouse.connection import create_warehouse_engine


# ============================================================
# RetailFlow
# Phase 7: Dimensional Model Validation
# ============================================================

DIMENSIONS = {
    "dim_customer",
    "dim_product",
    "dim_date",
    "dim_store",
    "dim_supplier",
    "dim_channel",
}

FACTS = {
    "fact_ecommerce_sales",
    "fact_pos_sales",
    "fact_payments",
    "fact_returns",
    "fact_inventory_snapshot",
    "fact_inventory_movements",
    "fact_supplier_deliveries",
}

EXPECTED_FOREIGN_KEYS = {
    "fact_ecommerce_sales": {
        "customer_key",
        "product_key",
        "date_key",
        "channel_key",
    },
    "fact_pos_sales": {
        "product_key",
        "store_key",
        "date_key",
        "channel_key",
    },
    "fact_payments": {
        "date_key",
    },
    "fact_returns": {
        "customer_key",
        "product_key",
        "date_key",
    },
    "fact_inventory_snapshot": {
        "snapshot_date_key",
        "product_key",
        "store_key",
    },
    "fact_inventory_movements": {
        "product_key",
        "store_key",
        "date_key",
    },
    "fact_supplier_deliveries": {
        "supplier_key",
        "product_key",
        "expected_date_key",
        "actual_date_key",
    },
}

failures = []
checks_run = 0


def check(condition, description):
    global checks_run

    checks_run += 1
    status = "PASS" if condition else "FAIL"

    print(f"{status} | {description}")

    if not condition:
        failures.append(description)


def expect_integrity_error(connection, sql, parameters=None):
    """
    Execute deliberately invalid SQL inside a SAVEPOINT.

    Return True only when PostgreSQL rejects the statement
    with an integrity constraint violation.

    The outer transaction remains usable.
    """
    savepoint = connection.begin_nested()

    try:
        connection.execute(
            text(sql),
            parameters or {},
        )

    except IntegrityError:
        savepoint.rollback()
        return True

    except Exception:
        savepoint.rollback()
        raise

    else:
        savepoint.rollback()
        return False


def test_product_constraints(connection):
    print()
    print("SCD Type 2 Constraint Tests")
    print("---------------------------")

    # The test business key is deliberately isolated
    # from RetailFlow's generated product identifiers.

    test_product_id = "__PHASE7_AUDIT_PRODUCT__"

    # This entire outer transaction is rolled back
    # after the tests finish.

    connection.execute(
        text(
            """
            INSERT INTO gold.dim_product (
                product_id,
                product_name,
                unit_price,
                effective_from,
                effective_to,
                is_current,
                attribute_hash
            )
            VALUES (
                :product_id,
                'Audit Product - Historical',
                10.00,
                '2026-09-01 00:00:00+00',
                '2026-09-15 00:00:00+00',
                FALSE,
                repeat('a', 64)
            )
            """
        ),
        {"product_id": test_product_id},
    )

    # 1. Overlapping historical validity periods

    check(
        expect_integrity_error(
            connection,
            """
            INSERT INTO gold.dim_product (
                product_id,
                product_name,
                effective_from,
                effective_to,
                is_current,
                attribute_hash
            )
            VALUES (
                :product_id,
                'Overlapping Product',
                '2026-09-10 00:00:00+00',
                '2026-09-20 00:00:00+00',
                FALSE,
                repeat('b', 64)
            )
            """,
            {"product_id": test_product_id},
        ),
        "Overlapping product history rejected",
    )

    # 2. Invalid effective date range

    check(
        expect_integrity_error(
            connection,
            """
            INSERT INTO gold.dim_product (
                product_id,
                effective_from,
                effective_to,
                is_current,
                attribute_hash
            )
            VALUES (
                '__PHASE7_INVALID_DATES__',
                '2026-09-20 00:00:00+00',
                '2026-09-10 00:00:00+00',
                FALSE,
                repeat('c', 64)
            )
            """,
        ),
        "Invalid effective date range rejected",
    )

    # 3. Insert a valid current version

    connection.execute(
        text(
            """
            INSERT INTO gold.dim_product (
                product_id,
                product_name,
                unit_price,
                effective_from,
                effective_to,
                is_current,
                attribute_hash
            )
            VALUES (
                :product_id,
                'Audit Product - Current',
                15.00,
                '2026-09-15 00:00:00+00',
                NULL,
                TRUE,
                repeat('d', 64)
            )
            """
        ),
        {"product_id": test_product_id},
    )

    # 4. Duplicate current version

    check(
        expect_integrity_error(
            connection,
            """
            INSERT INTO gold.dim_product (
                product_id,
                effective_from,
                effective_to,
                is_current,
                attribute_hash
            )
            VALUES (
                :product_id,
                '2026-10-01 00:00:00+00',
                NULL,
                TRUE,
                repeat('e', 64)
            )
            """,
            {"product_id": test_product_id},
        ),
        "Duplicate current product version rejected",
    )

    # 5. Inconsistent current flag

    check(
        expect_integrity_error(
            connection,
            """
            INSERT INTO gold.dim_product (
                product_id,
                effective_from,
                effective_to,
                is_current,
                attribute_hash
            )
            VALUES (
                '__PHASE7_INVALID_FLAG__',
                '2026-09-01 00:00:00+00',
                NULL,
                FALSE,
                repeat('f', 64)
            )
            """,
        ),
        "Inconsistent SCD current flag rejected",
    )


def test_fact_constraints(connection):
    print()
    print("Fact Table Constraint Tests")
    print("---------------------------")

    # Unknown dimension members with key 0 allow
    # an isolated test row without loading real data.

    connection.execute(
        text(
            """
            INSERT INTO gold.fact_ecommerce_sales (
                order_item_id,
                order_id,
                customer_key,
                product_key,
                date_key,
                channel_key,
                quantity,
                line_total
            )
            VALUES (
                '__PHASE7_AUDIT_ITEM__',
                '__PHASE7_AUDIT_ORDER__',
                0,
                0,
                0,
                0,
                1,
                10.00
            )
            """
        )
    )

    check(
        expect_integrity_error(
            connection,
            """
            INSERT INTO gold.fact_ecommerce_sales (
                order_item_id,
                order_id,
                customer_key,
                product_key,
                date_key,
                channel_key
            )
            VALUES (
                '__PHASE7_AUDIT_ITEM__',
                '__PHASE7_ANOTHER_ORDER__',
                0, 0, 0, 0
            )
            """,
        ),
        "Duplicate e-commerce order item rejected",
    )

    check(
        expect_integrity_error(
            connection,
            """
            INSERT INTO gold.fact_ecommerce_sales (
                order_item_id,
                order_id,
                customer_key,
                product_key,
                date_key,
                channel_key
            )
            VALUES (
                '__PHASE7_INVALID_FK__',
                '__PHASE7_AUDIT_ORDER__',
                999999999999,
                0, 0, 0
            )
            """,
        ),
        "Invalid customer foreign key rejected",
    )


def main():
    print("RetailFlow Phase 7 Dimensional Model Audit")
    print("==========================================")

    engine = create_warehouse_engine()

    try:
        with engine.connect() as connection:

            # ----------------------------------------
            # 1. Table inventory
            # ----------------------------------------

            tables = set(
                connection.execute(
                    text(
                        """
                        SELECT table_name
                        FROM information_schema.tables
                        WHERE table_schema = 'gold'
                          AND table_type = 'BASE TABLE'
                        """
                    )
                ).scalars()
            )

            check(
                tables == DIMENSIONS | FACTS,
                "Exactly 13 expected Gold tables exist",
            )

            check(
                len(tables & DIMENSIONS) == 6,
                "Six dimensions exist",
            )

            check(
                len(tables & FACTS) == 7,
                "Seven fact tables exist",
            )

            # ----------------------------------------
            # 2. Primary keys
            # ----------------------------------------

            primary_keys = set(
                connection.execute(
                    text(
                        """
                        SELECT c.relname
                        FROM pg_constraint con
                        JOIN pg_class c
                          ON c.oid = con.conrelid
                        JOIN pg_namespace n
                          ON n.oid = c.relnamespace
                        WHERE con.contype = 'p'
                          AND n.nspname = 'gold'
                        """
                    )
                ).scalars()
            )

            check(
                tables.issubset(primary_keys),
                "Every Gold table has a primary key",
            )

            # ----------------------------------------
            # 3. Foreign keys
            # ----------------------------------------

            actual_foreign_keys = {}

            rows = connection.execute(
                text(
                    """
                    SELECT
                        tc.table_name,
                        kcu.column_name
                    FROM information_schema.table_constraints tc
                    JOIN information_schema.key_column_usage kcu
                      ON tc.constraint_name = kcu.constraint_name
                     AND tc.constraint_schema = kcu.constraint_schema
                    WHERE tc.table_schema = 'gold'
                      AND tc.constraint_type = 'FOREIGN KEY'
                    """
                )
            ).all()

            for table_name, column_name in rows:
                actual_foreign_keys.setdefault(
                    table_name, set()
                ).add(column_name)

            for fact_table, expected_keys in (
                EXPECTED_FOREIGN_KEYS.items()
            ):
                check(
                    actual_foreign_keys.get(
                        fact_table, set()
                    ) == expected_keys,
                    f"{fact_table} foreign keys match design",
                )

            # ----------------------------------------
            # 4. Unknown dimension members
            # ----------------------------------------

            unknown_keys = {
                "dim_customer": "customer_key",
                "dim_product": "product_key",
                "dim_date": "date_key",
                "dim_store": "store_key",
                "dim_supplier": "supplier_key",
                "dim_channel": "channel_key",
            }

            for table_name, key_column in unknown_keys.items():
                # Both identifiers come from a fixed
                # internal whitelist, not user input.

                count = connection.execute(
                    text(
                        f"""
                        SELECT COUNT(*)
                        FROM gold.{table_name}
                        WHERE {key_column} = 0
                        """
                    )
                ).scalar_one()

                check(
                    count == 1,
                    f"{table_name} has unknown member",
                )

            # ----------------------------------------
            # 5. Product SCD constraints
            # ----------------------------------------

            constraint_names = set(
                connection.execute(
                    text(
                        """
                        SELECT con.conname
                        FROM pg_constraint con
                        JOIN pg_class c
                          ON c.oid = con.conrelid
                        JOIN pg_namespace n
                          ON n.oid = c.relnamespace
                        WHERE n.nspname = 'gold'
                          AND c.relname = 'dim_product'
                        """
                    )
                ).scalars()
            )

            check(
                "ex_dim_product_no_overlap"
                in constraint_names,
                "Product history exclusion constraint exists",
            )

            check(
                "ck_product_effective_dates"
                in constraint_names,
                "Product effective-date check exists",
            )

            check(
                "ck_product_current_period"
                in constraint_names,
                "Product current-period check exists",
            )

            current_index_exists = connection.execute(
                text(
                    """
                    SELECT EXISTS (
                        SELECT 1
                        FROM pg_indexes
                        WHERE schemaname = 'gold'
                          AND tablename = 'dim_product'
                          AND indexname = 'uq_dim_product_current'
                    )
                    """
                )
            ).scalar_one()

            check(
                current_index_exists,
                "Unique current-product index exists",
            )

        # --------------------------------------------
        # 6. Transactional integrity tests
        # --------------------------------------------

        with engine.connect() as connection:
            outer_transaction = connection.begin()

            try:
                test_product_constraints(connection)
                test_fact_constraints(connection)
            finally:
                outer_transaction.rollback()

        # --------------------------------------------
        # 7. Analytics role permissions
        # --------------------------------------------

        with engine.connect() as connection:
            permissions = connection.execute(
                text(
                    """
                    SELECT
                        has_schema_privilege(
                            'retailflow_analytics_user',
                            'gold',
                            'USAGE'
                        ) AS gold_usage,
                        has_table_privilege(
                            'retailflow_analytics_user',
                            'gold.dim_product',
                            'SELECT'
                        ) AS product_read,
                        has_table_privilege(
                            'retailflow_analytics_user',
                            'gold.fact_ecommerce_sales',
                            'SELECT'
                        ) AS sales_read,
                        has_table_privilege(
                            'retailflow_analytics_user',
                            'gold.dim_product',
                            'INSERT'
                        ) AS product_write,
                        has_schema_privilege(
                            'retailflow_analytics_user',
                            'silver',
                            'USAGE'
                        ) AS silver_usage
                    """
                )
            ).mappings().one()

            check(
                permissions["gold_usage"],
                "Analytics role can access Gold schema",
            )

            check(
                permissions["product_read"]
                and permissions["sales_read"],
                "Analytics role can read Gold tables",
            )

            check(
                not permissions["product_write"],
                "Analytics role cannot insert Gold data",
            )

            check(
                not permissions["silver_usage"],
                "Analytics role cannot access Silver schema",
            )

    finally:
        engine.dispose()

    # ------------------------------------------------
    # Final summary
    # ------------------------------------------------

    print()
    print("Phase 7 Audit Summary")
    print("---------------------")
    print(f"Checks executed: {checks_run}")
    print(f"Checks failed: {len(failures)}")

    if failures:
        print()
        print("PHASE 7 AUDIT RESULT: FAIL")

        for failure in failures:
            print(f" - {failure}")

        raise SystemExit(1)

    print()
    print("PHASE 7 AUDIT RESULT: PASS")
    print("RetailFlow dimensional model validated.")


if __name__ == "__main__":
    main()
