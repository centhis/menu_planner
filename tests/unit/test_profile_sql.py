from __future__ import annotations

import os
import unittest
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from menu_planner.application.profile_persistence import (
    PROFILE_COMMIT_OPERATION,
    PROFILE_ENTITY_TYPE,
    profile_entity_id,
)
from menu_planner.application.profile_scenario import (
    ProfileScenarioIds,
    m4_profile_fields,
)
from menu_planner.application.profile_service import (
    CommitProfileCommand,
    ConfirmProfileCommitCommand,
    CreateProfileConfirmationCommand,
    CreateProfilePreviewCommand,
    ProfileApplicationService,
    SaveProfileDraftCommand,
)
from menu_planner.application.safe_commit import (
    AuditEventRecord,
    AuditEventRepository,
    SafeCommitUnitOfWork,
)
from menu_planner.domain.contracts.models import (
    SCHEMA_VERSION,
    JsonObject,
    ProfileVersion,
    WorkflowRun,
    WorkflowState,
)
from menu_planner.domain.errors import ErrorCode
from menu_planner.domain.workflow import allowed_actions
from menu_planner.infrastructure.profile_sql import (
    SqlProfileVersionedRecordRepository,
)
from menu_planner.infrastructure.safe_commit_sql import SqlSafeCommitUnitOfWork


def _database_url() -> str:
    return os.environ.get("DATABASE_URL", "")


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


def _workflow(user_id: str, state: WorkflowState) -> WorkflowRun:
    return WorkflowRun(
        schema_version=SCHEMA_VERSION,
        workflow_id=f"workflow_{uuid4().hex}",
        user_id=user_id,
        state=state,
        allowed_actions=[action.value for action in allowed_actions(state)],
        attempts=0,
    )


class FailingAuditRepository:
    def __init__(self, delegate: AuditEventRepository) -> None:
        self._delegate = delegate

    def add(self, record: AuditEventRecord) -> None:
        raise RuntimeError("injected SQL audit failure")

    def get(self, audit_event_id: str) -> AuditEventRecord | None:
        return self._delegate.get(audit_event_id)


class FailingAuditSqlSafeCommitUnitOfWork(SqlSafeCommitUnitOfWork):
    def __enter__(self) -> SafeCommitUnitOfWork:
        super().__enter__()
        self.audit_events = FailingAuditRepository(self.audit_events)
        return self


