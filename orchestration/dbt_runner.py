
"""
RetailFlow dbt execution integration.

Runs dbt using its dedicated Python environment.
Designed for invocation after the Gold warehouse has been built.
"""

from __future__ import annotations

import logging
import subprocess
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]

DBT_PROJECT_DIR = (
    PROJECT_ROOT / "dbt" / "retailflow_analytics"
)

DBT_EXECUTABLE = (
    PROJECT_ROOT / ".venv-dbt" / "Scripts" / "dbt.exe"
)

LOGGER = logging.getLogger(__name__)


def run_dbt(
    command: str = "build",
    *,
    select: str | None = None,
    timeout_seconds: int = 1800,
) -> None:
    """
    Execute a dbt command and fail if dbt fails.

    The default 'build' command executes models and tests
    in dependency order.
    """

    if command not in {"build", "run", "test", "parse"}:
        raise ValueError(f"Unsupported dbt command: {command}")

    if not DBT_EXECUTABLE.is_file():
        raise FileNotFoundError(
            f"dbt executable not found: {DBT_EXECUTABLE}"
        )

    if not (DBT_PROJECT_DIR / "dbt_project.yml").is_file():
        raise FileNotFoundError(
            f"dbt project not found: {DBT_PROJECT_DIR}"
        )

    args = [
        str(DBT_EXECUTABLE),
        command,
        "--profiles-dir",
        str(DBT_PROJECT_DIR),
    ]

    if select:
        args.extend(["--select", select])

    LOGGER.info("Starting dbt command: %s", command)

    started = time.monotonic()

    try:
        result = subprocess.run(
            args,
            cwd=DBT_PROJECT_DIR,
            check=False,
            timeout=timeout_seconds,
        )

    except subprocess.TimeoutExpired as exc:
        LOGGER.error(
            "dbt exceeded its %s-second timeout",
            timeout_seconds,
        )
        raise RuntimeError("dbt execution timed out") from exc

    duration = time.monotonic() - started

    if result.returncode != 0:
        raise RuntimeError(
            f"dbt {command} failed with exit code "
            f"{result.returncode} after {duration:.1f}s"
        )

    LOGGER.info(
        "dbt %s completed successfully in %.1fs",
        command,
        duration,
    )


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )

    run_dbt("build")
