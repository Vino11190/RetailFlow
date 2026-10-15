import os
import random
from datetime import timedelta
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine, text


# ============================================================
# RetailFlow
# Synthetic Returns Source Generator
# ============================================================

RETURN_COUNT = 2_000
RANDOM_SEED = 42

RETURN_REASONS = [
    "DAMAGED",
    "WRONG_ITEM",
    "NOT_AS_EXPECTED",
    "SIZE_FIT",
    "CHANGED_MIND",
    "LATE_DELIVERY",
]

RETURN_REASON_WEIGHTS = [
    12,
    8,
    25,
    18,
    30,
    7,
]

random.seed(RANDOM_SEED)

load_dotenv()


PROJECT_ROOT = Path(__file__).resolve().parents[2]

OUTPUT_DIRECTORY = (
    PROJECT_ROOT
    / "sources"
    / "returns"
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


def read_return_candidates() -> list[dict]:
    """
    Read real order items that are eligible
    to become synthetic returns.

    Cancelled orders are excluded because they
    should not normally produce a physical return.
    """

    engine = create_engine(
        get_database_url()
    )

    query = text(
        """
        SELECT
            o.order_id,
            o.customer_id,
            o.order_timestamp,
            o.status AS order_status,
            oi.order_item_id,
            oi.product_id,
            oi.quantity,
            oi.unit_price,
            oi.discount,
            oi.line_total
        FROM orders o
        INNER JOIN order_items oi
            ON o.order_id = oi.order_id
        WHERE o.status <> 'CANCELLED'
          AND o.customer_id IS NOT NULL
        ORDER BY oi.order_item_id;
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


def generate_returns(
    candidates: list[dict],
) -> list[dict]:
    """Generate returns from genuine order-item records."""

    if len(candidates) < RETURN_COUNT:
        raise RuntimeError(
            "Not enough eligible order items "
            "to generate the requested returns."
        )

    selected_items = random.sample(
        candidates,
        RETURN_COUNT,
    )

    returns = []

    for number, item in enumerate(
        selected_items,
        start=1,
    ):
        return_id = (
            f"RET{number:08d}"
        )

        purchased_quantity = int(
            item["quantity"]
        )

        return_quantity = random.randint(
            1,
            purchased_quantity,
        )

        reason = random.choices(
            population=RETURN_REASONS,
            weights=RETURN_REASON_WEIGHTS,
            k=1,
        )[0]

        # Returns occur between 1 and 45 days
        # after the original order.
        return_date = (
            item["order_timestamp"].date()
            + timedelta(
                days=random.randint(1, 45)
            )
        )

        line_total = Decimal(
            str(item["line_total"])
        )

        quantity = Decimal(
            str(purchased_quantity)
        )

        returned_quantity = Decimal(
            str(return_quantity)
        )

        # Refund is proportional to the quantity
        # returned from the original line item.
        refund_amount = (
            (
                line_total
                / quantity
            )
            * returned_quantity
        ).quantize(
            Decimal("0.01"),
            rounding=ROUND_HALF_UP,
        )

        returns.append(
            {
                "return_id": return_id,
                "order_id": item["order_id"],
                "product_id": item["product_id"],
                "customer_id": item["customer_id"],
                "return_date": (
                    return_date.isoformat()
                ),
                "quantity": return_quantity,
                "reason": reason,
                "refund_amount": float(
                    refund_amount
                ),
            }
        )

    return returns


def save_returns(
    returns: list[dict],
) -> Path:
    """Save returns as a CSV source file."""

    OUTPUT_DIRECTORY.mkdir(
        parents=True,
        exist_ok=True,
    )

    output_path = (
        OUTPUT_DIRECTORY
        / "returns.csv"
    )

    dataframe = pd.DataFrame(
        returns
    )

    dataframe.to_csv(
        output_path,
        index=False,
    )

    return output_path


def validate_returns(
    candidates: list[dict],
    returns: list[dict],
) -> None:
    """Run basic return source validation."""

    candidate_lookup = {
        (
            item["order_id"],
            item["product_id"],
        ): item
        for item in candidates
    }

    return_ids = [
        record["return_id"]
        for record in returns
    ]

    duplicate_return_ids = (
        len(return_ids)
        - len(set(return_ids))
    )

    invalid_order_product_pairs = 0
    invalid_customers = 0
    invalid_quantities = 0
    invalid_refunds = 0
    invalid_return_dates = 0

    for record in returns:

        key = (
            record["order_id"],
            record["product_id"],
        )

        source_item = (
            candidate_lookup.get(key)
        )

        if source_item is None:
            invalid_order_product_pairs += 1
            continue

        if (
            record["customer_id"]
            != source_item["customer_id"]
        ):
            invalid_customers += 1

        if (
            record["quantity"] <= 0
            or record["quantity"]
            > int(source_item["quantity"])
        ):
            invalid_quantities += 1

        if record["refund_amount"] < 0:
            invalid_refunds += 1

        source_order_date = (
            source_item[
                "order_timestamp"
            ].date()
        )

        return_date = pd.to_datetime(
            record["return_date"]
        ).date()

        if return_date <= source_order_date:
            invalid_return_dates += 1

    print("\nValidation")
    print("----------")

    print(
        f"Eligible order items read: "
        f"{len(candidates):,}"
    )

    print(
        f"Returns generated: "
        f"{len(returns):,}"
    )

    print(
        f"Duplicate return IDs: "
        f"{duplicate_return_ids}"
    )

    print(
        f"Invalid order/product references: "
        f"{invalid_order_product_pairs}"
    )

    print(
        f"Invalid customer references: "
        f"{invalid_customers}"
    )

    print(
        f"Invalid return quantities: "
        f"{invalid_quantities}"
    )

    print(
        f"Invalid refund amounts: "
        f"{invalid_refunds}"
    )

    print(
        f"Invalid return dates: "
        f"{invalid_return_dates}"
    )


def main() -> None:
    print(
        "RetailFlow Returns Generator"
    )

    print(
        "============================"
    )

    print(
        "\nReading eligible order items "
        "from e-commerce..."
    )

    candidates = (
        read_return_candidates()
    )

    print(
        f"Eligible order items found: "
        f"{len(candidates):,}"
    )

    print(
        "\nGenerating returns..."
    )

    returns = generate_returns(
        candidates
    )

    output_path = save_returns(
        returns
    )

    print(
        f"Saved returns: "
        f"{output_path}"
    )

    validate_returns(
        candidates,
        returns,
    )


if __name__ == "__main__":
    main()
