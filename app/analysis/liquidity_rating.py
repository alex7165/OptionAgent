from dataclasses import dataclass


@dataclass(slots=True)
class LiquidityRating:
    spread_percent: float | None
    open_interest: int | None
    volume: int | None

    @property
    def has_good_spread(self) -> bool:
        return (
            self.spread_percent is not None
            and self.spread_percent <= 0.10
        )

    @property
    def has_good_open_interest(self) -> bool:
        return (
            self.open_interest is not None
            and self.open_interest >= 500
        )

    @property
    def has_good_volume(self) -> bool:
        return (
            self.volume is not None
            and self.volume >= 50
        )

    @property
    def is_liquid(self) -> bool:
        return (
            self.has_good_spread
            and self.has_good_open_interest
            and self.has_good_volume
        )