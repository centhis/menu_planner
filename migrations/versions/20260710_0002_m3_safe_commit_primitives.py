"""add M3 safe commit persistence primitives

Revision ID: 20260710_0002
Revises: 20260709_0001
Create Date: 2026-07-10 00:00:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260710_0002"
down_revision: str | None = "20260709_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "confirmations",
        sa.Column("confirmation_id", sa.Text(), primary_key=True),
        sa.Column("user_id", sa.Text(), nullable=False),
        sa.Column("operation", sa.Text(), nullable=False),
        sa.Column("entity_type", sa.Text(), nullable=False),
        sa.Column("entity_id", sa.Text(), nullable=False),
        sa.Column("expected_version", sa.Integer(), nullable=False),
        sa.Column("draft_version", sa.Integer(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("summary_hash", sa.String(length=64), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("committed_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "status in ('pending', 'confirmed', 'committed', 'expired', "
            "'rejected', 'used')",
            name="ck_confirmations_status",
        ),
        sa.CheckConstraint(
            "char_length(summary_hash) = 64",
            name="ck_confirmations_summary_hash_length",
        ),
    )
    op.create_index(
        "ix_confirmations_user_status_expires",
        "confirmations",
        ["user_id", "status", "expires_at"],
    )
    op.create_index(
        "ix_confirmations_user_entity",
        "confirmations",
        ["user_id", "entity_type", "entity_id"],
    )

    op.create_table(
        "idempotency_records",
        sa.Column("idempotency_record_id", sa.Text(), primary_key=True),
        sa.Column("user_id", sa.Text(), nullable=False),
        sa.Column("operation", sa.Text(), nullable=False),
        sa.Column("idempotency_key", sa.Text(), nullable=False),
        sa.Column("request_fingerprint", sa.String(length=64), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("outcome_ref", sa.Text(), nullable=True),
        sa.Column("error_code", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "status in ('in_progress', 'completed', 'failed')",
            name="ck_idempotency_records_status",
        ),
        sa.CheckConstraint(
            "char_length(request_fingerprint) = 64",
            name="ck_idempotency_records_request_fingerprint_length",
        ),
        sa.UniqueConstraint(
            "user_id",
            "operation",
            "idempotency_key",
            name="uq_idempotency_records_user_operation_key",
        ),
    )

    op.create_table(
        "audit_events",
        sa.Column("audit_event_id", sa.Text(), primary_key=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("user_id", sa.Text(), nullable=False),
        sa.Column("operation", sa.Text(), nullable=False),
        sa.Column("entity_type", sa.Text(), nullable=False),
        sa.Column("entity_id", sa.Text(), nullable=False),
        sa.Column("previous_version", sa.Integer(), nullable=True),
        sa.Column("new_version", sa.Integer(), nullable=True),
        sa.Column("confirmation_id", sa.Text(), nullable=True),
        sa.Column("idempotency_key", sa.Text(), nullable=True),
        sa.Column("summary_hash", sa.String(length=64), nullable=True),
        sa.Column("result_status", sa.Text(), nullable=False),
        sa.Column("reason_code", sa.Text(), nullable=True),
        sa.Column(
            "event_metadata",
            postgresql.JSONB(astext_type=sa.Text()),  # type: ignore[no-untyped-call]
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["confirmation_id"],
            ["confirmations.confirmation_id"],
            name="fk_audit_events_confirmation_id",
        ),
        sa.CheckConstraint(
            "result_status in ('succeeded', 'failed')",
            name="ck_audit_events_result_status",
        ),
        sa.CheckConstraint(
            "summary_hash is null or char_length(summary_hash) = 64",
            name="ck_audit_events_summary_hash_length",
        ),
    )
    op.create_index(
        "ix_audit_events_user_entity_created",
        "audit_events",
        ["user_id", "entity_type", "entity_id", "created_at"],
    )
    op.create_index(
        "ix_audit_events_confirmation_id",
        "audit_events",
        ["confirmation_id"],
    )

    op.create_table(
        "m3_versioned_records",
        sa.Column("record_id", sa.Text(), primary_key=True),
        sa.Column("user_id", sa.Text(), nullable=False),
        sa.Column("entity_type", sa.Text(), nullable=False),
        sa.Column("entity_id", sa.Text(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("lifecycle_status", sa.Text(), nullable=False),
        sa.Column(
            "payload",
            postgresql.JSONB(astext_type=sa.Text()),  # type: ignore[no-untyped-call]
            nullable=False,
        ),
        sa.Column("confirmation_id", sa.Text(), nullable=True),
        sa.Column("idempotency_key", sa.Text(), nullable=True),
        sa.Column("audit_event_id", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["confirmation_id"],
            ["confirmations.confirmation_id"],
            name="fk_m3_versioned_records_confirmation_id",
        ),
        sa.ForeignKeyConstraint(
            ["audit_event_id"],
            ["audit_events.audit_event_id"],
            name="fk_m3_versioned_records_audit_event_id",
        ),
        sa.CheckConstraint("version >= 0", name="ck_m3_versioned_records_version"),
        sa.CheckConstraint(
            "lifecycle_status in ('draft', 'committed')",
            name="ck_m3_versioned_records_lifecycle_status",
        ),
        sa.UniqueConstraint(
            "user_id",
            "entity_type",
            "entity_id",
            "version",
            "lifecycle_status",
            name="uq_m3_versioned_records_user_entity_version_status",
        ),
    )
    op.create_index(
        "ix_m3_versioned_records_user_entity_status",
        "m3_versioned_records",
        ["user_id", "entity_type", "entity_id", "lifecycle_status"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_m3_versioned_records_user_entity_status",
        table_name="m3_versioned_records",
    )
    op.drop_table("m3_versioned_records")
    op.drop_index("ix_audit_events_confirmation_id", table_name="audit_events")
    op.drop_index("ix_audit_events_user_entity_created", table_name="audit_events")
    op.drop_table("audit_events")
    op.drop_table("idempotency_records")
    op.drop_index("ix_confirmations_user_entity", table_name="confirmations")
    op.drop_index("ix_confirmations_user_status_expires", table_name="confirmations")
    op.drop_table("confirmations")
