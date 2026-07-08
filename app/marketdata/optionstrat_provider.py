import json
import zlib
from datetime import date

import requests


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