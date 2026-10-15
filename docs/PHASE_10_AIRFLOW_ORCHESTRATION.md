# RetailFlow — Phase 10: Apache Airflow Orchestration

## Overview

RetailFlow is a multi-source retail data engineering project. Phase 10 introduces Apache Airflow to orchestrate the existing ingestion, transformation, warehouse-loading, and dbt analytics components as a five-task, dependency-ordered workflow.

**Validation date:** 15 October 2026
**DAG ID:** `retailflow_pipeline`
**Airflow:** 2.11.0
**Execution model:** Docker Compose, `LocalExecutor`
**Schedule:** Manual (`schedule_interval=None`)
**Maximum concurrent DAG runs:** 1

## Architecture

```text
Retail source systems
       |
       v
bronze_ingestion
       |
       v
silver_transformation
       |
       v
gold_dimensions
       |
       v
gold_facts
       |
       v
dbt_analytics_build
       |
       v
Analytics models and data-quality tests
```

Airflow manages task order, retry behaviour, logs, and run status. Each ETL task runs in a separate Python virtual environment inside the Airflow container, avoiding dependency conflicts between Airflow's SQLAlchemy 1.x requirement and the ETL application's SQLAlchemy 2.x requirement.

### Runtime components

| Component | Configuration / purpose |
|---|---|
| Airflow image | Custom image based on `apache/airflow:2.11.0` |
| Airflow executor | `LocalExecutor` |
| Airflow metadata | Dedicated PostgreSQL 17 container |
| ETL Python | `/opt/retailflow-venv/bin/python` |
| dbt executable | `/opt/retailflow-venv/bin/dbt` |
| dbt Core / PostgreSQL adapter | 1.9.11 / 1.9.1 |
| Project mount | `/opt/retailflow` |
| RetailFlow source PostgreSQL | Windows host via `host.docker.internal:5432` |
| RetailFlow warehouse PostgreSQL | Windows host via `host.docker.internal:5433` |
| Products API | `http://host.docker.internal:8000` |
| Web interface | `http://localhost:8080` |

The pinned dbt 1.9 version produced a deprecation warning in validation logs. Plan a separate, tested upgrade to a supported dbt release; do not combine that upgrade with unrelated pipeline changes.

## DAG implementation

**File:** `airflow/dags/retailflow_pipeline.py`

| Task | Command run inside container |
|---|---|
| `bronze_ingestion` | `python -m src.ingestion.run_ingestion all` |
| `silver_transformation` | `python -m src.transformations.silver.silver_loader --source all` |
| `gold_dimensions` | `python -m src.transformations.gold.dimension_loader` |
| `gold_facts` | `python -m src.transformations.gold.fact_loader` |
| `dbt_analytics_build` | `dbt build --profiles-dir .` |

Commands use the full paths to the isolated Python and dbt executables. The first four commands execute from `/opt/retailflow`; dbt executes from `/opt/retailflow/dbt/retailflow_analytics`.

### Reliability configuration

- Two retries per failed task.
- Initial retry delay of two minutes with exponential backoff, capped at ten minutes.
- Thirty-minute execution timeout per task.
- Failure callback writes task and run context to Airflow logs.
- `catchup=False` and `max_active_runs=1` to avoid overlapping scheduled backfills or DAG runs.
- No automatic schedule is configured yet; the DAG is triggered manually.

**Operational caution:** Airflow retries are at the task level, not a global transaction. Bronze ingestion creates new run identifiers and files. The Silver and Gold fact loaders use transactional snapshot replacement, but the complete pipeline is not atomic across all five stages.

## Bronze-to-Gold processing strategy

### Bronze

The ingestion tracker writes per-source run records under:

`/opt/retailflow/data/bronze/_metadata/runs`

Each run has a unique identifier and status. The Bronze reader selects the most recent successful run for a source system, then filters dataset Parquet rows to that run's `_pipeline_run_id`. This prevents accidental mixing of records from different ingestion runs.

**Scaling consideration:** The current Bronze reader enumerates historical Parquet files and reads them before filtering by run ID. Partitioning or a run manifest could reduce scanning costs at larger volumes.

### Silver

The Silver loader stages cleaned records in PostgreSQL temporary tables and transactionally replaces the corresponding Silver dataset snapshot. It validates staged and final record counts and records quarantined rows for the relevant ingestion run.

### Gold dimensions

Six shared dimensions are loaded:

- Customer, store, supplier, and channel dimensions use conflict-handling / Type 1 patterns.
- Product uses Slowly Changing Dimension Type 2 (SCD2), with attribute hashes and current-version flags.
- Date uses deterministic calendar keys.

An advisory transaction lock prevents concurrent dimension-loading transactions.

### Gold facts

Seven fact tables are loaded using temporary staging tables, count reconciliation, and transactional full-snapshot replacement. An advisory transaction lock prevents concurrent fact-loading transactions.

**Known modelling limitation:** Historical transactions currently reference the current product dimension version rather than the product version valid at event time. Event-time SCD2 resolution is future work.

## Verified execution evidence

A manual execution on **15 October 2026** completed successfully.

