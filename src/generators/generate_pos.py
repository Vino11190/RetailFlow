import random
from datetime import date, datetime, time, timedelta
from pathlib import Path

import pandas as pd


# ============================================================
# RetailFlow
# Synthetic Point-of-Sale Batch File Generator
# ============================================================

RANDOM_SEED = 42

START_DATE = date(2026, 9, 1)
END_DATE = date(2026, 9, 30)

STORE_COUNT = 12
PRODUCT_COUNT = 500
TARGET_TRANSACTION_COUNT = 20_000

PAYMENT_METHODS = [
    "CARD",
    "CARD",
    "CARD",
    "CONTACTLESS",
    "CONTACTLESS",
    "CASH",
    "MOBILE_WALLET",
]

random.seed(RANDOM_SEED)


PROJECT_ROOT = Path(__file__).resolve().parents[2]

OUTPUT_DIRECTORY = (
    PROJECT_ROOT
    / "sources"
    / "pos"
    / "outbound"
)


def get_dates(
    start_date: date,
    end_date: date,
) -> list[date]:
    """Return all dates in the requested period."""

    dates = []

    current_date = start_date

    while current_date <= end_date:
        dates.append(current_date)
        current_date += timedelta(days=1)

    return dates


def allocate_daily_counts(
    dates: list[date],
    target_count: int,
) -> dict[date, int]:
    """
    Allocate transaction volumes across dates.

    Weekends receive somewhat higher transaction volumes.
    """

    weights = []

    for transaction_date in dates:
        if transaction_date.weekday() >= 5:
            weights.append(1.30)
        else:
            weights.append(1.00)

    total_weight = sum(weights)

    counts = {}

    allocated = 0

    for transaction_date, weight in zip(
        dates[:-1],
        weights[:-1],
    ):
        count = round(
            target_count
            * weight
            / total_weight
        )

        counts[transaction_date] = count
        allocated += count

    counts[dates[-1]] = (
        target_count - allocated
    )

    return counts


def random_transaction_time(
    transaction_date: date,
) -> datetime:
    """Generate a transaction time during store opening hours."""

    opening = datetime.combine(
        transaction_date,
        time(hour=8),
    )

    closing = datetime.combine(
        transaction_date,
        time(hour=21, minute=30),
    )

    seconds = int(
        (closing - opening).total_seconds()
    )

    return opening + timedelta(
        seconds=random.randint(0, seconds)
    )


def generate_transaction(
    transaction_number: int,
    transaction_date: date,
) -> dict:
    """Generate one synthetic POS transaction."""

    transaction_id = (
        f"POS{transaction_number:09d}"
    )

    store_id = (
        f"STORE{random.randint(1, STORE_COUNT):03d}"
    )

    product_id = (
        f"PROD{random.randint(1, PRODUCT_COUNT):05d}"
    )

    transaction_timestamp = (
        random_transaction_time(
            transaction_date
        )
    )

    quantity = random.choices(
        population=[1, 2, 3, 4, 5],
        weights=[68, 20, 7, 3, 2],
        k=1,
    )[0]

    unit_price = round(
        random.uniform(2.99, 499.99),
        2,
    )

    gross_amount = round(
        quantity * unit_price,
        2,
    )

    discount_rate = random.choices(
        population=[
            0.00,
            0.05,
            0.10,
            0.15,
        ],
        weights=[
            75,
            10,
            10,
            5,
        ],
        k=1,
    )[0]

    discount = round(
        gross_amount * discount_rate,
        2,
    )

    total_amount = round(
        gross_amount - discount,
        2,
    )

    payment_method = random.choice(
        PAYMENT_METHODS
    )

    return {
        "transaction_id": transaction_id,
        "store_id": store_id,
        "product_id": product_id,
        "transaction_timestamp": (
            transaction_timestamp.isoformat()
        ),
        "quantity": quantity,
        "unit_price": unit_price,
        "discount": discount,
        "total_amount": total_amount,
        "payment_method": payment_method,
    }


def generate_pos_files() -> None:
    """Generate one POS CSV file per business date."""

    OUTPUT_DIRECTORY.mkdir(
        parents=True,
        exist_ok=True,
    )

    dates = get_dates(
        START_DATE,
        END_DATE,
    )

    daily_counts = allocate_daily_counts(
        dates,
        TARGET_TRANSACTION_COUNT,
    )

    transaction_number = 1
    total_generated = 0

    print(
        "RetailFlow POS Batch Generator"
    )
    print(
        "=============================="
    )

    for transaction_date in dates:

        daily_records = []

        daily_count = daily_counts[
            transaction_date
        ]

        for _ in range(daily_count):

            record = generate_transaction(
                transaction_number,
                transaction_date,
            )

            daily_records.append(
                record
            )

            transaction_number += 1

        dataframe = pd.DataFrame(
            daily_records
        )

        filename = (
            "pos_transactions_"
            f"{transaction_date.isoformat()}"
            ".csv"
        )

        output_path = (
            OUTPUT_DIRECTORY
            / filename
        )

        dataframe.to_csv(
            output_path,
            index=False,
        )

        total_generated += len(
            dataframe
        )

        print(
            f"{filename}: "
            f"{len(dataframe):,} rows"
        )

    print(
        "\nGeneration complete"
    )
    print(
        "-------------------"
    )
    print(
        f"Files generated: "
        f"{len(dates)}"
    )
    print(
        f"Transactions generated: "
        f"{total_generated:,}"
    )


if __name__ == "__main__":
    generate_pos_files()