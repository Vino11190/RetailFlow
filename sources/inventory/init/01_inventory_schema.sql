-- ============================================================
-- RetailFlow
-- Inventory Operational Source Database
-- ============================================================

CREATE TABLE inventory (
    product_id VARCHAR(20) NOT NULL,
    store_id VARCHAR(20) NOT NULL,
    quantity_on_hand INTEGER NOT NULL,
    reorder_level INTEGER NOT NULL,
    last_updated TIMESTAMP NOT NULL,

    CONSTRAINT pk_inventory
        PRIMARY KEY (product_id, store_id),

    CONSTRAINT chk_inventory_quantity
        CHECK (quantity_on_hand >= 0),

    CONSTRAINT chk_reorder_level
        CHECK (reorder_level >= 0)
);


CREATE TABLE inventory_movements (
    movement_id VARCHAR(25) PRIMARY KEY,
    product_id VARCHAR(20) NOT NULL,
    store_id VARCHAR(20) NOT NULL,
    movement_type VARCHAR(30) NOT NULL,
    quantity INTEGER NOT NULL,
    movement_timestamp TIMESTAMP NOT NULL,

    CONSTRAINT chk_movement_quantity
        CHECK (quantity > 0),

    CONSTRAINT chk_movement_type
        CHECK (
            movement_type IN (
                'SALE',
                'RETURN',
                'DELIVERY',
                'TRANSFER_IN',
                'TRANSFER_OUT',
                'ADJUSTMENT'
            )
        )
);


CREATE INDEX idx_inventory_last_updated
ON inventory(last_updated);


CREATE INDEX idx_inventory_store
ON inventory(store_id);


CREATE INDEX idx_movements_timestamp
ON inventory_movements(movement_timestamp);


CREATE INDEX idx_movements_product
ON inventory_movements(product_id);


CREATE INDEX idx_movements_store
ON inventory_movements(store_id);