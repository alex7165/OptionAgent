import requests
import pytest

from app.marketdata.massive_client import MassiveClient


class DummyResponse:

    def __init__(
        self,
        payload: object,
        status_code: int = 200,
        headers: dict[str, str] | None = None,
    ) -> None:
        self.payload = payload
        self.status_code = status_code
        self.headers = headers or {}
        self.raise_for_status_called = False

    def raise_for_status(self) -> None:
        self.raise_for_status_called = True

        if self.status_code >= 400:
            response = requests.Response()
            response.status_code = self.status_code
            response.url = "https://api.massive.com/v2/test?apiKey=secret-key"
            raise requests.HTTPError(
                f"{self.status_code} error for url: {response.url}",
                response=response,
            )

    def json(self) -> object:
        return self.payload


class DummySession:

    def __init__(self, *responses: DummyResponse) -> None:
        self.responses = list(responses)
        self.calls: list[dict] = []

    def get(
        self,
        url: str,
        params: dict,
        timeout: int,
    ) -> DummyResponse:
        self.calls.append(
            {
                "url": url,
                "params": params,
                "timeout": timeout,
            }
        )

        return self.responses.pop(0)


def test_get_adds_api_key_and_returns_payload() -> None:
    response = DummyResponse(
        {
            "status": "OK",
            "results": [],
        }
    )
    session = DummySession(response)

    client = MassiveClient(
        api_key="test-key",
        session=session,
    )

    payload = client.get(
        path="/v2/test",
        params={
            "sort": "asc",
        },
    )

    assert payload == {
        "status": "OK",
        "results": [],
    }

    assert session.calls == [
        {
            "url": "https://api.massive.com/v2/test",
            "params": {
                "sort": "asc",
                "apiKey": "test-key",
            },
            "timeout": 30,
        }
    ]

    assert response.raise_for_status_called is True


def test_get_does_not_modify_original_params() -> None:
    response = DummyResponse({"status": "OK"})
    session = DummySession(response)

    client = MassiveClient(
        api_key="test-key",
        session=session,
    )

    params = {
        "sort": "asc",
    }

    client.get(
        path="/v2/test",
        params=params,
    )

    assert params == {
        "sort": "asc",
    }


def test_get_rejects_non_dictionary_response() -> None:
    response = DummyResponse([])
    session = DummySession(response)

    client = MassiveClient(
        api_key="test-key",
        session=session,
    )

    with pytest.raises(
        ValueError,
        match="Massive API returned an invalid response",
    ):
        client.get(path="/v2/test")


def test_retries_429_using_retry_after_header() -> None:
    session = DummySession(
        DummyResponse({}, status_code=429, headers={"Retry-After": "2.5"}),
        DummyResponse({"status": "OK"}),
    )
    sleep_calls: list[float] = []
    client = MassiveClient(
        api_key="secret-key",
        session=session,
        max_retries=2,
        sleep=sleep_calls.append,
    )

    payload = client.get(path="/v2/test")

    assert payload == {"status": "OK"}
    assert len(session.calls) == 2
    assert sleep_calls == [2.5]


def test_429_stops_after_max_retries_and_hides_api_key() -> None:
    session = DummySession(
        DummyResponse({}, status_code=429),
        DummyResponse({}, status_code=429),
        DummyResponse({}, status_code=429),
    )
    sleep_calls: list[float] = []
    client = MassiveClient(
        api_key="secret-key",
        session=session,
        max_retries=2,
        sleep=sleep_calls.append,
    )

    with pytest.raises(RuntimeError) as error:
        client.get(path="/v2/test")

    assert str(error.value) == "Massive API request failed with status 429"
    assert "secret-key" not in str(error.value)
    assert len(session.calls) == 3
    assert sleep_calls == [1.0, 1.0]


def test_http_error_hides_api_key() -> None:
    session = DummySession(DummyResponse({}, status_code=500))
    client = MassiveClient(
        api_key="secret-key",
        session=session,
    )

    with pytest.raises(RuntimeError) as error:
        client.get(path="/v2/test")

    assert str(error.value) == "Massive API request failed with status 500"
    assert "secret-key" not in str(error.value)


def test_requires_api_key(monkeypatch) -> None:
    monkeypatch.delenv("MASSIVE_API_KEY", raising=False)

    with pytest.raises(
        ValueError,
        match="MASSIVE_API_KEY is not configured",
    ):
        MassiveClient()
