"""Tests for web_mcp.py — all synthetic feeds, no network access.

Run with:  pytest tests/test_web_mcp.py -v
"""
import email.utils
import ipaddress
import socket
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


# ---- fetch-time pinning and redirect validation -------------------------------
PUBLIC_IP = "93.184.216.34"


def fake_getaddrinfo(host, port, *args, **kwargs):
    """Resolve literal IPs to themselves and any name to a public address.

    Keeps these tests entirely offline while still exercising the real
    classification logic in assert_fetchable.
    """
    try:
        ipaddress.ip_address(host)
        resolved = host
    except ValueError:
        resolved = PUBLIC_IP
    return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", (resolved, port))]


class FakeResponse:
    def __init__(self, status=200, headers=None, body=b"", reason="OK"):
        self.status = status
        self.reason = reason
        self._headers = headers or {}
        self._body = body

    def getheader(self, name, default=None):
        return self._headers.get(name, default)

    def read(self, amt=-1):
        return self._body if amt < 0 else self._body[:amt]


class FakeConn:
    def __init__(self, response):
        self._response = response
        self.closed = False

    def request(self, method, target, headers=None):
        self.method, self.target, self.headers = method, target, headers

    def getresponse(self):
        return self._response

    def close(self):
        self.closed = True


@pytest.fixture
def offline(monkeypatch):
    monkeypatch.setattr(socket, "getaddrinfo", fake_getaddrinfo)


def scripted_opener(monkeypatch, responses):
    """Replace open_pinned with a scripted sequence, recording each hop."""
    hops = []
    queue = list(responses)

    def _open(parsed, ip, timeout):
        hops.append((parsed.geturl(), ip))
        return FakeConn(queue.pop(0))

    monkeypatch.setattr(web_mcp, "open_pinned", _open)
    return hops


@pytest.mark.parametrize("addr", [
    "127.0.0.1", "10.0.0.5", "192.168.1.1", "172.16.0.1", "169.254.169.254",
    "::1", "0.0.0.0", "224.0.0.1",
    "::ffff:127.0.0.1", "::ffff:169.254.169.254", "::ffff:10.0.0.1",
])
def test_is_blocked_ip_rejects_non_public(addr):
    assert web_mcp.is_blocked_ip(ipaddress.ip_address(addr)) is True


@pytest.mark.parametrize("addr", ["93.184.216.34", "8.8.8.8", "2606:2800:220:1::1", "::ffff:8.8.8.8"])
def test_is_blocked_ip_allows_public(addr):
    assert web_mcp.is_blocked_ip(ipaddress.ip_address(addr)) is False


def test_assert_fetchable_returns_pinned_ip(offline):
    parsed, ip = web_mcp.assert_fetchable("https://feeds.example/rss")
    assert parsed.hostname == "feeds.example"
    assert ip == PUBLIC_IP


def test_assert_fetchable_rejects_when_any_resolved_address_is_private(monkeypatch):
    """A host answering with both a public and a private record must be
    refused outright — otherwise a retry could land on the private one."""
    def mixed(host, port, *args, **kwargs):
        return [
            (socket.AF_INET, socket.SOCK_STREAM, 6, "", (PUBLIC_IP, port)),
            (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("127.0.0.1", port)),
        ]
    monkeypatch.setattr(socket, "getaddrinfo", mixed)
    with pytest.raises(ValueError, match="non-public"):
        web_mcp.assert_fetchable("https://split-horizon.example/rss")


def test_assert_fetchable_rejects_empty_resolution(monkeypatch):
    monkeypatch.setattr(socket, "getaddrinfo", lambda *a, **k: [])
    with pytest.raises(ValueError, match="no addresses"):
        web_mcp.assert_fetchable("https://void.example/rss")


