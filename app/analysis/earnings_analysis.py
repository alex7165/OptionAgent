from dataclasses import dataclass
from datetime import date


@dataclass
class EarningsAnalysis:
    has_earnings: bool
    report_date: date | None
    timing: str | None