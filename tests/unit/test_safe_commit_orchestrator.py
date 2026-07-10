from __future__ import annotations

import unittest
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from types import TracebackType

from menu_planner.application.safe_commit import (
    AuditEventRecord,
    AuditEventRepository,
    ConfirmationRecord,
    ConfirmationRepository,
    IdempotencyRecord,
    IdempotencyRepository,
    SafeCommitCommand,
    SafeCommitOrchestrator,
    SafeCommitUnitOfWork,
    VersionedRecord,
    VersionedRecordRepository,
    idempotency_request_fingerprint,
)
from menu_planner.domain.contracts.models import JsonObject
from menu_planner.domain.errors import ErrorCode


def _hash(char: str) -> str:
    return char * 64


def _command(*, idempotency_key: str = "idem_key_001") -> SafeCommitCommand:
    return SafeCommitCommand(
        confirmation_id="confirm_001",
        idempotency_record_id="idem_record_001",
        committed_record_id="record_committed_002",
        audit_event_id="audit_001",
        user_id="user_001",
        operation="commit_m3_record",
        entity_type="m3_test_entity",
        entity_id="entity_001",
        expected_version=1,
        draft_version=2,
        summary_hash=_hash("a"),
        idempotency_key=idempotency_key,
        now=datetime.now(UTC),
    )


