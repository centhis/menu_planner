from __future__ import annotations

import copy
import json
import pathlib
import unittest
from datetime import datetime
from types import TracebackType
from typing import cast

from menu_planner.application.recipe_persistence import (
    RECIPE_ENTITY_TYPE,
    RECIPE_PERSIST_OPERATION,
    RecipePersistenceService,
    RecipeVersionedRecordRepository,
    SaveRecipeVersionCommand,
    recipe_entity_id,
)
from menu_planner.application.recipe_validation import (
    RecipeDraftValidationResult,
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
from menu_planner.domain.contracts.models import JsonObject

ROOT = pathlib.Path(__file__).resolve().parents[2]
GOLDEN_ROOT = ROOT / "fixtures" / "golden" / "m6b_recipe_generation"


class RecipePersistenceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.unit_of_work = InMemorySafeCommitUnitOfWork()
        self.service = RecipePersistenceService(lambda: self.unit_of_work)

    def test_recipe_identity_and_operation_are_m6b_values(self) -> None:
        self.assertEqual(RECIPE_ENTITY_TYPE, "recipe")
        self.assertEqual(RECIPE_PERSIST_OPERATION, "persist_recipe_version")
        self.assertEqual(
            recipe_entity_id("user_001", "menu_001", "slot_001"),
            "recipe:user_001:menu_001:slot_001",
        )

    def test_valid_recipe_is_saved_as_versioned_record_with_audit(self) -> None:
        result = self.service.save_validated_recipe_version(_command())

        self.assertTrue(result.ok, result.errors)
        self.assertIsNotNone(result.recipe_version)
        assert result.recipe_version is not None
        self.assertEqual(result.recipe_version.recipe_id, "recipe_001")
        self.assertTrue(result.side_effects_executed)
        self.assertFalse(result.active_menu_changed)
        self.assertEqual(self.unit_of_work.commits, 1)
        self.assertEqual(self.unit_of_work.rollbacks, 0)
        self.assertEqual(len(self.unit_of_work.versioned_record_repo.records), 1)
        self.assertEqual(len(self.unit_of_work.audit_event_repo.records), 1)

        records = RecipeVersionedRecordRepository(self.unit_of_work.versioned_records)
        self.assertEqual(
            records.get_current_version("user_001", "recipe_001"),
            result.recipe_version,
        )
        saved = self.unit_of_work.versioned_record_repo.records[0]
        self.assertEqual(saved.entity_type, "recipe")
        self.assertEqual(saved.lifecycle_status, "committed")
        self.assertEqual(saved.audit_event_id, "recipe_audit_001")

    def test_invalid_recipe_does_not_create_valid_version(self) -> None:
        payload = _valid_payload()
        payload["source_meal_slot_id"] = "slot_999"
        validation = validate_recipe_draft_for_menu_item(
            draft=payload,
            accepted_menu_item=_accepted_menu_item(),
        )

        result = self.service.save_validated_recipe_version(
            _command(validation=validation)
        )

        self.assertFalse(result.ok)
        self.assertIsNone(result.recipe_version)
        self.assertFalse(result.side_effects_executed)
        self.assertFalse(result.active_menu_changed)
        self.assertEqual(self.unit_of_work.commits, 0)
        self.assertEqual(self.unit_of_work.rollbacks, 0)
        self.assertEqual(self.unit_of_work.versioned_record_repo.records, [])
        self.assertEqual(self.unit_of_work.audit_event_repo.records, {})

    def test_failure_rolls_back_recipe_audit_and_version(self) -> None:
        self.unit_of_work.versioned_record_repo.fail_on_add = True

        with self.assertRaisesRegex(RuntimeError, "version write failure"):
            self.service.save_validated_recipe_version(_command())

        self.assertEqual(self.unit_of_work.commits, 0)
        self.assertEqual(self.unit_of_work.rollbacks, 1)
        self.assertEqual(self.unit_of_work.versioned_record_repo.records, [])
        self.assertEqual(self.unit_of_work.audit_event_repo.records, {})

    def test_recipe_persistence_does_not_change_active_menu_record(self) -> None:
        self.unit_of_work.versioned_record_repo.records.append(
            VersionedRecord(
                record_id="menu_record_001",
                user_id="user_001",
                entity_type="menu",
                entity_id="menu_001",
                version=1,
                lifecycle_status="committed",
                payload={"schema_version": "m2.v1", "menu_id": "menu_001"},
            )
        )

        result = self.service.save_validated_recipe_version(_command())

        self.assertTrue(result.ok, result.errors)
        menu_records = [
            record
            for record in self.unit_of_work.versioned_record_repo.records
            if record.entity_type == "menu"
        ]
        self.assertEqual(len(menu_records), 1)
        self.assertEqual(menu_records[0].record_id, "menu_record_001")
        self.assertFalse(result.active_menu_changed)


class InMemoryConfirmationRepository:
    def add(self, record: ConfirmationRecord) -> None:
        raise AssertionError("recipe persistence must not create confirmations")

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
        raise AssertionError("recipe persistence must not update confirmations")


class InMemoryIdempotencyRepository:
    def add(self, record: IdempotencyRecord) -> None:
        raise AssertionError("recipe persistence must not create idempotency records")

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
        raise AssertionError("recipe persistence must not update idempotency records")


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
        self.fail_on_add = False

    def add(self, record: VersionedRecord) -> None:
        if self.fail_on_add:
            raise RuntimeError("injected version write failure")
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
    validation: RecipeDraftValidationResult | None = None,
) -> SaveRecipeVersionCommand:
    return SaveRecipeVersionCommand(
        record_id="recipe_record_001",
        audit_event_id="recipe_audit_001",
        recipe_id="recipe_001",
        version=1,
        validation=validation
        if validation is not None
        else validate_recipe_draft_for_menu_item(
            draft=_valid_payload(),
            accepted_menu_item=_accepted_menu_item(),
        ),
    )


def _valid_payload() -> JsonObject:
    return cast(JsonObject, copy.deepcopy(_load_json("one_day/recipe_draft.json")))


def _accepted_menu_item() -> JsonObject:
    return cast(
        JsonObject,
        copy.deepcopy(_load_json("one_day/accepted_menu_item.json")),
    )


def _load_json(relative_path: str) -> object:
    return json.loads((GOLDEN_ROOT / relative_path).read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
