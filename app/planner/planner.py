from app.analysis.trade_exporter import TradeExporter
from datetime import date
from pathlib import Path

from app.ai.client import ask_agent
from app.analysis.earnings import EarningsAnalyzer
from app.analysis.earnings_crush_analyzer_factory import (
    EarningsCrushAnalyzerFactory,
)
from app.browser.browser import BrowserClient
from app.planner.symbol_extractor import SymbolExtractor
from app.reports.reporting import save_report


class Planner:

    def __init__(
        self,
        market_data=None,
        earnings_crush_analyzer_factory=None,
    ):
        self.market_data = market_data
        self.symbol_extractor = SymbolExtractor()
        self.earnings_crush_analyzer_factory = (
            earnings_crush_analyzer_factory
            or EarningsCrushAnalyzerFactory()
        )

    def execute(self, task: str) -> str:
        if self._is_url(task):
            return self._summarize_website(task)

        if self._is_earnings_range_question(task):
            return self._answer_earnings_range_question()

        if self._is_earnings_question(task):
            return self._answer_earnings_question(task)

        if self._is_price_question(task):
            return self._answer_price_question(task)

        return self._answer_question(task)

    def _is_url(self, text: str) -> bool:
        return text.startswith("http://") or text.startswith("https://")

    def _is_price_question(self, text: str) -> bool:
        lower_text = text.lower()
        return "kurs" in lower_text or "price" in lower_text

    def _is_earnings_question(self, text: str) -> bool:
        return "earnings" in text.lower()

    def _is_earnings_range_question(self, text: str) -> bool:
        lower_text = text.lower()
        return "earnings" in lower_text and "2026-07-06" in lower_text

    def _answer_price_question(self, question: str) -> str:
        if self.market_data is None:
            return "MarketDataService is not available."

        symbol = self.symbol_extractor.extract(question)

        if symbol is None:
            return "Kein Börsenkürzel gefunden."

        snapshot = self.market_data.get_snapshot(symbol)

        return f"{snapshot.symbol}: {snapshot.quote.price} {snapshot.quote.currency}"

    def _answer_earnings_question(self, question: str) -> str:
        if self.market_data is None:
            return "MarketDataService is not available."

        symbol = self.symbol_extractor.extract(question)

        if symbol is None:
            return "Kein Börsenkürzel gefunden."

        analyzer = EarningsAnalyzer(self.market_data)
        result = analyzer.analyze(symbol)

        return result.summary

    def _answer_earnings_range_question(self) -> str:
        if self.market_data is None:
            return "MarketDataService is not available."

        events = self.market_data.get_earnings_events(
            date(2026, 7, 6),
            date(2026, 7, 10),
        )

        analyzer = self.earnings_crush_analyzer_factory.create(
            self.market_data
        )
        candidates = analyzer.create_candidates(events)

        export_dir = Path("exports")
        export_dir.mkdir(exist_ok=True)

        export_path = export_dir / f"earnings_crush_{date.today().isoformat()}.xlsx"

        TradeExporter().export_excel(
            candidates,
            export_path
        )

        lines = [
            f"{candidate.earnings_event.symbol}: "
            f"{candidate.snapshot.quote.price} "
            f"{candidate.snapshot.quote.currency}"
            for candidate in candidates
        ]

        lines.append("")
        lines.append(f"Excel-Export: {export_path}")

        return "\n".join(lines)

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