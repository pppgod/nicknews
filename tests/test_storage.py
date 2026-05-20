import json

import pytest

from nicknews.storage import load_stocks, save_stocks


@pytest.fixture
def stocks_file(tmp_path, monkeypatch):
    path = tmp_path / "stocks.json"
    monkeypatch.setattr("nicknews.storage.STOCKS_FILE", str(path))
    return path


class TestLoadStocks:
    def test_returns_defaults_when_file_missing(self, stocks_file):
        result = load_stocks()
        assert result == {"kr": [], "us": [], "keywords": []}

    def test_returns_data_from_file(self, stocks_file):
        data = {"kr": [{"name": "삼성전자", "ticker": "005930.KS"}], "us": [], "keywords": ["AI"]}
        stocks_file.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        assert load_stocks() == data

    def test_adds_empty_keywords_when_missing(self, stocks_file):
        stocks_file.write_text(json.dumps({"kr": [], "us": []}), encoding="utf-8")
        result = load_stocks()
        assert result["keywords"] == []


class TestSaveStocks:
    def test_saved_data_can_be_read_back(self, stocks_file):
        data = {"kr": [{"name": "삼성전자", "ticker": "005930.KS"}], "us": [], "keywords": []}
        save_stocks(data)
        result = json.loads(stocks_file.read_text(encoding="utf-8"))
        assert result == data

    def test_korean_unicode_is_preserved(self, stocks_file):
        data = {"kr": [], "us": [], "keywords": ["삼성전자"]}
        save_stocks(data)
        raw = stocks_file.read_text(encoding="utf-8")
        assert "삼성전자" in raw
