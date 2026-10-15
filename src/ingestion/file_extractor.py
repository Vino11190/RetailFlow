from pathlib import Path

import pandas as pd


# ============================================================
# RetailFlow
# File-Based Source Extractor
# ============================================================


def extract_csv(
    file_path: str | Path,
) -> pd.DataFrame:
    """
    Read a CSV source file into a pandas DataFrame.
    """

    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(
            f"CSV source file does not exist: {path}"
        )

    if not path.is_file():
        raise ValueError(
            f"CSV source path is not a file: {path}"
        )

    if path.suffix.lower() != ".csv":
        raise ValueError(
            f"Expected a CSV file but received: {path.name}"
        )

    dataframe = pd.read_csv(path)

    return dataframe


def extract_json(
    file_path: str | Path,
) -> pd.DataFrame:
    """
    Read a JSON source file into a pandas DataFrame.

    Supports:
    - JSON lists
    - JSON objects containing a 'data' list
    """

    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(
            f"JSON source file does not exist: {path}"
        )

    if not path.is_file():
        raise ValueError(
            f"JSON source path is not a file: {path}"
        )

    if path.suffix.lower() != ".json":
        raise ValueError(
            f"Expected a JSON file but received: {path.name}"
        )

    payload = pd.read_json(
        path,
        typ="series",
    )

    raw_data = payload.to_dict()

    # Case 1:
    # JSON object containing a "data" list.
    if (
        isinstance(raw_data, dict)
        and "data" in raw_data
        and isinstance(raw_data["data"], list)
    ):
        return pd.DataFrame(
            raw_data["data"]
        )

    # Fall back to pandas' normal JSON reader.
    try:
        dataframe = pd.read_json(path)
    except ValueError as exc:
        raise ValueError(
            f"Unable to convert JSON source "
            f"to tabular records: {path}"
        ) from exc

    return dataframe


def discover_files(
    directory: str | Path,
    extension: str,
) -> list[Path]:
    """
    Discover source files with a specified extension.

    Results are returned in sorted filename order.
    """

    path = Path(directory)

    if not path.exists():
        raise FileNotFoundError(
            f"Source directory does not exist: {path}"
        )

    if not path.is_dir():
        raise ValueError(
            f"Source path is not a directory: {path}"
        )

    normalized_extension = (
        extension.lower().lstrip(".")
    )

    files = sorted(
        file
        for file in path.iterdir()
        if (
            file.is_file()
            and file.suffix.lower()
            == f".{normalized_extension}"
        )
    )

    return files