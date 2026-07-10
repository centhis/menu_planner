from __future__ import annotations

import unittest
from datetime import UTC, datetime, timedelta

from menu_planner.application.safe_commit import (
    ConfirmationLifecycle,
    ConfirmationRecord,
    ConfirmationRequest,
)
from menu_planner.domain.errors import ErrorCode


def _hash(char: str) -> str:
    return char * 64


def _confirmation(
    *,
    confirmation_id: str = "confirm_001",
    user_id: str = "user_001",
    operation: str = "commit_m3_record",
    entity_type: str = "m3_test_entity",
    entity_id: str = "entity_001",
    status: str = "pending",
    expires_at: datetime | None = None,
    summary_hash: str = _hash("a"),
) -> ConfirmationRecord:
    return ConfirmationRecord(
        confirmation_id=confirmation_id,
        user_id=user_id,
        operation=operation,
        entity_type=entity_type,
        entity_id=entity_id,
        expected_version=1,
        draft_version=2,
        expires_at=expires_at or datetime.now(UTC) + timedelta(minutes=5),
        summary_hash=summary_hash,
        status=status,
    )


def _request(
    *,
    confirmation_id: str = "confirm_001",
    user_id: str = "user_001",
    operation: str = "commit_m3_record",
    entity_type: str = "m3_test_entity",
    entity_id: str = "entity_001",
    summary_hash: str = _hash("a"),
    now: datetime | None = None,
) -> ConfirmationRequest:
    return ConfirmationRequest(
        confirmation_id=confirmation_id,
        user_id=user_id,
        operation=operation,
        entity_type=entity_type,
        entity_id=entity_id,
        summary_hash=summary_hash,
        now=now or datetime.now(UTC),
    )


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


class ConfirmationLifecycleTests(unittest.TestCase):
    def setUp(self) -> None:
        self.repository = InMemoryConfirmationRepository()
        self.lifecycle = ConfirmationLifecycle(self.repository)

    def test_create_pending_and_lookup_by_user(self) -> None:
        record = _confirmation()

        created = self.lifecycle.create_pending(record)
        found = self.lifecycle.get_for_user("confirm_001", "user_001")

        self.assertEqual(created.status, "pending")
        self.assertTrue(found.ok)
        self.assertIsNotNone(found.confirmation)

    def test_confirm_pending_confirmation(self) -> None:
        self.lifecycle.create_pending(_confirmation())

        result = self.lifecycle.confirm(_request())

        self.assertTrue(result.ok)
        self.assertIsNotNone(result.confirmation)
        assert result.confirmation is not None
        self.assertEqual(result.confirmation.status, "confirmed")
        self.assertIsNotNone(result.confirmation.confirmed_at)

    def test_validate_for_commit_accepts_confirmed_confirmation(self) -> None:
        self.repository.add(_confirmation(status="confirmed"))

        result = self.lifecycle.validate_for_commit(_request())

        self.assertTrue(result.ok)
        self.assertIsNotNone(result.confirmation)

    def test_expired_confirmation_cannot_confirm_or_commit(self) -> None:
        now = datetime.now(UTC)
        self.lifecycle.create_pending(
            _confirmation(expires_at=now - timedelta(seconds=1))
        )

        confirm_result = self.lifecycle.confirm(_request(now=now))
        commit_result = self.lifecycle.validate_for_commit(_request(now=now))

        self.assertIsNotNone(confirm_result.error)
        self.assertIsNotNone(commit_result.error)
        assert confirm_result.error is not None
        assert commit_result.error is not None
        self.assertEqual(confirm_result.error.code, ErrorCode.CONFIRMATION_EXPIRED)
        self.assertEqual(commit_result.error.code, ErrorCode.CONFIRMATION_EXPIRED)

    def test_wrong_user_is_rejected_with_machine_error(self) -> None:
        self.lifecycle.create_pending(_confirmation(user_id="user_002"))

        result = self.lifecycle.confirm(_request(user_id="user_001"))

        self.assertIsNotNone(result.error)
        assert result.error is not None
        self.assertEqual(result.error.code, ErrorCode.CONFIRMATION_USER_MISMATCH)

    def test_rejected_confirmation_cannot_commit(self) -> None:
        self.repository.add(_confirmation(status="rejected"))

        result = self.lifecycle.validate_for_commit(_request())

        self.assertIsNotNone(result.error)
        assert result.error is not None
        self.assertEqual(
            result.error.code,
            ErrorCode.CONFIRMATION_REJECTED_OR_CANCELLED,
        )

    def test_used_confirmation_cannot_commit_again(self) -> None:
        self.repository.add(_confirmation(status="committed"))

        result = self.lifecycle.validate_for_commit(_request())

        self.assertIsNotNone(result.error)
        assert result.error is not None
        self.assertEqual(result.error.code, ErrorCode.CONFIRMATION_ALREADY_USED)

    def test_stale_preview_hash_is_rejected(self) -> None:
        self.repository.add(_confirmation(status="confirmed"))

        result = self.lifecycle.validate_for_commit(_request(summary_hash=_hash("b")))

        self.assertIsNotNone(result.error)
        assert result.error is not None
        self.assertEqual(
            result.error.code,
            ErrorCode.PREVIEW_SUMMARY_HASH_MISMATCH,
        )

    def test_reject_marks_pending_confirmation_rejected(self) -> None:
        self.lifecycle.create_pending(_confirmation())

        result = self.lifecycle.reject("confirm_001", "user_001")

        self.assertTrue(result.ok)
        self.assertIsNotNone(result.confirmation)
        assert result.confirmation is not None
        self.assertEqual(result.confirmation.status, "rejected")

    def test_pending_confirmation_survives_new_lifecycle_instance(self) -> None:
        self.lifecycle.create_pending(_confirmation())
        restarted_lifecycle = ConfirmationLifecycle(self.repository)

        result = restarted_lifecycle.get_for_user("confirm_001", "user_001")

        self.assertTrue(result.ok)
        self.assertIsNotNone(result.confirmation)
        assert result.confirmation is not None
        self.assertEqual(result.confirmation.status, "pending")


if __name__ == "__main__":
    unittest.main()
