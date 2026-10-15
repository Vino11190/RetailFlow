
{{ config(materialized='view') }}

WITH source AS (

    SELECT *
    FROM {{ source('retailflow_gold', 'fact_ecommerce_sales') }}

),

standardized AS (

    SELECT
        sales_key,
        order_item_id,
        order_id,

        customer_key,
        product_key,
        date_key,
        channel_key,

        order_timestamp,
        order_status,
        currency,

        quantity,
        unit_price,
        discount,
        line_total,

        CASE
            WHEN order_status IN ('CANCELLED', 'CANCELED')
                THEN FALSE
            ELSE TRUE
        END AS is_non_cancelled_order

    FROM source

)

SELECT *
FROM standardized
