import os
from typing import Any

import requests


class MassiveClient:

    API_BASE_URL = "https://api.massive.com"

    def __init__(
        self,
        api_key: str | None = None,
        session: requests.Session | None = None,
    ) -> None:
        self.api_key = api_key or os.getenv("MASSIVE_API_KEY")

        if not self.api_key:
            raise ValueError("MASSIVE_API_KEY is not configured")

        self.session = session or requests.Session()

    def get(
        self,
        path: str,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        request_params = dict(params or {})
        request_params["apiKey"] = self.api_key

        response = self.session.get(
            f"{self.API_BASE_URL}{path}",
            params=request_params,
            timeout=30,
        )
        response.raise_for_status()

        payload = response.json()

        if not isinstance(payload, dict):
            raise ValueError("Massive API returned an invalid response")

        return payload