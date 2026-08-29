import json

import pytest

from nicknews.storage import (
    add_allowed_id, all_user_ids, load_allowed_ids,
    load_user_stocks, remove_allowed_id, save_user_stocks,
)


@pytest.fixture
def stocks_file(tmp_path, monkeypatch):
    path = tmp_path / "stocks.json"
    monkeypatch.setattr("nicknews.storage.STOCKS_FILE", str(path))
    return path


@pytest.fixture
def owner_env(monkeypatch):
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "111")


class TestLoadUserStocks:
    def test_returns_defaults_when_file_missing(self, stocks_file):
        result = load_user_stocks("111")
        assert result == {"kr": [], "us": [], "keywords": [], "flights": []}

    def test_returns_user_data(self, stocks_file):
        data = {"111": {"kr": [{"name": "삼성전자", "ticker": "005930.KS"}], "us": [], "keywords": ["AI"], "flights": []}}
        stocks_file.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        assert load_user_stocks("111") == data["111"]

    def test_different_users_are_isolated(self, stocks_file):
        data = {
            "111": {"kr": [{"name": "삼성전자", "ticker": "005930.KS"}], "us": [], "keywords": []},
            "222": {"kr": [], "us": [{"name": "Apple Inc.", "ticker": "AAPL"}], "keywords": []},
        }
        stocks_file.write_text(json.dumps(data), encoding="utf-8")
        assert load_user_stocks("111")["kr"][0]["ticker"] == "005930.KS"
        assert load_user_stocks("222")["us"][0]["ticker"] == "AAPL"

    def test_migrates_old_flat_format(self, stocks_file, owner_env):
        old = {"kr": [{"name": "삼성전자", "ticker": "005930.KS"}], "us": [], "keywords": []}
        stocks_file.write_text(json.dumps(old), encoding="utf-8")
        result = load_user_stocks("111")
        assert result["kr"][0]["ticker"] == "005930.KS"
        migrated = json.loads(stocks_file.read_text(encoding="utf-8"))
        assert "111" in migrated

    def test_adds_empty_keywords_when_missing(self, stocks_file):
        stocks_file.write_text(json.dumps({"111": {"kr": [], "us": []}}), encoding="utf-8")
        result = load_user_stocks("111")
        assert result["keywords"] == []

    def test_adds_empty_flights_when_missing(self, stocks_file):
        stocks_file.write_text(json.dumps({"111": {"kr": [], "us": [], "keywords": []}}), encoding="utf-8")
        result = load_user_stocks("111")
        assert result["flights"] == []


class TestSaveUserStocks:
    def test_saved_data_can_be_read_back(self, stocks_file):
        data = {"kr": [{"name": "삼성전자", "ticker": "005930.KS"}], "us": [], "keywords": [], "flights": []}
        save_user_stocks("111", data)
        assert load_user_stocks("111") == data

    def test_saving_one_user_does_not_affect_another(self, stocks_file):
        save_user_stocks("111", {"kr": [], "us": [], "keywords": ["AI"]})
        save_user_stocks("222", {"kr": [], "us": [], "keywords": ["반도체"]})
        assert load_user_stocks("111")["keywords"] == ["AI"]
        assert load_user_stocks("222")["keywords"] == ["반도체"]

    def test_korean_unicode_is_preserved(self, stocks_file):
        data = {"kr": [], "us": [], "keywords": ["삼성전자"]}
        save_user_stocks("111", data)
        raw = stocks_file.read_text(encoding="utf-8")
        assert "삼성전자" in raw


class TestAllUserIds:
    def test_includes_owner_even_if_no_data(self, stocks_file, owner_env):
        assert "111" in all_user_ids()

    def test_includes_users_with_data(self, stocks_file, owner_env):
        save_user_stocks("222", {"kr": [], "us": [], "keywords": []})
        ids = all_user_ids()
        assert "111" in ids
        assert "222" in ids

    def test_does_not_include_internal_keys(self, stocks_file, owner_env):
        add_allowed_id("333")
        ids = all_user_ids()
        assert "_allowed" not in ids


class TestAllowedIds:
    def test_empty_by_default(self, stocks_file):
        assert load_allowed_ids() == set()

    def test_add_allowed_id(self, stocks_file):
        add_allowed_id("222")
        assert "222" in load_allowed_ids()

    def test_add_multiple_ids(self, stocks_file):
        add_allowed_id("222")
        add_allowed_id("333")
        allowed = load_allowed_ids()
        assert "222" in allowed
        assert "333" in allowed

    def test_remove_allowed_id(self, stocks_file):
        add_allowed_id("222")
        remove_allowed_id("222")
        assert "222" not in load_allowed_ids()

    def test_remove_nonexistent_id_is_safe(self, stocks_file):
        remove_allowed_id("999")
        assert load_allowed_ids() == set()
