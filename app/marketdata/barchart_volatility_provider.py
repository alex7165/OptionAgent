import requests
from urllib.parse import urlencode

from app.browser.browser import BrowserClient
from app.marketdata.volatility_provider import VolatilityProvider


class BarchartVolatilityProvider(VolatilityProvider):

    PAGE_URL = "https://www.barchart.com/options/iv-rank-percentile/high?sector=stock"
    API_URL = "https://www.barchart.com/proxies/core-api/v1/quotes/get"

    def __init__(self, headless: bool = False):
        self.headless = headless

    def get_iv_rank(self, symbol: str) -> float | None:
        data = self._get_quote(symbol)
        if data is None:
            return None

        return data["raw"].get("optionsImpliedVolatilityRank1y")

    def get_iv_percentile(self, symbol: str) -> float | None:
        data = self._get_quote(symbol)
        if data is None:
            return None

        value = data["raw"].get("optionsImpliedVolatilityPercentile1y")
        if value is None:
            return None

        return value * 100

    def _get_quote(self, symbol: str) -> dict | None:
        browser = BrowserClient(headless=self.headless)
        browser.start()

        headers, cookies = browser.get_barchart_session()

        browser.close()

        session = requests.Session()

        for cookie in cookies:
            session.cookies.set(
                cookie["name"],
                cookie["value"],
                domain=cookie.get("domain"),
                path=cookie.get("path", "/"),
            )

        params = {
            "symbols": symbol,
            "fields": ",".join(
                [
                    "symbol",
                    "optionsImpliedVolatilityRank1y",
                    "optionsImpliedVolatilityPercentile1y",
                ]
            ),
            "raw": "1",
        }

        response = session.get(
            self.API_URL + "?" + urlencode(params),
            headers={
                "User-Agent": headers["user-agent"],
                "Accept": headers["accept"],
                "Referer": headers["referer"],
                "X-XSRF-TOKEN": headers["x-xsrf-token"],
            },
            timeout=30,
        )

        response.raise_for_status()

        data = response.json()["data"]

        if not data:
            return None

        return data[0]