from app.planner.symbol_extractor import SymbolExtractor


def test_extract_symbol():
    extractor = SymbolExtractor()

    assert extractor.extract("Was ist der Kurs von NVDA?") == "NVDA"
    assert extractor.extract("Kurs AAPL") == "AAPL"
    assert extractor.extract("Price TSLA") == "TSLA"
    assert extractor.extract("Hallo Welt") is None