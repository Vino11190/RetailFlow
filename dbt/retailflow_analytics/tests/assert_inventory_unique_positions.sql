
SELECT
    product_key,
    store_key,
    COUNT(*) AS duplicate_count
FROM {{ ref('mart_inventory_health') }}
GROUP BY product_key, store_key
HAVING COUNT(*) > 1
