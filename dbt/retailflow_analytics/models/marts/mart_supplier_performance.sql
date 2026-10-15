
{{ config(materialized='view') }}

WITH deliveries AS (

    SELECT
        delivery_key,
        delivery_id,
        supplier_key,
        product_key,
        expected_date_key,
        actual_date_key,
        quantity,
        UPPER(TRIM(delivery_status)) AS delivery_status,
        delivery_delay_days

    FROM {{ source('retailflow_gold', 'fact_supplier_deliveries') }}

),

supplier_aggregates AS (

    SELECT
        supplier_key,

        COUNT(*) AS total_delivery_records,

        COUNT(*) FILTER (
            WHERE actual_date_key IS NOT NULL
        ) AS completed_deliveries,

        COUNT(*) FILTER (
            WHERE delivery_status = 'CANCELLED'
        ) AS cancelled_deliveries,

        COUNT(*) FILTER (
            WHERE actual_date_key IS NULL
              AND delivery_status <> 'CANCELLED'
        ) AS pending_deliveries,

        COUNT(*) FILTER (
            WHERE actual_date_key IS NOT NULL
              AND delivery_delay_days <= 0
        ) AS on_time_deliveries,

        COUNT(*) FILTER (
            WHERE actual_date_key IS NOT NULL
              AND delivery_delay_days > 0
        ) AS late_deliveries,

        SUM(quantity) FILTER (
            WHERE actual_date_key IS NOT NULL
        ) AS completed_delivery_units,

        ROUND(
            AVG(delivery_delay_days) FILTER (
                WHERE actual_date_key IS NOT NULL
            ),
            2
        ) AS average_delay_days,

        MAX(delivery_delay_days) FILTER (
            WHERE actual_date_key IS NOT NULL
        ) AS maximum_delay_days

    FROM deliveries

    GROUP BY supplier_key

),

supplier_metrics AS (

    SELECT
        s.supplier_key,
        s.supplier_id,
        s.supplier_name,
        s.country,
        s.lead_time_days,
        s.active,

        COALESCE(a.total_delivery_records, 0)
            AS total_delivery_records,

        COALESCE(a.completed_deliveries, 0)
            AS completed_deliveries,

        COALESCE(a.cancelled_deliveries, 0)
            AS cancelled_deliveries,

        COALESCE(a.pending_deliveries, 0)
            AS pending_deliveries,

        COALESCE(a.on_time_deliveries, 0)
            AS on_time_deliveries,

        COALESCE(a.late_deliveries, 0)
            AS late_deliveries,

        COALESCE(a.completed_delivery_units, 0)
            AS completed_delivery_units,

        a.average_delay_days,
        a.maximum_delay_days,

        ROUND(
            100.0 * a.on_time_deliveries
            / NULLIF(a.completed_deliveries, 0),
            2
        ) AS on_time_delivery_rate_pct,

        ROUND(
            100.0 * a.completed_deliveries
            / NULLIF(a.total_delivery_records, 0),
            2
        ) AS delivery_completion_rate_pct,

        ROUND(
            100.0 * a.cancelled_deliveries
            / NULLIF(a.total_delivery_records, 0),
            2
        ) AS cancellation_rate_pct

    FROM {{ source('retailflow_gold', 'dim_supplier') }} s

    LEFT JOIN supplier_aggregates a
        ON s.supplier_key = a.supplier_key

)

SELECT *
FROM supplier_metrics
