from dataclasses import dataclass

from app.marketdata.models import OptionQuote


@dataclass(slots=True)
class StrikeSelection:
    put: OptionQuote | None
    call: OptionQuote | None
    put_target: float
    call_target: float
    long_put: OptionQuote | None = None
    long_call: OptionQuote | None = None

    @property
    def is_complete(self) -> bool:
        return self.put is not None and self.call is not None