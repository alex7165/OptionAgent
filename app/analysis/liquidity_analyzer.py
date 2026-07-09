from app.analysis.liquidity_rating import LiquidityRating
from app.analysis.option_data import OptionData


class LiquidityAnalyzer:

    def analyze(
        self,
        option_data: OptionData | None,
    ) -> LiquidityRating | None:
        if option_data is None:
            return None

        if option_data.call is None or option_data.put is None:
            return None

        call_spread = option_data.call.bid_ask_spread_percent
        put_spread = option_data.put.bid_ask_spread_percent

        spread_percent = max(
            call_spread,
            put_spread,
        )

        open_interest = min(
            option_data.call.open_interest,
            option_data.put.open_interest,
        )

        volume = min(
            option_data.call.volume,
            option_data.put.volume,
        )

        return LiquidityRating(
            spread_percent=spread_percent,
            open_interest=open_interest,
            volume=volume,
        )