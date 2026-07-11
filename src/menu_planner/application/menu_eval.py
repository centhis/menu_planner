from __future__ import annotations

import json
from pathlib import Path
from time import perf_counter
from typing import cast

from menu_planner.application.menu_generation import (
    FakeMenuDraftGenerator,
    MenuDraftGenerationRequest,
    generate_menu_draft,
)
from menu_planner.application.menu_preview import (
    CreateMenuPreviewCommand,
    create_menu_preview,
)
from menu_planner.application.menu_repair import (
    DEFAULT_MAX_REPAIR_ATTEMPTS,
    repair_menu_draft,
)
from menu_planner.application.menu_validation import validate_menu_draft_for_context
from menu_planner.domain.contracts.models import JsonObject, JsonValue, PlanningContext
from menu_planner.domain.contracts.validation import validate_contract

DEFAULT_PLANNING_CONTEXT_PATH = Path(
    "fixtures/golden/m6a_menu_draft_generation/one_day/planning_context.json"
)


def run_m6a_menu_eval(
    *,
    planning_context_path: Path = DEFAULT_PLANNING_CONTEXT_PATH,
) -> JsonObject:
    started = perf_counter()
    context = _load_planning_context(planning_context_path)
    request = MenuDraftGenerationRequest(
        draft_id="menu_draft_001",
        planning_context=context,
    )

    generation = generate_menu_draft(
        request=request,
        generator=FakeMenuDraftGenerator(),
    )
    validation = validate_menu_draft_for_context(
        draft=generation.draft_payload,
        planning_context=context,
    )
    repair = repair_menu_draft(
        request=request,
        max_attempts=DEFAULT_MAX_REPAIR_ATTEMPTS,
    )
    preview = create_menu_preview(
        CreateMenuPreviewCommand(
            preview_id="preview_001",
            menu_id="menu_001",
            expected_version=0,
            draft_version=1,
            validation=validation,
        )
    )
    elapsed_ms = (perf_counter() - started) * 1000

    failures = _failures(
        generation_ok=generation.ok,
        validation_ok=validation.ok,
        repair_ok=repair.ok,
        preview_ok=preview.ok,
        confirmed_state_changed=(
            generation.side_effects_executed
            or validation.side_effects_executed
            or repair.confirmed_state_changed
            or preview.confirmed_state_changed
        ),
    )
    return {
        "schema_version": "m6a.menu_draft_eval_report.v1",
        "planning_context_fixture": str(planning_context_path),
        "generator_candidate": {
            "name": FakeMenuDraftGenerator.name,
            "version": FakeMenuDraftGenerator.version,
        },
        "model_backed_experiment": {
            "status": "skipped",
            "reason": (
                "ADR-0008 accepts only deterministic fake generation for Gate "
                "M6A and defers model-backed generation until provider/model, "
                "prompt/schema versioning, credentials handling, raw-output "
                "policy, eval dataset, and repair bounds are explicitly "
                "approved."
            ),
            "provider": None,
            "model": None,
            "prompt_schema_version": None,
            "credentials_read": False,
            "raw_output_stored": False,
        },
        "metrics": {
            "elapsed_ms": elapsed_ms,
            "generation_ok": generation.ok,
            "validation_ok": validation.ok,
            "repair_ok": repair.ok,
            "preview_ok": preview.ok,
            "max_repair_attempts": DEFAULT_MAX_REPAIR_ATTEMPTS,
            "confirmed_state_changed": False,
            "side_effects_executed": False,
            "external_provider_required": False,
        },
        "week_draft_expansion": {
            "status": "skipped",
            "reason": (
                "ADR-0008 accepts the Gate M6A one-day period shape only. "
                "Week generation remains deferred until period semantics, "
                "week fixtures, and week validation rules are explicitly "
                "accepted."
            ),
            "adr_accepts_period_shape": False,
            "one_day_gate_green": (
                generation.ok and validation.ok and repair.ok and preview.ok
            ),
            "fixtures_added": False,
        },
        "preview": {
            "created": preview.preview is not None,
            "requires_confirmation": (
                preview.preview.requires_confirmation
                if preview.preview is not None
                else False
            ),
        },
        "failures": cast(JsonValue, failures),
    }


def _load_planning_context(path: Path) -> PlanningContext:
    payload = cast(JsonObject, json.loads(path.read_text(encoding="utf-8")))
    validation = validate_contract("planning_context", payload)
    if not validation.is_valid or validation.value is None:
        raise ValueError("planning_context fixture is invalid")
    return cast(PlanningContext, validation.value)


def _failures(
    *,
    generation_ok: bool,
    validation_ok: bool,
    repair_ok: bool,
    preview_ok: bool,
    confirmed_state_changed: bool,
) -> list[JsonObject]:
    failures: list[JsonObject] = []
    checks = {
        "generation_ok": generation_ok,
        "validation_ok": validation_ok,
        "repair_ok": repair_ok,
        "preview_ok": preview_ok,
        "confirmed_state_unchanged": not confirmed_state_changed,
    }
    for check, passed in checks.items():
        if not passed:
            failures.append({"check": check, "passed": False})
    return failures
