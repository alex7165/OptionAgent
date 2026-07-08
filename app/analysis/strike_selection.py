from dataclasses import dataclass

from app.marketdata.models import OptionQuote


@dataclass(slots=True)
class StrikeSelection:
    put: OptionQuote | None
    call: OptionQuote | None
    put_target: float
    call_target: float