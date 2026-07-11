from __future__ import annotations

import copy
import unittest
from datetime import datetime
from types import TracebackType

from menu_planner.application.menu_replacement import (
    REPLACE_MEAL_SLOT_OPERATION,
    CreateReplacementDiffCommand,
    MenuReplacementService,
    ReplaceMealSlotCommand,
    create_replacement_diff,
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
from menu_planner.domain.contracts.models import JsonObject
from menu_planner.domain.errors import ErrorCode


class MenuReplacementTests(unittest.TestCase):
    def setUp(self) -> None:
        self.unit_of_work = InMemorySafeCommitUnitOfWork()
        self.unit_of_work.versioned_record_repo.records.append(_source_menu_record())
        self.service = MenuReplacementService(lambda: self.unit_of_work)

    def test_happy_path_creates_draft_version_for_one_slot(self) -> None:
        result = self.service.create_local_replacement_draft(
            _command(candidate_menu_payload=_candidate_payload())
        )

        self.assertTrue(result.ok, result.errors)
        self.assertTrue(result.side_effects_executed)
        self.assertFalse(result.shopping_list_changed)
        self.assertEqual(self.unit_of_work.commits, 1)
        self.assertEqual(self.unit_of_work.rollbacks, 0)
        assert result.audit_event is not None
        self.assertEqual(result.audit_event.operation, REPLACE_MEAL_SLOT_OPERATION)

        assert result.draft_record is not None
        self.assertEqual(result.draft_record.entity_type, "menu")
        self.assertEqual(result.draft_record.lifecycle_status, "draft")
        self.assertEqual(result.draft_record.version, 2)
        self.assertEqual(
            _item_by_slot(result.draft_record.payload, "slot_002")["title"],
            "Replacement soup",
        )

    def test_unknown_target_slot_is_rejected_without_write(self) -> None:
        result = self.service.create_local_replacement_draft(
            _command(
                target_meal_slot_id="slot_999",
                candidate_menu_payload=_candidate_payload(),
            )
        )

        self.assertFalse(result.ok)
        self.assertEqual(result.errors[0].code, ErrorCode.MENU_MEAL_SLOT_MISSING)
        self.assertEqual(self.unit_of_work.commits, 0)
        self.assertEqual(self.unit_of_work.rollbacks, 1)
        self.assertEqual(len(self.unit_of_work.versioned_record_repo.records), 1)
        self.assertEqual(self.unit_of_work.audit_event_repo.records, {})

    def test_stale_source_version_is_rejected_without_write(self) -> None:
        latest = _committed_menu_record(
            record_id="menu_record_002",
            version=2,
            payload=_parallel_replacement_payload(),
        )
        self.unit_of_work.versioned_record_repo.records.append(latest)

        result = self.service.create_local_replacement_draft(
            _command(candidate_menu_payload=_candidate_payload())
        )

        self.assertFalse(result.ok)
        self.assertEqual(result.errors[0].code, ErrorCode.EXPECTED_VERSION_MISMATCH)
        self.assertEqual(result.errors[0].details["expected_version"], 1)
        self.assertEqual(result.errors[0].details["actual_version"], 2)
        self.assertEqual(self.unit_of_work.commits, 0)
        self.assertEqual(self.unit_of_work.rollbacks, 1)
        self.assertEqual(len(self.unit_of_work.versioned_record_repo.records), 2)
        self.assertEqual(
            self.unit_of_work.versioned_record_repo.records[-1],
            latest,
        )
        self.assertEqual(self.unit_of_work.audit_event_repo.records, {})

    def test_parallel_replacement_leaves_latest_committed_state_unchanged(self) -> None:
        latest = _committed_menu_record(
            record_id="menu_record_002",
            version=2,
            payload=_parallel_replacement_payload(),
        )
        self.unit_of_work.versioned_record_repo.records.append(latest)
        latest_before = copy.deepcopy(latest)

        result = self.service.create_local_replacement_draft(
            _command(candidate_menu_payload=_candidate_payload())
        )

        self.assertFalse(result.ok)
        self.assertEqual(result.errors[0].code, ErrorCode.EXPECTED_VERSION_MISMATCH)
        self.assertEqual(
            self.unit_of_work.versioned_record_repo.get_current_committed(
                "user_001",
                "menu",
                "menu_001",
            ),
            latest_before,
        )
        self.assertEqual(
            [
                record
                for record in self.unit_of_work.versioned_record_repo.records
                if record.lifecycle_status == "draft"
            ],
            [],
        )

    def test_multiple_slot_change_is_rejected_without_write(self) -> None:
        candidate = _candidate_payload()
        _item_by_slot(candidate, "slot_001")["title"] = "Changed breakfast"

        result = self.service.create_local_replacement_draft(
            _command(candidate_menu_payload=candidate)
        )

        self.assertFalse(result.ok)
        self.assertEqual(result.errors[0].code, ErrorCode.MENU_REPLACEMENT_NOT_LOCAL)
        self.assertEqual(
            result.errors[0].details["changed_meal_slot_ids"],
            "slot_001,slot_002",
        )
        self.assertEqual(self.unit_of_work.commits, 0)
        self.assertEqual(self.unit_of_work.rollbacks, 1)
        self.assertEqual(len(self.unit_of_work.versioned_record_repo.records), 1)
        self.assertEqual(self.unit_of_work.audit_event_repo.records, {})

    def test_unaffected_slots_and_source_record_remain_unchanged(self) -> None:
        source_before = copy.deepcopy(
            self.unit_of_work.versioned_record_repo.records[0]
        )

        result = self.service.create_local_replacement_draft(
            _command(candidate_menu_payload=_candidate_payload())
        )

        self.assertTrue(result.ok, result.errors)
        assert result.draft_record is not None
        self.assertEqual(
            _item_by_slot(result.draft_record.payload, "slot_001"),
            _item_by_slot(source_before.payload, "slot_001"),
        )
        self.assertEqual(
            result.draft_record.payload["meal_slots"],
            source_before.payload["meal_slots"],
        )
        self.assertEqual(
            self.unit_of_work.versioned_record_repo.records[0],
            source_before,
        )

    def test_replacement_diff_is_stable_for_same_input(self) -> None:
        first = create_replacement_diff(_diff_command())
        second = create_replacement_diff(_diff_command())

        self.assertTrue(first.ok, first.errors)
        self.assertTrue(second.ok, second.errors)
        assert first.preview is not None
        assert second.preview is not None
        self.assertEqual(first.preview.summary_hash, second.preview.summary_hash)
        self.assertEqual(first.preview.changes, second.preview.changes)

    def test_replacement_diff_changes_when_replacement_data_changes(self) -> None:
        base = create_replacement_diff(_diff_command())
        changed_payload = _candidate_payload()
        _item_by_slot(changed_payload, "slot_002")["title"] = "Replacement stew"
        changed = create_replacement_diff(
            _diff_command(replacement_menu_payload=changed_payload)
        )

        self.assertTrue(base.ok, base.errors)
        self.assertTrue(changed.ok, changed.errors)
        assert base.preview is not None
        assert changed.preview is not None
        self.assertNotEqual(base.preview.summary_hash, changed.preview.summary_hash)
        self.assertNotEqual(base.preview.changes, changed.preview.changes)

    def test_replacement_diff_has_exact_user_facing_summary(self) -> None:
        result = create_replacement_diff(
            _diff_command(recipe_version_id="recipe_001:v2")
        )

        self.assertTrue(result.ok, result.errors)
        assert result.preview is not None
        self.assertEqual(result.preview.operation, REPLACE_MEAL_SLOT_OPERATION)
        self.assertEqual(result.preview.entity_ref, "menu:menu_001")
        self.assertTrue(result.preview.requires_confirmation)
        self.assertEqual(len(result.preview.changes), 1)
        change = result.preview.changes[0]
        self.assertEqual(change["source_menu_id"], "menu_001")
        self.assertEqual(change["source_menu_version"], 1)
        self.assertEqual(change["draft_version"], 2)
        self.assertEqual(change["target_meal_slot_id"], "slot_002")
        self.assertEqual(
            change["old_item"],
            _item_by_slot(_source_payload(), "slot_002"),
        )
        self.assertEqual(
            change["new_item"],
            _item_by_slot(_candidate_payload(), "slot_002"),
        )
        self.assertEqual(change["recipe_version_impact"], "recipe_001:v2")
        self.assertEqual(change["shopping_list_impact"], "none")
        self.assertEqual(change["unaffected_slots"], "unchanged")


class InMemoryConfirmationRepository:
    def add(self, record: ConfirmationRecord) -> None:
        raise AssertionError("replacement draft creation must not create confirmations")

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
        confirmed_at: datetime | None = None,
        committed_at: datetime | None = None,
    ) -> None:
        raise AssertionError("replacement draft creation must not update confirmations")