| Metric | Observed result |
|---|---|
| Latest run ID prefix | `manual__2026-10-15T04:18:26.765663+00:00` |
| Start | 2026-10-15 04:18:27 UTC (approximately) |
| End | 2026-10-15 04:20:24 UTC (approximately) |
| Elapsed time | Approximately 1 minute 58 seconds |
| DAG state | `success` |
| Successful tasks | 5 of 5 |
| dbt data tests | 42 passed, 0 warnings, 0 errors, 0 skipped |
| Successful runs visible in CLI history | 5 |

The Airflow Graph View screenshot supplied during validation showed all five tasks green. Add a screenshot to the repository's evidence directory and link it here once committed.

## Warehouse row-count report

### Silver

| Table | Rows |
|---|---:|
| `silver.ecommerce_customers` | 5,000 |
| `silver.ecommerce_orders` | 25,000 |
| `silver.ecommerce_order_items` | 66,442 |
| `silver.pos_transactions` | 20,000 |
| `silver.products_products` | 500 |
| `silver.payments_payments` | 25,000 |
| `silver.returns_returns` | 2,000 |
| `silver.inventory_inventory` | 6,000 |
| `silver.inventory_inventory_movements` | 50,000 |
| `silver.suppliers_suppliers` | 50 |
| `silver.suppliers_deliveries` | 5,000 |

### Gold dimensions

| Table | Rows |
|---|---:|
| `gold.dim_customer` | 5,001 |
| `gold.dim_product` | 501 |
| `gold.dim_date` | 5,845 |
| `gold.dim_store` | 13 |
| `gold.dim_supplier` | 51 |
| `gold.dim_channel` | 4 |

Customer and product dimension totals include configured unknown members.

### Gold facts

| Table | Rows |
|---|---:|
| `gold.fact_ecommerce_sales` | 66,442 |
| `gold.fact_pos_sales` | 20,000 |
| `gold.fact_payments` | 25,000 |
| `gold.fact_returns` | 2,000 |
| `gold.fact_inventory_snapshot` | 6,000 |
| `gold.fact_inventory_movements` | 50,000 |
| `gold.fact_supplier_deliveries` | 5,000 |

The seven Silver-to-Gold fact record counts matched. Count matching supports reconciliation but does not independently prove record-by-record equality.

## Data quality

The dbt project contains ten models, thirteen sources, and forty-two data tests. On the validated run, **all 42 tests passed**. Test categories include:

- Non-null and uniqueness checks.
- Relationships between fact/mart and dimension/staging keys.
- Accepted-value checks for channels, customer segments, and inventory statuses.
- Custom revenue reconciliation and sales arithmetic assertions.
- Inventory-position and stock-status assertions.
- Supplier delivery accounting and rate-range assertions.

## Local operation (Windows PowerShell)

From `C:\Projects\RetailFlow\airflow`:

```powershell
docker compose --env-file ..\.env --env-file .env -f docker-compose.airflow.yml up -d airflow-webserver airflow-scheduler
```

Open `http://localhost:8080`, select `retailflow_pipeline`, and manually trigger the DAG after verifying the Products API and database services are available.

Inspect DAG parsing and history:

```powershell
docker compose --env-file ..\.env --env-file .env -f docker-compose.airflow.yml exec airflow-scheduler airflow dags list-import-errors

docker compose --env-file ..\.env --env-file .env -f docker-compose.airflow.yml exec airflow-scheduler airflow dags list-runs -d retailflow_pipeline
```

Validate the warehouse:

```powershell
docker compose --env-file ..\.env --env-file .env -f docker-compose.airflow.yml exec airflow-scheduler /opt/retailflow-venv/bin/python -m src.warehouse.validate_airflow_run
```

Rerun dbt tests:

```powershell
docker compose --env-file ..\.env --env-file .env -f docker-compose.airflow.yml exec -w /opt/retailflow/dbt/retailflow_analytics airflow-scheduler /opt/retailflow-venv/bin/dbt test --profiles-dir .
```

### Troubleshooting

- **DAG import errors:** inspect `airflow dags list-import-errors` and scheduler logs.
- **Missing Python package:** check that it is installed in `/opt/retailflow-venv`, not only the Airflow environment.
- **dbt connection failures:** confirm warehouse availability, container environment variables, and `dbt debug --profiles-dir .`.
- **Products API failures:** confirm the host API is running and reachable from the container at `host.docker.internal:8000`.
- **Permission errors:** confirm mounted project directories are writable by the Airflow container user.
- **Task failure:** open the failed task in Graph View and inspect its logs before rerunning.

## Security and repository hygiene

Do not commit `.env` files, database passwords, Airflow admin credentials, private logs, or source data containing sensitive information. Store secrets in environment variables or a dedicated secret manager. Before publishing screenshots, inspect them for credentials and sensitive paths.

## Phase 10 completion criteria

- [x] Airflow and metadata database run under Docker Compose.
- [x] Isolated ETL/dbt Python environment built successfully.
- [x] Source database, warehouse database, and Products API reachable from Airflow.
- [x] Five-task DAG loaded and executed successfully.
- [x] Warehouse counts inspected.
- [x] All 42 dbt data tests passed.
- [x] Airflow Graph View and CLI run-history evidence captured.
- [ ] Add the final screenshot to the repository and commit this documentation.

**Status:** Phase 10 technically validated; repository documentation commit pending.