class SqlProfilePersistenceTests(unittest.TestCase):
    def setUp(self) -> None:
        database_url = _database_url()
        if not database_url:
            self.skipTest("DATABASE_URL is not configured")

        try:
            import psycopg
        except ModuleNotFoundError:
            self.skipTest("psycopg is not installed")

        self._psycopg = psycopg
        self._database_url = database_url
        self._conn = psycopg.connect(database_url)
        self._ids: list[str] = []

    def tearDown(self) -> None:
        if not hasattr(self, "_conn"):
            return

        try:
            with self._conn.cursor() as cursor:
                cursor.execute(
                    "delete from m3_versioned_records where record_id = any(%s)",
                    (self._ids,),
                )
                cursor.execute(
                    "delete from audit_events where audit_event_id = any(%s)",
                    (self._ids,),
                )
                cursor.execute(
                    "delete from idempotency_records "
                    "where idempotency_record_id = any(%s)",
                    (self._ids,),
                )
                cursor.execute(
                    "delete from confirmations where confirmation_id = any(%s)",
                    (self._ids,),
                )
            self._conn.commit()
        finally:
            self._conn.close()

    def _record_id(self, prefix: str) -> str:
        record_id = f"{prefix}_{uuid4().hex}"
        self._ids.append(record_id)
        return record_id

    def _scenario_ids(self) -> ProfileScenarioIds:
        ids = ProfileScenarioIds(
            run_id=f"m4_sql_{uuid4().hex}",
            idempotency_key=f"m4-profile-sql:{uuid4().hex}",
        )
        self._ids.extend(
            [
                ids.draft_record_id,
                ids.confirmation_id,
                ids.idempotency_record_id,
                ids.committed_record_id,
                ids.audit_event_id,
            ]
        )
        return ids

    def _service(self) -> ProfileApplicationService:
        return ProfileApplicationService(
            lambda: SqlSafeCommitUnitOfWork(self._database_url)
        )

    def test_committed_profile_version_survives_repository_restart(self) -> None:
        user_id = f"user_{uuid4().hex}"
        profile = ProfileVersion(
            schema_version=SCHEMA_VERSION,
            user_id=user_id,
            profile_id=profile_entity_id(user_id),
            version=1,
            fields=_profile_fields(),
        )
        repo = SqlProfileVersionedRecordRepository(self._conn)

        repo.add_committed(self._record_id("profile_committed_record"), profile)
        self._conn.commit()

        restarted_conn = self._psycopg.connect(_database_url())
        try:
            restarted_repo = SqlProfileVersionedRecordRepository(restarted_conn)
            loaded = restarted_repo.get_current_committed(user_id)
        finally:
            restarted_conn.close()

        self.assertEqual(loaded, profile)

    def test_profile_vertical_slice_survives_restart_and_writes_audit(self) -> None:
        user_id = f"user_{uuid4().hex}"
        ids = self._scenario_ids()
        now = datetime(2026, 7, 10, 12, 0, tzinfo=UTC)
        service = self._service()

        save = service.save_draft(
            SaveProfileDraftCommand(
                record_id=ids.draft_record_id,
                user_id=user_id,
                draft_id=ids.draft_id,
                draft_version=ids.draft_version,
                fields=m4_profile_fields(),
                workflow=_workflow(user_id, WorkflowState.PROFILE_REQUIRED),
            )
        )
        self.assertTrue(save.ok)
        preview = service.create_preview(
            CreateProfilePreviewCommand(
                preview_id=ids.preview_id,
                user_id=user_id,
                draft_version=ids.draft_version,
                workflow=_workflow(user_id, WorkflowState.PROFILE_REQUIRED),
            )
        )
        self.assertIsNotNone(preview.preview)
        assert preview.preview is not None
        confirmation = service.create_confirmation(
            CreateProfileConfirmationCommand(
                confirmation_id=ids.confirmation_id,
                user_id=user_id,
                draft_version=ids.draft_version,
                expected_version=0,
                expires_at=now + timedelta(minutes=5),
                summary_hash=preview.preview.summary_hash,
                workflow=_workflow(
                    user_id,
                    WorkflowState.PROFILE_WAITING_CONFIRMATION,
                ),
            )
        )
        self.assertTrue(confirmation.ok)

        with SqlSafeCommitUnitOfWork(self._database_url) as unit_of_work:
            loaded_pending = unit_of_work.confirmations.get_for_user(
                ids.confirmation_id,
                user_id,
            )
            unit_of_work.rollback()
        self.assertIsNotNone(loaded_pending)
        assert loaded_pending is not None
        self.assertEqual(loaded_pending.status, "pending")

        restarted_service = self._service()
        confirmed = restarted_service.confirm_profile_commit(
            ConfirmProfileCommitCommand(
                confirmation_id=ids.confirmation_id,
                user_id=user_id,
                summary_hash=loaded_pending.summary_hash,
                now=now,
                workflow=_workflow(
                    user_id,
                    WorkflowState.PROFILE_WAITING_CONFIRMATION,
                ),
            )
        )
        self.assertTrue(confirmed.ok)
        committed = restarted_service.commit_profile(
            CommitProfileCommand(
                confirmation_id=ids.confirmation_id,
                idempotency_record_id=ids.idempotency_record_id,
                committed_record_id=ids.committed_record_id,
                audit_event_id=ids.audit_event_id,
                user_id=user_id,
                expected_version=loaded_pending.expected_version,
                draft_version=loaded_pending.draft_version,
                summary_hash=loaded_pending.summary_hash,
                idempotency_key=ids.idempotency_key,
                now=now,
                workflow=_workflow(
                    user_id,
                    WorkflowState.PROFILE_WAITING_CONFIRMATION,
                ),
            )
        )
        self.assertTrue(committed.ok, committed.safe_commit)

        read_back_service = self._service()
        loaded_profile = read_back_service.get_current_profile(user_id)
        self.assertIsNotNone(loaded_profile)
        assert loaded_profile is not None
        self.assertEqual(loaded_profile.profile_id, profile_entity_id(user_id))
        self.assertEqual(loaded_profile.version, ids.draft_version)
        self.assertEqual(loaded_profile.fields, m4_profile_fields())

        with SqlSafeCommitUnitOfWork(self._database_url) as unit_of_work:
            audit_event = unit_of_work.audit_events.get(ids.audit_event_id)
            idempotency = unit_of_work.idempotency_records.get(
                user_id,
                PROFILE_COMMIT_OPERATION,
                ids.idempotency_key,
            )
            unit_of_work.rollback()

        self.assertIsNotNone(audit_event)
        assert audit_event is not None
        self.assertEqual(audit_event.user_id, user_id)
        self.assertEqual(audit_event.operation, PROFILE_COMMIT_OPERATION)
        self.assertEqual(audit_event.entity_type, PROFILE_ENTITY_TYPE)
        self.assertEqual(audit_event.entity_id, profile_entity_id(user_id))
        self.assertIsNone(audit_event.previous_version)
        self.assertEqual(audit_event.new_version, ids.draft_version)
        self.assertEqual(audit_event.confirmation_id, ids.confirmation_id)
        self.assertEqual(audit_event.idempotency_key, ids.idempotency_key)
        self.assertEqual(audit_event.summary_hash, loaded_pending.summary_hash)
        self.assertEqual(audit_event.result_status, "succeeded")
        self.assertEqual(
            audit_event.event_metadata,
            {"draft_record_id": ids.draft_record_id},
        )
        self.assertIsNotNone(audit_event.created_at)
        self.assertIsNotNone(idempotency)
        assert idempotency is not None
        self.assertEqual(idempotency.status, "completed")
        self.assertEqual(idempotency.outcome_ref, ids.committed_record_id)

    def test_profile_commit_sql_rollback_leaves_no_partial_state(self) -> None:
        user_id = f"user_{uuid4().hex}"
        ids = self._scenario_ids()
        now = datetime(2026, 7, 10, 12, 0, tzinfo=UTC)
        service = self._service()

        save = service.save_draft(
            SaveProfileDraftCommand(
                record_id=ids.draft_record_id,
                user_id=user_id,
                draft_id=ids.draft_id,
                draft_version=ids.draft_version,
                fields=m4_profile_fields(),
                workflow=_workflow(user_id, WorkflowState.PROFILE_REQUIRED),
            )
        )
        self.assertTrue(save.ok)
        preview = service.create_preview(
            CreateProfilePreviewCommand(
                preview_id=ids.preview_id,
                user_id=user_id,
                draft_version=ids.draft_version,
                workflow=_workflow(user_id, WorkflowState.PROFILE_REQUIRED),
            )
        )
        self.assertIsNotNone(preview.preview)
        assert preview.preview is not None
        confirmation = service.create_confirmation(
            CreateProfileConfirmationCommand(
                confirmation_id=ids.confirmation_id,
                user_id=user_id,
                draft_version=ids.draft_version,
                expected_version=0,
                expires_at=now + timedelta(minutes=5),
                summary_hash=preview.preview.summary_hash,
                workflow=_workflow(
                    user_id,
                    WorkflowState.PROFILE_WAITING_CONFIRMATION,
                ),
            )
        )
        self.assertTrue(confirmation.ok)
        confirmed = service.confirm_profile_commit(
            ConfirmProfileCommitCommand(
                confirmation_id=ids.confirmation_id,
                user_id=user_id,
                summary_hash=preview.preview.summary_hash,
                now=now,
                workflow=_workflow(
                    user_id,
                    WorkflowState.PROFILE_WAITING_CONFIRMATION,
                ),
            )
        )
        self.assertTrue(confirmed.ok)

        failing_service = ProfileApplicationService(
            lambda: FailingAuditSqlSafeCommitUnitOfWork(self._database_url)
        )
        committed = failing_service.commit_profile(
            CommitProfileCommand(
                confirmation_id=ids.confirmation_id,
                idempotency_record_id=ids.idempotency_record_id,
                committed_record_id=ids.committed_record_id,
                audit_event_id=ids.audit_event_id,
                user_id=user_id,
                expected_version=0,
                draft_version=ids.draft_version,
                summary_hash=preview.preview.summary_hash,
                idempotency_key=ids.idempotency_key,
                now=now,
                workflow=_workflow(
                    user_id,
                    WorkflowState.PROFILE_WAITING_CONFIRMATION,
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
            ErrorCode.TRANSACTION_CONFLICT,
        )
        self.assertIsNone(self._service().get_current_profile(user_id))

        with SqlSafeCommitUnitOfWork(self._database_url) as unit_of_work:
            confirmation_after_rollback = unit_of_work.confirmations.get_for_user(
                ids.confirmation_id,
                user_id,
            )
            committed_record = unit_of_work.versioned_records.get(
                user_id,
                PROFILE_ENTITY_TYPE,
                profile_entity_id(user_id),
                ids.draft_version,
                "committed",
            )
            audit_event = unit_of_work.audit_events.get(ids.audit_event_id)
            idempotency = unit_of_work.idempotency_records.get(
                user_id,
                PROFILE_COMMIT_OPERATION,
                ids.idempotency_key,
            )
            unit_of_work.rollback()

        self.assertIsNotNone(confirmation_after_rollback)
        assert confirmation_after_rollback is not None
        self.assertEqual(confirmation_after_rollback.status, "confirmed")
        self.assertIsNone(committed_record)
        self.assertIsNone(audit_event)
        self.assertIsNone(idempotency)


if __name__ == "__main__":
    unittest.main()