class InMemoryIdempotencyRepository:
    def add(self, record: IdempotencyRecord) -> None:
        raise AssertionError("replacement draft creation must not create idempotency")

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
        raise AssertionError("replacement draft creation must not update idempotency")


class InMemoryAuditEventRepository:
    def __init__(self) -> None:
        self.records: dict[str, AuditEventRecord] = {}

    def add(self, record: AuditEventRecord) -> None:
        self.records[record.audit_event_id] = record

    def get(self, audit_event_id: str) -> AuditEventRecord | None:
        return self.records.get(audit_event_id)


class InMemoryVersionedRecordRepository:
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


class InMemorySafeCommitUnitOfWork:
    def __init__(self) -> None:
        self.confirmations: ConfirmationRepository = InMemoryConfirmationRepository()
        self.idempotency_records: IdempotencyRepository = (
            InMemoryIdempotencyRepository()
        )
        self.audit_event_repo = InMemoryAuditEventRepository()
        self.audit_events: AuditEventRepository = self.audit_event_repo
        self.versioned_record_repo = InMemoryVersionedRecordRepository()
        self.versioned_records: VersionedRecordRepository = self.versioned_record_repo
        self.commits = 0
        self.rollbacks = 0
        self._snapshot: tuple[
            dict[str, AuditEventRecord],
            list[VersionedRecord],
        ] | None = None

    def __enter__(self) -> SafeCommitUnitOfWork:
        self._snapshot = (
            dict(self.audit_event_repo.records),
            list(self.versioned_record_repo.records),
        )
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> bool | None:
        return None

    def commit(self) -> None:
        self.commits += 1

    def rollback(self) -> None:
        self.rollbacks += 1
        if self._snapshot is None:
            return
        audit_events, versioned_records = self._snapshot
        self.audit_event_repo.records = dict(audit_events)
        self.versioned_record_repo.records = list(versioned_records)


