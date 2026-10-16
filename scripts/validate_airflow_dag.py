
"""Static validation of the RetailFlow Airflow DAG."""

import ast
from pathlib import Path


DAG_PATH = (
    Path(__file__).resolve().parents[1]
    / "airflow"
    / "dags"
    / "retailflow_pipeline.py"
)

EXPECTED_DAG_ID = "retailflow_pipeline"

EXPECTED_TASKS = {
    "bronze_ingestion",
    "silver_transformation",
    "gold_dimensions",
    "gold_facts",
    "dbt_analytics_build",
}


def main() -> None:
    if not DAG_PATH.is_file():
        raise SystemExit(f"FAIL: DAG file missing: {DAG_PATH}")

    source = DAG_PATH.read_text(encoding="utf-8-sig")
    tree = ast.parse(source, filename=str(DAG_PATH))

    dag_ids = set()
    task_ids = set()

    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue

        for keyword in node.keywords:
            if not isinstance(keyword.value, ast.Constant):
                continue

            if keyword.arg == "dag_id":
                dag_ids.add(keyword.value.value)

            if keyword.arg == "task_id":
                task_ids.add(keyword.value.value)

    if EXPECTED_DAG_ID not in dag_ids:
        raise SystemExit(
            f"FAIL: Expected DAG ID '{EXPECTED_DAG_ID}' not found."
        )

    missing = EXPECTED_TASKS - task_ids

    if missing:
        raise SystemExit(
            f"FAIL: Missing Airflow tasks: {sorted(missing)}"
        )

    print("PASS: Airflow DAG syntax validated.")
    print(f"PASS: DAG ID: {EXPECTED_DAG_ID}")
    print(f"PASS: All {len(EXPECTED_TASKS)} expected tasks found.")
    print("NOTE: Runtime imports and dependencies not yet validated.")


if __name__ == "__main__":
    main()
