
{{ config(materialized='view') }}

WITH ranked_snapshots AS (

    SELECT
        snapshot_key,
        snapshot_timestamp,
        snapshot_date_key,
        product_key,
        store_key,
        quantity_on_hand,
        reorder_level,

        ROW_NUMBER() OVER (
            PARTITION BY product_key, store_key
            ORDER BY snapshot_timestamp DESC, snapshot_key DESC
        ) AS snapshot_rank

    FROM {{ source('retailflow_gold', 'fact_inventory_snapshot') }}

),

latest_snapshots AS (

    SELECT *
    FROM ranked_snapshots
    WHERE snapshot_rank = 1

),

movement_aggregates AS (

    SELECT
        product_key,
        store_key,

        COUNT(*) AS movement_count,
        SUM(ABS(quantity)) AS total_movement_units,
        MIN(movement_timestamp) AS first_movement_at,
        MAX(movement_timestamp) AS last_movement_at

    FROM {{ source('retailflow_gold', 'fact_inventory_movements') }}

    GROUP BY product_key, store_key

),

inventory_metrics AS (

    SELECT
        s.snapshot_key,
        s.snapshot_timestamp,
        s.snapshot_date_key,
        s.product_key,
        s.store_key,
        s.quantity_on_hand,
        s.reorder_level,

        GREATEST(
            s.reorder_level - s.quantity_on_hand,
            0
        ) AS units_below_reorder_level,

        CASE
            WHEN s.quantity_on_hand <= 0 THEN 'OUT_OF_STOCK'
            WHEN s.quantity_on_hand <= s.reorder_level THEN 'LOW_STOCK'
            ELSE 'HEALTHY'
        END AS stock_status,

        COALESCE(m.movement_count, 0) AS movement_count,
        COALESCE(m.total_movement_units, 0) AS total_movement_units,
        m.first_movement_at,
        m.last_movement_at

    FROM latest_snapshots s

    LEFT JOIN movement_aggregates m
        ON s.product_key = m.product_key
       AND s.store_key = m.store_key

)

SELECT
    i.*,
    p.product_id,
    p.sku,
    p.product_name,
    p.category_name,
    p.brand

FROM inventory_metrics i

LEFT JOIN {{ ref('stg_products') }} p
    ON i.product_key = p.product_key
