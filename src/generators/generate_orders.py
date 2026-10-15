import os
import random
from datetime import datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP

import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine, text


# ============================================================
# RetailFlow
# Synthetic E-commerce Order Generator
# ============================================================

ORDER_COUNT = 25_000
PRODUCT_COUNT = 500
RANDOM_SEED = 42

START_DATE = datetime(2025, 1, 1)
END_DATE = datetime(2026, 9, 30, 23, 59, 59)

ORDER_STATUSES = [
    "COMPLETED",
    "COMPLETED",
    "COMPLETED",
    "COMPLETED",
    "SHIPPED",
    "PROCESSING",
    "CANCELLED",
]

CHANNELS = [
    "WEB",
    "MOBILE_APP",
]

CURRENCY = "GBP"

random.seed(RANDOM_SEED)

load_dotenv()


def get_database_url() -> str:
    """Build the PostgreSQL connection URL."""

    user = os.getenv("POSTGRES_USER")
    password = os.getenv("POSTGRES_PASSWORD")
    database = os.getenv("POSTGRES_DB")

    if not all([user, password, database]):
        raise ValueError(
            "Missing PostgreSQL environment variables. "
            "Check your .env file."
        )

    return (
        f"postgresql+psycopg2://{user}:{password}"
        f"@localhost:5432/{database}"
    )


def money(value) -> Decimal:
    """Round monetary values to two decimal places."""

    return Decimal(str(value)).quantize(
        Decimal("0.01"),
        rounding=ROUND_HALF_UP,
    )


def random_datetime(
    start: datetime,
    end: datetime,
) -> datetime:
    """Generate a random datetime between two dates."""

    difference = end - start

    seconds = random.randint(
        0,
        int(difference.total_seconds()),
    )

    return start + timedelta(seconds=seconds)


def get_customer_ids() -> list[str]:
    """Read available customer IDs from PostgreSQL."""

    engine = create_engine(
        get_database_url()
    )

    with engine.connect() as connection:
        rows = connection.execute(
            text(
                """
                SELECT customer_id
                FROM customers
                ORDER BY customer_id;
                """
            )
        ).fetchall()

    customer_ids = [
        row[0]
        for row in rows
    ]

    if not customer_ids:
        raise ValueError(
            "No customers found. "
            "Run generate_customers.py first."
        )

    return customer_ids


def generate_product_prices() -> dict[str, Decimal]:
    """
    Create a deterministic temporary product-price catalogue.

    The dedicated Product API source system will be built later.
    """

    prices = {}

    for number in range(1, PRODUCT_COUNT + 1):
        product_id = f"PROD{number:05d}"

        price = money(
            random.uniform(2.99, 499.99)
        )

        prices[product_id] = price

    return prices


