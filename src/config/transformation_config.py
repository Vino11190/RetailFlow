
"""
RetailFlow Transformation Configuration.

Defines how Bronze datasets map to Silver tables
and how each dataset should be processed.
"""

from dataclasses import dataclass

from src.config.source_registry import SOURCE_REGISTRY


@dataclass(frozen=True)
class TransformationDefinition:
    source_system: str
    dataset_name: str
    bronze_dataset: str
    silver_schema: str
    silver_table: str
    load_strategy: str
    primary_key: tuple[str, ...]


PRIMARY_KEYS = {
    ("ecommerce", "customers"): ("customer_id",),
    ("ecommerce", "orders"): ("order_id",),
    ("ecommerce", "order_items"): ("order_item_id",),

    ("products", "products"): ("product_id",),
    ("products", "categories"): ("category_id",),

    ("pos", "transactions"): ("transaction_id",),

    ("inventory", "inventory"): (
        "product_id",
        "store_id",
    ),
    ("inventory", "inventory_movements"): (
        "movement_id",
    ),

    ("suppliers", "suppliers"): ("supplier_id",),
    ("suppliers", "deliveries"): ("delivery_id",),

    ("payments", "payments"): ("payment_id",),
    ("returns", "returns"): ("return_id",),
}


TRANSFORMATION_REGISTRY = {}

for source_name, source_definition in SOURCE_REGISTRY.items():
    for dataset_name in source_definition.datasets:

        dataset_key = (source_name, dataset_name)

        if dataset_key not in PRIMARY_KEYS:
            raise ValueError(
                f"Missing primary key for {dataset_key}"
            )

        transformation = TransformationDefinition(
            source_system=source_name,
            dataset_name=dataset_name,
            bronze_dataset=(
                f"{source_name}/{dataset_name}"
            ),
            silver_schema="silver",
            silver_table=(
                f"{source_name}_{dataset_name}"
            ),
            load_strategy="FULL",
            primary_key=PRIMARY_KEYS[dataset_key],
        )

        TRANSFORMATION_REGISTRY[
            dataset_key
        ] = transformation


def get_transformation(source_system, dataset_name):
    key = (source_system, dataset_name)

    if key not in TRANSFORMATION_REGISTRY:
        raise KeyError(
            f"Transformation not registered: {key}"
        )

    return TRANSFORMATION_REGISTRY[key]


def list_transformations():
    return list(TRANSFORMATION_REGISTRY.values())
