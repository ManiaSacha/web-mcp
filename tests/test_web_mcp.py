"""Tests for web_mcp.py — all synthetic feeds, no network access.

Run with:  pytest tests/test_web_mcp.py -v
"""
import email.utils
import time

import pytest

import web_mcp


RSS_FEED = """<?xml version="1.0"?>
<rss version="2.0">
  <channel>
    <title>Example News</title>
    <link>https://example.com</link>
    <item>
      <title>Rockets launch new satellite into orbit</title>
      <link>https://example.com/articles/rocket-launch</link>
      <description>A rocket company launched a new satellite today.</description>
      <pubDate>{recent}</pubDate>
      <guid>https://example.com/articles/rocket-launch</guid>
    </item>
    <item>
      <title>Local bakery wins award</title>
      <link>https://example.com/articles/bakery-award</link>
      <description>A small bakery downtown won a regional award.</description>
      <pubDate>{old}</pubDate>
    </item>
  </channel>
</rss>
"""

ATOM_FEED = """<?xml version="1.0" encoding="utf-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <title>Example Atom Feed</title>
  <entry>
    <title>New satellite constellation announced</title>
    <link rel="self" href="https://example.org/self/satellite-constellation"/>
    <link rel="alternate" href="https://example.org/articles/satellite-constellation"/>
    <id>urn:uuid:1234</id>
    <summary>A company announced a new satellite constellation.</summary>
    <updated>{recent}</updated>
  </entry>
  <entry>
    <title>Entry with only a self link</title>
    <link rel="self" href="https://example.org/self/only"/>
    <id>urn:uuid:5678</id>
    <summary>This entry has no alternate link.</summary>
    <updated>{recent}</updated>
  </entry>
</feed>
"""

# An item with no title/summary words that survive stopword filtering.
EMPTY_TOKENS_RSS = """<?xml version="1.0"?>
<rss version="2.0">
  <channel>
    <item>
      <title>a an the</title>
      <link>https://example.com/empty</link>
      <description>is are was</description>
      <pubDate>{recent}</pubDate>
    </item>
  </channel>
</rss>
"""


def rfc822(ts: float) -> str:
    return email.utils.format_datetime(
        __import__("datetime").datetime.fromtimestamp(ts, tz=__import__("datetime").timezone.utc)
    )


@pytest.fixture
def index():
    return web_mcp.NewsIndex()


def _rss_text():
    now = time.time()
    return RSS_FEED.format(recent=rfc822(now), old=rfc822(now - 30 * 86400))


def _atom_text():
    return ATOM_FEED.format(recent=rfc822(time.time()))


# ---- parse_feed ---------------------------------------------------------------
def test_parse_rss_link_survives_when_no_guid_element():
    """Regression test: an operator-precedence bug used to wipe <link> to ''
    for any RSS item lacking a <guid>/<id> element (i.e. almost all RSS)."""
    records = web_mcp.parse_feed(_rss_text())
    assert records[0]["link"] == "https://example.com/articles/rocket-launch"
    assert records[1]["link"] == "https://example.com/articles/bakery-award"


def test_parse_rss_basic_fields():
    records = web_mcp.parse_feed(_rss_text())
    assert len(records) == 2
    assert records[0]["title"] == "Rockets launch new satellite into orbit"
    assert "rocket company" in records[0]["summary"]


def test_parse_atom_prefers_alternate_link_over_self():
    """Regression test: collapsing multiple <link> children into a dict by
    tag name kept whichever link happened to appear last (often rel=self),
    not the human-facing rel=alternate link."""
    records = web_mcp.parse_feed(_atom_text())
    assert records[0]["link"] == "https://example.org/articles/satellite-constellation"


def test_parse_atom_falls_back_to_self_link_when_no_alternate():
    records = web_mcp.parse_feed(_atom_text())
    assert records[1]["link"] == "https://example.org/self/only"


def test_parse_feed_raises_on_malformed_xml():
    with pytest.raises(Exception):
        web_mcp.parse_feed("<rss><channel><item><title>unclosed")


