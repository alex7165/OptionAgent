from app.ai.client import ask_agent
from app.browser.browser import BrowserClient
from app.planner.symbol_extractor import SymbolExtractor
from app.reports.reporting import save_report


class Planner:

    def __init__(self, market_data=None):
        self.market_data = market_data
        self.symbol_extractor = SymbolExtractor()

    def execute(self, task: str) -> str:
        if self._is_url(task):
            return self._summarize_website(task)

        if self._is_price_question(task):
            return self._answer_price_question(task)

        return self._answer_question(task)

    def _is_url(self, text: str) -> bool:
        return text.startswith("http://") or text.startswith("https://")

    def _is_price_question(self, text: str) -> bool:
        lower_text = text.lower()
        return "kurs" in lower_text or "price" in lower_text

    def _answer_price_question(self, question: str) -> str:
        if self.market_data is None:
            return "MarketDataService is not available."

        symbol = self.symbol_extractor.extract(question)

        if symbol is None:
            return "Kein Börsenkürzel gefunden."

        snapshot = self.market_data.get_snapshot(symbol)

        return f"{snapshot.symbol}: {snapshot.quote.price} {snapshot.quote.currency}"

    def _answer_question(self, question: str) -> str:
        answer = ask_agent(question)
        save_report(question, answer)
        return answer

    def _summarize_website(self, url: str) -> str:
        browser = BrowserClient(headless=False)

        browser.start()
        browser.goto(url)

        title = browser.get_title()
        text = browser.get_text()

        browser.close()

        prompt = f"""
Titel:
{title}

Seiteninhalt:
{text[:8000]}

Fasse diese Webseite in höchstens 10 Stichpunkten zusammen.
"""

        answer = ask_agent(prompt)
        save_report(url, answer)

        return answer