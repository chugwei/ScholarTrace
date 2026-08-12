"""Dependency-free health monitoring for local Staging and offline checks."""

from __future__ import annotations

import http.client
import json
from datetime import UTC, datetime
from urllib.error import HTTPError
from urllib.request import urlopen

from scholartrace.schemas.delivery import HealthProbeResult


def probe_health(endpoint: str, *, timeout_seconds: float = 3) -> HealthProbeResult:
    """Probe a JSON `/health` endpoint without hiding HTTP or network failures."""

    checked_at = datetime.now(UTC)
    try:
        with urlopen(endpoint, timeout=timeout_seconds) as response:
            status_code = response.status
            raw = response.read()
        payload = json.loads(raw.decode("utf-8"))
        if not isinstance(payload, dict):
            return HealthProbeResult(
                endpoint=endpoint,
                status_code=status_code,
                ok=False,
                error="health response must be a JSON object",
                checked_at=checked_at,
            )
        ok = status_code == 200 and payload.get("status") == "ok"
        return HealthProbeResult(
            endpoint=endpoint,
            status_code=status_code,
            ok=ok,
            payload=payload,
            error=None if ok else "health response did not report status=ok",
            checked_at=checked_at,
        )
    except HTTPError as error:
        return HealthProbeResult(
            endpoint=endpoint,
            status_code=error.code,
            ok=False,
            error=f"HTTP {error.code}",
            checked_at=checked_at,
        )
    except (
        http.client.HTTPException,
        OSError,
        ValueError,
        UnicodeDecodeError,
        json.JSONDecodeError,
    ) as error:
        return HealthProbeResult(
            endpoint=endpoint,
            ok=False,
            error=f"{type(error).__name__}: {error}",
            checked_at=checked_at,
        )
