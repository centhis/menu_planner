"""Application HTTP API adapter for the Menu Planner Hermes plugin."""

from __future__ import annotations

import json
import socket
from dataclasses import dataclass
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen

JsonObject = dict[str, Any]


@dataclass(frozen=True)
class ApplicationHttpClient:
    """Small stdlib HTTP client used by Hermes tool handlers.

    The adapter intentionally talks only to the Application HTTP API. State
    changes remain behind the Application service transaction boundary.
    """

    base_url: str
    timeout_seconds: float = 5.0

    def get(self, path: str, *, correlation_id: str) -> JsonObject:
        return self.request("GET", path, correlation_id=correlation_id)

    def post(
        self,
        path: str,
        *,
        payload: JsonObject,
        correlation_id: str,
        idempotency_key: str | None = None,
    ) -> JsonObject:
        return self.request(
            "POST",
            path,
            payload=payload,
            correlation_id=correlation_id,
            idempotency_key=idempotency_key,
        )

    def request(
        self,
        method: str,
        path: str,
        *,
        correlation_id: str,
        payload: JsonObject | None = None,
        idempotency_key: str | None = None,
    ) -> JsonObject:
        try:
            url = _join_url(self.base_url, path)
            body = None if payload is None else _json_bytes(payload)
            headers = {
                "Accept": "application/json",
                "X-Correlation-ID": correlation_id,
            }
            if body is not None:
                headers["Content-Type"] = "application/json"
            if idempotency_key:
                headers["Idempotency-Key"] = idempotency_key

            request = Request(url, data=body, headers=headers, method=method.upper())
            with urlopen(request, timeout=self.timeout_seconds) as response:
                status = int(response.status)
                data = _decode_json(response.read())
            return {
                "ok": True,
                "status": status,
                "correlation_id": correlation_id,
                "data": data,
            }
        except TimeoutError:
            return _error(
                "application_timeout",
                "Application HTTP API timed out",
                correlation_id,
            )
        except socket.timeout:
            return _error(
                "application_timeout",
                "Application HTTP API timed out",
                correlation_id,
            )
        except HTTPError as exc:
            return _http_error(exc, correlation_id)
        except URLError as exc:
            return _error(
                "application_unreachable",
                f"Application HTTP API is unreachable: {exc.reason}",
                correlation_id,
            )
        except ValueError as exc:
            return _error("application_request_invalid", str(exc), correlation_id)
        except json.JSONDecodeError:
            return _error(
                "application_invalid_json",
                "Application HTTP API returned invalid JSON",
                correlation_id,
            )


def _join_url(base_url: str, path: str) -> str:
    if not base_url:
        raise ValueError("base_url is required")
    if not path.startswith("/"):
        raise ValueError("path must start with /")

    parsed_path = urlparse(path)
    if parsed_path.scheme or parsed_path.netloc:
        raise ValueError("path must be relative to the Application HTTP API")
    if ".." in parsed_path.path.split("/"):
        raise ValueError("path must not contain parent-directory traversal")

    return urljoin(base_url.rstrip("/") + "/", path.lstrip("/"))


def _json_bytes(payload: JsonObject) -> bytes:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")


def _decode_json(raw: bytes) -> Any:
    if not raw:
        return None
    return json.loads(raw.decode("utf-8"))


def _http_error(exc: HTTPError, correlation_id: str) -> JsonObject:
    try:
        details = _decode_json(exc.read())
    except json.JSONDecodeError:
        details = None

    return _error(
        "application_http_error",
        f"Application HTTP API returned HTTP {exc.code}",
        correlation_id,
        status=int(exc.code),
        details=details,
    )


def _error(
    code: str,
    message: str,
    correlation_id: str,
    *,
    status: int | None = None,
    details: Any = None,
) -> JsonObject:
    error: JsonObject = {
        "code": code,
        "message": message,
    }
    if status is not None:
        error["status"] = status
    if details is not None:
        error["details"] = details

    return {
        "ok": False,
        "correlation_id": correlation_id,
        "error": error,
    }
