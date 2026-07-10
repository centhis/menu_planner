from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from datetime import UTC, datetime

from menu_planner.application.profile_scenario import (
    ProfileScenarioIds,
    ProfileScenarioResult,
    run_m4_profile_scenario,
)
from menu_planner.application.profile_service import ProfileApplicationService
from menu_planner.config import get_settings
from menu_planner.infrastructure.safe_commit_sql import SqlSafeCommitUnitOfWork


def main(argv: Sequence[str] | None = None) -> int:
    parser = _parser()
    args = parser.parse_args(argv)
    settings = get_settings()
    if not settings.database_url:
        print("DATABASE_URL is required for the M4 profile scenario", file=sys.stderr)
        return 2

    try:
        expires_at = _parse_aware_datetime(args.expires_at)
        now = _parse_aware_datetime(args.now) if args.now else datetime.now(UTC)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    ids = ProfileScenarioIds(
        run_id=args.run_id,
        idempotency_key=args.idempotency_key,
        draft_version=args.draft_version,
    )

    def unit_of_work_factory() -> SqlSafeCommitUnitOfWork:
        return SqlSafeCommitUnitOfWork(settings.database_url)

    service = ProfileApplicationService(unit_of_work_factory)
    result = run_m4_profile_scenario(
        service=service,
        unit_of_work_factory=unit_of_work_factory,
        user_id=args.user_id,
        ids=ids,
        now=now,
        expires_at=expires_at,
    )
    print(json.dumps(_summary(args.user_id, ids, result), sort_keys=True))
    return 0 if result.ok else 1


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run the deterministic M4 profile vertical slice scenario.",
    )
    parser.add_argument("--user-id", default="user_001")
    parser.add_argument("--run-id", default="m4_profile_cli")
    parser.add_argument("--draft-version", type=int, default=1)
    parser.add_argument("--idempotency-key", required=True)
    parser.add_argument("--expires-at", required=True)
    parser.add_argument("--now")
    return parser


def _parse_aware_datetime(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError(f"{value} must include a timezone offset")
    return parsed


def _summary(
    user_id: str,
    ids: ProfileScenarioIds,
    scenario: ProfileScenarioResult,
) -> dict[str, object]:
    profile = scenario.current_profile
    safe_commit = (
        scenario.commit_result.safe_commit
        if scenario.commit_result is not None
        else None
    )
    error = safe_commit.error if safe_commit is not None else None
    return {
        "ok": scenario.ok,
        "user_id": user_id,
        "run_id": ids.run_id,
        "draft_version": ids.draft_version,
        "idempotency_key": ids.idempotency_key,
        "replayed": scenario.replayed,
        "reused_draft": scenario.reused_draft,
        "reused_confirmation": scenario.reused_confirmation,
        "profile_id": profile.profile_id if profile is not None else None,
        "profile_version": profile.version if profile is not None else None,
        "summary_hash": (
            scenario.confirmation.summary_hash
            if scenario.confirmation is not None
            else None
        ),
        "error_code": error.code if error is not None else None,
    }


if __name__ == "__main__":
    raise SystemExit(main())
