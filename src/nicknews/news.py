import html
import feedparser
from urllib.parse import quote

TECH_FEEDS = [
    "https://it.chosun.com/rss/allArticle.xml",
    "https://feeds.feedburner.com/zdkorea",
]

ECONOMY_FEEDS = [
    "https://www.yna.co.kr/rss/economy.xml",
    "https://www.mk.co.kr/rss/30000001/",
]


def fetch_rss(feed_urls, count=5):
    articles = []
    for url in feed_urls:
        feed = feedparser.parse(url)
        for entry in feed.entries:
            articles.append({
                "title": entry.get("title", ""),
                "url": entry.get("link", ""),
            })
        if len(articles) >= count:
            break
    return articles[:count]


def fetch_keyword_news(keyword, count=3):
    url = f"https://news.google.com/rss/search?q={quote(keyword)}&hl=ko&gl=KR&ceid=KR:ko"
    feed = feedparser.parse(url)
    return [
        {"title": e.get("title", "").split(" - ")[0].strip(), "url": e.get("link", "")}
        for e in feed.entries[:count]
    ]


def format_section(articles, header):
    lines = [header]
    for i, article in enumerate(articles, 1):
        title = html.escape(article["title"].strip())
        url = article["url"]
        if not url.startswith(("http://", "https://")):
            url = "#"
        lines.append(f'{i}. <a href="{url}">{title}</a>')
    return "\n".join(lines)
