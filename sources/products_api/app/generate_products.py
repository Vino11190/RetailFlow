import json
import random
from datetime import datetime, timedelta
from pathlib import Path


# ============================================================
# RetailFlow
# Synthetic Product Catalogue Generator
# ============================================================

PRODUCT_COUNT = 500
RANDOM_SEED = 42

START_DATE = datetime(2025, 1, 1)
END_DATE = datetime(2026, 9, 30, 23, 59, 59)

random.seed(RANDOM_SEED)


CATEGORIES = {
    "CAT001": {
        "category_name": "Electronics",
        "products": [
            "Wireless Headphones",
            "Bluetooth Speaker",
            "Smart Watch",
            "USB-C Charger",
            "Wireless Mouse",
            "Mechanical Keyboard",
            "Webcam",
            "Portable Power Bank",
        ],
    },
    "CAT002": {
        "category_name": "Home & Kitchen",
        "products": [
            "Electric Kettle",
            "Toaster",
            "Coffee Maker",
            "Table Lamp",
            "Storage Box",
            "Kitchen Scale",
            "Water Bottle",
            "Food Container Set",
        ],
    },
    "CAT003": {
        "category_name": "Clothing",
        "products": [
            "Cotton T-Shirt",
            "Hoodie",
            "Jeans",
            "Jacket",
            "Joggers",
            "Polo Shirt",
            "Sweatshirt",
            "Shorts",
        ],
    },
    "CAT004": {
        "category_name": "Health & Beauty",
        "products": [
            "Shampoo",
            "Conditioner",
            "Body Wash",
            "Face Moisturiser",
            "Hand Cream",
            "Hair Dryer",
            "Electric Toothbrush",
            "Skin Cleanser",
        ],
    },
    "CAT005": {
        "category_name": "Sports & Fitness",
        "products": [
            "Yoga Mat",
            "Resistance Bands",
            "Dumbbell Set",
            "Gym Bag",
            "Skipping Rope",
            "Fitness Bottle",
            "Exercise Ball",
            "Running Belt",
        ],
    },
    "CAT006": {
        "category_name": "Toys & Games",
        "products": [
            "Board Game",
            "Building Blocks",
            "Puzzle Set",
            "Remote Control Car",
            "Card Game",
            "Educational Toy",
            "Craft Kit",
            "Plush Toy",
        ],
    },
    "CAT007": {
        "category_name": "Office",
        "products": [
            "Notebook",
            "Desk Organiser",
            "Ballpoint Pen Set",
            "Document Folder",
            "Laptop Stand",
            "Desk Pad",
            "Calculator",
            "Stapler",
        ],
    },
    "CAT008": {
        "category_name": "Garden & Outdoor",
        "products": [
            "Garden Gloves",
            "Plant Pot",
            "Watering Can",
            "Outdoor Lantern",
            "Garden Tool Set",
            "Picnic Blanket",
            "Folding Chair",
            "Plant Mister",
        ],
    },
}


BRANDS = [
    "Northstar",
    "UrbanPeak",
    "BrightHome",
    "Nova",
    "Evergreen",
    "CoreLife",
    "BlueRiver",
    "Summit",
    "Oakwell",
    "Vertex",
]


ADJECTIVES = [
    "Essential",
    "Premium",
    "Classic",
    "Compact",
    "Pro",
    "Everyday",
    "Smart",
    "Eco",
]


def random_datetime(
    start: datetime,
    end: datetime,
) -> datetime:
    """Return a random datetime between two dates."""

    difference = end - start

    seconds = random.randint(
        0,
        int(difference.total_seconds()),
    )

    return start + timedelta(seconds=seconds)


def generate_categories() -> list[dict]:
    """Convert category configuration into API records."""

    categories = []

    for category_id, details in CATEGORIES.items():
        categories.append(
            {
                "category_id": category_id,
                "category_name": details["category_name"],
                "active": True,
            }
        )

    return categories


def generate_products() -> list[dict]:
    """Generate the RetailFlow synthetic product catalogue."""

    products = []

    category_ids = list(CATEGORIES.keys())

    for number in range(1, PRODUCT_COUNT + 1):

        product_id = f"PROD{number:05d}"

        category_id = random.choice(
            category_ids
        )

        category = CATEGORIES[
            category_id
        ]

        base_product = random.choice(
            category["products"]
        )

        brand = random.choice(
            BRANDS
        )

        adjective = random.choice(
            ADJECTIVES
        )

        product_name = (
            f"{brand} {adjective} "
            f"{base_product}"
        )

        sku = f"RF-{number:06d}"

        unit_price = round(
            random.uniform(
                2.99,
                499.99,
            ),
            2,
        )

        created_at = random_datetime(
            START_DATE,
            END_DATE,
        )

        maximum_update_days = max(
            0,
            (END_DATE - created_at).days,
        )

        update_days = random.randint(
            0,
            maximum_update_days,
        )

        updated_at = (
            created_at
            + timedelta(days=update_days)
        )

        active = random.choices(
            population=[True, False],
            weights=[96, 4],
            k=1,
        )[0]

        products.append(
            {
                "product_id": product_id,
                "sku": sku,
                "product_name": product_name,
                "category_id": category_id,
                "category_name": category["category_name"],
                "brand": brand,
                "unit_price": unit_price,
                "currency": "GBP",
                "active": active,
                "created_at": created_at.isoformat(),
                "updated_at": updated_at.isoformat(),
            }
        )

    return products


def save_json(
    data,
    filename: str,
) -> None:
    """Write generated data to the Product API data directory."""

    data_directory = (
        Path(__file__).resolve().parent.parent
        / "data"
    )

    data_directory.mkdir(
        parents=True,
        exist_ok=True,
    )

    output_path = (
        data_directory / filename
    )

    with output_path.open(
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            data,
            file,
            indent=2,
        )

    print(
        f"Saved: {output_path}"
    )


def validate_products(
    products: list[dict],
) -> None:
    """Run basic catalogue validation."""

    product_ids = [
        product["product_id"]
        for product in products
    ]

    skus = [
        product["sku"]
        for product in products
    ]

    duplicate_product_ids = (
        len(product_ids)
        - len(set(product_ids))
    )

    duplicate_skus = (
        len(skus)
        - len(set(skus))
    )

    invalid_prices = sum(
        1
        for product in products
        if product["unit_price"] <= 0
    )

    missing_categories = sum(
        1
        for product in products
        if not product["category_id"]
    )

    print("\nCatalogue validation")
    print("--------------------")
    print(
        f"Products generated: "
        f"{len(products):,}"
    )
    print(
        f"Duplicate product IDs: "
        f"{duplicate_product_ids}"
    )
    print(
        f"Duplicate SKUs: "
        f"{duplicate_skus}"
    )
    print(
        f"Invalid prices: "
        f"{invalid_prices}"
    )
    print(
        f"Missing categories: "
        f"{missing_categories}"
    )


def main() -> None:
    print(
        "RetailFlow Product Catalogue Generator"
    )
    print(
        "======================================"
    )

    categories = generate_categories()
    products = generate_products()

    save_json(
        categories,
        "categories.json",
    )

    save_json(
        products,
        "products.json",
    )

    validate_products(
        products
    )

    print("\nSample products:")

    for product in products[:5]:
        print(
            f"{product['product_id']} | "
            f"{product['sku']} | "
            f"{product['product_name']} | "
            f"£{product['unit_price']:.2f}"
        )


if __name__ == "__main__":
    main()