def generate_orders_and_items(
    customer_ids: list[str],
    product_prices: dict[str, Decimal],
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Generate synthetic orders and associated order items."""

    orders = []
    order_items = []

    order_item_counter = 1

    product_ids = list(
        product_prices.keys()
    )

    for order_number in range(
        1,
        ORDER_COUNT + 1,
    ):
        order_id = (
            f"ORD{order_number:08d}"
        )

        customer_id = random.choice(
            customer_ids
        )

        order_timestamp = random_datetime(
            START_DATE,
            END_DATE,
        )

        channel = random.choice(
            CHANNELS
        )

        status = random.choice(
            ORDER_STATUSES
        )

        # Produces an average of approximately 2.6 items/order.
        item_count = random.choices(
            population=[1, 2, 3, 4, 5],
            weights=[20, 30, 25, 15, 10],
            k=1,
        )[0]

        selected_products = random.sample(
            product_ids,
            k=item_count,
        )

        order_subtotal = Decimal("0.00")
        order_discount = Decimal("0.00")

        current_order_items = []

        for product_id in selected_products:
            quantity = random.choices(
                population=[1, 2, 3, 4],
                weights=[70, 20, 8, 2],
                k=1,
            )[0]

            unit_price = product_prices[
                product_id
            ]

            gross_line_value = money(
                unit_price * quantity
            )

            discount_rate = random.choices(
                population=[
                    Decimal("0.00"),
                    Decimal("0.05"),
                    Decimal("0.10"),
                    Decimal("0.15"),
                ],
                weights=[70, 12, 12, 6],
                k=1,
            )[0]

            line_discount = money(
                gross_line_value
                * discount_rate
            )

            line_total = money(
                gross_line_value
                - line_discount
            )

            order_subtotal += gross_line_value
            order_discount += line_discount

            order_item_id = (
                f"ITEM{order_item_counter:09d}"
            )

            current_order_items.append(
                {
                    "order_item_id": order_item_id,
                    "order_id": order_id,
                    "product_id": product_id,
                    "quantity": quantity,
                    "unit_price": unit_price,
                    "discount": line_discount,
                    "line_total": line_total,
                }
            )

            order_item_counter += 1

        order_subtotal = money(
            order_subtotal
        )

        order_discount = money(
            order_discount
        )

        # Free shipping for orders worth £50+ after discount.
        merchandise_total = money(
            order_subtotal
            - order_discount
        )

        if merchandise_total >= Decimal("50.00"):
            shipping = Decimal("0.00")
        else:
            shipping = Decimal("4.99")

        order_total = money(
            merchandise_total
            + shipping
        )

        maximum_update_days = max(
            0,
            (END_DATE - order_timestamp).days,
        )

        update_days = random.randint(
            0,
            min(maximum_update_days, 14),
        )

        updated_at = (
            order_timestamp
            + timedelta(days=update_days)
        )

        orders.append(
            {
                "order_id": order_id,
                "customer_id": customer_id,
                "order_timestamp": order_timestamp,
                "channel": channel,
                "status": status,
                "currency": CURRENCY,
                "subtotal": order_subtotal,
                "discount": order_discount,
                "shipping": shipping,
                "order_total": order_total,
                "updated_at": updated_at,
            }
        )

        order_items.extend(
            current_order_items
        )

    return (
        pd.DataFrame(orders),
        pd.DataFrame(order_items),
    )


def load_orders_and_items(
    orders_df: pd.DataFrame,
    order_items_df: pd.DataFrame,
) -> None:
    """Load orders and order items into PostgreSQL."""

    engine = create_engine(
        get_database_url()
    )

    with engine.begin() as connection:

        # Only transactional tables are reset.
        # Customer records remain intact.
        connection.execute(
            text(
                """
                TRUNCATE TABLE
                    order_items,
                    orders;
                """
            )
        )

        orders_df.to_sql(
            name="orders",
            con=connection,
            if_exists="append",
            index=False,
            method="multi",
            chunksize=1000,
        )

        order_items_df.to_sql(
            name="order_items",
            con=connection,
            if_exists="append",
            index=False,
            method="multi",
            chunksize=1000,
        )


def validate_load() -> None:
    """Run basic integrity and reconciliation checks."""

    engine = create_engine(
        get_database_url()
    )

    with engine.connect() as connection:

        order_count = connection.execute(
            text(
                "SELECT COUNT(*) FROM orders;"
            )
        ).scalar_one()

        item_count = connection.execute(
            text(
                "SELECT COUNT(*) FROM order_items;"
            )
        ).scalar_one()

        orphan_orders = connection.execute(
            text(
                """
                SELECT COUNT(*)
                FROM orders o
                LEFT JOIN customers c
                    ON o.customer_id = c.customer_id
                WHERE c.customer_id IS NULL;
                """
            )
        ).scalar_one()

        orphan_items = connection.execute(
            text(
                """
                SELECT COUNT(*)
                FROM order_items oi
                LEFT JOIN orders o
                    ON oi.order_id = o.order_id
                WHERE o.order_id IS NULL;
                """
            )
        ).scalar_one()

        duplicate_orders = connection.execute(
            text(
                """
                SELECT COUNT(*)
                FROM (
                    SELECT order_id
                    FROM orders
                    GROUP BY order_id
                    HAVING COUNT(*) > 1
                ) duplicates;
                """
            )
        ).scalar_one()

        reconciliation_failures = connection.execute(
            text(
                """
                SELECT COUNT(*)
                FROM (
                    SELECT
                        o.order_id
                    FROM orders o
                    JOIN (
                        SELECT
                            order_id,
                            ROUND(
                                SUM(line_total),
                                2
                            ) AS item_total
                        FROM order_items
                        GROUP BY order_id
                    ) i
                        ON o.order_id = i.order_id
                    WHERE
                        ROUND(
                            o.order_total - o.shipping,
                            2
                        ) <> i.item_total
                ) failures;
                """
            )
        ).scalar_one()

    print("\nPost-load validation")
    print("--------------------")
    print(
        f"Database order count: "
        f"{order_count:,}"
    )
    print(
        f"Database order-item count: "
        f"{item_count:,}"
    )
    print(
        f"Orders with invalid customers: "
        f"{orphan_orders}"
    )
    print(
        f"Order items with invalid orders: "
        f"{orphan_items}"
    )
    print(
        f"Duplicate order IDs: "
        f"{duplicate_orders}"
    )
    print(
        f"Financial reconciliation failures: "
        f"{reconciliation_failures}"
    )


def main() -> None:
    print(
        "RetailFlow Order Generator"
    )
    print(
        "=========================="
    )

    customer_ids = get_customer_ids()

    print(
        f"\nCustomers available: "
        f"{len(customer_ids):,}"
    )

    product_prices = (
        generate_product_prices()
    )

    print(
        f"Temporary products available: "
        f"{len(product_prices):,}"
    )

    print(
        f"\nGenerating "
        f"{ORDER_COUNT:,} orders..."
    )

    orders_df, order_items_df = (
        generate_orders_and_items(
            customer_ids,
            product_prices,
        )
    )

    print(
        f"Generated orders: "
        f"{len(orders_df):,}"
    )

    print(
        f"Generated order items: "
        f"{len(order_items_df):,}"
    )

    print("\nSample orders:")
    print(
        orders_df.head(5).to_string(
            index=False
        )
    )

    print(
        "\nLoading transactional data "
        "into PostgreSQL..."
    )

    load_orders_and_items(
        orders_df,
        order_items_df,
    )

    print(
        "Transactional load completed "
        "successfully."
    )

    validate_load()


if __name__ == "__main__":
    main()