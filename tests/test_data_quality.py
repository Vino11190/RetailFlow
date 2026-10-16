
import pandas as pd


def validate_required_columns(
    dataframe: pd.DataFrame,
    required_columns: list[str],
) -> bool:
    """Check that all required columns exist in a dataset."""
    return all(
        column in dataframe.columns
        for column in required_columns
    )


def test_valid_customer_dataset():
    dataframe = pd.DataFrame(
        {
            "customer_id": ["C001", "C002"],
            "first_name": ["Alice", "James"],
            "last_name": ["Brown", "Wilson"],
        }
    )

    required_columns = [
        "customer_id",
        "first_name",
        "last_name",
    ]

    assert validate_required_columns(
        dataframe,
        required_columns,
    )


def test_missing_required_column():
    dataframe = pd.DataFrame(
        {
            "customer_id": ["C001"],
            "first_name": ["Alice"],
        }
    )

    required_columns = [
        "customer_id",
        "first_name",
        "last_name",
    ]

    assert not validate_required_columns(
        dataframe,
        required_columns,
    )


def test_empty_dataframe_with_required_columns():
    dataframe = pd.DataFrame(
        columns=[
            "customer_id",
            "first_name",
            "last_name",
        ]
    )

    assert validate_required_columns(
        dataframe,
        [
            "customer_id",
            "first_name",
            "last_name",
        ],
    )
