from app.analysis.option_data import OptionData
from app.marketdata.option_data_provider import OptionDataProvider


class DummyOptionDataProvider(OptionDataProvider):

    def get_option_data(self, symbol: str) -> OptionData:
        return OptionData()