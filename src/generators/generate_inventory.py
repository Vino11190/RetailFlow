import os
import random
from datetime import datetime, timedelta

import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine, text


# ============================================================
# RetailFlow
# Synthetic Inventory Source Generator
# ============================================================

PRODUCT_COUNT = 500
STORE_COUNT = 12
MOVEMENT_COUNT = 50_000
RANDOM_SEED = 42

START_DATE = datetime(2025, 1, 1)
END_DATE = datetime(2026, 9, 30, 23, 59, 59)

MOVEMENT_TYPES = [
    "SALE",
    "RETURN",
    "DELIVERY",
    "TRANSFER_IN",
    "TRANSFER_OUT",
    "ADJUSTMENT",
]

MOVEMENT_WEIGHTS = [
    50,
    10,
    20,
    7,
    7,
    6,
]

random.seed(RANDOM_SEED)

load_dotenv()


def get_database_url() -> str:
    """Build the inventory PostgreSQL connection URL."""

    user = os.getenv("POSTGRES_USER")
    password = os.getenv("POSTGRES_PASSWORD")

    if not all([user, password]):
        raise ValueError(
            "Missing PostgreSQL credentials in .env."
        )

    return (
        f"postgresql+psycopg2://{user}:{password}"
        "@localhost:5432/retailflow_inventory"
    )


def random_datetime(
    start: datetime,
    end: datetime,
) -> datetime:
    """Return a random datetime between two timestamps."""

    seconds = random.randint(
        0,
        int((end - start).total_seconds()),
    )

    return start + timedelta(seconds=seconds)


def generate_inventory() -> pd.DataFrame:
    """Generate current inventory state for every product/store pair."""

    records = []

    for product_number in range(
        1,
        PRODUCT_COUNT + 1,
    ):
        product_id = (
            f"PROD{product_number:05d}"
        )

        for store_number in range(
            1,
            STORE_COUNT + 1,
        ):
            store_id = (
                f"STORE{store_number:03d}"
            )

            reorder_level = random.randint(
                5,
                30,
            )

            quantity_on_hand = random.randint(
                0,
                200,
            )

            # Current-state records should have relatively
            # recent last-updated timestamps.
            last_updated = END_DATE - timedelta(
                days=random.randint(0, 30),
                seconds=random.randint(
                    0,
                    86_399,
                ),
            )

            records.append(
                {
                    "product_id": product_id,
                    "store_id": store_id,
                    "quantity_on_hand": quantity_on_hand,
                    "reorder_level": reorder_level,
                    "last_updated": last_updated,
                }
            )

    return pd.DataFrame(records)


def generate_movements() -> pd.DataFrame:
    """Generate historical inventory movement events."""

    records = []

    for number in range(
        1,
        MOVEMENT_COUNT + 1,
    ):
        movement_id = (
            f"MOV{number:010d}"
        )

        product_id = (
            f"PROD{random.randint(1, PRODUCT_COUNT):05d}"
        )

        store_id = (
            f"STORE{random.randint(1, STORE_COUNT):03d}"
        )

        movement_type = random.choices(
            population=MOVEMENT_TYPES,
            weights=MOVEMENT_WEIGHTS,
            k=1,
        )[0]

        if movement_type == "DELIVERY":
            quantity = random.randint(
                10,
                100,
            )

        elif movement_type in {
            "TRANSFER_IN",
            "TRANSFER_OUT",
        }:
            quantity = random.randint(
                1,
                30,
            )

        elif movement_type == "ADJUSTMENT":
            quantity = random.randint(
                1,
                15,
            )

        else:
            quantity = random.randint(
                1,
                5,
            )

        movement_timestamp = random_datetime(
            START_DATE,
            END_DATE,
        )

        records.append(
            {
                "movement_id": movement_id,
                "product_id": product_id,
                "store_id": store_id,
                "movement_type": movement_type,
                "quantity": quantity,
                "movement_timestamp": movement_timestamp,
            }
        )

    dataframe = pd.DataFrame(records)

    return dataframe.sort_values(
        by="movement_timestamp"
    ).reset_index(
        drop=True
    )


def load_inventory(
    inventory_df: pd.DataFrame,
    movements_df: pd.DataFrame,
) -> None:
    """Load generated inventory data into PostgreSQL."""

    engine = create_engine(
        get_database_url()
    )

    with engine.begin() as connection:

        connection.execute(
            text(
                """
                TRUNCATE TABLE
                    inventory_movements,
                    inventory;
                """
            )
        )

        inventory_df.to_sql(
            name="inventory",
            con=connection,
            if_exists="append",
            index=False,
            method="multi",
            chunksize=1000,
        )

        movements_df.to_sql(
            name="inventory_movements",
            con=connection,
            if_exists="append",
            index=False,
            method="multi",
            chunksize=1000,
        )


def validate_inventory() -> None:
    """Run basic post-load validation checks."""

    engine = create_engine(
        get_database_url()
    )

    with engine.connect() as connection:

        inventory_count = connection.execute(
            text(
                "SELECT COUNT(*) FROM inventory;"
            )
        ).scalar_one()

        movement_count = connection.execute(
            text(
                """
                SELECT COUNT(*)
                FROM inventory_movements;
                """
            )
        ).scalar_one()

        duplicate_positions = connection.execute(
            text(
                """
                SELECT COUNT(*)
                FROM (
                    SELECT
                        product_id,
                        store_id
                    FROM inventory
                    GROUP BY
                        product_id,
                        store_id
                    HAVING COUNT(*) > 1
                ) duplicates;
                """
            )
        ).scalar_one()

        invalid_inventory = connection.execute(
            text(
                """
                SELECT COUNT(*)
                FROM inventory
                WHERE quantity_on_hand < 0
                   OR reorder_level < 0;
                """
            )
        ).scalar_one()

        invalid_movements = connection.execute(
            text(
                """
                SELECT COUNT(*)
                FROM inventory_movements
                WHERE quantity <= 0;
                """
            )
        ).scalar_one()

        invalid_products = connection.execute(
            text(
                """
                SELECT COUNT(*)
                FROM inventory
                WHERE product_id NOT LIKE 'PROD%';
                """
            )
        ).scalar_one()

    print("\nPost-load validation")
    print("--------------------")
    print(
        f"Inventory positions: "
        f"{inventory_count:,}"
    )
    print(
        f"Inventory movements: "
        f"{movement_count:,}"
    )
    print(
        f"Duplicate positions: "
        f"{duplicate_positions}"
    )
    print(
        f"Invalid inventory quantities: "
        f"{invalid_inventory}"
    )
    print(
        f"Invalid movement quantities: "
        f"{invalid_movements}"
    )
    print(
        f"Invalid product identifiers: "
        f"{invalid_products}"
    )


def main() -> None:
    print(
        "RetailFlow Inventory Generator"
    )
    print(
        "=============================="
    )

    print(
        "\nGenerating current inventory..."
    )

    inventory_df = generate_inventory()

    print(
        f"Generated inventory positions: "
        f"{len(inventory_df):,}"
    )

    print(
        "\nGenerating inventory movement history..."
    )

    movements_df = generate_movements()

    print(
        f"Generated movements: "
        f"{len(movements_df):,}"
    )

    print(
        "\nLoading inventory source database..."
    )

    load_inventory(
        inventory_df,
        movements_df,
    )

    print(
        "Inventory load completed successfully."
    )

    validate_inventory()


if __name__ == "__main__":
    main()