
{{ config(materialized='view') }}

SELECT
    product_key,
    product_id,
    sku,
    product_name,
    category_id,
    category_name,
    brand,
    unit_price,
    currency,
    active,
    effective_from,
    effective_to,
    is_current,
    attribute_hash

FROM {{ source('retailflow_gold', 'dim_product') }}
