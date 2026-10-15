import json
import os
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine, text


# ============================================================
# RetailFlow
# Phase 3 Source-System Audit
# ============================================================

load_dotenv()

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def database_url(database: str) -> str:
    """Build a PostgreSQL connection URL."""

    user = os.getenv("POSTGRES_USER")
    password = os.getenv("POSTGRES_PASSWORD")

    if not user or not password:
        raise RuntimeError(
            "PostgreSQL credentials are missing from .env."
        )

    return (
        f"postgresql+psycopg2://"
        f"{user}:{password}"
        f"@localhost:5432/{database}"
    )


def query_count(
    database: str,
    table: str,
) -> int:
    """Return the number of records in a PostgreSQL table."""

    engine = create_engine(
        database_url(database)
    )

    with engine.connect() as connection:
        return connection.execute(
            text(
                f"SELECT COUNT(*) FROM {table};"
            )
        ).scalar_one()


def load_json(
    path: Path,
):
    """Load JSON data."""

    with path.open(
        "r",
        encoding="utf-8",
    ) as file:
        return json.load(file)


def audit() -> None:
    """Audit all Phase 3 RetailFlow sources."""

    print(
        "RetailFlow Phase 3 Source-System Audit"
    )
    print(
        "======================================"
    )

    results = []

    # --------------------------------------------------------
    # 1. E-commerce PostgreSQL
    # --------------------------------------------------------

    ecommerce_database = os.getenv(
        "POSTGRES_DB",
        "retailflow_ecommerce",
    )

    customers = query_count(
        ecommerce_database,
        "customers",
    )

    orders = query_count(
        ecommerce_database,
        "orders",
    )

    order_items = query_count(
        ecommerce_database,
        "order_items",
    )

    results.extend(
        [
            (
                "E-commerce customers",
                customers,
                5_000,
            ),
            (
                "E-commerce orders",
                orders,
                25_000,
            ),
            (
                "E-commerce order items",
                order_items,
                1,
            ),
        ]
    )

    # --------------------------------------------------------
    # 2. Product Catalogue
    # --------------------------------------------------------

    product_directory = (
        PROJECT_ROOT
        / "sources"
        / "products_api"
        / "data"
    )

    products = load_json(
        product_directory
        / "products.json"
    )

    categories = load_json(
        product_directory
        / "categories.json"
    )

    results.extend(
        [
            (
                "Products",
                len(products),
                500,
            ),
            (
                "Categories",
                len(categories),
                8,
            ),
        ]
    )

    # --------------------------------------------------------
    # 3. POS
    # --------------------------------------------------------

    pos_directory = (
        PROJECT_ROOT
        / "sources"
        / "pos"
        / "outbound"
    )

    pos_files = sorted(
        pos_directory.glob(
            "pos_transactions_*.csv"
        )
    )

    pos_rows = sum(
        len(
            pd.read_csv(file)
        )
        for file in pos_files
    )

    results.extend(
        [
            (
                "POS daily files",
                len(pos_files),
                30,
            ),
            (
                "POS transactions",
                pos_rows,
                20_000,
            ),
        ]
    )

    # --------------------------------------------------------
    # 4. Inventory PostgreSQL
    # --------------------------------------------------------

    inventory_positions = query_count(
        "retailflow_inventory",
        "inventory",
    )

    inventory_movements = query_count(
        "retailflow_inventory",
        "inventory_movements",
    )

    results.extend(
        [
            (
                "Inventory positions",
                inventory_positions,
                6_000,
            ),
            (
                "Inventory movements",
                inventory_movements,
                50_000,
            ),
        ]
    )

    # --------------------------------------------------------
    # 5. Suppliers
    # --------------------------------------------------------

    supplier_directory = (
        PROJECT_ROOT
        / "sources"
        / "suppliers"
        / "outbound"
    )

    suppliers = pd.read_csv(
        supplier_directory
        / "suppliers.csv"
    )

    deliveries = load_json(
        supplier_directory
        / "deliveries.json"
    )

    results.extend(
        [
            (
                "Suppliers",
                len(suppliers),
                50,
            ),
            (
                "Supplier deliveries",
                len(deliveries),
                5_000,
            ),
        ]
    )

    # --------------------------------------------------------
    # 6. Payments
    # --------------------------------------------------------

    payments = load_json(
        PROJECT_ROOT
        / "sources"
        / "payments"
        / "outbound"
        / "payments.json"
    )

    results.append(
        (
            "Payments",
            len(payments),
            25_000,
        )
    )

    # --------------------------------------------------------
    # 7. Returns
    # --------------------------------------------------------

    returns = pd.read_csv(
        PROJECT_ROOT
        / "sources"
        / "returns"
        / "outbound"
        / "returns.csv"
    )

    results.append(
        (
            "Returns",
            len(returns),
            2_000,
        )
    )

    # --------------------------------------------------------
    # Report
    # --------------------------------------------------------

    print()

    failures = 0

    for name, actual, expected in results:

        # Order items are variable, so we only require
        # the table to contain records.
        if name == "E-commerce order items":
            passed = actual >= expected
        else:
            passed = actual == expected

        status = (
            "PASS"
            if passed
            else "FAIL"
        )

        if not passed:
            failures += 1

        print(
            f"[{status}] "
            f"{name:<25} "
            f"{actual:,}"
        )

    print()
    print(
        "--------------------------------------"
    )

    if failures == 0:
        print(
            "PHASE 3 AUDIT RESULT: PASS"
        )
        print(
            "All RetailFlow source systems "
            "are ready."
        )
    else:
        print(
            "PHASE 3 AUDIT RESULT: FAIL"
        )
        print(
            f"Failed checks: {failures}"
        )

        raise RuntimeError(
            "Phase 3 source audit failed."
        )


if __name__ == "__main__":
    audit()