
"""
RetailFlow Bronze-to-Silver Cleaning Engine.

Returns:
- Cleaned DataFrame
- Quarantined DataFrame
- Data quality metrics

No database writes are performed here.
"""

from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

import pandas as pd

from src.config.transformation_config import get_transformation
from src.config.silver_cleaning_config import (
    TIMESTAMP_COLUMNS,
    DATE_COLUMNS,
    MONETARY_COLUMNS,
    REQUIRED_COLUMNS,
    BOOLEAN_COLUMNS,
    REQUIRED_MONETARY_COLUMNS,
)


def _missing(value):
    if value is None:
        return True

    if isinstance(value, str):
        return not value.strip()

    result = pd.isna(value)

    if isinstance(result, bool):
        return result

    return False


def _clean_text(value):
    if _missing(value):
        return None

    if isinstance(value, str):
        return value.strip()

    return value


def _money(value):
    if _missing(value):
        return None

    try:
        amount = Decimal(str(value))

        if not amount.is_finite():
            return None

        return amount.quantize(
            Decimal("0.01"),
            rounding=ROUND_HALF_UP,
        )

    except (InvalidOperation, ValueError, TypeError):
        return None


def _boolean(value):
    if _missing(value):
        return None

    if isinstance(value, bool):
        return value

    if str(value).strip().lower() in ("true", "1", "yes"):
        return True

    if str(value).strip().lower() in ("false", "0", "no"):
        return False

    return None


def _timestamp(value):
    if _missing(value):
        return pd.NaT

    return pd.to_datetime(
        value,
        utc=True,
        errors="coerce",
    )


def _date(value):
    if _missing(value):
        return pd.NaT

    parsed = pd.to_datetime(
        value,
        errors="coerce",
    )

    if pd.isna(parsed):
        return pd.NaT

    return parsed.date()


def clean_bronze_dataframe(
    source_system,
    dataset_name,
    dataframe,
):
    """
    Clean one registered Bronze dataset.

    Invalid records are quarantined rather than
    silently dropped.
    """

    definition = get_transformation(
        source_system,
        dataset_name,
    )

    key = (source_system, dataset_name)

    frame = dataframe.copy()

    initial_count = len(frame)

    required = REQUIRED_COLUMNS.get(key, ())
    timestamp_columns = TIMESTAMP_COLUMNS.get(key, ())
    date_columns = DATE_COLUMNS.get(key, ())
    money_columns = MONETARY_COLUMNS.get(key, ())
    boolean_columns = BOOLEAN_COLUMNS.get(key, ())
    required_money = REQUIRED_MONETARY_COLUMNS.get(key, ())

    configured_columns = set(
        required
        + timestamp_columns
        + date_columns
        + money_columns
        + boolean_columns
        + definition.primary_key
    )

    missing_columns = configured_columns - set(frame.columns)

    if missing_columns:
        raise ValueError(
            f"{key}: missing expected columns: "
            f"{sorted(missing_columns)}"
        )

    # ----------------------------------------
    # 1. Standardise text columns
    # ----------------------------------------

    for column in frame.columns:
        if column.startswith("_"):
            continue

        if (
            pd.api.types.is_object_dtype(frame[column])
            or pd.api.types.is_string_dtype(frame[column])
        ):
            frame[column] = frame[column].map(_clean_text)

    # ----------------------------------------
    # 2. Standardise timestamps
    # ----------------------------------------

    for column in timestamp_columns:
        frame[column] = pd.to_datetime(
            frame[column],
            utc=True,
            errors="coerce",
        )

    # ----------------------------------------
    # 3. Standardise dates
    # ----------------------------------------

    for column in date_columns:
        frame[column] = frame[column].map(_date)

    # ----------------------------------------
    # 4. Standardise monetary fields
    # ----------------------------------------

    for column in money_columns:
        frame[column] = frame[column].map(_money)

    # ----------------------------------------
    # 5. Standardise booleans
    # ----------------------------------------

    for column in boolean_columns:
        frame[column] = frame[column].map(_boolean)

    # ----------------------------------------
    # 6. Validate required fields
    # ----------------------------------------

    invalid_mask = pd.Series(
        False,
        index=frame.index,
    )

    reasons = pd.Series(
        "",
        index=frame.index,
        dtype="object",
    )

    for column in required:
        missing_mask = frame[column].map(_missing)

        invalid_mask |= missing_mask

        reasons.loc[missing_mask] += (
            f"missing_or_invalid_{column};"
        )

    for column in required_money:
        missing_mask = frame[column].map(_missing)

        invalid_mask |= missing_mask

        reasons.loc[missing_mask] += (
            f"invalid_monetary_{column};"
        )

    # ----------------------------------------
    # 7. Separate quarantined records
    # ----------------------------------------

    quarantine = frame.loc[invalid_mask].copy()

    quarantine["_quarantine_reason"] = reasons.loc[
        invalid_mask
    ].str.rstrip(";")

    clean = frame.loc[~invalid_mask].copy()

    # ----------------------------------------
    # 8. Deduplicate by business key
    # ----------------------------------------

    before_deduplication = len(clean)

    # Stable ordering: latest ingestion timestamp,
    # then source record number when available.

    sort_columns = [
        column
        for column in (
            "_ingestion_timestamp",
            "_source_record_number",
        )
        if column in clean.columns
    ]

    if sort_columns:
        clean = clean.sort_values(
            sort_columns,
            kind="stable",
        )

    duplicate_mask = clean.duplicated(
        subset=list(definition.primary_key),
        keep="last",
    )

    duplicate_count = int(duplicate_mask.sum())

    duplicate_rows = clean.loc[duplicate_mask].copy()

    if not duplicate_rows.empty:
        duplicate_rows["_quarantine_reason"] = (
            "duplicate_business_key"
        )

        quarantine = pd.concat(
            [quarantine, duplicate_rows],
            ignore_index=True,
        )

    clean = clean.loc[~duplicate_mask].copy()

    # ----------------------------------------
    # 9. Build quality metrics
    # ----------------------------------------

    metrics = {
        "source_system": source_system,
        "dataset_name": dataset_name,
        "input_records": initial_count,
        "clean_records": len(clean),
        "quarantined_records": len(quarantine),
        "duplicate_records": duplicate_count,
        "invalid_records": (
            initial_count - before_deduplication
        ),
    }

    assert (
        metrics["clean_records"]
        + metrics["quarantined_records"]
        == metrics["input_records"]
    ), "Record reconciliation failed"

    return {
        "clean": clean.reset_index(drop=True),
        "quarantine": quarantine.reset_index(drop=True),
        "metrics": metrics,
    }
