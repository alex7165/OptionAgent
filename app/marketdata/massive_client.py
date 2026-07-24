import os
import time
from collections.abc import Callable
from typing import Any

import requests


class MassiveClient:

    API_BASE_URL = "https://api.massive.com"

    def __init__(
        self,
        api_key: str | None = None,
        session: requests.Session | None = None,
        max_retries: int = 2,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self.api_key = api_key or os.getenv("MASSIVE_API_KEY")

        if not self.api_key:
            raise ValueError("MASSIVE_API_KEY is not configured")

        if max_retries < 0:
            raise ValueError("max_retries must not be negative")

        self.session = session or requests.Session()
        self.max_retries = max_retries
        self.sleep = sleep

    def get(
        self,
        path: str,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        request_params = dict(params or {})
        request_params["apiKey"] = self.api_key

        for attempt in range(self.max_retries + 1):
            response = self.session.get(
                f"{self.API_BASE_URL}{path}",
                params=request_params,
                timeout=30,
            )

            if response.status_code == 429 and attempt < self.max_retries:
                self.sleep(self._retry_after_seconds(response))
                continue

            try:
                response.raise_for_status()
            except requests.HTTPError as error:
                status_code = getattr(error.response, "status_code", None)
                status_text = str(status_code) if status_code is not None else "unknown"
                raise RuntimeError(
                    f"Massive API request failed with status {status_text}"
                ) from None

            payload = response.json()

            if not isinstance(payload, dict):
                raise ValueError("Massive API returned an invalid response")

            return payload

        raise RuntimeError("Massive API request failed")

    @staticmethod
    def _retry_after_seconds(response: requests.Response) -> float:
        raw_value = response.headers.get("Retry-After")

        if raw_value is None:
            return 1.0

        try:
            return max(float(raw_value), 0.0)
        except ValueError:
            return 1.0
