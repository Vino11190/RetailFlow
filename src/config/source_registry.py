from dataclasses import dataclass
from typing import Literal


# ============================================================
# RetailFlow
# Source Registry
# ============================================================


SourceType = Literal[
    "postgres",
    "rest_api",
    "csv",
    "json",
]


@dataclass(frozen=True)
class SourceDefinition:
    source_system: str
    source_type: SourceType
    datasets: tuple[str, ...]
    enabled: bool = True


SOURCE_REGISTRY = {
    "ecommerce": SourceDefinition(
        source_system="ecommerce",
        source_type="postgres",
        datasets=(
            "customers",
            "orders",
            "order_items",
        ),
    ),

    "products": SourceDefinition(
        source_system="products",
        source_type="rest_api",
        datasets=(
            "products",
            "categories",
        ),
    ),

    "pos": SourceDefinition(
        source_system="pos",
        source_type="csv",
        datasets=(
            "transactions",
        ),
    ),

    "inventory": SourceDefinition(
        source_system="inventory",
        source_type="postgres",
        datasets=(
            "inventory",
            "inventory_movements",
        ),
    ),

    "suppliers": SourceDefinition(
        source_system="suppliers",
        source_type="csv",
        datasets=(
            "suppliers",
            "deliveries",
        ),
    ),

    "payments": SourceDefinition(
        source_system="payments",
        source_type="json",
        datasets=(
            "payments",
        ),
    ),

    "returns": SourceDefinition(
        source_system="returns",
        source_type="csv",
        datasets=(
            "returns",
        ),
    ),
}


def get_source(
    source_system: str,
) -> SourceDefinition:

    if source_system not in SOURCE_REGISTRY:
        raise ValueError(
            f"Unknown source system: "
            f"{source_system}"
        )

    return SOURCE_REGISTRY[
        source_system
    ]


def get_enabled_sources() -> dict[
    str,
    SourceDefinition,
]:

    return {
        name: definition
        for name, definition
        in SOURCE_REGISTRY.items()
        if definition.enabled
    }