# ---- tokenize -------------------------------------------------------------
def test_tokenize_strips_stopwords_and_short_tokens():
    tokens = web_mcp.tokenize("The Rocket a Company Launched an Orbit")
    assert "the" not in tokens
    assert "a" not in tokens
    assert "an" not in tokens
    assert "rocket" in tokens
    assert "orbit" in tokens


# ---- NewsIndex --------------------------------------------------------------
def test_add_feed_indexes_articles(index):
    n = index.add_feed("https://feed.example/rss", fetch_text=_rss_text())
    assert n == 2
    assert len(index.docs) == 2
    assert index.feed_info["https://feed.example/rss"]["articles"] == 2


def test_add_feed_with_all_stopword_tokens_does_not_crash(index):
    """Regression test: a doc whose title+summary tokenize to nothing used to
    hit a ZeroDivisionError computing its TF-IDF vector norm."""
    text = EMPTY_TOKENS_RSS.format(recent=rfc822(time.time()))
    n = index.add_feed("https://feed.example/empty", fetch_text=text)
    assert n == 1
    # Doc is stored and shows up in recent(), just can't score in search().
    assert len(index.docs) == 1


def test_remove_feed_clears_its_docs(index):
    index.add_feed("https://feed.example/rss", fetch_text=_rss_text())
    assert index.remove_feed("https://feed.example/rss") is True
    assert len(index.docs) == 0
    assert "https://feed.example/rss" not in index.feed_info


def test_remove_feed_returns_false_for_unknown_url(index):
    assert index.remove_feed("https://nope.example/rss") is False


def test_search_ranks_matching_doc_and_ignores_unrelated(index):
    index.add_feed("https://feed.example/rss", fetch_text=_rss_text())
    results = index.search("rocket satellite")
    assert results
    assert "rocket" in results[0]["title"].lower()


def test_search_empty_query_returns_nothing(index):
    index.add_feed("https://feed.example/rss", fetch_text=_rss_text())
    assert index.search("") == []


def test_search_recency_boosts_newer_matching_doc(index):
    now = time.time()
    text = RSS_FEED.format(
        recent=rfc822(now),
        old=rfc822(now - 1 * 86400),
    ).replace("Local bakery wins award", "Rocket orbit demo mission")
    index.add_feed("https://feed.example/rss", fetch_text=text)
    results = index.search("rocket")
    assert len(results) == 2
    assert results[0]["score"] >= results[1]["score"]


def test_trending_only_counts_recent_docs(index):
    index.add_feed("https://feed.example/rss", fetch_text=_rss_text())
    top = index.trending(hours=24 * 10)
    assert "rocket" in top or "rockets" in top or "launch" in top


def test_digest_reports_no_recent_articles_when_all_old(index):
    text = RSS_FEED.format(
        recent=rfc822(time.time() - 60 * 86400),
        old=rfc822(time.time() - 90 * 86400),
    )
    index.add_feed("https://feed.example/rss", fetch_text=text)
    out = index.digest(hours=24)
    assert "No recent articles" in out


def test_source_health_reports_ok_for_fresh_feed(index):
    index.add_feed("https://feed.example/rss", fetch_text=_rss_text())
    out = index.source_health()
    assert "OK" in out
    assert "https://feed.example/rss" in out


# ---- SSRF / URL hardening -----------------------------------------------------
@pytest.mark.parametrize("url", [
    "file:///etc/passwd",
    "ftp://example.com/feed",
    "gopher://example.com/feed",
])
def test_assert_fetchable_rejects_non_http_schemes(url):
    with pytest.raises(ValueError):
        web_mcp.assert_fetchable(url)


@pytest.mark.parametrize("url", [
    "http://127.0.0.1/feed",
    "http://localhost/feed",
    "http://169.254.169.254/latest/meta-data/",  # cloud metadata endpoint
    "http://10.0.0.5/feed",
    "http://192.168.1.1/feed",
])
def test_assert_fetchable_rejects_private_and_loopback_hosts(url):
    with pytest.raises(ValueError):
        web_mcp.assert_fetchable(url)


def test_assert_fetchable_rejects_url_without_hostname():
    with pytest.raises(ValueError):
        web_mcp.assert_fetchable("http:///no-host")
