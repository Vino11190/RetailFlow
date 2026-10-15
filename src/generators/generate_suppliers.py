import json
import random
from datetime import date, timedelta
from pathlib import Path

import pandas as pd
from faker import Faker


# ============================================================
# RetailFlow
# Synthetic Supplier & Delivery Source Generator
# ============================================================

RANDOM_SEED = 42

SUPPLIER_COUNT = 50
DELIVERY_COUNT = 5_000
PRODUCT_COUNT = 500

START_DATE = date(2025, 1, 1)
END_DATE = date(2026, 9, 30)

COUNTRIES = [
    "United Kingdom",
    "Germany",
    "France",
    "Netherlands",
    "Spain",
    "Italy",
    "Poland",
    "Ireland",
]

DELIVERY_STATUSES = [
    "DELIVERED",
    "DELIVERED",
    "DELIVERED",
    "DELIVERED",
    "LATE",
    "CANCELLED",
    "IN_TRANSIT",
]

random.seed(RANDOM_SEED)

fake = Faker("en_GB")
Faker.seed(RANDOM_SEED)


PROJECT_ROOT = Path(__file__).resolve().parents[2]

OUTPUT_DIRECTORY = (
    PROJECT_ROOT
    / "sources"
    / "suppliers"
    / "outbound"
)


def random_date(
    start: date,
    end: date,
) -> date:
    """Generate a random date between two dates."""

    difference = (end - start).days

    return start + timedelta(
        days=random.randint(0, difference)
    )


def generate_suppliers() -> pd.DataFrame:
    """Generate supplier master records."""

    suppliers = []

    for number in range(
        1,
        SUPPLIER_COUNT + 1,
    ):
        supplier_id = (
            f"SUP{number:04d}"
        )

        supplier_name = (
            f"{fake.company()} Supply"
        )

        country = random.choice(
            COUNTRIES
        )

        lead_time_days = random.randint(
            2,
            30,
        )

        active = random.choices(
            population=[True, False],
            weights=[94, 6],
            k=1,
        )[0]

        suppliers.append(
            {
                "supplier_id": supplier_id,
                "supplier_name": supplier_name,
                "contact_email": fake.company_email(),
                "country": country,
                "lead_time_days": lead_time_days,
                "active": active,
            }
        )

    return pd.DataFrame(suppliers)


def generate_deliveries(
    supplier_ids: list[str],
) -> list[dict]:
    """Generate supplier delivery records."""

    deliveries = []

    for number in range(
        1,
        DELIVERY_COUNT + 1,
    ):
        delivery_id = (
            f"DEL{number:08d}"
        )

        supplier_id = random.choice(
            supplier_ids
        )

        product_id = (
            f"PROD{random.randint(1, PRODUCT_COUNT):05d}"
        )

        expected_date = random_date(
            START_DATE,
            END_DATE,
        )

        status = random.choice(
            DELIVERY_STATUSES
        )

        if status == "DELIVERED":
            actual_date = (
                expected_date
                + timedelta(
                    days=random.randint(-2, 2)
                )
            )

        elif status == "LATE":
            actual_date = (
                expected_date
                + timedelta(
                    days=random.randint(3, 14)
                )
            )

        else:
            actual_date = None

        quantity = random.randint(
            10,
            500,
        )

        deliveries.append(
            {
                "delivery_id": delivery_id,
                "supplier_id": supplier_id,
                "product_id": product_id,
                "expected_date": (
                    expected_date.isoformat()
                ),
                "actual_date": (
                    actual_date.isoformat()
                    if actual_date
                    else None
                ),
                "quantity": quantity,
                "status": status,
            }
        )

    return deliveries


def save_suppliers(
    suppliers_df: pd.DataFrame,
) -> Path:
    """Save supplier master data as CSV."""

    OUTPUT_DIRECTORY.mkdir(
        parents=True,
        exist_ok=True,
    )

    output_path = (
        OUTPUT_DIRECTORY
        / "suppliers.csv"
    )

    suppliers_df.to_csv(
        output_path,
        index=False,
    )

    return output_path


def save_deliveries(
    deliveries: list[dict],
) -> Path:
    """Save delivery records as JSON."""

    output_path = (
        OUTPUT_DIRECTORY
        / "deliveries.json"
    )

    with output_path.open(
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            deliveries,
            file,
            indent=2,
        )

    return output_path


def validate_data(
    suppliers_df: pd.DataFrame,
    deliveries: list[dict],
) -> None:
    """Validate generated supplier and delivery data."""

    supplier_ids = (
        suppliers_df["supplier_id"]
        .tolist()
    )

    duplicate_suppliers = (
        len(supplier_ids)
        - len(set(supplier_ids))
    )

    delivery_ids = [
        delivery["delivery_id"]
        for delivery in deliveries
    ]

    duplicate_deliveries = (
        len(delivery_ids)
        - len(set(delivery_ids))
    )

    invalid_supplier_references = sum(
        1
        for delivery in deliveries
        if delivery["supplier_id"]
        not in supplier_ids
    )

    invalid_product_ids = sum(
        1
        for delivery in deliveries
        if not delivery[
            "product_id"
        ].startswith("PROD")
    )

    invalid_quantities = sum(
        1
        for delivery in deliveries
        if delivery["quantity"] <= 0
    )

    print("\nValidation")
    print("----------")

    print(
        f"Suppliers generated: "
        f"{len(suppliers_df):,}"
    )

    print(
        f"Deliveries generated: "
        f"{len(deliveries):,}"
    )

    print(
        f"Duplicate supplier IDs: "
        f"{duplicate_suppliers}"
    )

    print(
        f"Duplicate delivery IDs: "
        f"{duplicate_deliveries}"
    )

    print(
        f"Invalid supplier references: "
        f"{invalid_supplier_references}"
    )

    print(
        f"Invalid product identifiers: "
        f"{invalid_product_ids}"
    )

    print(
        f"Invalid quantities: "
        f"{invalid_quantities}"
    )


def main() -> None:
    print(
        "RetailFlow Supplier Generator"
    )

    print(
        "============================="
    )

    suppliers_df = (
        generate_suppliers()
    )

    supplier_ids = (
        suppliers_df[
            "supplier_id"
        ].tolist()
    )

    deliveries = (
        generate_deliveries(
            supplier_ids
        )
    )

    supplier_path = (
        save_suppliers(
            suppliers_df
        )
    )

    delivery_path = (
        save_deliveries(
            deliveries
        )
    )

    print(
        f"\nSaved suppliers: "
        f"{supplier_path}"
    )

    print(
        f"Saved deliveries: "
        f"{delivery_path}"
    )

    validate_data(
        suppliers_df,
        deliveries,
    )


if __name__ == "__main__":
    main()