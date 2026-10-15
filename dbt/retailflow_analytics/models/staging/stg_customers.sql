
{{ config(materialized='view') }}

SELECT
    customer_key,
    customer_id,
    city,
    postcode,
    country,
    created_at,
    updated_at

FROM {{ source('retailflow_gold', 'dim_customer') }}
