import json
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException, Query


# ============================================================
# RetailFlow Product Catalogue API
# ============================================================

app = FastAPI(
    title="RetailFlow Product Catalogue API",
    description=(
        "Synthetic operational product catalogue source "
        "for the RetailFlow data engineering platform."
    ),
    version="1.0.0",
)


# ------------------------------------------------------------
# Data paths
# ------------------------------------------------------------

BASE_DIRECTORY = Path(__file__).resolve().parent.parent
DATA_DIRECTORY = BASE_DIRECTORY / "data"

PRODUCTS_FILE = DATA_DIRECTORY / "products.json"
CATEGORIES_FILE = DATA_DIRECTORY / "categories.json"


# ------------------------------------------------------------
# JSON loading
# ------------------------------------------------------------

def load_json_file(file_path: Path) -> list[dict]:
    """Load records from a JSON source file."""

    if not file_path.exists():
        raise RuntimeError(
            f"Required data file does not exist: {file_path}"
        )

    with file_path.open(
        "r",
        encoding="utf-8",
    ) as file:
        return json.load(file)


products = load_json_file(PRODUCTS_FILE)
categories = load_json_file(CATEGORIES_FILE)


# ------------------------------------------------------------
# Health endpoint
# ------------------------------------------------------------

@app.get("/health")
def health_check() -> dict:
    """Return basic API health information."""

    return {
        "status": "healthy",
        "service": "retailflow-products-api",
        "product_count": len(products),
        "category_count": len(categories),
    }


# ------------------------------------------------------------
# Product endpoints
# ------------------------------------------------------------

@app.get("/products")
def get_products(
    page: int = Query(
        default=1,
        ge=1,
    ),
    page_size: int = Query(
        default=50,
        ge=1,
        le=100,
    ),
    category_id: Optional[str] = None,
    active: Optional[bool] = None,
) -> dict:
    """
    Return a paginated list of products.

    Optional filters:
    - category_id
    - active
    """

    filtered_products = products

    if category_id is not None:
        filtered_products = [
            product
            for product in filtered_products
            if product["category_id"] == category_id
        ]

    if active is not None:
        filtered_products = [
            product
            for product in filtered_products
            if product["active"] == active
        ]

    total_records = len(filtered_products)

    start = (page - 1) * page_size
    end = start + page_size

    page_records = filtered_products[
        start:end
    ]

    total_pages = (
        (total_records + page_size - 1)
        // page_size
        if total_records > 0
        else 0
    )

    return {
        "page": page,
        "page_size": page_size,
        "total_records": total_records,
        "total_pages": total_pages,
        "data": page_records,
    }


@app.get("/products/{product_id}")
def get_product(
    product_id: str,
) -> dict:
    """Return one product by product ID."""

    for product in products:
        if product["product_id"] == product_id:
            return product

    raise HTTPException(
        status_code=404,
        detail=(
            f"Product {product_id} "
            "was not found."
        ),
    )


# ------------------------------------------------------------
# Category endpoints
# ------------------------------------------------------------

@app.get("/categories")
def get_categories() -> dict:
    """Return all product categories."""

    return {
        "total_records": len(categories),
        "data": categories,
    }