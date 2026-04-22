"""TAGO HTTP client — single entry point for every API call.

Encapsulates:
- httpx session with configurable timeout
- tenacity retry policy (network-level only; TAGO resultCode errors raise immediately)
- Unified error branching per docs/tago-batch-spec.md §9.1
- Raw response dumping on JSON parse failure
"""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx
import structlog
from tenacity import (
    retry,
    retry_if_exception,
    stop_after_attempt,
    wait_exponential,
)

from rhythmscape.ingest.tago.normalize import normalize_keys

log = structlog.get_logger(__name__)


class TagoAPIError(Exception):
    """TAGO resultCode != '00' — API responded with a business-logic error."""

    def __init__(self, code: str, msg: str, endpoint: str):
        self.code = code
        self.msg = msg
        self.endpoint = endpoint
        super().__init__(f"[{endpoint}] {code}: {msg}")


class TagoQuotaExceeded(TagoAPIError):
    """resultCode 22 — daily call quota exceeded for this service key."""


class TagoKeyUnregistered(TagoAPIError):
    """resultCode 30 — service key not registered or URL-double-encoded."""


def _should_retry_network(exc: BaseException) -> bool:
    """Retry only on transient network errors + 5xx. Client errors (4xx) fail fast.

    4xx are retried zero times because they are almost always caused by a
    request shape error (bad params, malformed serviceKey) — retrying would
    only burn quota.
    """
    if isinstance(exc, httpx.TimeoutException):
        return True
    if isinstance(exc, httpx.HTTPStatusError):
        return 500 <= exc.response.status_code < 600
    if isinstance(exc, httpx.TransportError):
        return True
    return False


class TagoClient:
    """Session-scoped TAGO API client.

    Example
    -------
    >>> client = TagoClient(api_key=os.environ["TAGO_API_KEY"])
    >>> body = client.call(
    ...     "BusSttnInfoInqireService",
    ...     "getSttnNoList",
    ...     {"cityCode": 38010, "numOfRows": 100, "pageNo": 1},
    ... )
    """

    BASE = "https://apis.data.go.kr/1613000"
    DEFAULT_TIMEOUT = 10.0

    def __init__(
        self,
        api_key: str,
        timeout: float = DEFAULT_TIMEOUT,
        raw_dump_dir: Path | None = None,
    ):
        if not api_key:
            raise ValueError("TAGO_API_KEY is empty — check .env loading")
        self.api_key = api_key
        self._http = httpx.Client(timeout=timeout)
        self._raw_dump_dir = raw_dump_dir or Path("logs/tago")

    def __enter__(self) -> "TagoClient":
        return self

    def __exit__(self, *exc_info: Any) -> None:
        self.close()

    def close(self) -> None:
        self._http.close()

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception(_should_retry_network),
        reraise=True,
    )
    def _get(self, url: str, params: dict[str, Any]) -> httpx.Response:
        response = self._http.get(url, params=params)
        response.raise_for_status()
        return response

    def call(
        self,
        service: str,
        operation: str,
        params: dict[str, Any],
    ) -> dict:
        """Invoke a TAGO endpoint and return the normalized response ``body`` dict.

        Parameters
        ----------
        service
            Service name, e.g. ``"BusSttnInfoInqireService"``.
        operation
            Endpoint operation, e.g. ``"getSttnNoList"``.
        params
            Query parameters excluding ``serviceKey`` and ``_type`` (injected here).

        Returns
        -------
        dict
            The normalized ``response.body`` dict. Keys are lowercased.

        Raises
        ------
        TagoQuotaExceeded
            resultCode 22.
        TagoKeyUnregistered
            resultCode 30.
        TagoAPIError
            Any other resultCode != '00'.
        ValueError
            JSON parsing failed. Raw bytes are dumped to ``raw_dump_dir``.
        """
        url = f"{self.BASE}/{service}/{operation}"
        full_params = {
            "serviceKey": self.api_key,
            "_type": "json",
            **params,
        }

        response = self._get(url, full_params)

        try:
            raw = response.json()
        except ValueError as exc:
            dump_path = self._dump_raw(response.content, service, operation)
            log.error(
                "tago_json_parse_failed",
                service=service,
                operation=operation,
                dump=str(dump_path),
                status=response.status_code,
            )
            raise ValueError(
                f"TAGO JSON parse failed at {service}/{operation}; raw dumped to {dump_path}"
            ) from exc

        data = normalize_keys(raw)
        resp = data.get("response") or {}
        header = resp.get("header") or {}
        body = resp.get("body") or {}

        code = str(header.get("resultcode", ""))
        msg = str(header.get("resultmsg", ""))

        if code == "00":
            return body
        if code == "22":
            log.warning("tago_quota_exceeded", endpoint=operation)
            raise TagoQuotaExceeded(code, msg, operation)
        if code == "30":
            log.error("tago_key_unregistered", endpoint=operation)
            raise TagoKeyUnregistered(code, msg, operation)
        log.warning("tago_api_error", code=code, msg=msg, endpoint=operation)
        raise TagoAPIError(code, msg, operation)

    def _dump_raw(self, content: bytes, service: str, operation: str) -> Path:
        self._raw_dump_dir.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now(tz=timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        digest = hashlib.sha256(content).hexdigest()[:8]
        path = self._raw_dump_dir / f"raw_dump_{service}_{operation}_{stamp}_{digest}.bin"
        path.write_bytes(content)
        return path
