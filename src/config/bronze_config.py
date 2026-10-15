from pathlib import Path


# ============================================================
# RetailFlow
# Bronze Layer Configuration
# ============================================================


# ------------------------------------------------------------
# Project paths
# ------------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[2]

DATA_DIRECTORY = (
    PROJECT_ROOT
    / "data"
)

BRONZE_DIRECTORY = (
    DATA_DIRECTORY
    / "bronze"
)

BRONZE_METADATA_DIRECTORY = (
    BRONZE_DIRECTORY
    / "_metadata"
)


# ------------------------------------------------------------
# Bronze metadata columns
# ------------------------------------------------------------

BRONZE_METADATA_COLUMNS = [
    "_ingestion_timestamp",
    "_source_system",
    "_source_dataset",
    "_batch_id",
    "_pipeline_run_id",
    "_source_file_name",
    "_source_record_number",
]


# ------------------------------------------------------------
# Supported source systems and datasets
# ------------------------------------------------------------

BRONZE_DATASETS = {

    "ecommerce": [
        "customers",
        "orders",
        "order_items",
    ],

    "products": [
        "products",
        "categories",
    ],

    "pos": [
        "transactions",
    ],

    "inventory": [
        "inventory",
        "inventory_movements",
    ],

    "suppliers": [
        "suppliers",
        "deliveries",
    ],

    "payments": [
        "payments",
    ],

    "returns": [
        "returns",
    ],
}


# ------------------------------------------------------------
# Storage configuration
# ------------------------------------------------------------

BRONZE_FILE_FORMAT = "parquet"

BRONZE_COMPRESSION = "snappy"

BRONZE_PARTITION_COLUMN = (
    "ingestion_date"
)


# ------------------------------------------------------------
# Naming conventions
# ------------------------------------------------------------

PARQUET_FILE_PREFIX = "part"

BATCH_ID_TIMESTAMP_FORMAT = (
    "%Y%m%dT%H%M%S"
)