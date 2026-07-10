from __future__ import annotations

import ast
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]
DOMAIN_ROOT = ROOT / "src" / "menu_planner" / "domain"


def _imports(path: pathlib.Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    modules: list[str] = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module is not None:
            modules.append(node.module)

    return modules


class SafeCommitBoundaryTests(unittest.TestCase):
    def test_domain_core_keeps_runtime_and_adapter_imports_out(self) -> None:
        forbidden_modules = (
            "alembic",
            "fastapi",
            "httpx",
            "menu_planner.adapters",
            "menu_planner.application",
            "menu_planner.infrastructure",
            "openai",
            "psycopg",
            "pydantic",
            "requests",
            "sqlalchemy",
            "telegram",
        )

        for path in DOMAIN_ROOT.rglob("*.py"):
            with self.subTest(path=path.relative_to(ROOT)):
                for module in _imports(path):
                    self.assertFalse(
                        module in forbidden_modules
                        or module.startswith(forbidden_modules),
                        module,
                    )

    def test_application_ports_do_not_import_infrastructure(self) -> None:
        modules = _imports(
            ROOT / "src" / "menu_planner" / "application" / "safe_commit.py"
        )

        self.assertNotIn("menu_planner.infrastructure", modules)
        for module in modules:
            self.assertFalse(module.startswith("menu_planner.infrastructure."))

    def test_hermes_infrastructure_does_not_call_safe_commit_sql_adapters(self) -> None:
        modules = _imports(
            ROOT / "src" / "menu_planner" / "infrastructure" / "hermes.py"
        )

        self.assertNotIn("menu_planner.infrastructure.safe_commit_sql", modules)


if __name__ == "__main__":
    unittest.main()
