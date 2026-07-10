from __future__ import annotations

import unittest
from datetime import datetime

from menu_planner.application.safe_commit import (
    IdempotencyRecord,
    IdempotencyRequest,
    IdempotencyService,
    idempotency_request_fingerprint,
)
from menu_planner.domain.contracts.models import JsonObject
from menu_planner.domain.errors import ErrorCode


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
                created_at=record.created_at,
                updated_at=datetime.now(),
            )
            return
        raise KeyError(idempotency_record_id)


def _request(
    *,
    idempotency_record_id: str = "idem_record_001",
    idempotency_key: str = "idem_key_001",
    payload: JsonObject | None = None,
) -> IdempotencyRequest:
    return IdempotencyRequest(
        idempotency_record_id=idempotency_record_id,
        user_id="user_001",
        operation="commit_m3_record",
        idempotency_key=idempotency_key,
        payload=payload or {"value": "draft"},
    )


class IdempotencyServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.repository = InMemoryIdempotencyRepository()
        self.service = IdempotencyService(self.repository)

    def test_start_creates_in_progress_record_for_new_key(self) -> None:
        result = self.service.start(_request())

        self.assertTrue(result.ok)
        self.assertFalse(result.replay)
        self.assertIsNotNone(result.record)
        assert result.record is not None
        self.assertEqual(result.record.status, "in_progress")
        self.assertEqual(
            result.record.request_fingerprint,
            idempotency_request_fingerprint({"value": "draft"}),
        )

    def test_missing_required_key_is_blocked_before_storage(self) -> None:
        result = self.service.start(_request(idempotency_key=""))

        self.assertIsNotNone(result.error)
        assert result.error is not None
        self.assertEqual(result.error.code, ErrorCode.IDEMPOTENCY_KEY_MISSING)
        self.assertEqual(self.repository.records, {})

    def test_same_key_and_same_payload_returns_controlled_replay(self) -> None:
        first = self.service.start(_request())
        self.assertIsNotNone(first.record)
        assert first.record is not None
        self.service.record_outcome(
            first.record.idempotency_record_id,
            "completed",
            outcome_ref="version_001",
        )

        replay = self.service.start(
            _request(idempotency_record_id="idem_record_002")
        )

        self.assertTrue(replay.replay)
        self.assertIsNotNone(replay.record)
        self.assertIsNotNone(replay.error)
        assert replay.record is not None
        assert replay.error is not None
        self.assertEqual(replay.record.outcome_ref, "version_001")
        self.assertEqual(replay.error.code, ErrorCode.IDEMPOTENCY_REPLAY)

    def test_same_key_and_different_payload_returns_conflict(self) -> None:
        self.service.start(_request(payload={"value": "draft"}))

        conflict = self.service.start(
            _request(
                idempotency_record_id="idem_record_002",
                payload={"value": "changed"},
            )
        )

        self.assertFalse(conflict.ok)
        self.assertFalse(conflict.replay)
        self.assertIsNotNone(conflict.error)
        assert conflict.error is not None
        self.assertEqual(conflict.error.code, ErrorCode.IDEMPOTENCY_PAYLOAD_MISMATCH)

    def test_request_fingerprint_is_stable_for_object_key_order(self) -> None:
        left: JsonObject = {"value": {"a": 1, "b": 2}}
        right: JsonObject = {"value": {"b": 2, "a": 1}}

        self.assertEqual(
            idempotency_request_fingerprint(left),
            idempotency_request_fingerprint(right),
        )


if __name__ == "__main__":
    unittest.main()
