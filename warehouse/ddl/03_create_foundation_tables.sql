
-- ============================================================
-- RetailFlow
-- Phase 6.5: Foundational Warehouse Tables
-- ============================================================

BEGIN;

-- ============================================================
-- 1. PIPELINE RUNS
-- ============================================================

CREATE TABLE IF NOT EXISTS metadata.pipeline_runs (
    pipeline_run_id UUID PRIMARY KEY,
    pipeline_name VARCHAR(150) NOT NULL,
    source_system VARCHAR(100),
    status VARCHAR(30) NOT NULL DEFAULT 'STARTED',
    started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    finished_at TIMESTAMPTZ,
    duration_seconds NUMERIC(12,3),
    records_processed BIGINT NOT NULL DEFAULT 0,
    error_message TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT chk_pipeline_status
        CHECK (
            status IN (
                'STARTED',
                'RUNNING',
                'SUCCESS',
                'FAILED',
                'SKIPPED'
            )
        ),

    CONSTRAINT chk_pipeline_record_count
        CHECK (records_processed >= 0),

    CONSTRAINT chk_pipeline_duration
        CHECK (
            duration_seconds IS NULL
            OR duration_seconds >= 0
        ),

    CONSTRAINT chk_pipeline_time_order
        CHECK (
            finished_at IS NULL
            OR finished_at >= started_at
        )
);

CREATE INDEX IF NOT EXISTS idx_pipeline_runs_status
ON metadata.pipeline_runs (status);

CREATE INDEX IF NOT EXISTS idx_pipeline_runs_started_at
ON metadata.pipeline_runs (started_at DESC);


-- ============================================================
-- 2. PIPELINE WATERMARKS
-- ============================================================

CREATE TABLE IF NOT EXISTS metadata.pipeline_watermarks (
    source_system VARCHAR(100) NOT NULL,
    dataset_name VARCHAR(150) NOT NULL,
    watermark_column VARCHAR(150) NOT NULL,
    watermark_value TEXT,
    last_successful_run_id UUID,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    PRIMARY KEY (source_system, dataset_name),

    CONSTRAINT fk_watermark_pipeline_run
        FOREIGN KEY (last_successful_run_id)
        REFERENCES metadata.pipeline_runs (pipeline_run_id)
);

-- A watermark records the last successfully processed
-- position for an incremental data pipeline.


-- ============================================================
-- 3. DATASET REGISTRY
-- ============================================================

CREATE TABLE IF NOT EXISTS metadata.dataset_registry (
    dataset_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    source_system VARCHAR(100) NOT NULL,
    dataset_name VARCHAR(150) NOT NULL,
    source_type VARCHAR(50) NOT NULL,
    target_schema VARCHAR(100),
    target_table VARCHAR(150),
    is_enabled BOOLEAN NOT NULL DEFAULT TRUE,
    load_strategy VARCHAR(30) NOT NULL DEFAULT 'FULL',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT uq_dataset_registry
        UNIQUE (source_system, dataset_name),

    CONSTRAINT chk_load_strategy
        CHECK (
            load_strategy IN (
                'FULL',
                'INCREMENTAL',
                'CDC'
            )
        )
);


-- ============================================================
-- 4. DATA QUALITY RESULTS
-- ============================================================

CREATE TABLE IF NOT EXISTS audit.data_quality_results (
    quality_result_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    pipeline_run_id UUID,
    source_system VARCHAR(100),
    dataset_name VARCHAR(150) NOT NULL,
    check_name VARCHAR(150) NOT NULL,
    check_type VARCHAR(100) NOT NULL,
    status VARCHAR(20) NOT NULL,
    records_checked BIGINT,
    records_failed BIGINT,
    failure_details TEXT,
    checked_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT fk_quality_pipeline_run
        FOREIGN KEY (pipeline_run_id)
        REFERENCES metadata.pipeline_runs (pipeline_run_id),

    CONSTRAINT chk_quality_status
        CHECK (status IN ('PASS', 'FAIL', 'WARN')),

    CONSTRAINT chk_quality_counts
        CHECK (
            (records_checked IS NULL OR records_checked >= 0)
            AND
            (records_failed IS NULL OR records_failed >= 0)
            AND
            (
                records_checked IS NULL
                OR records_failed IS NULL
                OR records_failed <= records_checked
            )
        )
);

CREATE INDEX IF NOT EXISTS idx_quality_dataset
ON audit.data_quality_results (
    source_system,
    dataset_name,
    checked_at DESC
);


-- ============================================================
-- 5. RECONCILIATION RESULTS
-- ============================================================

CREATE TABLE IF NOT EXISTS audit.reconciliation_results (
    reconciliation_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    pipeline_run_id UUID,
    source_system VARCHAR(100),
    dataset_name VARCHAR(150) NOT NULL,
    source_record_count BIGINT NOT NULL,
    target_record_count BIGINT NOT NULL,
    difference_count BIGINT GENERATED ALWAYS AS (
        target_record_count - source_record_count
    ) STORED,
    status VARCHAR(20) NOT NULL,
    checked_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT fk_reconciliation_pipeline_run
        FOREIGN KEY (pipeline_run_id)
        REFERENCES metadata.pipeline_runs (pipeline_run_id),

    CONSTRAINT chk_reconciliation_status
        CHECK (status IN ('PASS', 'FAIL', 'WARN')),

    CONSTRAINT chk_reconciliation_counts
        CHECK (
            source_record_count >= 0
            AND target_record_count >= 0
        )
);

CREATE INDEX IF NOT EXISTS idx_reconciliation_dataset
ON audit.reconciliation_results (
    source_system,
    dataset_name,
    checked_at DESC
);


-- ============================================================
-- 6. PIPELINE ERRORS
-- ============================================================

CREATE TABLE IF NOT EXISTS audit.pipeline_errors (
    error_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    pipeline_run_id UUID,
    source_system VARCHAR(100),
    dataset_name VARCHAR(150),
    error_type VARCHAR(150) NOT NULL,
    error_message TEXT NOT NULL,
    error_details TEXT,
    occurred_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT fk_error_pipeline_run
        FOREIGN KEY (pipeline_run_id)
        REFERENCES metadata.pipeline_runs (pipeline_run_id)
);

CREATE INDEX IF NOT EXISTS idx_pipeline_errors_run
ON audit.pipeline_errors (pipeline_run_id);


COMMIT;

-- ============================================================
-- Verify foundational tables
-- ============================================================

SELECT
    table_schema,
    table_name
FROM information_schema.tables
WHERE table_schema IN ('metadata', 'audit')
  AND table_type = 'BASE TABLE'
ORDER BY table_schema, table_name;
