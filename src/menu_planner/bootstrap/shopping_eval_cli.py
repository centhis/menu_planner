from __future__ import annotations

import argparse
import json
from collections.abc import Sequence
from pathlib import Path
from typing import cast

from menu_planner.application.shopping_eval import (
    DEFAULT_CATALOG_SNAPSHOT_PATH,
    run_m7_shopping_eval,
)
from menu_planner.domain.contracts.models import JsonObject


def main(argv: Sequence[str] | None = None) -> int:
    parser = _parser()
    args = parser.parse_args(argv)
    report = run_m7_shopping_eval(catalog_snapshot_path=args.catalog_snapshot)
    serialized = json.dumps(report, sort_keys=True)
    if args.output is not None:
        args.output.write_text(f"{serialized}\n", encoding="utf-8")
    else:
        print(serialized)

    metrics = cast(JsonObject, report["metrics"])
    failures = cast(list[JsonObject], report["failures"])
    if failures or metrics["confirmed_state_changed"]:
        return 1
    return 0


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run the M7 shopping list and mock catalog golden eval.",
    )
    parser.add_argument(
        "--catalog-snapshot",
        type=Path,
        default=DEFAULT_CATALOG_SNAPSHOT_PATH,
        help="Path to the reviewed M7 mock catalog snapshot fixture.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Optional path for the machine-readable JSON report.",
    )
    return parser


if __name__ == "__main__":
    raise SystemExit(main())
