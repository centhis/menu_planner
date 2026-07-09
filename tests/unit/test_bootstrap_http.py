from __future__ import annotations

import unittest
from collections.abc import Mapping, Sequence
from typing import Any
from unittest import mock

from menu_planner.bootstrap.http import create_app


class HttpBootstrapTests(unittest.TestCase):
    def test_create_app_reports_missing_fastapi_dependency(self) -> None:
        real_import = __import__

        def fake_import(
            name: str,
            globals_: Mapping[str, object] | None = None,
            locals_: Mapping[str, object] | None = None,
            fromlist: Sequence[str] = (),
            level: int = 0,
        ) -> Any:
            if name == "fastapi":
                raise ModuleNotFoundError("No module named 'fastapi'")
            return real_import(name, globals_, locals_, fromlist, level)

        with self.assertRaisesRegex(RuntimeError, "FastAPI is not installed"):
            with mock.patch("builtins.__import__", side_effect=fake_import):
                create_app()


if __name__ == "__main__":
    unittest.main()
