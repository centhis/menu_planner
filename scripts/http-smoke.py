from __future__ import annotations

import json
import os
from urllib.error import HTTPError
from urllib.request import urlopen


def fetch_json(url: str) -> dict[str, object]:
    with urlopen(url, timeout=5) as response:
        payload = response.read().decode("utf-8")
    return json.loads(payload)


def main() -> None:
    base_url = os.environ.get("APP_BASE_URL", "http://127.0.0.1:8080")

    health = fetch_json(f"{base_url}/healthz")
    if health.get("status") != "ok":
        raise SystemExit(f"unexpected health response: {health}")

    try:
        readiness = fetch_json(f"{base_url}/readyz")
    except HTTPError as exc:
        detail = exc.read().decode("utf-8")
        raise SystemExit(f"readiness request failed: {exc.code} {detail}") from exc

    if readiness.get("status") != "ready":
        raise SystemExit(f"unexpected readiness response: {readiness}")

    print("http health/readiness ok")


if __name__ == "__main__":
    main()