def test_open_pinned_dials_the_validated_ip_not_the_hostname(monkeypatch):
    """Regression test for DNS rebinding: the socket must be opened against
    the address assert_fetchable approved, never by re-resolving the name."""
    dialed = {}

    def fake_create_connection(address, timeout=None):
        dialed["address"] = address
        return object()

    monkeypatch.setattr(socket, "create_connection", fake_create_connection)
    parsed = web_mcp.urlparse("http://feeds.example/rss")
    conn = web_mcp.open_pinned(parsed, PUBLIC_IP, timeout=5)

    assert dialed["address"] == (PUBLIC_IP, 80)
    assert conn.host == "feeds.example"   # Host header still uses the name


def test_fetch_returns_body(offline, monkeypatch):
    scripted_opener(monkeypatch, [FakeResponse(body=b"<rss></rss>")])
    assert web_mcp.fetch("https://feeds.example/rss") == "<rss></rss>"


def test_fetch_revalidates_each_redirect_hop(offline, monkeypatch):
    """Every hop must go back through assert_fetchable, not just the first."""
    checked = []
    real = web_mcp.assert_fetchable
    monkeypatch.setattr(web_mcp, "assert_fetchable",
                        lambda u: (checked.append(u), real(u))[1])
    hops = scripted_opener(monkeypatch, [
        FakeResponse(301, {"Location": "https://cdn.example/rss"}),
        FakeResponse(body=b"<rss>final</rss>"),
    ])

    assert web_mcp.fetch("https://feeds.example/rss") == "<rss>final</rss>"
    assert checked == ["https://feeds.example/rss", "https://cdn.example/rss"]
    assert len(hops) == 2


def test_fetch_blocks_redirect_to_cloud_metadata_endpoint(offline, monkeypatch):
    """Regression test: a public URL that 302s at an internal address used to
    be followed blindly, because urllib re-runs no checks on redirects."""
    scripted_opener(monkeypatch, [
        FakeResponse(302, {"Location": "http://169.254.169.254/latest/meta-data/"}),
        FakeResponse(body=b"SHOULD NEVER BE READ"),
    ])
    with pytest.raises(ValueError, match="non-public address"):
        web_mcp.fetch("https://feeds.example/rss")


def test_fetch_blocks_relative_redirect_onto_blocked_host(offline, monkeypatch):
    scripted_opener(monkeypatch, [
        FakeResponse(307, {"Location": "//127.0.0.1/rss"}),
        FakeResponse(body=b"SHOULD NEVER BE READ"),
    ])
    with pytest.raises(ValueError, match="non-public address"):
        web_mcp.fetch("https://feeds.example/rss")


def test_fetch_gives_up_after_max_redirects(offline, monkeypatch):
    scripted_opener(monkeypatch, [
        FakeResponse(302, {"Location": f"https://hop{i}.example/rss"})
        for i in range(web_mcp.MAX_REDIRECTS + 1)
    ])
    with pytest.raises(ValueError, match="too many redirects"):
        web_mcp.fetch("https://feeds.example/rss")


def test_fetch_rejects_redirect_without_location(offline, monkeypatch):
    scripted_opener(monkeypatch, [FakeResponse(302, {})])
    with pytest.raises(ValueError, match="no Location"):
        web_mcp.fetch("https://feeds.example/rss")


def test_fetch_raises_on_error_status(offline, monkeypatch):
    scripted_opener(monkeypatch, [FakeResponse(404, reason="Not Found")])
    with pytest.raises(ValueError, match="HTTP 404"):
        web_mcp.fetch("https://feeds.example/rss")


def test_fetch_enforces_size_cap(offline, monkeypatch):
    oversized = b"x" * (web_mcp.MAX_FETCH_BYTES + 1)
    scripted_opener(monkeypatch, [FakeResponse(body=oversized)])
    with pytest.raises(ValueError, match="byte limit"):
        web_mcp.fetch("https://feeds.example/rss")


def test_fetch_closes_connection_on_error(offline, monkeypatch):
    opened = []

    def _open(parsed, ip, timeout):
        conn = FakeConn(FakeResponse(500, reason="Server Error"))
        opened.append(conn)
        return conn

    monkeypatch.setattr(web_mcp, "open_pinned", _open)
    with pytest.raises(ValueError):
        web_mcp.fetch("https://feeds.example/rss")
    assert opened[0].closed is True
