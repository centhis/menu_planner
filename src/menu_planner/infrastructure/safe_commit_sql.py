from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from typing import Protocol, cast

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


class SqlCursor(Protocol):
    def fetchone(self) -> tuple[object, ...] | None: ...


class SqlConnection(Protocol):
    def execute(
        self,
        query: str,
        params: Mapping[str, object] | None = None,
    ) -> SqlCursor: ...

    def commit(self) -> None: ...

    def rollback(self) -> None: ...

    def close(self) -> None: ...


def _jsonb(value: JsonObject) -> object:
    from psycopg.types.json import Jsonb

    return Jsonb(value)


class SqlConfirmationRepository:
    def __init__(self, connection: SqlConnection) -> None:
        self._connection = connection

    def add(self, record: ConfirmationRecord) -> None:
        self._connection.execute(
            """
            insert into confirmations (
                confirmation_id,
                user_id,
                operation,
                entity_type,
                entity_id,
                expected_version,
                draft_version,
                expires_at,
                summary_hash,
                status,
                confirmed_at,
                committed_at
            )
            values (
                %(confirmation_id)s,
                %(user_id)s,
                %(operation)s,
                %(entity_type)s,
                %(entity_id)s,
                %(expected_version)s,
                %(draft_version)s,
                %(expires_at)s,
                %(summary_hash)s,
                %(status)s,
                %(confirmed_at)s,
                %(committed_at)s
            )
            """,
            {
                "confirmation_id": record.confirmation_id,
                "user_id": record.user_id,
                "operation": record.operation,
                "entity_type": record.entity_type,
                "entity_id": record.entity_id,
                "expected_version": record.expected_version,
                "draft_version": record.draft_version,
                "expires_at": record.expires_at,
                "summary_hash": record.summary_hash,
                "status": record.status,
                "confirmed_at": record.confirmed_at,
                "committed_at": record.committed_at,
            },
        )

    def get(self, confirmation_id: str) -> ConfirmationRecord | None:
        row = self._connection.execute(
            """
            select confirmation_id,
                   user_id,
                   operation,
                   entity_type,
                   entity_id,
                   expected_version,
                   draft_version,
                   expires_at,
                   summary_hash,
                   status,
                   created_at,
                   updated_at,
                   confirmed_at,
                   committed_at
            from confirmations
            where confirmation_id = %(confirmation_id)s
            """,
            {"confirmation_id": confirmation_id},
        ).fetchone()
        if row is None:
            return None
        return _confirmation_from_row(row)

    def get_for_user(
        self,
        confirmation_id: str,
        user_id: str,
    ) -> ConfirmationRecord | None:
        row = self._connection.execute(
            """
            select confirmation_id,
                   user_id,
                   operation,
                   entity_type,
                   entity_id,
                   expected_version,
                   draft_version,
                   expires_at,
                   summary_hash,
                   status,
                   created_at,
                   updated_at,
                   confirmed_at,
                   committed_at
            from confirmations
            where confirmation_id = %(confirmation_id)s
              and user_id = %(user_id)s
            """,
            {"confirmation_id": confirmation_id, "user_id": user_id},
        ).fetchone()
        if row is None:
            return None
        return _confirmation_from_row(row)

    def update_status(
        self,
        confirmation_id: str,
        status: str,
        *,
        confirmed_at: datetime | None = None,
        committed_at: datetime | None = None,
    ) -> None:
        self._connection.execute(
            """
            update confirmations
            set status = %(status)s,
                updated_at = now(),
                confirmed_at = coalesce(%(confirmed_at)s, confirmed_at),
                committed_at = coalesce(%(committed_at)s, committed_at)
            where confirmation_id = %(confirmation_id)s
            """,
            {
                "confirmation_id": confirmation_id,
                "status": status,
                "confirmed_at": confirmed_at,
                "committed_at": committed_at,
            },
        )


class SqlIdempotencyRepository:
    def __init__(self, connection: SqlConnection) -> None:
        self._connection = connection

    def add(self, record: IdempotencyRecord) -> None:
        self._connection.execute(
            """
            insert into idempotency_records (
                idempotency_record_id,
                user_id,
                operation,
                idempotency_key,
                request_fingerprint,
                status,
                outcome_ref,
                error_code
            )
            values (
                %(idempotency_record_id)s,
                %(user_id)s,
                %(operation)s,
                %(idempotency_key)s,
                %(request_fingerprint)s,
                %(status)s,
                %(outcome_ref)s,
                %(error_code)s
            )
            """,
            {
                "idempotency_record_id": record.idempotency_record_id,
                "user_id": record.user_id,
                "operation": record.operation,
                "idempotency_key": record.idempotency_key,
                "request_fingerprint": record.request_fingerprint,
                "status": record.status,
                "outcome_ref": record.outcome_ref,
                "error_code": record.error_code,
            },
        )

    def get(
        self,
        user_id: str,
        operation: str,
        idempotency_key: str,
    ) -> IdempotencyRecord | None:
        row = self._connection.execute(
            """
            select idempotency_record_id,
                   user_id,
                   operation,
                   idempotency_key,
                   request_fingerprint,
                   status,
                   outcome_ref,
                   error_code,
                   created_at,
                   updated_at
            from idempotency_records
            where user_id = %(user_id)s
              and operation = %(operation)s
              and idempotency_key = %(idempotency_key)s
            """,
            {
                "user_id": user_id,
                "operation": operation,
                "idempotency_key": idempotency_key,
            },
        ).fetchone()
        if row is None:
            return None
        return _idempotency_from_row(row)

    def update_outcome(
        self,
        idempotency_record_id: str,
        status: str,
        *,
        outcome_ref: str | None = None,
        error_code: str | None = None,
    ) -> None:
        self._connection.execute(
            """
            update idempotency_records
            set status = %(status)s,
                outcome_ref = %(outcome_ref)s,
                error_code = %(error_code)s,
                updated_at = now()
            where idempotency_record_id = %(idempotency_record_id)s
            """,
            {
                "idempotency_record_id": idempotency_record_id,
                "status": status,
                "outcome_ref": outcome_ref,
                "error_code": error_code,
            },
        )


