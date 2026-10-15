
SELECT
    supplier_key,
    total_delivery_records,
    completed_deliveries,
    cancelled_deliveries,
    pending_deliveries
FROM {{ ref('mart_supplier_performance') }}
WHERE total_delivery_records <>
      completed_deliveries
      + cancelled_deliveries
      + pending_deliveries
