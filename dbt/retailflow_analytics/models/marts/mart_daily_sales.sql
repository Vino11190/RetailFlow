
{{ config(materialized='view') }}

WITH ecommerce_sales AS (

    SELECT
        date_key,
        'ECOMMERCE'::text AS sales_channel,
        order_id::text AS transaction_id,
        order_item_id::text AS line_id,
        quantity,
        (quantity * unit_price)::numeric AS gross_revenue,
        discount::numeric AS discount_amount,
        line_total::numeric AS net_revenue

    FROM {{ ref('stg_ecommerce_sales') }}

    WHERE is_non_cancelled_order IS TRUE

),

pos_sales AS (

    SELECT
        date_key,
        'POS'::text AS sales_channel,
        transaction_id::text AS transaction_id,
        pos_sales_key::text AS line_id,
        quantity,
        (quantity * unit_price)::numeric AS gross_revenue,
        discount::numeric AS discount_amount,
        total_amount::numeric AS net_revenue

    FROM {{ ref('stg_pos_sales') }}

),

combined_sales AS (

    SELECT * FROM ecommerce_sales

    UNION ALL

    SELECT * FROM pos_sales

),

daily_aggregates AS (

    SELECT
        date_key,
        TO_DATE(date_key::text, 'YYYYMMDD') AS sales_date,
        sales_channel,

        COUNT(*) AS sales_line_count,
        COUNT(DISTINCT transaction_id) AS transaction_count,

        SUM(quantity) AS units_sold,

        ROUND(SUM(gross_revenue), 2) AS gross_revenue,
        ROUND(SUM(discount_amount), 2) AS total_discounts,
        ROUND(SUM(net_revenue), 2) AS net_revenue,

        ROUND(
            SUM(net_revenue)
            / NULLIF(COUNT(DISTINCT transaction_id), 0),
            2
        ) AS average_transaction_value

    FROM combined_sales

    GROUP BY
        date_key,
        sales_channel

)

SELECT *
FROM daily_aggregates