def _idempotency_payload(command: SafeCommitCommand) -> JsonObject:
    return {
        "confirmation_id": command.confirmation_id,
        "user_id": command.user_id,
        "operation": command.operation,
        "entity_type": command.entity_type,
        "entity_id": command.entity_id,
        "expected_version": command.expected_version,
        "draft_version": command.draft_version,
        "summary_hash": command.summary_hash,
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
        for record in self.records:
            if (
                record.user_id == user_id
                and record.entity_type == entity_type
                and record.entity_id == entity_id
                and record.version == version
                and record.lifecycle_status == lifecycle_status
            ):
                return record
        return None

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


class SafeCommitOrchestratorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.unit_of_work = InMemorySafeCommitUnitOfWork()
        self.orchestrator = SafeCommitOrchestrator(lambda: self.unit_of_work)

    def seed_ready_to_commit(self) -> None:
        self.unit_of_work.confirmations.add(
            ConfirmationRecord(
                confirmation_id="confirm_001",
                user_id="user_001",
                operation="commit_m3_record",
                entity_type="m3_test_entity",
                entity_id="entity_001",
                expected_version=1,
                draft_version=2,
                expires_at=datetime.now(UTC) + timedelta(minutes=5),
                summary_hash=_hash("a"),
                status="confirmed",
            )
        )
        self.unit_of_work.versioned_records.add(
            VersionedRecord(
                record_id="record_committed_001",
                user_id="user_001",
                entity_type="m3_test_entity",
                entity_id="entity_001",
                version=1,
                lifecycle_status="committed",
                payload={"value": "old"},
            )
        )
        self.unit_of_work.versioned_records.add(
            VersionedRecord(
                record_id="record_draft_002",
                user_id="user_001",
                entity_type="m3_test_entity",
                entity_id="entity_001",
                version=2,
                lifecycle_status="draft",
                payload={"value": "new"},
            )
        )

    def test_commit_applies_version_confirmation_idempotency_and_audit(self) -> None:
        self.seed_ready_to_commit()

        result = self.orchestrator.commit(_command())

        self.assertTrue(result.ok)
        self.assertIsNotNone(result.committed_record)
        self.assertIsNotNone(result.audit_event)
        self.assertIsNotNone(result.idempotency_record)
        assert result.committed_record is not None
        assert result.audit_event is not None
        assert result.idempotency_record is not None
        self.assertEqual(result.committed_record.lifecycle_status, "committed")
        self.assertEqual(result.committed_record.payload, {"value": "new"})
        self.assertEqual(result.audit_event.previous_version, 1)
        self.assertEqual(result.audit_event.new_version, 2)
        self.assertEqual(result.idempotency_record.status, "completed")
        self.assertEqual(result.idempotency_record.outcome_ref, "record_committed_002")
        self.assertEqual(
            self.unit_of_work.confirmation_repo.records["confirm_001"].status,
            "committed",
        )
        self.assertEqual(self.unit_of_work.commits, 1)
        self.assertEqual(self.unit_of_work.rollbacks, 0)

    def test_expected_version_mismatch_blocks_commit(self) -> None:
        self.seed_ready_to_commit()
        command = _command()
        stale = SafeCommitCommand(
            **{**command.__dict__, "expected_version": 0},
        )

        result = self.orchestrator.commit(stale)

        self.assertFalse(result.ok)
        self.assertIsNotNone(result.error)
        assert result.error is not None
        self.assertEqual(result.error.code, ErrorCode.EXPECTED_VERSION_MISMATCH)
        self.assertEqual(self.unit_of_work.commits, 1)
        self.assertIsNone(
            self.unit_of_work.versioned_records.get(
                "user_001",
                "m3_test_entity",
                "entity_001",
                2,
                "committed",
            )
        )

    def test_same_idempotency_key_and_payload_returns_replay(self) -> None:
        self.seed_ready_to_commit()
        command = _command()
        fingerprint = idempotency_request_fingerprint(_idempotency_payload(command))
        self.unit_of_work.idempotency_repo.add(
            IdempotencyRecord(
                idempotency_record_id="idem_record_existing",
                user_id="user_001",
                operation="commit_m3_record",
                idempotency_key="idem_key_001",
                request_fingerprint=fingerprint,
                status="completed",
                outcome_ref="record_committed_002",
            )
        )

        result = self.orchestrator.commit(command)

        self.assertTrue(result.replay)
        self.assertIsNotNone(result.error)
        assert result.error is not None
        self.assertEqual(result.error.code, ErrorCode.IDEMPOTENCY_REPLAY)
        self.assertEqual(self.unit_of_work.rollbacks, 1)

    def test_same_idempotency_key_and_different_payload_returns_conflict(self) -> None:
        self.seed_ready_to_commit()
        self.unit_of_work.idempotency_repo.add(
            IdempotencyRecord(
                idempotency_record_id="idem_record_existing",
                user_id="user_001",
                operation="commit_m3_record",
                idempotency_key="idem_key_001",
                request_fingerprint=idempotency_request_fingerprint(
                    {"different": "payload"}
                ),
                status="completed",
                outcome_ref="record_committed_002",
            )
        )

        result = self.orchestrator.commit(_command())

        self.assertFalse(result.ok)
        self.assertIsNotNone(result.error)
        assert result.error is not None
        self.assertEqual(result.error.code, ErrorCode.IDEMPOTENCY_PAYLOAD_MISMATCH)
        self.assertEqual(self.unit_of_work.rollbacks, 1)

    def test_expired_confirmation_blocks_commit_with_machine_error(self) -> None:
        self.seed_ready_to_commit()
        original = self.unit_of_work.confirmation_repo.records["confirm_001"]
        self.unit_of_work.confirmation_repo.records["confirm_001"] = replace(
            original,
            expires_at=datetime.now(UTC) - timedelta(seconds=1),
        )

        result = self.orchestrator.commit(_command())

        self.assertFalse(result.ok)
        self.assertIsNotNone(result.error)
        assert result.error is not None
        self.assertEqual(result.error.code, ErrorCode.CONFIRMATION_EXPIRED)
        self.assertIsNone(self._committed_version(2))
        self.assertEqual(
            self.unit_of_work.confirmation_repo.records["confirm_001"].status,
            "confirmed",
        )

    def test_wrong_user_confirmation_blocks_commit_with_machine_error(self) -> None:
        self.seed_ready_to_commit()
        command = SafeCommitCommand(
            **{**_command().__dict__, "user_id": "user_002"},
        )

        result = self.orchestrator.commit(command)

        self.assertFalse(result.ok)
        self.assertIsNotNone(result.error)
        assert result.error is not None
        self.assertEqual(result.error.code, ErrorCode.CONFIRMATION_USER_MISMATCH)
        self.assertIsNone(self._committed_version(2))

    def test_changed_preview_hash_blocks_commit_with_machine_error(self) -> None:
        self.seed_ready_to_commit()
        command = SafeCommitCommand(
            **{**_command().__dict__, "summary_hash": _hash("b")},
        )

        result = self.orchestrator.commit(command)

        self.assertFalse(result.ok)
        self.assertIsNotNone(result.error)
        assert result.error is not None
        self.assertEqual(result.error.code, ErrorCode.PREVIEW_SUMMARY_HASH_MISMATCH)
        self.assertIsNone(self._committed_version(2))

    def test_draft_version_mismatch_blocks_commit_with_machine_error(self) -> None:
        self.seed_ready_to_commit()
        command = SafeCommitCommand(
            **{**_command().__dict__, "draft_version": 3},
        )

        result = self.orchestrator.commit(command)

        self.assertFalse(result.ok)
        self.assertIsNotNone(result.error)
        assert result.error is not None
        self.assertEqual(result.error.code, ErrorCode.DRAFT_VERSION_MISMATCH)
        self.assertIsNone(self._committed_version(2))

    def test_reusing_confirmation_with_new_key_is_rejected(self) -> None:
        self.seed_ready_to_commit()
        first = self.orchestrator.commit(_command())
        self.assertTrue(first.ok)
        repeated = SafeCommitCommand(
            **{
                **_command().__dict__,
                "idempotency_key": "idem_key_002",
                "idempotency_record_id": "idem_record_002",
            },
        )

        result = self.orchestrator.commit(repeated)

        self.assertFalse(result.ok)
        self.assertIsNotNone(result.error)
        assert result.error is not None
        self.assertEqual(result.error.code, ErrorCode.CONFIRMATION_ALREADY_USED)
        committed_v2 = [
            record
            for record in self.unit_of_work.versioned_record_repo.records
            if record.version == 2 and record.lifecycle_status == "committed"
        ]
        self.assertEqual(len(committed_v2), 1)

    def test_two_parallel_commits_detect_stale_expected_version_without_sleep(
        self,
    ) -> None:
        self.seed_ready_to_commit()
        self.unit_of_work.confirmations.add(
            ConfirmationRecord(
                confirmation_id="confirm_002",
                user_id="user_001",
                operation="commit_m3_record",
                entity_type="m3_test_entity",
                entity_id="entity_001",
                expected_version=1,
                draft_version=2,
                expires_at=datetime.now(UTC) + timedelta(minutes=5),
                summary_hash=_hash("a"),
                status="confirmed",
            )
        )
        first = self.orchestrator.commit(_command())
        second_command = SafeCommitCommand(
            **{
                **_command().__dict__,
                "confirmation_id": "confirm_002",
                "idempotency_key": "idem_key_002",
                "idempotency_record_id": "idem_record_002",
            },
        )

        second = self.orchestrator.commit(second_command)

        self.assertTrue(first.ok)
        self.assertFalse(second.ok)
        self.assertIsNotNone(second.error)
        assert second.error is not None
        self.assertEqual(second.error.code, ErrorCode.EXPECTED_VERSION_MISMATCH)

    def test_audit_write_failure_rolls_back_partial_commit(self) -> None:
        self.seed_ready_to_commit()
        self.unit_of_work.audit_event_repo.fail_on_add = True

        result = self.orchestrator.commit(_command())

        self.assertFalse(result.ok)
        self.assertIsNotNone(result.error)
        assert result.error is not None
        self.assertEqual(result.error.code, ErrorCode.TRANSACTION_CONFLICT)
        self.assertEqual(self.unit_of_work.rollbacks, 1)
        self.assertIsNone(self._committed_version(2))
        self.assertEqual(self.unit_of_work.audit_event_repo.records, {})
        self.assertEqual(
            self.unit_of_work.confirmation_repo.records["confirm_001"].status,
            "confirmed",
        )

    def test_version_write_failure_rolls_back_without_audit_event(self) -> None:
        self.seed_ready_to_commit()
        self.unit_of_work.versioned_record_repo.fail_on_add = True

        result = self.orchestrator.commit(_command())

        self.assertFalse(result.ok)
        self.assertIsNotNone(result.error)
        assert result.error is not None
        self.assertEqual(result.error.code, ErrorCode.TRANSACTION_CONFLICT)
        self.assertEqual(self.unit_of_work.rollbacks, 1)
        self.assertIsNone(self._committed_version(2))
        self.assertEqual(self.unit_of_work.audit_event_repo.records, {})

    def _committed_version(self, version: int) -> VersionedRecord | None:
        return self.unit_of_work.versioned_record_repo.get(
            "user_001",
            "m3_test_entity",
            "entity_001",
            version,
            "committed",
        )


if __name__ == "__main__":
    unittest.main()
