
SELECT
    supplier_key,
    on_time_delivery_rate_pct,
    delivery_completion_rate_pct,
    cancellation_rate_pct
FROM {{ ref('mart_supplier_performance') }}
WHERE on_time_delivery_rate_pct < 0
   OR on_time_delivery_rate_pct > 100
   OR delivery_completion_rate_pct < 0
   OR delivery_completion_rate_pct > 100
   OR cancellation_rate_pct < 0
   OR cancellation_rate_pct > 100
   OR on_time_deliveries > completed_deliveries
