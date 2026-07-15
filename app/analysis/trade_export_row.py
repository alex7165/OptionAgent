from dataclasses import dataclass


@dataclass(slots=True)
class TradeExportRow:
    aktie: str
    kurs: float
    strategie: str
    score: int | None = None
    short_put_prozent: float | None = None
    long_put_prozent: float | None = None
    short_call_prozent: float | None = None
    long_call_prozent: float | None = None
    short_put_strike: float | None = None
    long_put_strike: float | None = None
    short_call_strike: float | None = None
    long_call_strike: float | None = None
