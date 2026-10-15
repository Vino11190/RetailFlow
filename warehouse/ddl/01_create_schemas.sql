
-- ============================================================
-- RetailFlow
-- Phase 6: PostgreSQL Data Warehouse Foundation
-- Step 6.2: Create Warehouse Schemas
-- ============================================================

-- Staging: temporary or intermediate warehouse landing area
CREATE SCHEMA IF NOT EXISTS staging;

-- Silver: cleaned, validated and standardised datasets
CREATE SCHEMA IF NOT EXISTS silver;

-- Gold: business-ready analytical models
CREATE SCHEMA IF NOT EXISTS gold;

-- Audit: data quality, reconciliation and pipeline results
CREATE SCHEMA IF NOT EXISTS audit;

-- Metadata: technical configuration and pipeline state
CREATE SCHEMA IF NOT EXISTS metadata;

-- ============================================================
-- Verify schemas
-- ============================================================

SELECT
    schema_name
FROM information_schema.schemata
WHERE schema_name IN (
    'staging',
    'silver',
    'gold',
    'audit',
    'metadata'
)
ORDER BY schema_name;
