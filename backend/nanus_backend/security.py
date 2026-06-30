from __future__ import annotations

import os
import time
from dataclasses import dataclass, field
from typing import Iterable

from fastapi import Request
from fastapi.responses import JSONResponse


@dataclass
class RateBucket:
    window_started: float
    count: int = 0


@dataclass
class SecurityPolicy:
    api_keys: set[str]
    auth_required: bool
    rate_limit_per_minute: int
    buckets: dict[str, RateBucket] = field(default_factory=dict)

    @classmethod
    def from_env(cls) -> "SecurityPolicy":
        keys = {item.strip() for item in os.environ.get("NANUS_API_KEYS", "").split(",") if item.strip()}
        auth_required = os.environ.get("NANUS_AUTH_REQUIRED", "false").lower() in {"1", "true", "yes", "on"} or bool(keys)
        try:
            per_minute = int(os.environ.get("NANUS_RATE_LIMIT_PER_MINUTE", "120"))
        except ValueError:
            per_minute = 120
        return cls(api_keys=keys, auth_required=auth_required, rate_limit_per_minute=max(1, per_minute))

    def _public_request(self, request: Request) -> bool:
        return request.method == "OPTIONS" or is_path_public(request.url.path)

    def _api_key_from_request(self, request: Request) -> str:
        supplied = request.headers.get("x-nanus-api-key", "").strip()
        auth = request.headers.get("authorization", "").strip()
        if auth.lower().startswith("bearer "):
            supplied = auth.split(" ", 1)[1].strip()
        return supplied

    def check_auth(self, request: Request) -> JSONResponse | None:
        if not self.auth_required or self._public_request(request):
            return None
        supplied = self._api_key_from_request(request)
        if supplied and supplied in self.api_keys:
            return None
        return JSONResponse({"detail": "Nanus API authentication required"}, status_code=401)

    def check_rate_limit(self, request: Request) -> JSONResponse | None:
        if self._public_request(request):
            return None
        now = time.time()
        identity = self._api_key_from_request(request) or (request.client.host if request.client else "unknown")
        bucket = self.buckets.get(identity)
        if not bucket or now - bucket.window_started >= 60:
            self.buckets[identity] = RateBucket(window_started=now, count=1)
            return None
        bucket.count += 1
        if bucket.count > self.rate_limit_per_minute:
            return JSONResponse({"detail": "Nanus API rate limit exceeded"}, status_code=429)
        return None


def is_path_public(path: str, public_paths: Iterable[str] = ("/health",)) -> bool:
    return path in public_paths
