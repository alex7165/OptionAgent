from dataclasses import dataclass
from datetime import date

from app.analysis.earnings_status import EarningsStatus
from app.marketdata.models import EarningsEvent


@dataclass
class EarningsAnalysis:
    status: EarningsStatus
    report_date: date | None
    timing: str | None

    @classmethod
    def from_event(cls, event: EarningsEvent | None) -> "EarningsAnalysis":
        if event is None:
            return cls(
                status=EarningsStatus.NOT_AVAILABLE,
                report_date=None,
                timing=None,
            )

        return cls(
            status=EarningsStatus.AVAILABLE,
            report_date=event.report_date,
            timing=event.timing,
        )