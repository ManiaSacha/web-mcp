#!/usr/bin/env python3
"""
web-mcp — Semantic search over RSS/news feeds for AI agents.

A single-file MCP server that lets AI agents search a self-hosted corpus of
RSS/Atom feeds — no API key, no cloud, just the feeds you choose.

Features:
  - Add/remove/list feeds (RSS 2.0 + Atom)
  - Recency-boosted ranked search (TF-IDF cosine, pure stdlib)
  - Trend extraction ("what's hot right now?")
  - Source health monitoring (dead / silent / broken feeds)
  - Markdown digest generation
  - Scheduled background refresh
  - SSRF-guarded fetching: scheme allowlist, public-address checks,
    connect-time IP pinning, and per-hop redirect validation

Run:  python web_mcp.py [--feeds url1,url2]
"""
from __future__ import annotations

import argparse
import email.utils
import http.client
import ipaddress
import math
import re
import socket
import ssl
import sys
import threading
import time
import xml.etree.ElementTree as ET
from collections import Counter
from typing import Optional
from urllib.parse import ParseResult, urljoin, urlparse

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("web")

# ---- defaults -----------------------------------------------------------------
REFRESH_INTERVAL = 15 * 60          # seconds between background refreshes
FETCH_TIMEOUT = 15                  # seconds
MAX_FETCH_BYTES = 5 * 1024 * 1024   # refuse to buffer more than 5 MB per feed
MAX_LIMIT = 100                     # cap on any tool's "limit" argument
MAX_REDIRECTS = 5                   # hops allowed before a fetch is abandoned
USER_AGENT = "web-mcp/0.1"
REDIRECT_STATUSES = (301, 302, 303, 307, 308)
SSL_CONTEXT = ssl.create_default_context()
DEFAULT_FEEDS = [
    "https://hnrss.org/frontpage",
    "https://github.blog/feed/",
]
STOPWORDS = set("""
a an and are as at be been being but by for from have has had he her his how i if
in into is it its many more most not of on or our own same so than that the their
them then there these they this those through to under up we what when where which
while who why will with you your about after against also because before between
both each during even ever few first from further get give going just last less like
make may might much must near never new now old only other over per said same should
since some still such take than too under until very was way were well what's will
within without would
""".split())


