
"""
RetailFlow Airflow Warehouse Validation.

Checks row counts across Silver and Gold schemas
after a successful Airflow pipeline run.
"""

from sqlalchemy import text

from src.warehouse.connection import create_warehouse_engine


TABLES = {
    "silver": [
        "ecommerce_customers",
        "ecommerce_orders",
        "ecommerce_order_items",
        "pos_transactions",
        "products_products",
        "payments_payments",
        "returns_returns",
        "inventory_inventory",
        "inventory_inventory_movements",
        "suppliers_suppliers",
        "suppliers_deliveries",
    ],
    "gold": [
        "dim_customer",
        "dim_product",
        "dim_date",
        "dim_store",
        "dim_supplier",
        "dim_channel",
        "fact_ecommerce_sales",
        "fact_pos_sales",
        "fact_payments",
        "fact_returns",
        "fact_inventory_snapshot",
        "fact_inventory_movements",
        "fact_supplier_deliveries",
    ],
}


def main():
    engine = create_warehouse_engine()

    try:
        with engine.connect() as connection:
            print("\nRETAILFLOW WAREHOUSE VALIDATION")
            print("=" * 55)

            for schema, tables in TABLES.items():
                print(f"\n{schema.upper()} LAYER")

                for table in tables:
                    count = connection.execute(
                        text(
                            f"SELECT COUNT(*) "
                            f"FROM {schema}.{table}"
                        )
                    ).scalar_one()

                    print(
                        f"{schema}.{table}: "
                        f"{count:,} rows"
                    )

            print("\nWAREHOUSE COUNT REPORT: COMPLETE")

    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
