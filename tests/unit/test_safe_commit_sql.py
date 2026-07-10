from __future__ import annotations

import os
import unittest
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from menu_planner.application.safe_commit import (
    AuditEventRecord,
    ConfirmationRecord,
    IdempotencyRecord,
    VersionedRecord,
)
from menu_planner.infrastructure.safe_commit_sql import (
    SqlAuditEventRepository,
    SqlConfirmationRepository,
    SqlIdempotencyRepository,
    SqlVersionedRecordRepository,
)


def _database_url() -> str:
    return os.environ.get("DATABASE_URL", "")


def _hash(char: str) -> str:
    return char * 64


class SafeCommitSqlRepositoryTests(unittest.TestCase):
    def setUp(self) -> None:
        database_url = _database_url()
        if not database_url:
            self.skipTest("DATABASE_URL is not configured")

        try:
            import psycopg
        except ModuleNotFoundError:
            self.skipTest("psycopg is not installed")

        self._psycopg = psycopg
        self._conn = psycopg.connect(database_url)
        self._ids: list[str] = []

    def tearDown(self) -> None:
        if not hasattr(self, "_conn"):
            return

        ids = tuple(self._ids)
        try:
            with self._conn.cursor() as cursor:
                cursor.execute(
                    "delete from m3_versioned_records where record_id = any(%s)",
                    (list(ids),),
                )
                cursor.execute(
                    "delete from audit_events where audit_event_id = any(%s)",
                    (list(ids),),
                )
                cursor.execute(
                    "delete from idempotency_records "
                    "where idempotency_record_id = any(%s)",
                    (list(ids),),
                )
                cursor.execute(
                    "delete from confirmations where confirmation_id = any(%s)",
                    (list(ids),),
                )
            self._conn.commit()
        finally:
            self._conn.close()

    def _id(self, prefix: str) -> str:
        value = f"{prefix}_{uuid4().hex}"
        self._ids.append(value)
        return value

    def test_confirmation_repository_add_get_and_update_status(self) -> None:
        confirmation_id = self._id("confirm")
        repo = SqlConfirmationRepository(self._conn)
        expires_at = datetime.now(UTC) + timedelta(minutes=5)
        confirmed_at = datetime.now(UTC)

        repo.add(
            ConfirmationRecord(
                confirmation_id=confirmation_id,
                user_id="user_001",
                operation="commit_m3_record",
                entity_type="m3_test_entity",
                entity_id="entity_001",
                expected_version=1,
                draft_version=2,
                expires_at=expires_at,
                summary_hash=_hash("a"),
                status="pending",
            )
        )
        self._conn.commit()

        pending = repo.get(confirmation_id)
        self.assertIsNotNone(pending)
        assert pending is not None
        self.assertEqual(pending.status, "pending")
        self.assertEqual(pending.summary_hash, _hash("a"))
        self.assertIsNotNone(repo.get_for_user(confirmation_id, "user_001"))
        self.assertIsNone(repo.get_for_user(confirmation_id, "user_002"))

        repo.update_status(
            confirmation_id,
            "confirmed",
            confirmed_at=confirmed_at,
        )
        self._conn.commit()

        confirmed = repo.get(confirmation_id)
        self.assertIsNotNone(confirmed)
        assert confirmed is not None
        self.assertEqual(confirmed.status, "confirmed")
        self.assertIsNotNone(confirmed.confirmed_at)

    def test_confirmation_survives_repository_restart_before_confirm(self) -> None:
        confirmation_id = self._id("confirm")
        repo = SqlConfirmationRepository(self._conn)
        expires_at = datetime.now(UTC) + timedelta(minutes=5)

        repo.add(
            ConfirmationRecord(
                confirmation_id=confirmation_id,
                user_id="user_001",
                operation="commit_m3_record",
                entity_type="m3_test_entity",
                entity_id="entity_001",
                expected_version=1,
                draft_version=2,
                expires_at=expires_at,
                summary_hash=_hash("a"),
                status="pending",
            )
        )
        self._conn.commit()

        restarted_conn = self._psycopg.connect(_database_url())
        try:
            restarted_repo = SqlConfirmationRepository(restarted_conn)
            loaded = restarted_repo.get_for_user(confirmation_id, "user_001")
            self.assertIsNotNone(loaded)
            assert loaded is not None
            self.assertEqual(loaded.status, "pending")

            restarted_repo.update_status(
                confirmation_id,
                "confirmed",
                confirmed_at=datetime.now(UTC),
            )
            restarted_conn.commit()
        finally:
            restarted_conn.close()

        confirmed = repo.get(confirmation_id)
        self.assertIsNotNone(confirmed)
        assert confirmed is not None
        self.assertEqual(confirmed.status, "confirmed")

    def test_idempotency_repository_add_get_and_update_outcome(self) -> None:
        record_id = self._id("idem_record")
        repo = SqlIdempotencyRepository(self._conn)

        repo.add(
            IdempotencyRecord(
                idempotency_record_id=record_id,
                user_id="user_001",
                operation="commit_m3_record",
                idempotency_key="idem_key_001",
                request_fingerprint=_hash("b"),
                status="in_progress",
            )
        )
        self._conn.commit()

        in_progress = repo.get("user_001", "commit_m3_record", "idem_key_001")
        self.assertIsNotNone(in_progress)
        assert in_progress is not None
        self.assertEqual(in_progress.request_fingerprint, _hash("b"))

        repo.update_outcome(record_id, "completed", outcome_ref="version_001")
        self._conn.commit()

        completed = repo.get("user_001", "commit_m3_record", "idem_key_001")
        self.assertIsNotNone(completed)
        assert completed is not None
        self.assertEqual(completed.status, "completed")
        self.assertEqual(completed.outcome_ref, "version_001")

    def test_audit_and_versioned_record_repositories_add_and_get(self) -> None:
        confirmation_id = self._id("confirm")
        audit_event_id = self._id("audit")
        record_id = self._id("record")
        confirmation_repo = SqlConfirmationRepository(self._conn)
        audit_repo = SqlAuditEventRepository(self._conn)
        versioned_repo = SqlVersionedRecordRepository(self._conn)

        confirmation_repo.add(
            ConfirmationRecord(
                confirmation_id=confirmation_id,
                user_id="user_001",
                operation="commit_m3_record",
                entity_type="m3_test_entity",
                entity_id="entity_001",
                expected_version=1,
                draft_version=2,
                expires_at=datetime.now(UTC) + timedelta(minutes=5),
                summary_hash=_hash("c"),
                status="confirmed",
            )
        )
        audit_repo.add(
            AuditEventRecord(
                audit_event_id=audit_event_id,
                user_id="user_001",
                operation="commit_m3_record",
                entity_type="m3_test_entity",
                entity_id="entity_001",
                result_status="succeeded",
                previous_version=1,
                new_version=2,
                confirmation_id=confirmation_id,
                idempotency_key="idem_key_002",
                summary_hash=_hash("c"),
                event_metadata={"source": "test"},
            )
        )
        versioned_repo.add(
            VersionedRecord(
                record_id=record_id,
                user_id="user_001",
                entity_type="m3_test_entity",
                entity_id="entity_001",
                version=2,
                lifecycle_status="committed",
                payload={"value": "committed"},
                confirmation_id=confirmation_id,
                idempotency_key="idem_key_002",
                audit_event_id=audit_event_id,
            )
        )
        self._conn.commit()

        audit_event = audit_repo.get(audit_event_id)
        self.assertIsNotNone(audit_event)
        assert audit_event is not None
        self.assertEqual(audit_event.event_metadata, {"source": "test"})
        self.assertEqual(audit_event.confirmation_id, confirmation_id)

        versioned_record = versioned_repo.get(
            "user_001",
            "m3_test_entity",
            "entity_001",
            2,
            "committed",
        )
        self.assertIsNotNone(versioned_record)
        assert versioned_record is not None
        self.assertEqual(versioned_record.payload, {"value": "committed"})
        self.assertEqual(versioned_record.audit_event_id, audit_event_id)

        current = versioned_repo.get_current_committed(
            "user_001",
            "m3_test_entity",
            "entity_001",
        )
        self.assertIsNotNone(current)
        assert current is not None
        self.assertEqual(current.version, 2)


if __name__ == "__main__":
    unittest.main()
