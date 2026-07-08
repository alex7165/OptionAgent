from dataclasses import dataclass


@dataclass(slots=True)
class ExpectedMove:
    percent: float
    up_price: float
    down_price: float