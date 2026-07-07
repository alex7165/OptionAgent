import re


class SymbolExtractor:

    def extract(self, text: str) -> str | None:
        matches = re.findall(r"\b[A-Z]{1,5}\b", text)

        if not matches:
            return None

        return matches[0]