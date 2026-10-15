
{{ config(materialized='view') }}

WITH ecommerce AS (

    SELECT
        product_key,
        'ECOMMERCE'::text AS sales_channel,
        order_id::text AS transaction_id,
        quantity,
        (quantity * unit_price)::numeric AS gross_revenue,
        discount::numeric AS discount_amount,
        line_total::numeric AS net_revenue

    FROM {{ ref('stg_ecommerce_sales') }}

    WHERE is_non_cancelled_order IS TRUE

),

pos AS (

    SELECT
        product_key,
        'POS'::text AS sales_channel,
        transaction_id::text AS transaction_id,
        quantity,
        (quantity * unit_price)::numeric AS gross_revenue,
        discount::numeric AS discount_amount,
        total_amount::numeric AS net_revenue

    FROM {{ ref('stg_pos_sales') }}

),

combined_sales AS (

    SELECT * FROM ecommerce

    UNION ALL

    SELECT * FROM pos

),

product_aggregates AS (

    SELECT
        product_key,
        sales_channel,
        COUNT(*) AS sales_line_count,
        COUNT(DISTINCT transaction_id) AS transaction_count,
        SUM(quantity) AS units_sold,
        ROUND(SUM(gross_revenue), 2) AS gross_revenue,
        ROUND(SUM(discount_amount), 2) AS total_discounts,
        ROUND(SUM(net_revenue), 2) AS net_revenue

    FROM combined_sales

    GROUP BY product_key, sales_channel

)

SELECT
    a.product_key,
    p.product_id,
    p.sku,
    p.product_name,
    p.category_name,
    p.brand,
    a.sales_channel,
    a.sales_line_count,
    a.transaction_count,
    a.units_sold,
    a.gross_revenue,
    a.total_discounts,
    a.net_revenue,

    ROUND(
        a.net_revenue / NULLIF(a.units_sold, 0),
        2
    ) AS average_revenue_per_unit

FROM product_aggregates a

LEFT JOIN {{ ref('stg_products') }} p
    ON a.product_key = p.product_key
