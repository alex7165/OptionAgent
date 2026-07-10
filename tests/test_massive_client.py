import pytest

from app.marketdata.massive_client import MassiveClient


class DummyResponse:

    def __init__(self, payload: object) -> None:
        self.payload = payload
        self.raise_for_status_called = False

    def raise_for_status(self) -> None:
        self.raise_for_status_called = True

    def json(self) -> object:
        return self.payload


class DummySession:

    def __init__(self, response: DummyResponse) -> None:
        self.response = response
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

        return self.response


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


def test_requires_api_key(monkeypatch) -> None:
    monkeypatch.delenv("MASSIVE_API_KEY", raising=False)

    with pytest.raises(
        ValueError,
        match="MASSIVE_API_KEY is not configured",
    ):
        MassiveClient()