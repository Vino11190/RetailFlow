
"""
RetailFlow End-to-End Apache Airflow DAG.

Pipeline:
    Bronze ingestion
        -> Silver transformation
        -> Gold dimensions
        -> Gold facts
        -> dbt analytics build

The ETL tasks run in a separate Linux Python environment
to avoid dependency conflicts with Apache Airflow.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.bash import BashOperator


LOGGER = logging.getLogger(__name__)

PROJECT_ROOT = "/opt/retailflow"

ETL_PYTHON = "/opt/retailflow-venv/bin/python"
DBT_EXECUTABLE = "/opt/retailflow-venv/bin/dbt"

DBT_PROJECT_DIR = (
    "/opt/retailflow/dbt/retailflow_analytics"
)


def task_failure_callback(context):
    task_instance = context.get("task_instance")
    exception = context.get("exception")

    LOGGER.error(
        "RetailFlow pipeline task failed. "
        "Task: %s | DAG run: %s | Error: %s",
        task_instance.task_id if task_instance else "unknown",
        context.get("run_id"),
        exception,
    )


default_args = {
    "owner": "retailflow",
    "depends_on_past": False,
    "retries": 2,
    "retry_delay": timedelta(minutes=2),
    "retry_exponential_backoff": True,
    "max_retry_delay": timedelta(minutes=10),
    "execution_timeout": timedelta(minutes=30),
    "on_failure_callback": task_failure_callback,
}


with DAG(
    dag_id="retailflow_pipeline",
    description=(
        "RetailFlow Bronze, Silver, Gold and dbt "
        "data engineering pipeline"
    ),
    default_args=default_args,
    start_date=datetime(2026, 10, 1),
    schedule_interval=None,
    catchup=False,
    max_active_runs=1,
    tags=[
        "retailflow",
        "data-engineering",
        "etl",
        "dbt",
    ],
) as dag:

    bronze_ingestion = BashOperator(
        task_id="bronze_ingestion",
        bash_command=(
            f"{ETL_PYTHON} "
            "-m src.ingestion.run_ingestion all"
        ),
        cwd=PROJECT_ROOT,
        append_env=True,
    )

    silver_transformation = BashOperator(
        task_id="silver_transformation",
        bash_command=(
            f"{ETL_PYTHON} "
            "-m src.transformations.silver.silver_loader "
            "--source all"
        ),
        cwd=PROJECT_ROOT,
        append_env=True,
    )

    gold_dimensions = BashOperator(
        task_id="gold_dimensions",
        bash_command=(
            f"{ETL_PYTHON} "
            "-m src.transformations.gold.dimension_loader"
        ),
        cwd=PROJECT_ROOT,
        append_env=True,
    )

    gold_facts = BashOperator(
        task_id="gold_facts",
        bash_command=(
            f"{ETL_PYTHON} "
            "-m src.transformations.gold.fact_loader"
        ),
        cwd=PROJECT_ROOT,
        append_env=True,
    )

    dbt_analytics_build = BashOperator(
        task_id="dbt_analytics_build",
        bash_command=(
            f"{DBT_EXECUTABLE} build "
            "--profiles-dir ."
        ),
        cwd=DBT_PROJECT_DIR,
        append_env=True,
    )

    (
        bronze_ingestion
        >> silver_transformation
        >> gold_dimensions
        >> gold_facts
        >> dbt_analytics_build
    )
