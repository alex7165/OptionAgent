from datetime import date

from app.analysis.expiration_chain_analyzer import ExpirationChainAnalyzer
from app.marketdata.models import ExpirationChain, OptionQuote


def test_expiration_chain_analyzer_filters_calls_and_puts():
    chain = ExpirationChain(
        symbol="NVDA",
        expiration=date(2026, 7, 10),
        quotes=[
            OptionQuote(
                symbol="NVDA",
                expiration=date(2026, 7, 10),
                strike=200,
                option_type="call",
            ),
            OptionQuote(
                symbol="NVDA",
                expiration=date(2026, 7, 10),
                strike=180,
                option_type="put",
            ),
        ],
    )

    analyzer = ExpirationChainAnalyzer()

    assert len(analyzer.get_calls(chain)) == 1
    assert len(analyzer.get_puts(chain)) == 1


def test_expiration_chain_analyzer_finds_nearest_strike():
    chain = ExpirationChain(
        symbol="NVDA",
        expiration=date(2026, 7, 10),
        quotes=[
            OptionQuote(
                symbol="NVDA",
                expiration=date(2026, 7, 10),
                strike=195,
                option_type="call",
            ),
            OptionQuote(
                symbol="NVDA",
                expiration=date(2026, 7, 10),
                strike=200,
                option_type="call",
            ),
        ],
    )

    analyzer = ExpirationChainAnalyzer()
    quote = analyzer.find_nearest_strike(
        chain,
        target_strike=198,
        option_type="call",
    )

    assert quote.strike == 200

def test_expiration_chain_analyzer_finds_call_above():
    chain = ExpirationChain(
        symbol="NVDA",
        expiration=date(2026, 7, 10),
        quotes=[
            OptionQuote(
                symbol="NVDA",
                expiration=date(2026, 7, 10),
                strike=195,
                option_type="call",
            ),
            OptionQuote(
                symbol="NVDA",
                expiration=date(2026, 7, 10),
                strike=200,
                option_type="call",
            ),
        ],
    )

    analyzer = ExpirationChainAnalyzer()
    quote = analyzer.find_call_above(chain, 198)

    assert quote.strike == 200


def test_expiration_chain_analyzer_finds_put_below():
    chain = ExpirationChain(
        symbol="NVDA",
        expiration=date(2026, 7, 10),
        quotes=[
            OptionQuote(
                symbol="NVDA",
                expiration=date(2026, 7, 10),
                strike=180,
                option_type="put",
            ),
            OptionQuote(
                symbol="NVDA",
                expiration=date(2026, 7, 10),
                strike=185,
                option_type="put",
            ),
        ],
    )

    analyzer = ExpirationChainAnalyzer()
    quote = analyzer.find_put_below(chain, 183)

    assert quote.strike == 180

def test_expiration_chain_analyzer_finds_atm_straddle():
    chain = ExpirationChain(
        symbol="NVDA",
        expiration=date(2026, 7, 10),
        quotes=[
            OptionQuote(
                symbol="NVDA",
                expiration=date(2026, 7, 10),
                strike=195,
                option_type="call",
            ),
            OptionQuote(
                symbol="NVDA",
                expiration=date(2026, 7, 10),
                strike=195,
                option_type="put",
            ),
            OptionQuote(
                symbol="NVDA",
                expiration=date(2026, 7, 10),
                strike=200,
                option_type="call",
            ),
            OptionQuote(
                symbol="NVDA",
                expiration=date(2026, 7, 10),
                strike=200,
                option_type="put",
            ),
        ],
    )

    analyzer = ExpirationChainAnalyzer()
    call, put = analyzer.find_atm_straddle(chain, 198)

    assert call.strike == 200
    assert put.strike == 200