from unittest.mock import MagicMock, patch

from nicknews.news import fetch_keyword_news, fetch_rss, format_section


def _make_entry(title, link):
    entry = MagicMock()
    entry.get = lambda k, d="": {"title": title, "link": link}.get(k, d)
    return entry


def _make_feed(*entries):
    feed = MagicMock()
    feed.entries = list(entries)
    return feed


class TestFetchRss:
    def test_returns_articles_from_feed(self):
        with patch("nicknews.news.feedparser.parse", return_value=_make_feed(
            _make_entry("제목1", "https://example.com/1")
        )):
            result = fetch_rss(["https://feed.example.com"])
        assert result == [{"title": "제목1", "url": "https://example.com/1"}]

    def test_truncates_to_count(self):
        entries = [_make_entry(f"제목{i}", f"https://example.com/{i}") for i in range(10)]
        with patch("nicknews.news.feedparser.parse", return_value=_make_feed(*entries)):
            result = fetch_rss(["https://feed.example.com"], count=3)
        assert len(result) == 3

    def test_skips_second_feed_when_first_is_sufficient(self):
        entries = [_make_entry(f"제목{i}", f"https://example.com/{i}") for i in range(5)]
        with patch("nicknews.news.feedparser.parse", return_value=_make_feed(*entries)) as mock_parse:
            fetch_rss(["https://feed1.example.com", "https://feed2.example.com"], count=5)
        assert mock_parse.call_count == 1

    def test_parses_second_feed_when_first_is_insufficient(self):
        two_entries = [_make_entry(f"제목{i}", f"https://example.com/{i}") for i in range(2)]
        three_entries = [_make_entry(f"추가{i}", f"https://extra.com/{i}") for i in range(3)]
        with patch("nicknews.news.feedparser.parse", side_effect=[
            _make_feed(*two_entries),
            _make_feed(*three_entries),
        ]) as mock_parse:
            result = fetch_rss(["https://feed1.example.com", "https://feed2.example.com"], count=5)
        assert mock_parse.call_count == 2
        assert len(result) == 5


class TestFetchKeywordNews:
    def test_uses_google_news_url(self):
        with patch("nicknews.news.feedparser.parse", return_value=_make_feed()) as mock_parse:
            fetch_keyword_news("삼성전자")
        url = mock_parse.call_args[0][0]
        assert "news.google.com" in url

    def test_url_encodes_keyword(self):
        with patch("nicknews.news.feedparser.parse", return_value=_make_feed()) as mock_parse:
            fetch_keyword_news("삼성전자")
        url = mock_parse.call_args[0][0]
        assert "%EC%82%BC%EC%84%B1%EC%A0%84%EC%9E%90" in url

    def test_strips_source_name_from_title(self):
        with patch("nicknews.news.feedparser.parse", return_value=_make_feed(
            _make_entry("삼성전자 실적 발표 - 조선일보", "https://example.com/1")
        )):
            result = fetch_keyword_news("삼성전자")
        assert result[0]["title"] == "삼성전자 실적 발표"

    def test_truncates_to_count(self):
        entries = [_make_entry(f"제목{i} - 출처", f"https://example.com/{i}") for i in range(10)]
        with patch("nicknews.news.feedparser.parse", return_value=_make_feed(*entries)):
            result = fetch_keyword_news("삼성전자", count=2)
        assert len(result) == 2


class TestFormatSection:
    def test_header_is_first_line(self):
        result = format_section([], "💻 <b>기술</b>")
        assert result.startswith("💻 <b>기술</b>")

    def test_includes_numbered_article_links(self):
        articles = [{"title": "제목", "url": "https://example.com"}]
        result = format_section(articles, "헤더")
        assert '1. <a href="https://example.com">제목</a>' in result

    def test_escapes_html_in_title(self):
        articles = [{"title": "<script>xss</script>", "url": "https://example.com"}]
        result = format_section(articles, "헤더")
        assert "<script>" not in result
        assert "&lt;script&gt;" in result

    def test_replaces_invalid_url_with_hash(self):
        articles = [{"title": "제목", "url": "javascript:alert(1)"}]
        result = format_section(articles, "헤더")
        assert 'href="#"' in result

    def test_keeps_http_url(self):
        articles = [{"title": "제목", "url": "http://example.com"}]
        result = format_section(articles, "헤더")
        assert 'href="http://example.com"' in result
