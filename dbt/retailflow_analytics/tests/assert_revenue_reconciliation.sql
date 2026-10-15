
WITH daily AS (
    SELECT sales_channel, SUM(net_revenue) AS revenue
    FROM {{ ref('mart_daily_sales') }}
    GROUP BY sales_channel
),

products AS (
    SELECT sales_channel, SUM(net_revenue) AS revenue
    FROM {{ ref('mart_product_performance') }}
    GROUP BY sales_channel
)

SELECT
    COALESCE(d.sales_channel, p.sales_channel) AS sales_channel,
    d.revenue AS daily_revenue,
    p.revenue AS product_revenue
FROM daily d
FULL OUTER JOIN products p
    ON d.sales_channel = p.sales_channel
WHERE d.sales_channel IS NULL
   OR p.sales_channel IS NULL
   OR ABS(d.revenue - p.revenue) > 0.01
