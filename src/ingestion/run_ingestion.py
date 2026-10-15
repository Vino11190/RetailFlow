
import argparse
import importlib
import sys
from datetime import datetime, timezone

from src.config.source_registry import (
    SOURCE_REGISTRY,
    get_enabled_sources,
)


# ============================================================
# RetailFlow
# Unified Ingestion Runner
# ============================================================


INGESTION_MODULES = {
    "ecommerce": "src.ingestion.ingest_ecommerce",
    "products": "src.ingestion.ingest_products_api",
    "pos": "src.ingestion.ingest_pos",
    "inventory": "src.ingestion.ingest_inventory",
    "suppliers": "src.ingestion.ingest_suppliers",
    "payments": "src.ingestion.ingest_payments",
    "returns": "src.ingestion.ingest_returns",
}


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def run_source(source_system: str) -> bool:
    """
    Execute one registered ingestion pipeline.

    Returns True on success and False on failure.
    """

    if source_system not in SOURCE_REGISTRY:
        print(
            f"ERROR: Unknown source system: {source_system}"
        )
        return False

    source_definition = SOURCE_REGISTRY[source_system]

    if not source_definition.enabled:
        print(
            f"SKIPPED: {source_system} is disabled."
        )
        return True

    module_path = INGESTION_MODULES.get(source_system)

    if module_path is None:
        print(
            f"ERROR: No ingestion module registered "
            f"for {source_system}"
        )
        return False

    print()
    print("=" * 60)
    print(f"STARTING SOURCE: {source_system.upper()}")
    print("=" * 60)

    started_at = utc_now()

    try:
        module = importlib.import_module(module_path)

        module.main()

        duration = (
            utc_now() - started_at
        ).total_seconds()

        print()
        print(
            f"SUCCESS: {source_system} "
            f"({duration:.2f} seconds)"
        )

        return True

    except Exception as error:
        duration = (
            utc_now() - started_at
        ).total_seconds()

        print()
        print(
            f"FAILED: {source_system} "
            f"({duration:.2f} seconds)"
        )
        print(f"Error: {error}")

        return False


def list_sources() -> None:
    print()
    print("RetailFlow Registered Sources")
    print("=============================")

    for name, definition in SOURCE_REGISTRY.items():
        status = (
            "ENABLED"
            if definition.enabled
            else "DISABLED"
        )

        print(
            f"{name:<12} "
            f"{definition.source_type:<10} "
            f"{status:<8} "
            f"datasets={len(definition.datasets)}"
        )


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "RetailFlow unified ingestion runner."
        )
    )

    parser.add_argument(
        "source",
        nargs="?",
        default="list",
        help=(
            "Source name, 'all', or 'list'."
        ),
    )

    args = parser.parse_args()
    source = args.source.lower()

    if source == "list":
        list_sources()
        return

    if source == "all":
        sources = list(
            get_enabled_sources().keys()
        )
    else:
        if source not in SOURCE_REGISTRY:
            parser.error(
                f"Unknown source '{source}'. "
                "Use 'list' to see available sources."
            )

        sources = [source]

    print()
    print("RetailFlow Unified Ingestion")
    print("============================")
    print(f"Selected sources: {len(sources)}")

    results = {}

    for source_system in sources:
        results[source_system] = run_source(
            source_system
        )

    print()
    print("=" * 60)
    print("INGESTION EXECUTION SUMMARY")
    print("=" * 60)

    for source_system, success in results.items():
        status = (
            "SUCCESS"
            if success
            else "FAILED"
        )

        print(
            f"{source_system:<12} {status}"
        )

    successful = sum(results.values())
    failed = len(results) - successful

    print()
    print(f"Successful: {successful}")
    print(f"Failed: {failed}")

    if failed:
        sys.exit(1)


if __name__ == "__main__":
    main()
