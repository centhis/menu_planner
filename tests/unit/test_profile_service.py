from __future__ import annotations

import unittest
from datetime import UTC, datetime, timedelta
from types import TracebackType
from typing import cast

from menu_planner.application.profile_scenario import (
    ProfileScenarioIds,
    run_m4_profile_scenario,
)
from menu_planner.application.profile_service import (
    CommitProfileCommand,
    ConfirmProfileCommitCommand,
    CreateProfileConfirmationCommand,
    CreateProfilePreviewCommand,
    ProfileApplicationService,
    ProfileCommandResult,
    SaveProfileDraftCommand,
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
from menu_planner.domain.contracts.models import (
    SCHEMA_VERSION,
    JsonObject,
    WorkflowRun,
    WorkflowState,
)
from menu_planner.domain.errors import ErrorCode
from menu_planner.domain.workflow import allowed_actions


def _workflow(state: WorkflowState) -> WorkflowRun:
    return WorkflowRun(
        schema_version=SCHEMA_VERSION,
        workflow_id="workflow_001",
        user_id="user_001",
        state=state,
        allowed_actions=[action.value for action in allowed_actions(state)],
        attempts=0,
    )


def _profile_fields() -> JsonObject:
    return {
        "user_facts": {
            "people_count": 1,
            "locale": "en-US",
            "timezone": "UTC",
            "available_equipment": ["stovetop"],
            "default_max_active_time_minutes": 30,
        },
        "strict_restrictions": [
            {
                "kind": "ingredient_exclusion",
                "value": "peanut",
            }
        ],
        "soft_preferences": [
            {
                "direction": "prefer",
                "value": "vegetables",
            }
        ],
    }


class InMemoryConfirmationRepository:
    def __init__(self) -> None:
        self.records: dict[str, ConfirmationRecord] = {}

    def add(self, record: ConfirmationRecord) -> None:
        self.records[record.confirmation_id] = record

    def get(self, confirmation_id: str) -> ConfirmationRecord | None:
        return self.records.get(confirmation_id)

    def get_for_user(
        self,
        confirmation_id: str,
        user_id: str,
    ) -> ConfirmationRecord | None:
        record = self.records.get(confirmation_id)
        if record is None or record.user_id != user_id:
            return None
        return record

    def update_status(
        self,
        confirmation_id: str,
        status: str,
        *,
        confirmed_at: datetime | None = None,
        committed_at: datetime | None = None,
    ) -> None:
        record = self.records[confirmation_id]
        self.records[confirmation_id] = ConfirmationRecord(
            confirmation_id=record.confirmation_id,
            user_id=record.user_id,
            operation=record.operation,
            entity_type=record.entity_type,
            entity_id=record.entity_id,
            expected_version=record.expected_version,
            draft_version=record.draft_version,
            expires_at=record.expires_at,
            summary_hash=record.summary_hash,
            status=status,
            created_at=record.created_at,
            updated_at=record.updated_at,
            confirmed_at=confirmed_at or record.confirmed_at,
            committed_at=committed_at or record.committed_at,
        )


class InMemoryIdempotencyRepository:
    def __init__(self) -> None:
        self.records: dict[tuple[str, str, str], IdempotencyRecord] = {}

    def add(self, record: IdempotencyRecord) -> None:
        self.records[
            (record.user_id, record.operation, record.idempotency_key)
        ] = record

    def get(
        self,
        user_id: str,
        operation: str,
        idempotency_key: str,
    ) -> IdempotencyRecord | None:
        return self.records.get((user_id, operation, idempotency_key))

    def update_outcome(
        self,
        idempotency_record_id: str,
        status: str,
        *,
        outcome_ref: str | None = None,
        error_code: str | None = None,
    ) -> None:
        for key, record in self.records.items():
            if record.idempotency_record_id != idempotency_record_id:
                continue
            self.records[key] = IdempotencyRecord(
                idempotency_record_id=record.idempotency_record_id,
                user_id=record.user_id,
                operation=record.operation,
                idempotency_key=record.idempotency_key,
                request_fingerprint=record.request_fingerprint,
                status=status,
                outcome_ref=outcome_ref,
                error_code=error_code,
            )
            return
        raise KeyError(idempotency_record_id)


class InMemoryAuditEventRepository:
    def __init__(self) -> None:
        self.records: dict[str, AuditEventRecord] = {}
        self.fail_on_add = False

    def add(self, record: AuditEventRecord) -> None:
        if self.fail_on_add:
            raise RuntimeError("injected audit failure")
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
        self.confirmation_repo = InMemoryConfirmationRepository()
        self.confirmations: ConfirmationRepository = self.confirmation_repo
        self.idempotency_repo = InMemoryIdempotencyRepository()
        self.idempotency_records: IdempotencyRepository = self.idempotency_repo
        self.audit_event_repo = InMemoryAuditEventRepository()
        self.audit_events: AuditEventRepository = self.audit_event_repo
        self.versioned_record_repo = InMemoryVersionedRecordRepository()
        self.versioned_records: VersionedRecordRepository = self.versioned_record_repo
        self.commits = 0
        self.rollbacks = 0
        self._snapshot: tuple[
            dict[str, ConfirmationRecord],
            dict[tuple[str, str, str], IdempotencyRecord],
            dict[str, AuditEventRecord],
            list[VersionedRecord],
        ] | None = None

    def __enter__(self) -> SafeCommitUnitOfWork:
        self._snapshot = (
            dict(self.confirmation_repo.records),
            dict(self.idempotency_repo.records),
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
        confirmations, idempotency, audit_events, versioned_records = self._snapshot
        self.confirmation_repo.records = dict(confirmations)
        self.idempotency_repo.records = dict(idempotency)
        self.audit_event_repo.records = dict(audit_events)
        self.versioned_record_repo.records = list(versioned_records)


class ProfileApplicationServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.unit_of_work = InMemorySafeCommitUnitOfWork()
        self.service = ProfileApplicationService(lambda: self.unit_of_work)

    def _save_draft(
        self,
        *,
        draft_version: int = 1,
        fields: JsonObject | None = None,
    ) -> None:
        save = self.service.save_draft(
            SaveProfileDraftCommand(
                record_id=f"profile_draft_record_{draft_version:03d}",
                user_id="user_001",
                draft_id=f"profile_draft_{draft_version:03d}",
                draft_version=draft_version,
                fields=fields or _profile_fields(),
                workflow=_workflow(WorkflowState.PROFILE_REQUIRED),
            )
        )
        self.assertTrue(save.ok)

    def _preview(self, *, draft_version: int = 1) -> CreateProfilePreviewCommand:
        return CreateProfilePreviewCommand(
            preview_id=f"preview_{draft_version:03d}",
            user_id="user_001",
            draft_version=draft_version,
            workflow=_workflow(WorkflowState.PROFILE_REQUIRED),
        )

    def _create_confirmed_profile_confirmation(
        self,
        *,
        confirmation_id: str = "confirm_001",
        draft_version: int = 1,
        expected_version: int = 0,
        summary_hash: str,
        now: datetime,
    ) -> None:
        confirmation = self.service.create_confirmation(
            CreateProfileConfirmationCommand(
                confirmation_id=confirmation_id,
                user_id="user_001",
                draft_version=draft_version,
                expected_version=expected_version,
                expires_at=now + timedelta(minutes=5),
                summary_hash=summary_hash,
                workflow=_workflow(WorkflowState.PROFILE_WAITING_CONFIRMATION),
            )
        )
        self.assertTrue(confirmation.ok)
        confirmed = self.service.confirm_profile_commit(
            ConfirmProfileCommitCommand(
                confirmation_id=confirmation_id,
                user_id="user_001",
                summary_hash=summary_hash,
                now=now,
                workflow=_workflow(WorkflowState.PROFILE_WAITING_CONFIRMATION),
            )
        )
        self.assertTrue(confirmed.ok)

    def _commit_profile(
        self,
        *,
        confirmation_id: str = "confirm_001",
        expected_version: int = 0,
        draft_version: int = 1,
        summary_hash: str,
        idempotency_key: str = "idem_001",
        now: datetime | None = None,
    ) -> ProfileCommandResult:
        return self.service.commit_profile(
            CommitProfileCommand(
                confirmation_id=confirmation_id,
                idempotency_record_id=f"{idempotency_key}:record",
                committed_record_id=f"profile_committed_record_{draft_version:03d}",
                audit_event_id=f"audit_{draft_version:03d}",
                user_id="user_001",
                expected_version=expected_version,
                draft_version=draft_version,
                summary_hash=summary_hash,
                idempotency_key=idempotency_key,
                now=now or datetime.now(UTC),
                workflow=_workflow(WorkflowState.PROFILE_WAITING_CONFIRMATION),
            )
        )

    def _committed_records(self) -> list[VersionedRecord]:
        return [
            record
            for record in self.unit_of_work.versioned_record_repo.records
            if record.lifecycle_status == "committed"
        ]

    def test_profile_happy_path_runs_through_application_service(self) -> None:
        save = self.service.save_draft(
            SaveProfileDraftCommand(
                record_id="profile_draft_record_001",
                user_id="user_001",
                draft_id="profile_draft_001",
                draft_version=1,
                fields=_profile_fields(),
                workflow=_workflow(WorkflowState.PROFILE_REQUIRED),
            )
        )
        self.assertTrue(save.ok)

        preview = self.service.create_preview(
            CreateProfilePreviewCommand(
                preview_id="preview_001",
                user_id="user_001",
                draft_version=1,
                workflow=_workflow(WorkflowState.PROFILE_REQUIRED),
            )
        )
        self.assertTrue(preview.ok)
        self.assertIsNotNone(preview.preview)
        assert preview.preview is not None

        confirmation = self.service.create_confirmation(
            CreateProfileConfirmationCommand(
                confirmation_id="confirm_001",
                user_id="user_001",
                draft_version=1,
                expected_version=0,
                expires_at=datetime.now(UTC) + timedelta(minutes=5),
                summary_hash=preview.preview.summary_hash,
                workflow=_workflow(WorkflowState.PROFILE_WAITING_CONFIRMATION),
            )
        )
        self.assertTrue(confirmation.ok)

        confirmed = self.service.confirm_profile_commit(
            ConfirmProfileCommitCommand(
                confirmation_id="confirm_001",
                user_id="user_001",
                summary_hash=preview.preview.summary_hash,
                now=datetime.now(UTC),
                workflow=_workflow(WorkflowState.PROFILE_WAITING_CONFIRMATION),
            )
        )
        self.assertTrue(confirmed.ok)

        committed = self.service.commit_profile(
            CommitProfileCommand(
                confirmation_id="confirm_001",
                idempotency_record_id="idem_record_001",
                committed_record_id="profile_committed_record_001",
                audit_event_id="audit_001",
                user_id="user_001",
                expected_version=0,
                draft_version=1,
                summary_hash=preview.preview.summary_hash,
                idempotency_key="idem_001",
                now=datetime.now(UTC),
                workflow=_workflow(WorkflowState.PROFILE_WAITING_CONFIRMATION),
            )
        )
        self.assertTrue(committed.ok)
        self.assertIsNotNone(committed.profile_version)
        assert committed.profile_version is not None
        self.assertEqual(committed.profile_version.profile_id, "profile:user_001")
        self.assertEqual(committed.profile_version.version, 1)
        self.assertEqual(
            self.service.get_current_profile("user_001"),
            committed.profile_version,
        )

    def test_invalid_profile_input_is_rejected_without_draft(self) -> None:
        fields = _profile_fields()
        user_facts = fields["user_facts"]
        assert isinstance(user_facts, dict)
        user_facts["people_count"] = 0

        result = self.service.save_draft(
            SaveProfileDraftCommand(
                record_id="profile_draft_record_001",
                user_id="user_001",
                draft_id="profile_draft_001",
                draft_version=1,
                fields=fields,
                workflow=_workflow(WorkflowState.PROFILE_REQUIRED),
            )
        )

        self.assertFalse(result.ok)
        self.assertIsNotNone(result.validation)
        assert result.validation is not None
        self.assertEqual(result.validation.errors[0].code, ErrorCode.INVALID_RANGE)
        self.assertEqual(self.unit_of_work.versioned_record_repo.records, [])

    def test_missing_required_profile_field_is_machine_readable(self) -> None:
        fields = _profile_fields()
        user_facts = fields["user_facts"]
        assert isinstance(user_facts, dict)
        del user_facts["timezone"]

        result = self.service.save_draft(
            SaveProfileDraftCommand(
                record_id="profile_draft_record_001",
                user_id="user_001",
                draft_id="profile_draft_001",
                draft_version=1,
                fields=fields,
                workflow=_workflow(WorkflowState.PROFILE_REQUIRED),
            )
        )

        self.assertFalse(result.ok)
        self.assertIsNotNone(result.validation)
        assert result.validation is not None
        error = result.validation.errors[0]
        self.assertEqual(error.code, ErrorCode.MISSING_REQUIRED_FIELD)
        self.assertEqual(error.path, ("fields.user_facts.timezone",))

    def test_strict_restriction_with_soft_preference_shape_is_rejected(self) -> None:
        fields = _profile_fields()
        fields["strict_restrictions"] = [
            {
                "direction": "avoid",
                "value": "peanut",
            }
        ]

        result = self.service.save_draft(
            SaveProfileDraftCommand(
                record_id="profile_draft_record_001",
                user_id="user_001",
                draft_id="profile_draft_001",
                draft_version=1,
                fields=fields,
                workflow=_workflow(WorkflowState.PROFILE_REQUIRED),
            )
        )

        self.assertFalse(result.ok)
        self.assertIsNotNone(result.validation)
        assert result.validation is not None
        error = result.validation.errors[0]
        self.assertEqual(error.code, ErrorCode.MISSING_REQUIRED_FIELD)
        self.assertEqual(error.path, ("fields.strict_restrictions.0.kind",))

    def test_profile_actions_are_blocked_outside_current_workflow_state(self) -> None:
        result = self.service.save_draft(
            SaveProfileDraftCommand(
                record_id="profile_draft_record_001",
                user_id="user_001",
                draft_id="profile_draft_001",
                draft_version=1,
                fields=_profile_fields(),
                workflow=_workflow(WorkflowState.READY),
            )
        )

        self.assertFalse(result.ok)
        self.assertIsNotNone(result.policy)
        assert result.policy is not None
        self.assertEqual(result.policy.errors[0]["code"], ErrorCode.ACTION_NOT_ALLOWED)

    def test_commit_requires_confirmed_confirmation(self) -> None:
        save = self.service.save_draft(
            SaveProfileDraftCommand(
                record_id="profile_draft_record_001",
                user_id="user_001",
                draft_id="profile_draft_001",
                draft_version=1,
                fields=_profile_fields(),
                workflow=_workflow(WorkflowState.PROFILE_REQUIRED),
            )
        )
        self.assertTrue(save.ok)
        preview = self.service.create_preview(
            CreateProfilePreviewCommand(
                preview_id="preview_001",
                user_id="user_001",
                draft_version=1,
                workflow=_workflow(WorkflowState.PROFILE_REQUIRED),
            )
        )
        self.assertIsNotNone(preview.preview)
        assert preview.preview is not None
        confirmation = self.service.create_confirmation(
            CreateProfileConfirmationCommand(
                confirmation_id="confirm_001",
                user_id="user_001",
                draft_version=1,
                expected_version=0,
                expires_at=datetime.now(UTC) + timedelta(minutes=5),
                summary_hash=preview.preview.summary_hash,
                workflow=_workflow(WorkflowState.PROFILE_WAITING_CONFIRMATION),
            )
        )
        self.assertTrue(confirmation.ok)

        committed = self.service.commit_profile(
            CommitProfileCommand(
                confirmation_id="confirm_001",
                idempotency_record_id="idem_record_001",
                committed_record_id="profile_committed_record_001",
                audit_event_id="audit_001",
                user_id="user_001",
                expected_version=0,
                draft_version=1,
                summary_hash=preview.preview.summary_hash,
                idempotency_key="idem_001",
                now=datetime.now(UTC),
                workflow=_workflow(WorkflowState.PROFILE_WAITING_CONFIRMATION),
            )
        )

        self.assertFalse(committed.ok)
        self.assertIsNotNone(committed.safe_commit)
        assert committed.safe_commit is not None
        self.assertIsNotNone(committed.safe_commit.error)
        assert committed.safe_commit.error is not None
        self.assertEqual(
            committed.safe_commit.error.code,
            ErrorCode.CONFIRMATION_ALREADY_USED,
        )

    def test_expired_confirmation_does_not_commit_profile(self) -> None:
        now = datetime(2026, 7, 10, 12, 0, tzinfo=UTC)
        self._save_draft()
        preview = self.service.create_preview(self._preview())
        self.assertIsNotNone(preview.preview)
        assert preview.preview is not None
        confirmation = self.service.create_confirmation(
            CreateProfileConfirmationCommand(
                confirmation_id="confirm_001",
                user_id="user_001",
                draft_version=1,
                expected_version=0,
                expires_at=now - timedelta(seconds=1),
                summary_hash=preview.preview.summary_hash,
                workflow=_workflow(WorkflowState.PROFILE_WAITING_CONFIRMATION),
            )
        )
        self.assertTrue(confirmation.ok)

        confirmed = self.service.confirm_profile_commit(
            ConfirmProfileCommitCommand(
                confirmation_id="confirm_001",
                user_id="user_001",
                summary_hash=preview.preview.summary_hash,
                now=now,
                workflow=_workflow(WorkflowState.PROFILE_WAITING_CONFIRMATION),
            )
        )

        self.assertFalse(confirmed.ok)
        self.assertIsNotNone(confirmed.error)
        assert confirmed.error is not None
        self.assertEqual(confirmed.error.code, ErrorCode.CONFIRMATION_EXPIRED)
        self.assertIsNone(self.service.get_current_profile("user_001"))

    def test_wrong_user_confirmation_does_not_commit_profile(self) -> None:
        now = datetime(2026, 7, 10, 12, 0, tzinfo=UTC)
        self._save_draft()
        preview = self.service.create_preview(self._preview())
        self.assertIsNotNone(preview.preview)
        assert preview.preview is not None
        self._create_confirmed_profile_confirmation(
            summary_hash=preview.preview.summary_hash,
            now=now,
        )

        committed = self.service.commit_profile(
            CommitProfileCommand(
                confirmation_id="confirm_001",
                idempotency_record_id="idem_wrong_user",
                committed_record_id="profile_committed_record_001",
                audit_event_id="audit_001",
                user_id="user_002",
                expected_version=0,
                draft_version=1,
                summary_hash=preview.preview.summary_hash,
                idempotency_key="idem_wrong_user",
                now=now,
                workflow=WorkflowRun(
                    schema_version=SCHEMA_VERSION,
                    workflow_id="workflow_002",
                    user_id="user_002",
                    state=WorkflowState.PROFILE_WAITING_CONFIRMATION,
                    allowed_actions=[
                        action.value
                        for action in allowed_actions(
                            WorkflowState.PROFILE_WAITING_CONFIRMATION
                        )
                    ],
                    attempts=0,
                ),
            )
        )

        self.assertFalse(committed.ok)
        self.assertIsNotNone(committed.safe_commit)
        assert committed.safe_commit is not None
        self.assertIsNotNone(committed.safe_commit.error)
        assert committed.safe_commit.error is not None
        self.assertEqual(
            committed.safe_commit.error.code,
            ErrorCode.CONFIRMATION_USER_MISMATCH,
        )
        self.assertIsNone(self.service.get_current_profile("user_001"))

    def test_changed_preview_summary_hash_does_not_commit_profile(self) -> None:
        now = datetime(2026, 7, 10, 12, 0, tzinfo=UTC)
        self._save_draft()
        preview = self.service.create_preview(self._preview())
        self.assertIsNotNone(preview.preview)
        assert preview.preview is not None
        self._create_confirmed_profile_confirmation(
            summary_hash=preview.preview.summary_hash,
            now=now,
        )

        committed = self._commit_profile(
            summary_hash="b" * 64,
            idempotency_key="idem_hash_mismatch",
            now=now,
        )

        self.assertFalse(committed.ok)
        self.assertIsNotNone(committed.safe_commit)
        assert committed.safe_commit is not None
        self.assertIsNotNone(committed.safe_commit.error)
        assert committed.safe_commit.error is not None
        self.assertEqual(
            committed.safe_commit.error.code,
            ErrorCode.PREVIEW_SUMMARY_HASH_MISMATCH,
        )
        self.assertIsNone(self.service.get_current_profile("user_001"))

    def test_idempotency_payload_mismatch_does_not_duplicate_profile(self) -> None:
        now = datetime(2026, 7, 10, 12, 0, tzinfo=UTC)
        self._save_draft()
        preview = self.service.create_preview(self._preview())
        self.assertIsNotNone(preview.preview)
        assert preview.preview is not None
        self._create_confirmed_profile_confirmation(
            summary_hash=preview.preview.summary_hash,
            now=now,
        )
        first = self._commit_profile(
            summary_hash=preview.preview.summary_hash,
            idempotency_key="idem_payload",
            now=now,
        )
        self.assertTrue(first.ok)

        second = self._commit_profile(
            expected_version=1,
            summary_hash=preview.preview.summary_hash,
            idempotency_key="idem_payload",
            now=now,
        )

        self.assertFalse(second.ok)
        self.assertIsNotNone(second.safe_commit)
        assert second.safe_commit is not None
        self.assertIsNotNone(second.safe_commit.error)
        assert second.safe_commit.error is not None
        self.assertEqual(
            second.safe_commit.error.code,
            ErrorCode.IDEMPOTENCY_PAYLOAD_MISMATCH,
        )
        self.assertEqual(len(self._committed_records()), 1)

    def test_stale_expected_version_does_not_replace_current_profile(self) -> None:
        now = datetime(2026, 7, 10, 12, 0, tzinfo=UTC)
        self._save_draft(draft_version=1)
        first_preview = self.service.create_preview(self._preview(draft_version=1))
        self.assertIsNotNone(first_preview.preview)
        assert first_preview.preview is not None
        self._create_confirmed_profile_confirmation(
            confirmation_id="confirm_001",
            draft_version=1,
            expected_version=0,
            summary_hash=first_preview.preview.summary_hash,
            now=now,
        )
        first = self._commit_profile(
            confirmation_id="confirm_001",
            draft_version=1,
            expected_version=0,
            summary_hash=first_preview.preview.summary_hash,
            idempotency_key="idem_v1",
            now=now,
        )
        self.assertTrue(first.ok)
        current = self.service.get_current_profile("user_001")
        self.assertIsNotNone(current)
        assert current is not None
        self.assertEqual(current.version, 1)

        self._save_draft(draft_version=2)
        second_preview = self.service.create_preview(self._preview(draft_version=2))
        self.assertIsNotNone(second_preview.preview)
        assert second_preview.preview is not None
        self._create_confirmed_profile_confirmation(
            confirmation_id="confirm_002",
            draft_version=2,
            expected_version=0,
            summary_hash=second_preview.preview.summary_hash,
            now=now,
        )
        stale = self._commit_profile(
            confirmation_id="confirm_002",
            draft_version=2,
            expected_version=0,
            summary_hash=second_preview.preview.summary_hash,
            idempotency_key="idem_stale",
            now=now,
        )

        self.assertFalse(stale.ok)
        self.assertIsNotNone(stale.safe_commit)
        assert stale.safe_commit is not None
        self.assertIsNotNone(stale.safe_commit.error)
        assert stale.safe_commit.error is not None
        self.assertEqual(
            stale.safe_commit.error.code,
            ErrorCode.EXPECTED_VERSION_MISMATCH,
        )
        self.assertEqual(self.service.get_current_profile("user_001"), current)
        committed_versions = [record.version for record in self._committed_records()]
        self.assertEqual(committed_versions, [1])

    def test_commit_rollback_prevents_partial_profile_state(self) -> None:
        now = datetime(2026, 7, 10, 12, 0, tzinfo=UTC)
        self._save_draft()
        preview = self.service.create_preview(self._preview())
        self.assertIsNotNone(preview.preview)
        assert preview.preview is not None
        self._create_confirmed_profile_confirmation(
            summary_hash=preview.preview.summary_hash,
            now=now,
        )
        self.unit_of_work.audit_event_repo.fail_on_add = True

        committed = self._commit_profile(
            summary_hash=preview.preview.summary_hash,
            idempotency_key="idem_rollback",
            now=now,
        )

        self.assertFalse(committed.ok)
        self.assertIsNotNone(committed.safe_commit)
        assert committed.safe_commit is not None
        self.assertIsNotNone(committed.safe_commit.error)
        assert committed.safe_commit.error is not None
        self.assertEqual(
            committed.safe_commit.error.code,
            ErrorCode.TRANSACTION_CONFLICT,
        )
        self.assertIsNone(self.service.get_current_profile("user_001"))
        self.assertEqual(self._committed_records(), [])
        self.assertEqual(self.unit_of_work.audit_event_repo.records, {})
        self.assertEqual(
            self.unit_of_work.confirmation_repo.records["confirm_001"].status,
            "confirmed",
        )

    def test_read_current_profile_returns_none_before_commit(self) -> None:
        self.assertIsNone(self.service.get_current_profile("user_001"))

    def test_workflow_status_query_uses_policy_surface(self) -> None:
        status = self.service.get_workflow_status(
            _workflow(WorkflowState.PROFILE_REQUIRED)
        )

        self.assertTrue(status.allowed)
        self.assertIn("show_status", status.allowed_actions)

    def test_m4_profile_scenario_replays_same_idempotency_key(self) -> None:
        ids = ProfileScenarioIds(
            run_id="scenario_001",
            idempotency_key="scenario_idem_001",
        )
        now = datetime(2026, 7, 10, 12, 0, tzinfo=UTC)

        first = run_m4_profile_scenario(
            service=self.service,
            unit_of_work_factory=lambda: self.unit_of_work,
            user_id="user_001",
            ids=ids,
            now=now,
            expires_at=now + timedelta(minutes=5),
        )
        second = run_m4_profile_scenario(
            service=self.service,
            unit_of_work_factory=lambda: self.unit_of_work,
            user_id="user_001",
            ids=ids,
            now=now,
            expires_at=now + timedelta(minutes=5),
        )

        self.assertTrue(first.ok)
        self.assertTrue(second.ok)
        self.assertTrue(second.replayed)
        self.assertTrue(second.reused_draft)
        self.assertTrue(second.reused_confirmation)

        records = cast(
            InMemoryVersionedRecordRepository,
            self.unit_of_work.versioned_records,
        ).records
        committed_records = [
            record for record in records if record.lifecycle_status == "committed"
        ]
        self.assertEqual(len(committed_records), 1)


if __name__ == "__main__":
    unittest.main()
