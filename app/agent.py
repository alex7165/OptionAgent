from app.marketdata.yahoo_provider import YahooPriceProvider
from app.marketdata.service import MarketDataService
from app.planner.planner import Planner


class OptionAgent:

    def __init__(self):
        price_provider = YahooPriceProvider()
        market_data = MarketDataService(price_provider)

        self.planner = Planner(market_data=market_data)

    def run(self):

        print("OptionAgent gestartet")
        print()

        task = input("Aufgabe: ")

        result = self.planner.execute(task)

        print()
        print("Ergebnis:")
        print(result)