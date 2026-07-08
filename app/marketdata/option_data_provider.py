from abc import ABC, abstractmethod

from app.analysis.option_data import OptionData


class OptionDataProvider(ABC):

    @abstractmethod
    def get_option_data(self, symbol: str) -> OptionData:
        pass