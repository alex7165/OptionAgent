from datetime import date

import pytest

from app.analysis.liquidity_optimizer import LiquidityOptimizer
from app.analysis.strike_selection import StrikeSelection
from app.analysis.strategy import Strategy
from app.marketdata.models import ExpirationChain, OptionQuote


EXPIRATION = date(2026, 7, 17)


def quote(
    strike: float,
    option_type: str,
    *,
    bid: float = 1.00,
    ask: float = 1.08,
    open_interest: int = 600,
    volume: int = 60,
) -> OptionQuote:
    return OptionQuote(
        symbol="C",
        expiration=EXPIRATION,
        strike=strike,
        option_type=option_type,
        bid=bid,
        ask=ask,
        open_interest=open_interest,
        volume=volume,
    )


def selection(
    put: OptionQuote,
    call: OptionQuote,
    *,
    long_put: OptionQuote | None = None,
    long_call: OptionQuote | None = None,
    strategy: Strategy = Strategy.IRON_CONDOR,
) -> StrikeSelection:
    return StrikeSelection(
        put=put,
        call=call,
        put_target=132.5,
        call_target=146.0,
        long_put=long_put,
        long_call=long_call,
        strategy=strategy,
    )


def test_never_moves_call_inward_even_with_much_higher_open_interest():
    call_145 = quote(145, "call", open_interest=18_206)
    call_146 = quote(146, "call", open_interest=620)
    call_147 = quote(147, "call", open_interest=300)
    put_132 = quote(132, "put")
    chain = ExpirationChain(
        symbol="C",
        expiration=EXPIRATION,
        quotes=[put_132, call_145, call_146, call_147],
    )

    result = LiquidityOptimizer().optimize(
        selection(put_132, call_146),
        chain,
    )

    assert result.call is call_146


def test_moves_call_outward_for_clear_liquidity_improvement():
    call_145 = quote(145, "call", open_interest=20_000)
    call_146 = quote(146, "call", open_interest=100, volume=5)
    call_147 = quote(147, "call", open_interest=2_000, volume=100)
    put_132 = quote(132, "put")
    chain = ExpirationChain(
        symbol="C",
        expiration=EXPIRATION,
        quotes=[put_132, call_145, call_146, call_147],
    )

    result = LiquidityOptimizer().optimize(
        selection(put_132, call_146),
        chain,
    )

    assert result.call is call_147


def test_never_moves_put_inward_even_for_clear_liquidity_improvement():
    put_131 = quote(131, "put", open_interest=300)
    put_132 = quote(132, "put", open_interest=100, volume=5)
    put_133 = quote(133, "put", open_interest=20_000, volume=100)
    call_146 = quote(146, "call")
    chain = ExpirationChain(
        symbol="C",
        expiration=EXPIRATION,
        quotes=[put_131, put_132, put_133, call_146],
    )

    result = LiquidityOptimizer().optimize(
        selection(put_132, call_146),
        chain,
    )

    assert result.put is not put_133
    assert result.put.strike <= put_132.strike


def test_moves_put_outward_for_clear_liquidity_improvement():
    put_131 = quote(131, "put", open_interest=2_000, volume=100)
    put_132 = quote(132, "put", open_interest=100, volume=5)
    put_133 = quote(133, "put", open_interest=20_000, volume=100)
    call_146 = quote(146, "call")
    chain = ExpirationChain(
        symbol="C",
        expiration=EXPIRATION,
        quotes=[put_131, put_132, put_133, call_146],
    )

    result = LiquidityOptimizer().optimize(
        selection(put_132, call_146),
        chain,
    )

    assert result.put is put_131


def test_keeps_current_strike_when_outward_improvement_is_small():
    call_146 = quote(146, "call", open_interest=600)
    call_147 = quote(147, "call", open_interest=1_200)
    put_132 = quote(132, "put")
    chain = ExpirationChain(
        symbol="C",
        expiration=EXPIRATION,
        quotes=[put_132, call_146, call_147],
    )

    result = LiquidityOptimizer().optimize(
        selection(put_132, call_146),
        chain,
    )

    assert result.call is call_146


def test_checks_two_outward_listed_strikes():
    call_146 = quote(146, "call", open_interest=600)
    call_147 = quote(147, "call", open_interest=500)
    call_148 = quote(148, "call", open_interest=20_000)
    put_132 = quote(132, "put")
    chain = ExpirationChain(
        symbol="C",
        expiration=EXPIRATION,
        quotes=[put_132, call_146, call_147, call_148],
    )

    result = LiquidityOptimizer().optimize(
        selection(put_132, call_146),
        chain,
    )

    assert result.call is call_148