class SqlAuditEventRepository:
    def __init__(self, connection: SqlConnection) -> None:
        self._connection = connection

    def add(self, record: AuditEventRecord) -> None:
        self._connection.execute(
            """
            insert into audit_events (
                audit_event_id,
                user_id,
                operation,
                entity_type,
                entity_id,
                previous_version,
                new_version,
                confirmation_id,
                idempotency_key,
                summary_hash,
                result_status,
                reason_code,
                event_metadata
            )
            values (
                %(audit_event_id)s,
                %(user_id)s,
                %(operation)s,
                %(entity_type)s,
                %(entity_id)s,
                %(previous_version)s,
                %(new_version)s,
                %(confirmation_id)s,
                %(idempotency_key)s,
                %(summary_hash)s,
                %(result_status)s,
                %(reason_code)s,
                %(event_metadata)s
            )
            """,
            {
                "audit_event_id": record.audit_event_id,
                "user_id": record.user_id,
                "operation": record.operation,
                "entity_type": record.entity_type,
                "entity_id": record.entity_id,
                "previous_version": record.previous_version,
                "new_version": record.new_version,
                "confirmation_id": record.confirmation_id,
                "idempotency_key": record.idempotency_key,
                "summary_hash": record.summary_hash,
                "result_status": record.result_status,
                "reason_code": record.reason_code,
                "event_metadata": _jsonb(record.event_metadata or {}),
            },
        )

    def get(self, audit_event_id: str) -> AuditEventRecord | None:
        row = self._connection.execute(
            """
            select audit_event_id,
                   user_id,
                   operation,
                   entity_type,
                   entity_id,
                   previous_version,
                   new_version,
                   confirmation_id,
                   idempotency_key,
                   summary_hash,
                   result_status,
                   reason_code,
                   event_metadata,
                   created_at
            from audit_events
            where audit_event_id = %(audit_event_id)s
            """,
            {"audit_event_id": audit_event_id},
        ).fetchone()
        if row is None:
            return None
        return _audit_event_from_row(row)


class SqlVersionedRecordRepository:
    def __init__(self, connection: SqlConnection) -> None:
        self._connection = connection

    def add(self, record: VersionedRecord) -> None:
        self._connection.execute(
            """
            insert into m3_versioned_records (
                record_id,
                user_id,
                entity_type,
                entity_id,
                version,
                lifecycle_status,
                payload,
                confirmation_id,
                idempotency_key,
                audit_event_id
            )
            values (
                %(record_id)s,
                %(user_id)s,
                %(entity_type)s,
                %(entity_id)s,
                %(version)s,
                %(lifecycle_status)s,
                %(payload)s,
                %(confirmation_id)s,
                %(idempotency_key)s,
                %(audit_event_id)s
            )
            """,
            {
                "record_id": record.record_id,
                "user_id": record.user_id,
                "entity_type": record.entity_type,
                "entity_id": record.entity_id,
                "version": record.version,
                "lifecycle_status": record.lifecycle_status,
                "payload": _jsonb(record.payload),
                "confirmation_id": record.confirmation_id,
                "idempotency_key": record.idempotency_key,
                "audit_event_id": record.audit_event_id,
            },
        )

    def get(
        self,
        user_id: str,
        entity_type: str,
        entity_id: str,
        version: int,
        lifecycle_status: str,
    ) -> VersionedRecord | None:
        row = self._connection.execute(
            """
            select record_id,
                   user_id,
                   entity_type,
                   entity_id,
                   version,
                   lifecycle_status,
                   payload,
                   confirmation_id,
                   idempotency_key,
                   audit_event_id,
                   created_at
            from m3_versioned_records
            where user_id = %(user_id)s
              and entity_type = %(entity_type)s
              and entity_id = %(entity_id)s
              and version = %(version)s
              and lifecycle_status = %(lifecycle_status)s
            """,
            {
                "user_id": user_id,
                "entity_type": entity_type,
                "entity_id": entity_id,
                "version": version,
                "lifecycle_status": lifecycle_status,
            },
        ).fetchone()
        if row is None:
            return None
        return _versioned_record_from_row(row)

    def get_current_committed(
        self,
        user_id: str,
        entity_type: str,
        entity_id: str,
    ) -> VersionedRecord | None:
        row = self._connection.execute(
            """
            select record_id,
                   user_id,
                   entity_type,
                   entity_id,
                   version,
                   lifecycle_status,
                   payload,
                   confirmation_id,
                   idempotency_key,
                   audit_event_id,
                   created_at
            from m3_versioned_records
            where user_id = %(user_id)s
              and entity_type = %(entity_type)s
              and entity_id = %(entity_id)s
              and lifecycle_status = 'committed'
            order by version desc
            limit 1
            for update
            """,
            {
                "user_id": user_id,
                "entity_type": entity_type,
                "entity_id": entity_id,
            },
        ).fetchone()
        if row is None:
            return None
        return _versioned_record_from_row(row)


