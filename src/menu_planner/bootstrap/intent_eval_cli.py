from __future__ import annotations

import argparse
import json
from collections.abc import Sequence
from pathlib import Path
from typing import cast

from menu_planner.application.intent_eval import (
    FixtureExpectedRouterCandidate,
    RuleBasedBaselineRouterCandidate,
    run_intent_router_eval,
)
from menu_planner.domain.contracts.models import JsonObject

DEFAULT_DATASET_PATH = Path("fixtures/evals/intent_router/dataset.v1.json")


def main(argv: Sequence[str] | None = None) -> int:
    parser = _parser()
    args = parser.parse_args(argv)
    candidate = _candidate(args.candidate)
    report = run_intent_router_eval(
        dataset_path=args.dataset,
        candidate=candidate,
        split=args.split,
    )
    serialized = json.dumps(report, sort_keys=True)
    if args.output is not None:
        args.output.write_text(f"{serialized}\n", encoding="utf-8")
    else:
        print(serialized)

    metrics = cast(JsonObject, report["metrics"])
    failures = cast(list[JsonObject], report["failures"])
    dangerous_rate = metrics["dangerous_false_automatic_execution_rate"]
    if failures or dangerous_rate != 0.0:
        return 1
    return 0


def _candidate(
    name: str,
) -> FixtureExpectedRouterCandidate | RuleBasedBaselineRouterCandidate:
    if name == "fixture_expected":
        return FixtureExpectedRouterCandidate()
    return RuleBasedBaselineRouterCandidate()


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run the M5 Intent Router eval skeleton.",
    )
    parser.add_argument(
        "--dataset",
        type=Path,
        default=DEFAULT_DATASET_PATH,
        help="Path to the versioned intent-router eval dataset.",
    )
    parser.add_argument(
        "--split",
        choices=("development", "holdout"),
        help="Optional dataset split to evaluate.",
    )
    parser.add_argument(
        "--candidate",
        choices=("rule_based_baseline", "fixture_expected"),
        default="rule_based_baseline",
        help="Router candidate to evaluate.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Optional path for the machine-readable JSON report.",
    )
    return parser


if __name__ == "__main__":
    raise SystemExit(main())