def test_does_not_check_beyond_two_outward_listed_strikes():
    call_146 = quote(146, "call", open_interest=600)
    call_147 = quote(147, "call", open_interest=500)
    call_148 = quote(148, "call", open_interest=500)
    call_149 = quote(149, "call", open_interest=20_000)
    put_132 = quote(132, "put")
    chain = ExpirationChain(
        symbol="C",
        expiration=EXPIRATION,
        quotes=[put_132, call_146, call_147, call_148, call_149],
    )

    result = LiquidityOptimizer().optimize(
        selection(put_132, call_146),
        chain,
    )

    assert result.call is call_146


def test_prefers_nearer_candidate_when_liquidity_is_identical():
    call_146 = quote(146, "call", open_interest=100, volume=5)
    call_147 = quote(147, "call", open_interest=2_000, volume=100)
    call_148 = quote(148, "call", open_interest=2_000, volume=100)
    put_132 = quote(132, "put")
    chain = ExpirationChain(
        symbol="C",
        expiration=EXPIRATION,
        quotes=[put_132, call_146, call_147, call_148],
    )

    result = LiquidityOptimizer().optimize(
        selection(put_132, call_146),
        chain,
    )

    assert result.call is call_147


def test_reselects_long_legs_after_outward_short_strikes_change():
    long_put_125 = quote(125, "put")
    long_put_126 = quote(126, "put")
    long_put_127 = quote(127, "put")
    put_131 = quote(131, "put", open_interest=10_000)
    put_132 = quote(132, "put", open_interest=100, volume=5)
    call_146 = quote(146, "call", open_interest=100, volume=5)
    call_147 = quote(147, "call", open_interest=10_000)
    long_call_151 = quote(151, "call")
    long_call_152 = quote(152, "call")
    chain = ExpirationChain(
        symbol="C",
        expiration=EXPIRATION,
        quotes=[
            long_put_125,
            long_put_126,
            long_put_127,
            put_131,
            put_132,
            call_146,
            call_147,
            long_call_151,
            long_call_152,
        ],
    )

    result = LiquidityOptimizer().optimize(
        selection(
            put_132,
            call_146,
            long_put=long_put_127,
            long_call=long_call_151,
        ),
        chain,
    )

    assert result.put is put_131
    assert result.long_put is long_put_126
    assert result.call is call_147
    assert result.long_call is long_call_152


def test_short_strangle_does_not_add_long_legs():
    put_131 = quote(131, "put", open_interest=10_000)
    put_132 = quote(132, "put", open_interest=100, volume=5)
    call_146 = quote(146, "call", open_interest=100, volume=5)
    call_147 = quote(147, "call", open_interest=10_000)
    chain = ExpirationChain(
        symbol="C",
        expiration=EXPIRATION,
        quotes=[put_131, put_132, call_146, call_147],
    )

    result = LiquidityOptimizer().optimize(
        selection(
            put_132,
            call_146,
            strategy=Strategy.SHORT_STRANGLE,
        ),
        chain,
    )

    assert result.put is put_131
    assert result.call is call_147
    assert result.long_put is None
    assert result.long_call is None


def test_rejects_equal_or_crossed_short_strikes():
    put_130 = quote(130, "put")
    call_130 = quote(130, "call")
    chain = ExpirationChain(
        symbol="C",
        expiration=EXPIRATION,
        quotes=[put_130, call_130],
    )

    with pytest.raises(
        ValueError,
        match="short put strike must be below short call strike",
    ):
        LiquidityOptimizer().optimize(
            selection(put_130, call_130),
            chain,
        )


def test_accepts_underlying_price_for_strategy_selector_compatibility():
    put_90 = quote(90, "put", open_interest=100)
    put_95 = quote(95, "put", open_interest=100)
    call_105 = quote(105, "call", open_interest=100)
    call_110 = quote(110, "call", open_interest=100)
    chain = ExpirationChain(
        symbol="C",
        expiration=EXPIRATION,
        quotes=[put_90, put_95, call_105, call_110],
    )
    current_selection = selection(
        put_95,
        call_105,
        strategy=Strategy.SHORT_STRANGLE,
    )

    result = LiquidityOptimizer().optimize(
        selection=current_selection,
        chain=chain,
        underlying_price=100.0,
    )

    assert result is current_selection