class SqlSafeCommitUnitOfWork:
    def __init__(self, database_url: str) -> None:
        self._database_url = database_url
        self._connection: SqlConnection | None = None
        self.confirmations: ConfirmationRepository
        self.idempotency_records: IdempotencyRepository
        self.audit_events: AuditEventRepository
        self.versioned_records: VersionedRecordRepository

    def __enter__(self) -> SafeCommitUnitOfWork:
        import psycopg

        connection = cast(SqlConnection, psycopg.connect(self._database_url))
        self._connection = connection
        self.confirmations = SqlConfirmationRepository(connection)
        self.idempotency_records = SqlIdempotencyRepository(connection)
        self.audit_events = SqlAuditEventRepository(connection)
        self.versioned_records = SqlVersionedRecordRepository(connection)
        return cast(SafeCommitUnitOfWork, self)

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: object,
    ) -> bool | None:
        if self._connection is None:
            return None
        if exc_type is not None:
            self.rollback()
        self._connection.close()
        return None

    def commit(self) -> None:
        if self._connection is None:
            raise RuntimeError("unit of work is not active")
        self._connection.commit()

    def rollback(self) -> None:
        if self._connection is None:
            raise RuntimeError("unit of work is not active")
        self._connection.rollback()


def _confirmation_from_row(row: tuple[object, ...]) -> ConfirmationRecord:
    return ConfirmationRecord(
        confirmation_id=cast(str, row[0]),
        user_id=cast(str, row[1]),
        operation=cast(str, row[2]),
        entity_type=cast(str, row[3]),
        entity_id=cast(str, row[4]),
        expected_version=cast(int, row[5]),
        draft_version=cast(int, row[6]),
        expires_at=cast(datetime, row[7]),
        summary_hash=cast(str, row[8]),
        status=cast(str, row[9]),
        created_at=cast(datetime, row[10]),
        updated_at=cast(datetime, row[11]),
        confirmed_at=cast(datetime | None, row[12]),
        committed_at=cast(datetime | None, row[13]),
    )


def _idempotency_from_row(row: tuple[object, ...]) -> IdempotencyRecord:
    return IdempotencyRecord(
        idempotency_record_id=cast(str, row[0]),
        user_id=cast(str, row[1]),
        operation=cast(str, row[2]),
        idempotency_key=cast(str, row[3]),
        request_fingerprint=cast(str, row[4]),
        status=cast(str, row[5]),
        outcome_ref=cast(str | None, row[6]),
        error_code=cast(str | None, row[7]),
        created_at=cast(datetime, row[8]),
        updated_at=cast(datetime, row[9]),
    )


def _audit_event_from_row(row: tuple[object, ...]) -> AuditEventRecord:
    return AuditEventRecord(
        audit_event_id=cast(str, row[0]),
        user_id=cast(str, row[1]),
        operation=cast(str, row[2]),
        entity_type=cast(str, row[3]),
        entity_id=cast(str, row[4]),
        previous_version=cast(int | None, row[5]),
        new_version=cast(int | None, row[6]),
        confirmation_id=cast(str | None, row[7]),
        idempotency_key=cast(str | None, row[8]),
        summary_hash=cast(str | None, row[9]),
        result_status=cast(str, row[10]),
        reason_code=cast(str | None, row[11]),
        event_metadata=cast(JsonObject, row[12]),
        created_at=cast(datetime, row[13]),
    )


def _versioned_record_from_row(row: tuple[object, ...]) -> VersionedRecord:
    return VersionedRecord(
        record_id=cast(str, row[0]),
        user_id=cast(str, row[1]),
        entity_type=cast(str, row[2]),
        entity_id=cast(str, row[3]),
        version=cast(int, row[4]),
        lifecycle_status=cast(str, row[5]),
        payload=cast(JsonObject, row[6]),
        confirmation_id=cast(str | None, row[7]),
        idempotency_key=cast(str | None, row[8]),
        audit_event_id=cast(str | None, row[9]),
        created_at=cast(datetime, row[10]),
    )