# ---- SSRF / URL hardening ------------------------------------------------------
def is_blocked_ip(ip: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
    """True for any address a feed fetch has no business reaching."""
    # An IPv4-mapped IPv6 address (::ffff:127.0.0.1) describes an IPv4 target,
    # so classify the mapped address rather than the wrapper.
    mapped = getattr(ip, "ipv4_mapped", None)
    if mapped is not None:
        ip = mapped
    return bool(ip.is_private or ip.is_loopback or ip.is_link_local
                or ip.is_multicast or ip.is_reserved or ip.is_unspecified)


def assert_fetchable(url: str) -> tuple[ParseResult, str]:
    """Validate a URL for server-side fetching and pin the address to use.

    Blocks non-http(s) schemes, then resolves the hostname and rejects the URL
    unless *every* address it resolves to is publicly routable. Returns the
    parsed URL together with the single IP the caller must connect to.

    Returning the IP is the point: resolving here and letting the HTTP client
    resolve again at connect time leaves a window where DNS can answer
    differently the second time (rebinding), so the address that was checked
    is not the address that gets connected to. Callers pass this IP to
    open_pinned() so the validated address is the one actually dialed.
    """
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise ValueError(f"unsupported URL scheme: {parsed.scheme!r} (only http/https)")
    if not parsed.hostname:
        raise ValueError("URL has no hostname")

    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    try:
        infos = socket.getaddrinfo(parsed.hostname, port, type=socket.SOCK_STREAM)
    except socket.gaierror as exc:
        raise ValueError(f"could not resolve host {parsed.hostname!r}: {exc}") from exc
    if not infos:
        raise ValueError(f"host {parsed.hostname!r} resolved to no addresses")

    # Every answer is checked, not just the one we pin: a host that returns a
    # mix of public and private records must not be reachable by retrying.
    for _, _, _, _, sockaddr in infos:
        ip = ipaddress.ip_address(sockaddr[0])
        if is_blocked_ip(ip):
            raise ValueError(f"refusing to fetch {url!r}: resolves to non-public address {ip}")

    return parsed, infos[0][4][0]


def open_pinned(parsed: ParseResult, ip: str, timeout: int) -> http.client.HTTPConnection:
    """Open a connection to `ip`, addressed as `parsed.hostname`.

    The socket is built by hand and handed to HTTPConnection so that no second
    name resolution happens. TLS still uses the hostname for SNI and
    certificate validation, so pinning the IP does not weaken cert checking.
    """
    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    sock = socket.create_connection((ip, port), timeout)
    try:
        if parsed.scheme == "https":
            sock = SSL_CONTEXT.wrap_socket(sock, server_hostname=parsed.hostname)
    except Exception:
        sock.close()
        raise

    conn = http.client.HTTPConnection(parsed.hostname, port, timeout=timeout)
    # HTTPConnection.send() only dials when self.sock is None, so presetting it
    # makes the connection use our validated socket as-is.
    conn.sock = sock
    return conn


# ---- helpers -----------------------------------------------------------------
def local(el) -> str:
    return el.tag.split("}")[-1]


def parse_date(s: str) -> Optional[float]:
    if not s:
        return None
    try:
        dt = email.utils.parsedate_to_datetime(s)
        return dt.timestamp() if dt else None
    except Exception:
        return None


def fetch(url: str, timeout: int = FETCH_TIMEOUT) -> str:
    """Fetch a feed, validating every hop.

    Redirects are followed manually rather than by an HTTP library, because
    a library that follows them internally never re-runs the SSRF check: a
    public URL can answer 302 and send the fetch to 169.254.169.254 or any
    internal host. Each hop here goes back through assert_fetchable().
    """
    seen = []
    for _ in range(MAX_REDIRECTS + 1):
        seen.append(url)
        parsed, ip = assert_fetchable(url)
        conn = open_pinned(parsed, ip, timeout)
        try:
            target = parsed.path or "/"
            if parsed.query:
                target += "?" + parsed.query
            conn.request("GET", target, headers={
                "User-Agent": USER_AGENT,
                "Accept-Encoding": "identity",
                "Accept": "application/rss+xml, application/atom+xml, application/xml, text/xml, */*",
            })
            resp = conn.getresponse()

            if resp.status in REDIRECT_STATUSES:
                location = resp.getheader("Location")
                if not location:
                    raise ValueError(f"HTTP {resp.status} with no Location header: {url}")
                url = urljoin(url, location)
                continue

            if resp.status != 200:
                raise ValueError(f"HTTP {resp.status} {resp.reason}: {url}")

            body = resp.read(MAX_FETCH_BYTES + 1)
            if len(body) > MAX_FETCH_BYTES:
                raise ValueError(f"feed exceeds {MAX_FETCH_BYTES} byte limit: {url}")
            return body.decode("utf-8", errors="replace")
        finally:
            conn.close()

    raise ValueError(f"too many redirects (>{MAX_REDIRECTS}): {' -> '.join(seen)}")


def _entry_link(el) -> str:
    """Pick the best <link> for an RSS item or Atom entry.

    RSS items have a single text <link>. Atom entries may carry several
    <link> elements (alternate/self/enclosure/...); collapsing them into a
    dict by tag name (as a naive {local(c): c for c in el} would) silently
    keeps whichever one happens to appear last in document order. Instead,
    scan all <link> children and prefer rel="alternate" (or no rel, which
    defaults to "alternate" per the Atom spec).
    """
    links = [c for c in el if local(c) == "link"]
    if not links:
        return ""
    for c in links:
        if c.get("rel") in (None, "alternate") and c.get("href"):
            return c.get("href")
    # RSS-style text link, or an Atom link with only non-alternate rels
    return (links[0].text or "").strip() or (links[0].get("href") or "")


def parse_feed(text: str) -> list[dict]:
    """Parse RSS 2.0 or Atom into records.

    Only *direct* children of each item/entry are read, avoiding the
    feed-level <title>/<link> that descendants would otherwise surface.
    """
    root = ET.fromstring(text)  # may raise ParseError
    records = []
    for el in root.iter():
        name = local(el)
        if name not in ("item", "entry"):
            continue

        children = {local(c): c for c in el if local(c) != "link"}

        def text_of(key: str) -> str:
            c = children.get(key)
            if c is None:
                return ""
            if c.text:
                return c.text.strip()
            return ""

        link = _entry_link(el)
        if not link:
            # Fall back to the item's guid / entry's id only when no usable
            # <link> was found at all — never let it override a real link.
            guid = children.get("guid") or children.get("id")
            if guid is not None and guid.text:
                link = guid.text.strip()

        title = text_of("title") or "(untitled)"
        summary = text_of("description") or text_of("summary") or text_of("content")
        published = text_of("pubDate") or text_of("updated") or text_of("published")
        records.append({
            "title": title,
            "link": link,
            "summary": summary,
            "published": published,
            "ts": parse_date(published) or time.time(),
        })
    return records


# ---- tokenizing --------------------------------------------------------------
def tokenize(text: str) -> list[str]:
    words = re.findall(r"[a-z0-9']+", (text or "").lower())
    return [w for w in words if w not in STOPWORDS and len(w) > 1]


# ---- index -------------------------------------------------------------------
class NewsIndex:
    def __init__(self):
        self.docs: dict[int, dict] = {}
        self.feed_info: dict[str, dict] = {}
        self._lock = threading.RLock()
        self._id = 0
        self._df = Counter()
        self._vec: dict[int, Counter] = {}

    # -- adding -----------------------------------------------------------
    def add_feed(self, url: str, fetch_text: str | None = None) -> int:
        if fetch_text is None:
            fetch_text = fetch(url)
        records = parse_feed(fetch_text)
        with self._lock:
            self.feed_info[url] = {"title": None, "last_ok": time.time(),
                                   "last_fetch": time.time(), "error": None,
                                   "articles": 0}
            for r in records:
                doc_id = self._id
                self._id += 1
                r["feed"] = url
                r["tokens"] = Counter(tokenize(r["title"] + " " + r["summary"]))
                self.docs[doc_id] = r
                for term in r["tokens"]:
                    self._df[term] += 1
                norm = math.sqrt(sum(v * v for v in r["tokens"].values()))
                if norm:
                    self._vec[doc_id] = Counter({t: v / norm for t, v in r["tokens"].items()})
                else:
                    # Title/summary produced no indexable tokens (e.g. all
                    # stopwords or empty) — keep the doc retrievable via
                    # recent()/digest() but it can't score in search().
                    self._vec[doc_id] = Counter()
            self.feed_info[url]["articles"] = len(records)
        return len(records)

    def remove_feed(self, url: str) -> bool:
        with self._lock:
            to_del = [i for i, d in self.docs.items() if d["feed"] == url]
            for i in to_del:
                del self.docs[i]
                v = self._vec.pop(i, None)
                if v:
                    for t in v:
                        self._df[t] -= 1
            self.feed_info.pop(url, None)
            return bool(to_del)

    # -- search -----------------------------------------------------------
    def search(self, query: str, limit: int = 10,
               recency_half_life_hours: float = 48) -> list[dict]:
        qw = Counter(tokenize(query))
        if not qw:
            return []
        now = time.time()
        with self._lock:
            n = max(len(self.docs), 1)
            idf = {t: math.log(1 + n / (1 + self._df[t])) for t in qw}
            scored = []
            for doc_id, doc in self.docs.items():
                vec = self._vec[doc_id]
                score = sum(wt * idf.get(t, 0.0) * vec[t]
                            for t, wt in qw.items() if t in vec)
                if score <= 0:
                    continue
                age_h = max(0.0, (now - doc["ts"]) / 3600.0)
                recency = 0.5 ** (age_h / recency_half_life_hours)
                scored.append((score * recency, doc_id))
            scored.sort(reverse=True, key=lambda x: x[0])
            results = []
            for raw_score, doc_id in scored[:limit]:
                d = self.docs[doc_id]
                results.append({
                    "title": d["title"], "link": d["link"],
                    "feed": d["feed"], "summary": d["summary"],
                    "published": d["published"], "ts": d["ts"],
                    "score": round(raw_score, 3),
                })
        return results

    # -- trend + digest ---------------------------------------------------
    def trending(self, hours: float = 24, limit: int = 10) -> list[str]:
        cutoff = time.time() - hours * 3600
        terms = Counter()
        with self._lock:
            for d in self.docs.values():
                if d["ts"] >= cutoff:
                    terms.update(d["tokens"])
        return [t for t, _ in terms.most_common(limit)]

    def digest(self, hours: float = 24, limit: int = 8) -> str:
        cutoff = time.time() - hours * 3600
        with self._lock:
            recent = [d for d in self.docs.values() if d["ts"] >= cutoff]
        recent.sort(key=lambda d: d["ts"], reverse=True)
        top = self.trending(hours, 8)
        lines = [f"# News digest (last {int(hours)}h)", ""]
        if top:
            lines.append("**Trending topics:** " + ", ".join(f"`{t}`" for t in top) + "\n")
        grouped: dict[str, list[dict]] = {}
        for d in recent[: limit * 4]:
            grouped.setdefault(d["feed"], []).append(d)
        for feed, items in grouped.items():
            lines.append(f"## {feed}")
            for d in items[:limit]:
                lines.append(f"- [{d['title']}]({d['link']}) — {d['published']}")
            lines.append("")
        if not recent:
            lines.append("_No recent articles in the last window._")
        return "\n".join(lines)

    def source_health(self) -> str:
        lines = ["## Source health"]
        with self._lock:
            for url, info in self.feed_info.items():
                last = info.get("last_ok") or 0
                age_h = (time.time() - last) / 3600 if last else float("inf")
                status = "OK"
                if info.get("error"):
                    status = "ERROR"
                elif age_h > 24 * 7:
                    status = "SILENT"
                elif age_h > 24:
                    status = "WARN"
                lines.append(f"- {status} | {url} | {info.get('articles', 0)} arts | "
                             f"last OK {age_h:.0f}h ago | {info.get('error') or ''}")
        return "\n".join(lines)


INDEX = NewsIndex()


# ---- background refresher ------------------------------------------------------
def refresh_all():
    for url in list(INDEX.feed_info):
        try:
            text = fetch(url)
            INDEX.remove_feed(url)
            INDEX.add_feed(url, text)
        except Exception as exc:  # noqa: BLE001
            with INDEX._lock:
                INDEX.feed_info.setdefault(url, {}).update({"error": str(exc)[:120]})


def _bg_loop():
    while True:
        time.sleep(REFRESH_INTERVAL)
        try:
            refresh_all()
        except Exception:
            pass


# ---- MCP tools ----------------------------------------------------------------
@mcp.tool()
def add_feed(url: str) -> str:
    """Add an RSS/Atom feed and fetch its current articles."""
    try:
        n = INDEX.add_feed(url)
    except Exception as exc:  # noqa: BLE001
        return f"Failed to add {url}: {exc}"
    return f"Added {url}: indexed {n} articles."


@mcp.tool()
def remove_feed(url: str) -> str:
    """Remove a feed and all of its indexed articles."""
    removed = INDEX.remove_feed(url)
    return f"Removed {url}" if removed else f"No feed found: {url}"


@mcp.tool()
def list_feeds() -> str:
    """List configured feeds with article counts."""
    lines = ["## Feeds"]
    for url, info in INDEX.feed_info.items():
        lines.append(f"- {url} ({info.get('articles', 0)} articles)")
    return "\n".join(lines) if len(lines) > 1 else "No feeds configured."


@mcp.tool()
def search(query: str, limit: int = 10, max_days: float = 30.0) -> str:
    """Recency-boosted ranked search across indexed feeds."""
    limit = max(1, min(limit, MAX_LIMIT))
    results = INDEX.search(query, limit)
    if not results:
        return f"No matches for '{query}'."
    cutoff = time.time() - max_days * 86400
    lines = [f"## Results for '{query}'"]
    shown = 0
    for r in results:
        if r["ts"] < cutoff:
            continue
        shown += 1
        lines.append(f"- [{r['title']}]({r['link']})  _score {r['score']}_ · {r['published']}")
        if r["summary"]:
            lines.append(f"  {r['summary'][:180]}")
    if shown == 0:
        return f"No matches for '{query}' within the last {int(max_days)} days."
    return "\n".join(lines)


@mcp.tool()
def recent(limit: int = 20) -> str:
    """Most recent articles across all feeds."""
    limit = max(1, min(limit, MAX_LIMIT))
    docs = sorted(INDEX.docs.values(), key=lambda d: d["ts"], reverse=True)[:limit]
    if not docs:
        return "No articles indexed yet."
    lines = ["## Latest articles"]
    for d in docs:
        lines.append(f"- {d['published']} | [{d['title']}]({d['link']})")
    return "\n".join(lines)


@mcp.tool()
def trending(hours: float = 24, limit: int = 10) -> str:
    """Topics trending across your feeds in the last N hours."""
    limit = max(1, min(limit, MAX_LIMIT))
    top = INDEX.trending(hours, limit)
    return "## Trending\n" + ("\n".join(f"- {t}" for t in top) if top else "No recent articles.")


@mcp.tool()
def digest(hours: float = 24, limit: int = 8) -> str:
    """Generate a markdown digest grouping recent articles and trending topics."""
    limit = max(1, min(limit, MAX_LIMIT))
    return INDEX.digest(hours, limit)


@mcp.tool()
def source_health() -> str:
    """Check which feeds are healthy, late, or producing errors."""
    return INDEX.source_health()


@mcp.tool()
def refresh() -> str:
    """Force-refresh all feeds now."""
    refresh_all()
    return "Refreshed all feeds."


# ---- entrypoint ---------------------------------------------------------------
def main() -> None:
    parser = argparse.ArgumentParser(description="web-mcp server")
    parser.add_argument("--feeds", default=",".join(DEFAULT_FEEDS),
                        help="Comma-separated feed URLs to start with")
    args = parser.parse_args()
    for url in (u.strip() for u in args.feeds.split(",") if u.strip()):
        try:
            INDEX.add_feed(url)
        except Exception as exc:  # noqa: BLE001
            print(f"warning: could not add {url}: {exc}", file=sys.stderr)
            INDEX.feed_info[url] = {"title": None, "last_ok": None,
                                    "last_fetch": None, "error": str(exc)[:120],
                                    "articles": 0}
    threading.Thread(target=_bg_loop, daemon=True).start()
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
