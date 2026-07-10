from __future__ import annotations

import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]
BASELINE = ROOT / "migrations" / "versions" / "20260709_0001_baseline.py"
M3_SAFE_COMMIT = (
    ROOT
    / "migrations"
    / "versions"
    / "20260710_0002_m3_safe_commit_primitives.py"
)


class MigrationTests(unittest.TestCase):
    def test_baseline_migration_does_not_create_domain_tables(self) -> None:
        text = BASELINE.read_text(encoding="utf-8")

        forbidden_terms = [
            "create_table",
            "profile",
            "menu",
            "recipe",
            "shopping",
            "workflow",
            "confirmation",
        ]

        for term in forbidden_terms:
            self.assertNotIn(term, text)

    def test_migration_entrypoints_exist(self) -> None:
        self.assertTrue((ROOT / "scripts" / "migrate.sh").is_file())
        self.assertTrue((ROOT / "scripts" / "migration-status.sh").is_file())

    def test_m3_safe_commit_migration_creates_only_generic_primitives(self) -> None:
        text = M3_SAFE_COMMIT.read_text(encoding="utf-8")

        required_tables = [
            '"confirmations"',
            '"idempotency_records"',
            '"audit_events"',
            '"m3_versioned_records"',
        ]
        forbidden_product_terms = [
            "profile",
            "menu",
            "recipe",
            "shopping",
            "store",
            "telegram",
            "llm",
            "workflow",
        ]

        for table in required_tables:
            self.assertIn(table, text)
        for term in forbidden_product_terms:
            self.assertNotIn(term, text.lower())

    def test_m3_safe_commit_migration_has_versioning_and_idempotency_guards(
        self,
    ) -> None:
        text = M3_SAFE_COMMIT.read_text(encoding="utf-8")

        required_fragments = [
            'revision: str = "20260710_0002"',
            'down_revision: str | None = "20260709_0001"',
            "uq_idempotency_records_user_operation_key",
            "uq_m3_versioned_records_user_entity_version_status",
            "ck_confirmations_summary_hash_length",
            "ck_idempotency_records_request_fingerprint_length",
            "fk_audit_events_confirmation_id",
            "fk_m3_versioned_records_confirmation_id",
            "fk_m3_versioned_records_audit_event_id",
            "op.drop_table(\"m3_versioned_records\")",
            "op.drop_table(\"audit_events\")",
            "op.drop_table(\"idempotency_records\")",
            "op.drop_table(\"confirmations\")",
        ]

        for fragment in required_fragments:
            self.assertIn(fragment, text)


if __name__ == "__main__":
    unittest.main()
