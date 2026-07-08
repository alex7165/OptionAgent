from app.analysis.liquidity_rating import LiquidityRating
from app.marketdata.models import OptionQuote


class LiquidityAnalyzer:

    def analyze(
        self,
        quote: OptionQuote | None,
    ) -> LiquidityRating | None:
        if quote is None:
            return None

        return LiquidityRating(
            spread_percent=quote.bid_ask_spread_percent,
            open_interest=quote.open_interest,
            volume=quote.volume,
        )