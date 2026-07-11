from __future__ import annotations

import copy
from time import perf_counter
from typing import cast

from menu_planner.application.menu_replacement import (
    CreateReplacementDiffCommand,
    MenuReplacementService,
    ReplaceMealSlotCommand,
    create_replacement_diff,
)
from menu_planner.application.recipe_generation import (
    FakeRecipeDraftGenerator,
    RecipeDraftGenerationRequest,
    generate_recipe_draft,
)
from menu_planner.application.recipe_validation import (
    validate_recipe_draft_for_menu_item,
)
from menu_planner.application.safe_commit import (
    AuditEventRecord,
    AuditEventRepository,
    ConfirmationRecord,
    ConfirmationRepository,
    IdempotencyRecord,
    IdempotencyRepository,
    SafeCommitUnitOfWork,
    VersionedRecord,
    VersionedRecordRepository,
)
from menu_planner.domain.contracts.models import JsonObject, JsonValue
from menu_planner.domain.errors import ErrorCode


def run_m6b_recipe_replacement_eval() -> JsonObject:
    started = perf_counter()
    accepted_item = _accepted_menu_item()
    generation = generate_recipe_draft(
        request=RecipeDraftGenerationRequest(
            draft_id="recipe_draft_001",
            accepted_menu_item=accepted_item,
        ),
        generator=FakeRecipeDraftGenerator(),
    )
    validation = validate_recipe_draft_for_menu_item(
        draft=generation.draft_payload,
        accepted_menu_item=accepted_item,
    )
    diff = create_replacement_diff(
        CreateReplacementDiffCommand(
            preview_id="replacement_preview_001",
            user_id="user_001",
            menu_id="menu_001",
            source_version=1,
            draft_version=2,
            target_meal_slot_id="slot_002",
            source_menu_payload=_source_menu_payload(),
            replacement_menu_payload=_replacement_menu_payload(),
            recipe_version_id="recipe_001:v1",
        )
    )
    stale = _run_stale_replacement_check()
    elapsed_ms = (perf_counter() - started) * 1000

    confirmed_state_changed = cast(bool, stale["latest_state_changed"])
    failures = _failures(
        generation_ok=generation.ok,
        validation_ok=validation.ok,
        diff_ok=diff.ok,
        stale_rejected=cast(bool, stale["rejected"]),
        confirmed_state_changed=confirmed_state_changed,
    )
    return {
        "schema_version": "m6b.recipe_replacement_eval_report.v1",
        "generator_candidate": {
            "name": FakeRecipeDraftGenerator.name,
            "version": FakeRecipeDraftGenerator.version,
        },
        "model_backed_experiment": {
            "status": "skipped",
            "reason": (
                "ADR-0009 accepts only deterministic fake recipe/replacement "
                "behavior for Gate M6B. Model-backed generation remains "
                "deferred until provider/model/version, prompt/schema "
                "versioning, credentials handling, raw-output policy, eval "
                "dataset, and failure bounds are explicitly approved."
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
            "replacement_diff_ok": diff.ok,
            "stale_confirmation_rejected": stale["rejected"],
            "confirmed_state_changed": confirmed_state_changed,
            "side_effects_executed": stale["side_effects_executed"],
            "external_provider_required": False,
        },
        "preview": {
            "created": diff.preview is not None,
            "requires_confirmation": (
                diff.preview.requires_confirmation
                if diff.preview is not None
                else False
            ),
        },
        "failures": cast(JsonValue, failures),
    }


def _run_stale_replacement_check() -> JsonObject:
    unit_of_work = _InMemorySafeCommitUnitOfWork()
    latest = _committed_menu_record(
        record_id="menu_record_002",
        version=2,
        payload=_parallel_replacement_payload(),
    )
    unit_of_work.versioned_record_repo.records.extend(
        [
            _committed_menu_record(
                record_id="menu_record_001",
                version=1,
                payload=_source_menu_payload(),
            ),
            latest,
        ]
    )
    service = MenuReplacementService(lambda: unit_of_work)
    result = service.create_local_replacement_draft(
        ReplaceMealSlotCommand(
            record_id="replacement_draft_record_001",
            audit_event_id="replacement_audit_001",
            user_id="user_001",
            menu_id="menu_001",
            source_version=1,
            draft_version=2,
            target_meal_slot_id="slot_002",
            candidate_menu_payload=_replacement_menu_payload(),
        )
    )
    current = unit_of_work.versioned_record_repo.get_current_committed(
        "user_001",
        "menu",
        "menu_001",
    )
    return {
        "rejected": (
            not result.ok
            and bool(result.errors)
            and result.errors[0].code == ErrorCode.EXPECTED_VERSION_MISMATCH
        ),
        "latest_state_changed": current != latest,
        "side_effects_executed": result.side_effects_executed,
    }


def _failures(
    *,
    generation_ok: bool,
    validation_ok: bool,
    diff_ok: bool,
    stale_rejected: bool,
    confirmed_state_changed: bool,
) -> list[JsonObject]:
    failures: list[JsonObject] = []
    checks = {
        "generation_ok": generation_ok,
        "validation_ok": validation_ok,
        "replacement_diff_ok": diff_ok,
        "stale_confirmation_rejected": stale_rejected,
        "confirmed_state_unchanged": not confirmed_state_changed,
    }
    for check, passed in checks.items():
        if not passed:
            failures.append({"check": check, "passed": False})
    return failures


def _accepted_menu_item() -> JsonObject:
    return {
        "user_id": "user_001",
        "menu_id": "menu_001",
        "menu_version": 1,
        "meal_slot_id": "slot_002",
        "title": "Original dinner",
        "portions": 2,
        "available_equipment": ["oven", "stovetop"],
    }


def _source_menu_payload() -> JsonObject:
    return {
        "schema_version": "m2.v1",
        "user_id": "user_001",
        "menu_id": "menu_001",
        "meal_slots": [
            {
                "schema_version": "m2.v1",
                "slot_id": "slot_001",
                "date": "2026-07-10",
                "meal_type": "breakfast",
                "requirements": {},
            },
            {
                "schema_version": "m2.v1",
                "slot_id": "slot_002",
                "date": "2026-07-10",
                "meal_type": "dinner",
                "requirements": {},
            },
        ],
        "generated_items": [
            {"meal_slot_id": "slot_001", "title": "Original breakfast"},
            {"meal_slot_id": "slot_002", "title": "Original dinner"},
        ],
    }


def _replacement_menu_payload() -> JsonObject:
    payload = copy.deepcopy(_source_menu_payload())
    _item_by_slot(payload, "slot_002")["title"] = "Replacement soup"
    return payload


def _parallel_replacement_payload() -> JsonObject:
    payload = copy.deepcopy(_source_menu_payload())
    _item_by_slot(payload, "slot_002")["title"] = "Parallel replacement"
    return payload


def _item_by_slot(payload: JsonObject, meal_slot_id: str) -> JsonObject:
    generated_items = payload["generated_items"]
    assert isinstance(generated_items, list)
    for item in generated_items:
        assert isinstance(item, dict)
        if item.get("meal_slot_id") == meal_slot_id:
            return item
    raise ValueError(f"missing generated item for {meal_slot_id}")


def _committed_menu_record(
    *,
    record_id: str,
    version: int,
    payload: JsonObject,
) -> VersionedRecord:
    return VersionedRecord(
        record_id=record_id,
        user_id="user_001",
        entity_type="menu",
        entity_id="menu_001",
        version=version,
        lifecycle_status="committed",
        payload=payload,
    )


class _InMemoryConfirmationRepository:
    def add(self, record: ConfirmationRecord) -> None:
        raise AssertionError("M6B eval must not create confirmations")

    def get(self, confirmation_id: str) -> ConfirmationRecord | None:
        return None

    def get_for_user(
        self,
        confirmation_id: str,
        user_id: str,
    ) -> ConfirmationRecord | None:
        return None

    def update_status(
        self,
        confirmation_id: str,
        status: str,
        *,
        confirmed_at: object | None = None,
        committed_at: object | None = None,
    ) -> None:
        raise AssertionError("M6B eval must not update confirmations")


class _InMemoryIdempotencyRepository:
    def add(self, record: IdempotencyRecord) -> None:
        raise AssertionError("M6B eval must not create idempotency records")

    def get(
        self,
        user_id: str,
        operation: str,
        idempotency_key: str,
    ) -> IdempotencyRecord | None:
        return None

    def update_outcome(
        self,
        idempotency_record_id: str,
        status: str,
        *,
        outcome_ref: str | None = None,
        error_code: str | None = None,
    ) -> None:
        raise AssertionError("M6B eval must not update idempotency records")


class _InMemoryAuditEventRepository:
    def __init__(self) -> None:
        self.records: dict[str, AuditEventRecord] = {}

    def add(self, record: AuditEventRecord) -> None:
        self.records[record.audit_event_id] = record

    def get(self, audit_event_id: str) -> AuditEventRecord | None:
        return self.records.get(audit_event_id)


class _InMemoryVersionedRecordRepository:
    def __init__(self) -> None:
        self.records: list[VersionedRecord] = []

    def add(self, record: VersionedRecord) -> None:
        self.records.append(record)

    def get(
        self,
        user_id: str,
        entity_type: str,
        entity_id: str,
        version: int,
        lifecycle_status: str,
    ) -> VersionedRecord | None:
        return next(
            (
                record
                for record in self.records
                if record.user_id == user_id
                and record.entity_type == entity_type
                and record.entity_id == entity_id
                and record.version == version
                and record.lifecycle_status == lifecycle_status
            ),
            None,
        )

    def get_current_committed(
        self,
        user_id: str,
        entity_type: str,
        entity_id: str,
    ) -> VersionedRecord | None:
        matches = [
            record
            for record in self.records
            if record.user_id == user_id
            and record.entity_type == entity_type
            and record.entity_id == entity_id
            and record.lifecycle_status == "committed"
        ]
        if not matches:
            return None
        return max(matches, key=lambda record: record.version)


class _InMemorySafeCommitUnitOfWork:
    def __init__(self) -> None:
        self.confirmations: ConfirmationRepository = _InMemoryConfirmationRepository()
        self.idempotency_records: IdempotencyRepository = (
            _InMemoryIdempotencyRepository()
        )
        self.audit_events: AuditEventRepository = _InMemoryAuditEventRepository()
        self.versioned_record_repo = _InMemoryVersionedRecordRepository()
        self.versioned_records: VersionedRecordRepository = self.versioned_record_repo

    def __enter__(self) -> SafeCommitUnitOfWork:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: object | None,
    ) -> bool | None:
        return None

    def commit(self) -> None:
        return None

    def rollback(self) -> None:
        return None
