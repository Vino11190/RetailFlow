
"""
RetailFlow Silver Cleaning Configuration.

Defines source-specific timestamp, date,
monetary and required-field rules.
"""

TIMESTAMP_COLUMNS = {
    ("ecommerce", "customers"): (
        "created_at", "updated_at"
    ),
    ("ecommerce", "orders"): (
        "order_timestamp", "updated_at"
    ),
    ("ecommerce", "order_items"): (),

    ("products", "products"): (
        "created_at", "updated_at"
    ),
    ("products", "categories"): (),

    ("pos", "transactions"): (
        "transaction_timestamp",
    ),

    ("inventory", "inventory"): (
        "last_updated",
    ),
    ("inventory", "inventory_movements"): (
        "movement_timestamp",
    ),

    ("suppliers", "suppliers"): (),
    ("suppliers", "deliveries"): (),

    ("payments", "payments"): (
        "payment_timestamp",
    ),
    ("returns", "returns"): (),
}


DATE_COLUMNS = {
    ("suppliers", "deliveries"): (
        "expected_date", "actual_date"
    ),
    ("returns", "returns"): (
        "return_date",
    ),
}


MONETARY_COLUMNS = {
    ("ecommerce", "orders"): (
        "subtotal", "discount",
        "shipping", "order_total"
    ),
    ("ecommerce", "order_items"): (
        "unit_price", "discount", "line_total"
    ),
    ("products", "products"): (
        "unit_price",
    ),
    ("pos", "transactions"): (
        "unit_price", "discount", "total_amount"
    ),
    ("payments", "payments"): (
        "amount",
    ),
    ("returns", "returns"): (
        "refund_amount",
    ),
}


REQUIRED_COLUMNS = {
    ("ecommerce", "customers"): ("customer_id",),
    ("ecommerce", "orders"): (
        "order_id", "customer_id", "order_timestamp"
    ),
    ("ecommerce", "order_items"): (
        "order_item_id", "order_id", "product_id"
    ),

    ("products", "products"): (
        "product_id", "product_name"
    ),
    ("products", "categories"): (
        "category_id", "category_name"
    ),

    ("pos", "transactions"): (
        "transaction_id",
        "product_id",
        "store_id",
        "transaction_timestamp"
    ),

    ("inventory", "inventory"): (
        "product_id", "store_id"
    ),
    ("inventory", "inventory_movements"): (
        "movement_id",
        "product_id",
        "store_id",
        "movement_timestamp"
    ),

    ("suppliers", "suppliers"): (
        "supplier_id", "supplier_name"
    ),
    ("suppliers", "deliveries"): (
        "delivery_id",
        "supplier_id",
        "product_id",
        "expected_date"
    ),

    ("payments", "payments"): (
        "payment_id",
        "order_id",
        "payment_timestamp"
    ),
    ("returns", "returns"): (
        "return_id",
        "order_id",
        "product_id",
        "return_date"
    ),
}


BOOLEAN_COLUMNS = {
    ("products", "products"): ("active",),
    ("products", "categories"): ("active",),
    ("suppliers", "suppliers"): ("active",),
}


# These fields must contain a valid value if present
# in a row. Other optional fields may remain null.

REQUIRED_MONETARY_COLUMNS = {
    ("ecommerce", "orders"): ("order_total",),
    ("ecommerce", "order_items"): ("line_total",),
    ("products", "products"): ("unit_price",),
    ("pos", "transactions"): ("total_amount",),
    ("payments", "payments"): ("amount",),
    ("returns", "returns"): ("refund_amount",),
}
