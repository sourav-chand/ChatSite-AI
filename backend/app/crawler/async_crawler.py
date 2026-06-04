"""Async website crawler built on httpx + BeautifulSoup4.

Pipeline per page:
  fetch (with retry/backoff) → soup → extract structured fields → normalize
"""
from __future__ import annotations

import asyncio
import hashlib
import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Iterable
from urllib.parse import urldefrag, urljoin, urlparse, urlunparse
from urllib.robotparser import RobotFileParser
from xml.etree import ElementTree as ET

import httpx
import structlog
from bs4 import BeautifulSoup

from app.core.config import settings

log = structlog.get_logger(__name__)

USER_AGENT = settings.CRAWL_USER_AGENT
TIMEOUT = settings.CRAWL_TIMEOUT_SEC
MAX_DEPTH = settings.CRAWL_MAX_DEPTH
CONCURRENCY = settings.CRAWL_CONCURRENCY
DOMAIN_DELAY = settings.CRAWL_REQUEST_DELAY

BINARY_EXTS = {
    ".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg", ".ico", ".bmp", ".tiff",
    ".pdf", ".zip", ".tar", ".gz", ".7z", ".rar",
    ".mp3", ".mp4", ".mov", ".avi", ".wav",
    ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx",
    ".css", ".js", ".woff", ".woff2", ".ttf", ".eot",
}

BLOCK_TAGS = {"script", "style", "noscript", "iframe", "svg", "nav", "footer", "header", "aside"}


@dataclass(slots=True)
class PageResult:
    url: str
    canonical_url: str
    title: str | None = None
    meta_description: str | None = None
    headings: dict = field(default_factory=dict)
    main_content: str = ""
    word_count: int = 0
    language: str | None = None
    http_status: int | None = None
    redirect_chain: list[str] = field(default_factory=list)
    content_hash: str = ""
    error: str | None = None


def normalize_url(url: str) -> str:
    """Strip fragments, normalize scheme+host to lowercase, drop default ports."""
    url, _ = urldefrag(url)
    parsed = urlparse(url)
    scheme = parsed.scheme.lower() or "https"
    netloc = parsed.netloc.lower()
    if netloc.endswith(":80") and scheme == "http":
        netloc = netloc[:-3]
    if netloc.endswith(":443") and scheme == "https":
        netloc = netloc[:-4]
    return urlunparse((scheme, netloc, parsed.path or "/", parsed.params, parsed.query, ""))


def is_binary(url: str) -> bool:
    path = urlparse(url).path.lower()
    return any(path.endswith(ext) for ext in BINARY_EXTS)


def looks_like_login_blocked(html: str) -> bool:
    lowered = html.lower()
    return any(s in lowered for s in ("<form", "sign in", "log in", "password", "auth-wall"))


def is_same_domain(url: str, base: str) -> bool:
    return urlparse(url).netloc == urlparse(base).netloc


async def fetch_robots(base_url: str, client: httpx.AsyncClient) -> RobotFileParser | None:
    parsed = urlparse(base_url)
    robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
    try:
        r = await client.get(robots_url, timeout=5.0, follow_redirects=True)
        if r.status_code != 200:
            return None
        rp = RobotFileParser()
        rp.parse(r.text.splitlines())
        return rp
    except Exception as exc:
        log.warning("robots.fetch_failed", url=robots_url, error=str(exc))
        return None


async def fetch_sitemap(base_url: str, client: httpx.AsyncClient) -> list[str]:
    parsed = urlparse(base_url)
    sitemap_url = f"{parsed.scheme}://{parsed.netloc}/sitemap.xml"
    try:
        r = await client.get(sitemap_url, timeout=5.0)
        if r.status_code != 200:
            return []
        root = ET.fromstring(r.text)
        ns = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
        urls = [loc.text for loc in root.findall(".//sm:loc", ns) if loc.text]
        return [normalize_url(u) for u in urls if u]
    except Exception as exc:
        log.warning("sitemap.parse_failed", url=sitemap_url, error=str(exc))
        return []


def extract_links(html: str, base_url: str) -> list[str]:
    soup = BeautifulSoup(html, "lxml")
    out: list[str] = []
    for a in soup.find_all("a", href=True):
        href = a["href"]
        absolute = urljoin(base_url, href)
        if is_same_domain(absolute, base_url):
            out.append(normalize_url(absolute))
    return list(dict.fromkeys(out))


