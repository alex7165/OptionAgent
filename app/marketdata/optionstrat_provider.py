import json
import zlib
from datetime import date

import requests
from app.marketdata.models import OptionQuote
from app.marketdata.models import ExpirationChain, OptionQuote


class OptionStratProvider:

    BASE_URL = "https://optionstrat.com/api/quote/chain/delayed"

    def get_option_chain(self, symbol: str) -> dict:
        response = requests.get(
            f"{self.BASE_URL}/{symbol.upper()}",
            timeout=10,
        )
        response.raise_for_status()

        return self._decrypt_response(response.content)

    def get_expirations(self, symbol: str) -> list[str]:
        data = self.get_option_chain(symbol)

        chains = data["context"]["i"]["c"][symbol.upper()]

        return [chain["exp"] for chain in chains]

    def _decrypt_response(self, data: bytes) -> dict:
        key_index = data[0]
        xor_key = data[1]
        encrypted = bytearray(data[2:])

        for index in range(len(encrypted)):
            encrypted[index] ^= index % xor_key

        decompressed = bytearray(
            zlib.decompress(bytes(encrypted), wbits=-15)
        )

        decompressed[key_index] ^= xor_key

        return json.loads(decompressed.decode("utf-8"))

    def parse_expiration(self, expiration: str) -> date:
        year = 2000 + int(expiration[:2])
        month = int(expiration[2:4])
        day = int(expiration[4:6])

        return date(year, month, day)

    def get_expiration_dates(self, symbol: str) -> list[date]:
        expirations = self.get_expirations(symbol)

        return [
            self.parse_expiration(expiration)
            for expiration in expirations
        ]

    def get_next_expiration_on_or_after(
        self,
        symbol: str,
        target_date: date,
    ) -> date | None:
        expirations = self.get_expiration_dates(symbol)

        valid_expirations = [
            expiration
            for expiration in expirations
            if expiration >= target_date
        ]

        if not valid_expirations:
            return None

        return min(valid_expirations)

    def get_chain_for_expiration(
        self,
        symbol: str,
        expiration: date,
    ) -> dict | None:
        data = self.get_option_chain(symbol)

        expiration_code = expiration.strftime("%y%m%d")

        chains = data["context"]["i"]["c"][symbol.upper()]

        for chain in chains:
            if chain["exp"] == expiration_code:
                return chain

        return None

    def get_expiration_chain(
        self,
        symbol: str,
        expiration: date,
    ) -> ExpirationChain | None:
        chain = self.get_chain_for_expiration(symbol, expiration)

        if chain is None:
            return None

        quotes: list[OptionQuote] = []

        for strike_key, strike_data in chain["s"].items():
            strike = float(strike_key)

            for option_type, key in [
                ("call", "c"),
                ("put", "p"),
            ]:
                quote = strike_data.get(key)

                if quote is None:
                    continue

                quotes.append(
                    OptionQuote(
                        symbol=symbol.upper(),
                        expiration=expiration,
                        strike=strike,
                        option_type=option_type,
                        bid=quote.get("b"),
                        ask=quote.get("a"),
                        last=quote.get("p"),
                        volume=quote.get("v"),
                        open_interest=quote.get("o"),
                    )
                )

        return ExpirationChain(
            symbol=symbol.upper(),
            expiration=expiration,
            quotes=quotes,
        )

    def get_strikes_for_expiration(
        self,
        symbol: str,
        expiration: date,
    ) -> list[float]:
        chain = self.get_chain_for_expiration(symbol, expiration)

        if chain is None:
            return []

        return sorted(float(strike) for strike in chain["s"].keys())

    def get_option_quote(
        self,
        symbol: str,
        expiration: date,
        strike: float,
        option_type: str,
    ) -> OptionQuote | None:
        chain = self.get_chain_for_expiration(symbol, expiration)

        if chain is None:
            return None

        strike_key = str(int(strike)) if strike.is_integer() else str(strike)
        strike_data = chain["s"].get(strike_key)

        if strike_data is None:
            return None

        key = "c" if option_type == "call" else "p"
        quote = strike_data.get(key)

        if quote is None:
            return None

        return OptionQuote(
            symbol=symbol.upper(),
            expiration=expiration,
            strike=strike,
            option_type=option_type,
            bid=quote.get("b"),
            ask=quote.get("a"),
            last=quote.get("p"),
            volume=quote.get("v"),
            open_interest=quote.get("o"),
        )
