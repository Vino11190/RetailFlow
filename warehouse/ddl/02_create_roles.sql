
-- ============================================================
-- RetailFlow
-- Phase 6.4: Warehouse Roles and Permissions
-- ============================================================

-- Create group roles if they do not already exist.
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_roles
        WHERE rolname = 'retailflow_etl_role'
    ) THEN
        CREATE ROLE retailflow_etl_role NOLOGIN;
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_roles
        WHERE rolname = 'retailflow_analytics_role'
    ) THEN
        CREATE ROLE retailflow_analytics_role NOLOGIN;
    END IF;
END
$$;

-- Login roles are created separately using credentials
-- from environment variables. No passwords are stored
-- in this SQL file.

-- Restrict default database access for PUBLIC.
REVOKE CONNECT ON DATABASE retailflow_warehouse
FROM PUBLIC;

-- Remove PUBLIC's default schema creation privileges.
REVOKE ALL ON SCHEMA public FROM PUBLIC;

-- Give group roles database connectivity.
GRANT CONNECT ON DATABASE retailflow_warehouse
TO retailflow_etl_role, retailflow_analytics_role;

-- ============================================================
-- ETL ROLE
-- ============================================================

GRANT USAGE ON SCHEMA staging, silver, gold
TO retailflow_etl_role;

GRANT SELECT, INSERT, UPDATE, DELETE
ON ALL TABLES IN SCHEMA staging, silver, gold
TO retailflow_etl_role;

GRANT USAGE, SELECT
ON ALL SEQUENCES IN SCHEMA staging, silver, gold
TO retailflow_etl_role;

-- Future tables and sequences created by retailflow.
ALTER DEFAULT PRIVILEGES FOR ROLE retailflow
IN SCHEMA staging, silver, gold
GRANT SELECT, INSERT, UPDATE, DELETE
ON TABLES TO retailflow_etl_role;

ALTER DEFAULT PRIVILEGES FOR ROLE retailflow
IN SCHEMA staging, silver, gold
GRANT USAGE, SELECT
ON SEQUENCES TO retailflow_etl_role;

-- ============================================================
-- ANALYTICS ROLE
-- ============================================================

GRANT USAGE ON SCHEMA gold
TO retailflow_analytics_role;

GRANT SELECT
ON ALL TABLES IN SCHEMA gold
TO retailflow_analytics_role;

-- Future Gold tables created by retailflow.
ALTER DEFAULT PRIVILEGES FOR ROLE retailflow
IN SCHEMA gold
GRANT SELECT ON TABLES
TO retailflow_analytics_role;

-- ============================================================
-- Role membership
-- ============================================================

GRANT retailflow_etl_role
TO retailflow_etl_user;

GRANT retailflow_analytics_role
TO retailflow_analytics_user;

-- ============================================================
-- Verification
-- ============================================================

SELECT
    rolname,
    rolcanlogin,
    rolsuper
FROM pg_roles
WHERE rolname IN (
    'retailflow_etl_role',
    'retailflow_analytics_role',
    'retailflow_etl_user',
    'retailflow_analytics_user'
)
ORDER BY rolname;
