import os
import random
from datetime import datetime, timedelta

import pandas as pd
from dotenv import load_dotenv
from faker import Faker
from sqlalchemy import create_engine, text


# ------------------------------------------------------------
# Configuration
# ------------------------------------------------------------

CUSTOMER_COUNT = 5_000
RANDOM_SEED = 42

START_DATE = datetime(2025, 1, 1)
END_DATE = datetime(2026, 9, 30, 23, 59, 59)


# ------------------------------------------------------------
# Reproducibility
# ------------------------------------------------------------

random.seed(RANDOM_SEED)

fake = Faker("en_GB")
Faker.seed(RANDOM_SEED)


# ------------------------------------------------------------
# Environment
# ------------------------------------------------------------

load_dotenv()


def get_database_url() -> str:
    """Build the PostgreSQL connection URL from environment variables."""

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


# ------------------------------------------------------------
# Date generation
# ------------------------------------------------------------

def random_datetime(start: datetime, end: datetime) -> datetime:
    """Return a random datetime between start and end."""

    difference = end - start
    random_seconds = random.randint(
        0,
        int(difference.total_seconds())
    )

    return start + timedelta(seconds=random_seconds)


# ------------------------------------------------------------
# Customer generation
# ------------------------------------------------------------

def generate_customers(count: int) -> pd.DataFrame:
    """Generate synthetic RetailFlow customer records."""

    customers = []

    for number in range(1, count + 1):

        customer_id = f"CUST{number:07d}"

        created_at = random_datetime(
            START_DATE,
            END_DATE
        )

        # Simulate customers whose records were later updated.
        maximum_update_days = max(
            0,
            (END_DATE - created_at).days
        )

        update_days = random.randint(
            0,
            maximum_update_days
        )

        updated_at = created_at + timedelta(
            days=update_days
        )

        first_name = fake.first_name()
        last_name = fake.last_name()

        customer = {
            "customer_id": customer_id,
            "first_name": first_name,
            "last_name": last_name,
            "email": fake.email(),
            "phone": fake.phone_number(),
            "address_line_1": fake.street_address(),
            "city": fake.city(),
            "postcode": fake.postcode(),
            "country": "United Kingdom",
            "created_at": created_at,
            "updated_at": updated_at,
        }

        customers.append(customer)

    return pd.DataFrame(customers)


# ------------------------------------------------------------
# Database loading
# ------------------------------------------------------------

def load_customers(
    dataframe: pd.DataFrame
) -> None:
    """Load generated customers into PostgreSQL."""

    engine = create_engine(
        get_database_url()
    )

    with engine.begin() as connection:

        # Development generator is intentionally rerunnable.
        connection.execute(
            text("TRUNCATE TABLE customers CASCADE;")
        )

        dataframe.to_sql(
            name="customers",
            con=connection,
            if_exists="append",
            index=False,
            method="multi",
            chunksize=1000,
        )


# ------------------------------------------------------------
# Validation
# ------------------------------------------------------------

def validate_customers() -> None:
    """Perform basic post-load validation."""

    engine = create_engine(
        get_database_url()
    )

    with engine.connect() as connection:

        count = connection.execute(
            text(
                "SELECT COUNT(*) FROM customers;"
            )
        ).scalar_one()

        duplicates = connection.execute(
            text(
                """
                SELECT COUNT(*)
                FROM (
                    SELECT customer_id
                    FROM customers
                    GROUP BY customer_id
                    HAVING COUNT(*) > 1
                ) duplicate_customers;
                """
            )
        ).scalar_one()

        null_ids = connection.execute(
            text(
                """
                SELECT COUNT(*)
                FROM customers
                WHERE customer_id IS NULL;
                """
            )
        ).scalar_one()

    print("\nPost-load validation")
    print("--------------------")
    print(f"Database customer count: {count:,}")
    print(f"Duplicate customer IDs: {duplicates}")
    print(f"Null customer IDs: {null_ids}")


# ------------------------------------------------------------
# Main execution
# ------------------------------------------------------------

def main() -> None:

    print("RetailFlow Customer Generator")
    print("=============================")

    print(
        f"\nGenerating {CUSTOMER_COUNT:,} "
        "synthetic customers..."
    )

    customers_df = generate_customers(
        CUSTOMER_COUNT
    )

    print("\nSample generated records:")
    print(
        customers_df.head(5).to_string(
            index=False
        )
    )

    print("\nLoading customers into PostgreSQL...")

    load_customers(
        customers_df
    )

    print("Customer load completed successfully.")

    validate_customers()


if __name__ == "__main__":
    main()