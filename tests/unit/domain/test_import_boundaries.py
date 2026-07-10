from __future__ import annotations

import ast
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[3]
DOMAIN_ROOT = ROOT / "src" / "menu_planner" / "domain"

FORBIDDEN_IMPORT_PREFIXES = (
    "aiohttp",
    "aiogram",
    "alembic",
    "anthropic",
    "fastapi",
    "hermes",
    "httpx",
    "menu_planner.application",
    "menu_planner.bootstrap",
    "menu_planner.infrastructure",
    "openai",
    "plugins",
    "psycopg",
    "pydantic",
    "requests",
    "sqlalchemy",
    "telegram",
    "urllib3",
)


def _imported_modules(tree: ast.AST) -> list[str]:
    modules: list[str] = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module is not None:
            modules.append(node.module)

    return modules


def _is_forbidden_import(module: str) -> bool:
    return any(
        module == prefix or module.startswith(f"{prefix}.")
        for prefix in FORBIDDEN_IMPORT_PREFIXES
    )


class DomainImportBoundaryTests(unittest.TestCase):
    def test_domain_package_exists(self) -> None:
        self.assertTrue(DOMAIN_ROOT.is_dir())

    def test_domain_core_does_not_import_forbidden_runtime_layers(self) -> None:
        violations: list[str] = []

        for path in sorted(DOMAIN_ROOT.rglob("*.py")):
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            for module in _imported_modules(tree):
                if _is_forbidden_import(module):
                    relative_path = path.relative_to(ROOT)
                    violations.append(f"{relative_path}: forbidden import {module}")

        self.assertEqual(violations, [])

    def test_boundary_check_detects_forbidden_imports(self) -> None:
        tree = ast.parse("from menu_planner.infrastructure.database import x\n")

        forbidden_modules = [
            module for module in _imported_modules(tree) if _is_forbidden_import(module)
        ]

        self.assertEqual(forbidden_modules, ["menu_planner.infrastructure.database"])


if __name__ == "__main__":
    unittest.main()
