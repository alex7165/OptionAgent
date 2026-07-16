from __future__ import annotations

from math import erf, exp, isfinite, log, sqrt

from app.marketdata.models import OptionQuote


class OptionDeltaResolver:
    """Resolve option delta from provider data or current option prices.

    Resolution order:
    1. finite provider delta;
    2. finite provider implied volatility;
    3. implied volatility solved from a finite current mid/last price.
    """

    def __init__(self, risk_free_rate: float = 0.045) -> None:
        self.risk_free_rate = risk_free_rate

    def resolve(
        self,
        quote: OptionQuote,
        *,
        underlying_price: float,
        days_to_expiration: int,
    ) -> float | None:
        provider_delta = self._finite_float(quote.delta)
        if provider_delta is not None:
            return provider_delta

        if underlying_price <= 0 or quote.strike <= 0:
            return None

        time_years = max(days_to_expiration, 1) / 365.0
        volatility = self._normalized_volatility(quote.implied_volatility)
        if volatility is None:
            option_price = self._option_price(quote)
            if option_price is not None:
                volatility = self._solve_implied_volatility(
                    option_type=quote.option_type,
                    option_price=option_price,
                    underlying_price=underlying_price,
                    strike=quote.strike,
                    time_years=time_years,
                )

        if volatility is None:
            return None

        return self._delta_from_volatility(
            option_type=quote.option_type,
            underlying_price=underlying_price,
            strike=quote.strike,
            time_years=time_years,
            volatility=volatility,
        )

    def _delta_from_volatility(
        self,
        *,
        option_type: str,
        underlying_price: float,
        strike: float,
        time_years: float,
        volatility: float,
    ) -> float:
        d1 = (
            log(underlying_price / strike)
            + (self.risk_free_rate + 0.5 * volatility**2) * time_years
        ) / (volatility * sqrt(time_years))
        call_delta = self._normal_cdf(d1)
        if option_type == "call":
            return call_delta
        if option_type == "put":
            return call_delta - 1.0
        raise ValueError(f"unsupported option_type: {option_type}")

    def _solve_implied_volatility(
        self,
        *,
        option_type: str,
        option_price: float,
        underlying_price: float,
        strike: float,
        time_years: float,
    ) -> float | None:
        discounted_strike = strike * exp(-self.risk_free_rate * time_years)
        if option_type == "call":
            lower_bound = max(0.0, underlying_price - discounted_strike)
            upper_bound = underlying_price
        elif option_type == "put":
            lower_bound = max(0.0, discounted_strike - underlying_price)
            upper_bound = discounted_strike
        else:
            raise ValueError(f"unsupported option_type: {option_type}")

        tolerance = 1e-6
        if option_price < lower_bound - tolerance or option_price > upper_bound + tolerance:
            return None

        # Prices at intrinsic value imply a delta very close to its expiry limit.
        if option_price <= lower_bound + 1e-5:
            return 1e-6

        low = 1e-6
        high = 5.0
        high_price = self._black_scholes_price(
            option_type=option_type,
            underlying_price=underlying_price,
            strike=strike,
            time_years=time_years,
            volatility=high,
        )
        if high_price < option_price:
            return None

        for _ in range(100):
            midpoint = (low + high) / 2.0
            model_price = self._black_scholes_price(
                option_type=option_type,
                underlying_price=underlying_price,
                strike=strike,
                time_years=time_years,
                volatility=midpoint,
            )
            if abs(model_price - option_price) < 1e-6:
                return midpoint
            if model_price < option_price:
                low = midpoint
            else:
                high = midpoint
        return (low + high) / 2.0

    def _black_scholes_price(
        self,
        *,
        option_type: str,
        underlying_price: float,
        strike: float,
        time_years: float,
        volatility: float,
    ) -> float:
        root_time = sqrt(time_years)
        d1 = (
            log(underlying_price / strike)
            + (self.risk_free_rate + 0.5 * volatility**2) * time_years
        ) / (volatility * root_time)
        d2 = d1 - volatility * root_time
        discounted_strike = strike * exp(-self.risk_free_rate * time_years)
        if option_type == "call":
            return (
                underlying_price * self._normal_cdf(d1)
                - discounted_strike * self._normal_cdf(d2)
            )
        if option_type == "put":
            return (
                discounted_strike * self._normal_cdf(-d2)
                - underlying_price * self._normal_cdf(-d1)
            )
        raise ValueError(f"unsupported option_type: {option_type}")

    @classmethod
    def _option_price(cls, quote: OptionQuote) -> float | None:
        bid = cls._finite_float(quote.bid)
        ask = cls._finite_float(quote.ask)
        if bid is not None and ask is not None and bid >= 0 and ask >= bid:
            mid = (bid + ask) / 2.0
            if mid > 0:
                return mid
        last = cls._finite_float(quote.last)
        if last is not None and last > 0:
            return last
        return None

    @classmethod
    def _normalized_volatility(cls, value: object) -> float | None:
        volatility = cls._finite_float(value)
        if volatility is None or volatility <= 0:
            return None
        if volatility > 3.0:
            volatility /= 100.0
        return volatility if volatility > 0 else None

    @staticmethod
    def _finite_float(value: object) -> float | None:
        if value is None:
            return None
        try:
            number = float(value)
        except (TypeError, ValueError):
            return None
        return number if isfinite(number) else None

    @staticmethod
    def _normal_cdf(value: float) -> float:
        return 0.5 * (1.0 + erf(value / sqrt(2.0)))
