
{{ config(materialized='view') }}

WITH channel_sales AS (

    SELECT
        sales_channel,

        COUNT(*) AS active_sales_days,
        SUM(sales_line_count) AS total_sales_lines,
        SUM(transaction_count) AS total_transactions,
        SUM(units_sold) AS total_units_sold,

        SUM(gross_revenue) AS gross_revenue,
        SUM(total_discounts) AS total_discounts,
        SUM(net_revenue) AS net_revenue

    FROM {{ ref('mart_daily_sales') }}

    GROUP BY sales_channel

),

channel_metrics AS (

    SELECT
        sales_channel,
        active_sales_days,
        total_sales_lines,
        total_transactions,
        total_units_sold,

        ROUND(gross_revenue, 2) AS gross_revenue,
        ROUND(total_discounts, 2) AS total_discounts,
        ROUND(net_revenue, 2) AS net_revenue,

        ROUND(
            net_revenue / NULLIF(total_transactions, 0),
            2
        ) AS average_transaction_value,

        ROUND(
            100.0 * total_discounts
            / NULLIF(gross_revenue, 0),
            2
        ) AS discount_rate_pct,

        ROUND(
            100.0 * net_revenue
            / NULLIF(SUM(net_revenue) OVER (), 0),
            2
        ) AS revenue_contribution_pct

    FROM channel_sales

)

SELECT *
FROM channel_metrics
