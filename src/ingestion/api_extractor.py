import requests
import pandas as pd


# ============================================================
# RetailFlow
# REST API Source Extractor
# ============================================================


def extract_json_endpoint(
    url: str,
    timeout: int = 30,
) -> pd.DataFrame:
    """
    Extract a non-paginated JSON endpoint
    and return the records as a pandas DataFrame.

    Supports:
    - a direct JSON list
    - a JSON object containing records in a 'data' field
    """

    response = requests.get(
        url,
        timeout=timeout,
    )

    response.raise_for_status()

    payload = response.json()

    if isinstance(payload, list):
        records = payload

    elif (
        isinstance(payload, dict)
        and isinstance(payload.get("data"), list)
    ):
        records = payload["data"]

    else:
        raise ValueError(
            f"Expected a JSON list or an object "
            f"containing a 'data' list from {url}."
        )

    return pd.DataFrame(records)


def extract_paginated_products(
    base_url: str,
    page_size: int = 100,
    timeout: int = 30,
) -> pd.DataFrame:
    """
    Extract all products from the paginated
    RetailFlow Product API.

    Expected response structure:

    {
        "page": 1,
        "page_size": 100,
        "total_records": 500,
        "total_pages": 5,
        "data": [...]
    }
    """

    all_records = []

    page = 1

    while True:

        response = requests.get(
            f"{base_url}/products",
            params={
                "page": page,
                "page_size": page_size,
            },
            timeout=timeout,
        )

        response.raise_for_status()

        payload = response.json()

        if not isinstance(payload, dict):
            raise ValueError(
                "Expected /products to return "
                "a JSON object."
            )

        records = payload.get("data")

        if not isinstance(records, list):
            raise ValueError(
                "Expected /products response "
                "to contain a 'data' list."
            )

        total_pages = payload.get(
            "total_pages"
        )

        total_records = payload.get(
            "total_records"
        )

        print(
            f"API page {page}: "
            f"{len(records):,} products extracted."
        )

        all_records.extend(records)

        # Stop when the API reports that
        # we have reached the final page.
        if total_pages is not None:

            if page >= total_pages:
                break

        # Fallback in case pagination metadata
        # is unavailable.
        elif len(records) < page_size:
            break

        page += 1

    dataframe = pd.DataFrame(
        all_records
    )

    # Verify that the API's reported total agrees
    # with the number of records we extracted.
    if (
        total_records is not None
        and len(dataframe) != total_records
    ):
        raise ValueError(
            "Product API extraction count mismatch. "
            f"API reported {total_records:,} records, "
            f"but extractor received "
            f"{len(dataframe):,}."
        )

    return dataframe