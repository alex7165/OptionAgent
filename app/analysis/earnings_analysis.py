from dataclasses import dataclass
from datetime import date

from app.marketdata.models import EarningsEvent


@dataclass
class EarningsAnalysis:
    has_earnings: bool
    report_date: date | None
    timing: str |None

    @classmethod
    def from_event(cls, event: EarningsEvent | None) -> "EarningsAnalysis":
        if event is None:
            return cls(
                has_earnings=False,
                report_date=None,
                timing=None,
            )

        return cls(
            has_earnings=True,
            report_date=event.report_date,
            timing=event.timing,
        )