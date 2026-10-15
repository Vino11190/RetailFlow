import os

from dotenv import load_dotenv
from sqlalchemy import create_engine, text


load_dotenv()


def get_database_url() -> str:
    user = os.getenv("POSTGRES_USER")
    password = os.getenv("POSTGRES_PASSWORD")
    database = os.getenv("POSTGRES_DB")

    if not all([user, password, database]):
        raise ValueError(
            "Missing PostgreSQL environment variables. "
            "Check POSTGRES_USER, POSTGRES_PASSWORD and POSTGRES_DB in .env."
        )

    return (
        f"postgresql+psycopg2://{user}:{password}"
        f"@localhost:5432/{database}"
    )


def test_connection() -> None:
    engine = create_engine(get_database_url())

    with engine.connect() as connection:
        result = connection.execute(
            text("SELECT current_database(), current_user;")
        ).fetchone()

        print("RetailFlow PostgreSQL connection successful.")
        print(f"Database: {result[0]}")
        print(f"User: {result[1]}")

        tables = connection.execute(
            text(
                """
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'public'
                ORDER BY table_name;
                """
            )
        ).fetchall()

        print("\nAvailable tables:")

        for table in tables:
            print(f" - {table[0]}")


if __name__ == "__main__":
    test_connection()