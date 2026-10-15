
{{ config(materialized='view') }}

WITH customer_orders AS (

    SELECT
        customer_key,
        order_id,
        MIN(order_timestamp) AS order_timestamp,
        SUM(line_total) AS order_revenue,
        SUM(quantity) AS order_units

    FROM {{ ref('stg_ecommerce_sales') }}

    WHERE is_non_cancelled_order IS TRUE
      AND customer_key IS NOT NULL

    GROUP BY customer_key, order_id

),

customer_metrics AS (

    SELECT
        customer_key,
        COUNT(*) AS total_orders,
        SUM(order_units) AS total_units_purchased,
        ROUND(SUM(order_revenue), 2) AS lifetime_revenue,
        ROUND(AVG(order_revenue), 2) AS average_order_value,
        MIN(order_timestamp) AS first_order_at,
        MAX(order_timestamp) AS last_order_at

    FROM customer_orders

    GROUP BY customer_key

)

SELECT
    c.customer_key,
    c.customer_id,
    c.city,
    c.postcode,
    c.country,
    c.created_at AS customer_created_at,

    COALESCE(m.total_orders, 0) AS total_orders,
    COALESCE(m.total_units_purchased, 0) AS total_units_purchased,
    COALESCE(m.lifetime_revenue, 0) AS lifetime_revenue,
    COALESCE(m.average_order_value, 0) AS average_order_value,

    m.first_order_at,
    m.last_order_at,

    CASE
        WHEN COALESCE(m.total_orders, 0) = 0 THEN 'NO_PURCHASE'
        WHEN m.total_orders = 1 THEN 'ONE_TIME'
        ELSE 'REPEAT'
    END AS customer_segment

FROM {{ ref('stg_customers') }} c

LEFT JOIN customer_metrics m
    ON c.customer_key = m.customer_key
