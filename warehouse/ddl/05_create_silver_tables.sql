
-- RetailFlow Phase 8.4
-- Silver warehouse tables

BEGIN;

CREATE TABLE IF NOT EXISTS silver.ecommerce_customers (
    customer_id TEXT PRIMARY KEY,
    first_name TEXT,
    last_name TEXT,
    email TEXT,
    phone TEXT,
    address_line_1 TEXT,
    city TEXT,
    postcode TEXT,
    country TEXT,
    created_at TIMESTAMPTZ,
    updated_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS silver.ecommerce_orders (
    order_id TEXT PRIMARY KEY,
    customer_id TEXT,
    order_timestamp TIMESTAMPTZ,
    channel TEXT,
    status TEXT,
    currency TEXT,
    subtotal NUMERIC(18,2),
    discount NUMERIC(18,2),
    shipping NUMERIC(18,2),
    order_total NUMERIC(18,2),
    updated_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS silver.ecommerce_order_items (
    order_item_id TEXT PRIMARY KEY,
    order_id TEXT,
    product_id TEXT,
    quantity BIGINT,
    unit_price NUMERIC(18,2),
    discount NUMERIC(18,2),
    line_total NUMERIC(18,2)
);

CREATE TABLE IF NOT EXISTS silver.products_products (
    product_id TEXT PRIMARY KEY,
    sku TEXT,
    product_name TEXT,
    category_id TEXT,
    category_name TEXT,
    brand TEXT,
    unit_price NUMERIC(18,2),
    currency TEXT,
    active BOOLEAN,
    created_at TIMESTAMPTZ,
    updated_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS silver.products_categories (
    category_id TEXT PRIMARY KEY,
    category_name TEXT,
    active BOOLEAN
);

CREATE TABLE IF NOT EXISTS silver.pos_transactions (
    transaction_id TEXT PRIMARY KEY,
    store_id TEXT,
    product_id TEXT,
    transaction_timestamp TIMESTAMPTZ,
    quantity BIGINT,
    unit_price NUMERIC(18,2),
    discount NUMERIC(18,2),
    total_amount NUMERIC(18,2),
    payment_method TEXT
);

CREATE TABLE IF NOT EXISTS silver.inventory_inventory (
    product_id TEXT NOT NULL,
    store_id TEXT NOT NULL,
    quantity_on_hand BIGINT,
    reorder_level BIGINT,
    last_updated TIMESTAMPTZ,
    PRIMARY KEY (product_id, store_id)
);

CREATE TABLE IF NOT EXISTS silver.inventory_inventory_movements (
    movement_id TEXT PRIMARY KEY,
    product_id TEXT,
    store_id TEXT,
    movement_type TEXT,
    quantity BIGINT,
    movement_timestamp TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS silver.suppliers_suppliers (
    supplier_id TEXT PRIMARY KEY,
    supplier_name TEXT,
    contact_email TEXT,
    country TEXT,
    lead_time_days BIGINT,
    active BOOLEAN
);

CREATE TABLE IF NOT EXISTS silver.suppliers_deliveries (
    delivery_id TEXT PRIMARY KEY,
    supplier_id TEXT,
    product_id TEXT,
    expected_date DATE,
    actual_date DATE,
    quantity BIGINT,
    status TEXT
);

CREATE TABLE IF NOT EXISTS silver.payments_payments (
    payment_id TEXT PRIMARY KEY,
    order_id TEXT,
    payment_timestamp TIMESTAMPTZ,
    amount NUMERIC(18,2),
    currency TEXT,
    status TEXT,
    payment_method TEXT
);

CREATE TABLE IF NOT EXISTS silver.returns_returns (
    return_id TEXT PRIMARY KEY,
    order_id TEXT,
    product_id TEXT,
    customer_id TEXT,
    return_date DATE,
    quantity BIGINT,
    reason TEXT,
    refund_amount NUMERIC(18,2)
);

-- Metadata is stored in each Silver table.
-- Existing business columns remain unchanged.

DO $$
DECLARE
    table_name TEXT;
    silver_tables TEXT[] := ARRAY[
        'ecommerce_customers',
        'ecommerce_orders',
        'ecommerce_order_items',
        'products_products',
        'products_categories',
        'pos_transactions',
        'inventory_inventory',
        'inventory_inventory_movements',
        'suppliers_suppliers',
        'suppliers_deliveries',
        'payments_payments',
        'returns_returns'
    ];
BEGIN
    FOREACH table_name IN ARRAY silver_tables LOOP
        EXECUTE format(
            'ALTER TABLE silver.%I
             ADD COLUMN IF NOT EXISTS _pipeline_run_id UUID',
            table_name
        );

        EXECUTE format(
            'ALTER TABLE silver.%I
             ADD COLUMN IF NOT EXISTS _batch_id TEXT',
            table_name
        );

        EXECUTE format(
            'ALTER TABLE silver.%I
             ADD COLUMN IF NOT EXISTS _ingestion_timestamp TIMESTAMPTZ',
            table_name
        );

        EXECUTE format(
            'ALTER TABLE silver.%I
             ADD COLUMN IF NOT EXISTS _source_system TEXT',
            table_name
        );

        EXECUTE format(
            'ALTER TABLE silver.%I
             ADD COLUMN IF NOT EXISTS _source_dataset TEXT',
            table_name
        );

        EXECUTE format(
            'ALTER TABLE silver.%I
             ADD COLUMN IF NOT EXISTS _source_file_name TEXT',
            table_name
        );

        EXECUTE format(
            'ALTER TABLE silver.%I
             ADD COLUMN IF NOT EXISTS _source_record_number BIGINT',
            table_name
        );
    END LOOP;
END $$;

CREATE TABLE IF NOT EXISTS silver.quarantine_records (
    quarantine_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    source_system TEXT NOT NULL,
    dataset_name TEXT NOT NULL,
    pipeline_run_id UUID NOT NULL,
    source_record_number BIGINT,
    quarantine_reason TEXT NOT NULL,
    record_payload JSONB NOT NULL,
    quarantined_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_silver_quarantine_dataset
ON silver.quarantine_records (
    source_system, dataset_name, pipeline_run_id
);

COMMIT;
