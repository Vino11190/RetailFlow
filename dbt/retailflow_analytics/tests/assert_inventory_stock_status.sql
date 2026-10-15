
SELECT
    product_key,
    store_key,
    quantity_on_hand,
    reorder_level,
    units_below_reorder_level,
    stock_status
FROM {{ ref('mart_inventory_health') }}
WHERE quantity_on_hand IS NULL
   OR reorder_level IS NULL
   OR quantity_on_hand < 0
   OR reorder_level < 0
   OR units_below_reorder_level <>
       GREATEST(reorder_level - quantity_on_hand, 0)
   OR (
       stock_status = 'OUT_OF_STOCK'
       AND quantity_on_hand > 0
   )
   OR (
       stock_status = 'LOW_STOCK'
       AND (
           quantity_on_hand <= 0
           OR quantity_on_hand > reorder_level
       )
   )
   OR (
       stock_status = 'HEALTHY'
       AND quantity_on_hand <= reorder_level
   )