def _command(
    *,
    target_meal_slot_id: str = "slot_002",
    candidate_menu_payload: JsonObject,
) -> ReplaceMealSlotCommand:
    return ReplaceMealSlotCommand(
        record_id="replacement_draft_record_001",
        audit_event_id="replacement_audit_001",
        user_id="user_001",
        menu_id="menu_001",
        source_version=1,
        draft_version=2,
        target_meal_slot_id=target_meal_slot_id,
        candidate_menu_payload=candidate_menu_payload,
    )


def _diff_command(
    *,
    replacement_menu_payload: JsonObject | None = None,
    recipe_version_id: str | None = None,
) -> CreateReplacementDiffCommand:
    return CreateReplacementDiffCommand(
        preview_id="replacement_preview_001",
        user_id="user_001",
        menu_id="menu_001",
        source_version=1,
        draft_version=2,
        target_meal_slot_id="slot_002",
        source_menu_payload=_source_payload(),
        replacement_menu_payload=replacement_menu_payload or _candidate_payload(),
        recipe_version_id=recipe_version_id,
    )


def _source_menu_record() -> VersionedRecord:
    return _committed_menu_record(
        record_id="menu_record_001",
        version=1,
        payload=_source_payload(),
    )


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


def _source_payload() -> JsonObject:
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


def _candidate_payload() -> JsonObject:
    payload = copy.deepcopy(_source_payload())
    _item_by_slot(payload, "slot_002")["title"] = "Replacement soup"
    return payload


def _parallel_replacement_payload() -> JsonObject:
    payload = copy.deepcopy(_source_payload())
    _item_by_slot(payload, "slot_002")["title"] = "Parallel replacement"
    return payload


def _item_by_slot(payload: JsonObject, meal_slot_id: str) -> JsonObject:
    generated_items = payload["generated_items"]
    assert isinstance(generated_items, list)
    for item in generated_items:
        assert isinstance(item, dict)
        if item.get("meal_slot_id") == meal_slot_id:
            return item
    raise AssertionError(f"missing generated item for {meal_slot_id}")


if __name__ == "__main__":
    unittest.main()
