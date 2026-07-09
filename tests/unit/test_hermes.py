from __future__ import annotations

import unittest

from menu_planner.infrastructure.hermes import HermesReachabilityProbe


class HermesReachabilityProbeTests(unittest.TestCase):
    def test_ping_fails_clearly_when_base_url_is_missing(self) -> None:
        probe = HermesReachabilityProbe("")

        with self.assertRaisesRegex(RuntimeError, "HERMES_BASE_URL is not configured"):
            probe.ping()

    def test_ping_fails_clearly_when_base_url_has_no_reachable_host(self) -> None:
        probe = HermesReachabilityProbe("not-a-url")

        with self.assertRaisesRegex(RuntimeError, "HERMES_BASE_URL is not reachable"):
            probe.ping()


if __name__ == "__main__":
    unittest.main()
