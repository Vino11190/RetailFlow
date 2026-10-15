import json
import os
import random
from datetime import timedelta
from decimal import Decimal
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine, text


# ============================================================
# RetailFlow
# Synthetic Payment Source Generator
# ============================================================

RANDOM_SEED = 42

PAYMENT_METHODS = [
    "VISA",
    "MASTERCARD",
    "PAYPAL",
    "APPLE_PAY",
    "GOOGLE_PAY",
]

PAYMENT_STATUSES = [
    "COMPLETED",
    "FAILED",
    "PENDING",
    "REFUNDED",
]

STATUS_WEIGHTS = [
    88,
    4,
    3,
    5,
]

random.seed(RANDOM_SEED)

load_dotenv()


PROJECT_ROOT = Path(__file__).resolve().parents[2]

OUTPUT_DIRECTORY = (
    PROJECT_ROOT
    / "sources"
    / "payments"
    / "outbound"
)


def get_database_url() -> str:
    """Build the e-commerce PostgreSQL connection URL."""

    user = os.getenv("POSTGRES_USER")
    password = os.getenv("POSTGRES_PASSWORD")
    database = os.getenv("POSTGRES_DB")

    if not all(
        [
            user,
            password,
            database,
        ]
    ):
        raise ValueError(
            "Missing PostgreSQL configuration in .env."
        )

    return (
        f"postgresql+psycopg2://"
        f"{user}:{password}"
        f"@localhost:5432/{database}"
    )


def read_orders() -> list[dict]:
    """Read source orders from the e-commerce database."""

    engine = create_engine(
        get_database_url()
    )

    query = text(
        """
        SELECT
            order_id,
            order_timestamp,
            order_total,
            currency,
            status AS order_status
        FROM orders
        ORDER BY order_id;
        """
    )

    with engine.connect() as connection:
        rows = connection.execute(
            query
        ).mappings().all()

    return [
        dict(row)
        for row in rows
    ]


def determine_payment_status(
    order_status: str,
) -> str:
    """
    Generate a realistic payment status.

    Cancelled orders are more likely to have
    failed, refunded, or pending payments.
    """

    if order_status == "CANCELLED":
        return random.choices(
            population=[
                "FAILED",
                "REFUNDED",
                "PENDING",
            ],
            weights=[
                45,
                45,
                10,
            ],
            k=1,
        )[0]

    return random.choices(
        population=PAYMENT_STATUSES,
        weights=STATUS_WEIGHTS,
        k=1,
    )[0]


def generate_payments(
    orders: list[dict],
) -> list[dict]:
    """Generate one payment record per order."""

    payments = []

    for number, order in enumerate(
        orders,
        start=1,
    ):
        payment_id = (
            f"PAY{number:09d}"
        )

        payment_status = (
            determine_payment_status(
                order["order_status"]
            )
        )

        payment_timestamp = (
            order["order_timestamp"]
            + timedelta(
                seconds=random.randint(
                    5,
                    900,
                )
            )
        )

        order_total = Decimal(
            str(order["order_total"])
        )

        if payment_status == "FAILED":
            amount = Decimal("0.00")
        else:
            amount = order_total

        payment_method = random.choice(
            PAYMENT_METHODS
        )

        payments.append(
            {
                "payment_id": payment_id,
                "order_id": order["order_id"],
                "payment_timestamp": (
                    payment_timestamp.isoformat()
                ),
                "amount": float(amount),
                "currency": order["currency"],
                "status": payment_status,
                "payment_method": payment_method,
            }
        )

    return payments


def save_payments(
    payments: list[dict],
) -> Path:
    """Save payments to JSON."""

    OUTPUT_DIRECTORY.mkdir(
        parents=True,
        exist_ok=True,
    )

    output_path = (
        OUTPUT_DIRECTORY
        / "payments.json"
    )

    with output_path.open(
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            payments,
            file,
            indent=2,
        )

    return output_path


def validate_payments(
    orders: list[dict],
    payments: list[dict],
) -> None:
    """Run basic payment source validation."""

    order_ids = {
        order["order_id"]
        for order in orders
    }

    payment_ids = [
        payment["payment_id"]
        for payment in payments
    ]

    duplicate_payment_ids = (
        len(payment_ids)
        - len(set(payment_ids))
    )

    invalid_order_references = sum(
        1
        for payment in payments
        if payment["order_id"]
        not in order_ids
    )

    invalid_amounts = sum(
        1
        for payment in payments
        if payment["amount"] < 0
    )

    invalid_currencies = sum(
        1
        for payment in payments
        if payment["currency"] != "GBP"
    )

    failed_with_amount = sum(
        1
        for payment in payments
        if (
            payment["status"] == "FAILED"
            and payment["amount"] != 0
        )
    )

    valid_statuses = {
        "COMPLETED",
        "FAILED",
        "REFUNDED",
        "PENDING",
    }

    invalid_statuses = sum(
        1
        for payment in payments
        if payment["status"]
        not in valid_statuses
    )

    print("\nValidation")
    print("----------")

    print(
        f"Orders read: "
        f"{len(orders):,}"
    )

    print(
        f"Payments generated: "
        f"{len(payments):,}"
    )

    print(
        f"Duplicate payment IDs: "
        f"{duplicate_payment_ids}"
    )

    print(
        f"Invalid order references: "
        f"{invalid_order_references}"
    )

    print(
        f"Invalid amounts: "
        f"{invalid_amounts}"
    )

    print(
        f"Invalid currencies: "
        f"{invalid_currencies}"
    )

    print(
        f"Failed payments with non-zero amount: "
        f"{failed_with_amount}"
    )

    print(
        f"Invalid statuses: "
        f"{invalid_statuses}"
    )


def main() -> None:
    print(
        "RetailFlow Payment Generator"
    )

    print(
        "============================"
    )

    print(
        "\nReading orders from "
        "the e-commerce source..."
    )

    orders = read_orders()

    print(
        f"Orders found: "
        f"{len(orders):,}"
    )

    if not orders:
        raise RuntimeError(
            "No e-commerce orders were found."
        )

    print(
        "\nGenerating payments..."
    )

    payments = generate_payments(
        orders
    )

    output_path = save_payments(
        payments
    )

    print(
        f"Saved payments: "
        f"{output_path}"
    )

    validate_payments(
        orders,
        payments,
    )


if __name__ == "__main__":
    main()