
SELECT
    date_key,
    sales_channel,
    gross_revenue,
    total_discounts,
    net_revenue
FROM {{ ref('mart_daily_sales') }}
WHERE ABS(
    gross_revenue - total_discounts - net_revenue
) > 0.01
