from __future__ import annotations

import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]


class ContainerSetupTests(unittest.TestCase):
    def test_application_dockerfile_is_explicitly_not_hermes(self) -> None:
        dockerfiles = sorted(path.name for path in ROOT.glob("Dockerfile*"))
        dockerfile = (ROOT / "Dockerfile.app").read_text(encoding="utf-8")

        self.assertEqual(dockerfiles, ["Dockerfile.app"])
        self.assertIn("FROM python:3.12-slim", dockerfile)
        self.assertIn("requirements.txt", dockerfile)
        self.assertIn("uvicorn", dockerfile)
        self.assertNotIn("FROM nousresearch/hermes-agent", dockerfile)
        self.assertNotIn("docker compose build hermes", dockerfile.lower())

    def test_dependency_files_are_pinned(self) -> None:
        for name in ["requirements.txt", "requirements-dev.txt"]:
            text = (ROOT / name).read_text(encoding="utf-8")
            for line in text.splitlines():
                stripped = line.strip()
                if (
                    not stripped
                    or stripped.startswith("#")
                    or stripped.startswith("-r ")
                ):
                    continue
                self.assertIn(
                    "==",
                    stripped,
                    f"{name} has unpinned dependency: {stripped}",
                )

    def test_compose_has_application_service_without_hermes_build(self) -> None:
        compose = (ROOT / "compose.yaml").read_text(encoding="utf-8")

        self.assertIn("  app:", compose)
        self.assertIn("dockerfile: Dockerfile.app", compose)
        self.assertIn("image: menu-planner-app:local", compose)
        self.assertIn("nousresearch/hermes-agent:v2026.6.19", compose)
        self.assertIn(
            "HERMES_BASE_URL: http://hermes:${HERMES_DASHBOARD_PORT:-9119}",
            compose,
        )
        self.assertIn('EXPECTED_MIGRATION_REVISION: "20260709_0001"', compose)
        self.assertNotIn("plugins/menu-planner-probe", compose)

        hermes_block = compose.split("  hermes:", 1)[1].split("  postgres:", 1)[0]
        self.assertNotIn("build:", hermes_block)

    def test_stage_0_probe_plugin_is_not_enabled_by_default(self) -> None:
        config = (ROOT / "config" / "hermes-managed-config.yaml").read_text(
            encoding="utf-8"
        )

        self.assertIn("dashboard_auth/basic", config)
        self.assertNotIn("menu-planner-probe", config)

    def test_dockerignore_excludes_local_secrets_from_build_context(self) -> None:
        dockerignore = (ROOT / ".dockerignore").read_text(encoding="utf-8")

        for fragment in [".env", ".git", "auth.json", "credentials", "*token*"]:
            self.assertIn(fragment, dockerignore)


if __name__ == "__main__":
    unittest.main()
