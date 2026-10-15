
{{ config(materialized='view') }}

SELECT
    pos_sales_key,
    transaction_id,
    product_key,
    store_key,
    date_key,
    channel_key,
    transaction_timestamp,
    payment_method,
    quantity,
    unit_price,
    discount,
    total_amount

FROM {{ source('retailflow_gold', 'fact_pos_sales') }}