def extract_metadata(html: str, url: str) -> PageResult:
    soup = BeautifulSoup(html, "lxml")

    canonical_tag = soup.find("link", rel="canonical")
    canonical_url = (
        canonical_tag["href"] if canonical_tag and canonical_tag.get("href") else url
    )
    canonical_url = normalize_url(canonical_url)

    title = (soup.title.string or "").strip() if soup.title and soup.title.string else None

    meta_desc_tag = soup.find("meta", attrs={"name": "description"})
    meta_desc = (
        meta_desc_tag["content"].strip()
        if meta_desc_tag and meta_desc_tag.get("content")
        else None
    )

    html_tag = soup.find("html")
    language = html_tag.get("lang") if html_tag else None

    headings: dict[str, list[str]] = {"h1": [], "h2": [], "h3": []}
    for level in headings:
        for h in soup.find_all(level):
            txt = h.get_text(" ", strip=True)
            if txt:
                headings[level].append(txt)

    for tag in soup.find_all(BLOCK_TAGS):
        tag.decompose()
    main = soup.find("main") or soup.find("article") or soup.body or soup
    text = main.get_text("\n", strip=True) if main else ""
    text = re.sub(r"\n{2,}", "\n\n", text)

    content_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()
    word_count = len(text.split())

    return PageResult(
        url=url,
        canonical_url=canonical_url,
        title=title,
        meta_description=meta_desc,
        headings=headings,
        main_content=text,
        word_count=word_count,
        language=language,
        content_hash=content_hash,
    )


async def fetch_page(
    client: httpx.AsyncClient,
    url: str,
    *,
    max_retries: int = 3,
) -> tuple[int, str, list[str]]:
    last_exc: Exception | None = None
    for attempt in range(max_retries):
        try:
            r = await client.get(
                url,
                timeout=TIMEOUT,
                follow_redirects=True,
                headers={"User-Agent": USER_AGENT, "Accept": "text/html,application/xhtml+xml"},
            )
            chain = [str(h.url) for h in r.history] + [str(r.url)]
            return r.status_code, r.text, chain
        except (httpx.TimeoutException, httpx.NetworkError) as exc:
            last_exc = exc
            await asyncio.sleep(2**attempt)
    raise RuntimeError(f"Failed to fetch {url}: {last_exc}")


class AsyncCrawler:
    def __init__(self, base_url: str, *, max_depth: int = MAX_DEPTH, concurrency: int = CONCURRENCY) -> None:
        self.base_url = normalize_url(base_url)
        self.max_depth = max_depth
        self.concurrency = concurrency
        self.robots: RobotFileParser | None = None
        self.visited: set[str] = set()
        self.results: dict[str, PageResult] = {}
        self.seen_hashes: set[str] = set()
        self._sem = asyncio.Semaphore(concurrency)
        self._domain_last_request: dict[str, float] = {}

    async def crawl(self) -> list[PageResult]:
        async with httpx.AsyncClient(http2=True) as client:
            self.robots = await fetch_robots(self.base_url, client)
            seed_urls = await fetch_sitemap(self.base_url, client) or [self.base_url]

            queue: asyncio.Queue[tuple[str, int]] = asyncio.Queue()
            for u in seed_urls:
                await queue.put((u, 0))

            async def worker() -> None:
                while True:
                    try:
                        url, depth = queue.get_nowait()
                    except asyncio.QueueEmpty:
                        return
                    await self._process(client, url, depth, queue)
                    queue.task_done()

            tasks = [asyncio.create_task(worker()) for _ in range(self.concurrency)]
            await asyncio.gather(*tasks)

        return list(self.results.values())

    async def _process(
        self,
        client: httpx.AsyncClient,
        url: str,
        depth: int,
        queue: asyncio.Queue,
    ) -> None:
        url = normalize_url(url)
        if url in self.visited or is_binary(url):
            return
        if depth > self.max_depth:
            return
        if self.robots and not self.robots.can_fetch(USER_AGENT, url):
            log.info("crawl.robots_blocked", url=url)
            return

        async with self._sem:
            await self._respect_rate_limit()
            try:
                status, html, chain = await fetch_page(client, url)
            except Exception as exc:
                self.results[url] = PageResult(
                    url=url, canonical_url=url, error=str(exc), http_status=None
                )
                self.visited.add(url)
                return

        if status in (401, 403):
            self.results[url] = PageResult(url=url, canonical_url=url, http_status=status, error="auth")
            self.visited.add(url)
            return
        if status >= 400:
            self.results[url] = PageResult(url=url, canonical_url=url, http_status=status, error=f"http_{status}")
            self.visited.add(url)
            return
        if looks_like_login_blocked(html):
            self.results[url] = PageResult(url=url, canonical_url=url, http_status=status, error="login_required")
            self.visited.add(url)
            return

        meta = extract_metadata(html, url)
        meta.http_status = status
        meta.redirect_chain = chain
        if meta.content_hash in self.seen_hashes:
            self.visited.add(url)
            return
        self.seen_hashes.add(meta.content_hash)
        self.results[meta.canonical_url] = meta
        self.visited.add(url)

        if depth < self.max_depth:
            for link in extract_links(html, url):
                if link not in self.visited:
                    await queue.put((link, depth + 1))

    async def _respect_rate_limit(self) -> None:
        host = urlparse(self.base_url).netloc
        last = self._domain_last_request.get(host, 0.0)
        now = asyncio.get_event_loop().time()
        wait = DOMAIN_DELAY - (now - last)
        if wait > 0:
            await asyncio.sleep(wait)
        self._domain_last_request[host] = asyncio.get_event_loop().time()
