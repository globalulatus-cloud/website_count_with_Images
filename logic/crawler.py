import asyncio
from typing import Set, List, Dict, Optional
from urllib.parse import urljoin, urlparse, urlunparse

import aiohttp
from bs4 import BeautifulSoup

from logic.counter import count_stats


USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)

SKIP_EXTENSIONS = (
    ".pdf", ".jpg", ".jpeg", ".png", ".gif", ".webp", ".zip",
    ".mp4", ".mp3", ".doc", ".docx", ".xls", ".xlsx",
    ".css", ".js", ".ico", ".svg", ".woff", ".woff2", ".ttf", ".eot"
)


def normalize_url(url: str) -> str:
    parsed = urlparse(url)
    scheme = parsed.scheme or "https"
    netloc = parsed.netloc.lower()
    path = parsed.path or "/"
    return urlunparse((scheme, netloc, path, "", "", ""))


def is_valid_url(url: str, root_domain: str, follow_external: bool) -> bool:
    parsed = urlparse(url)

    if parsed.scheme not in ("http", "https"):
        return False

    if any(parsed.path.lower().endswith(ext) for ext in SKIP_EXTENSIONS):
        return False

    if follow_external:
        return True

    return parsed.netloc.lower() == root_domain.lower()


def clean_text(text: str) -> str:
    if not text:
        return ""
    return " ".join(text.replace(" ", " ").split())


def extract_title_from_html(html: str, fallback: str = "") -> str:
    try:
        soup = BeautifulSoup(html, "html.parser")
        if soup.title and soup.title.string:
            title = soup.title.string.strip()
            if title:
                return title
    except Exception:
        pass
    return fallback


def extract_text_from_html(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "nav", "footer", "header", "aside", "noscript", "svg"]):
        tag.decompose()
    return clean_text(soup.get_text(separator=" ", strip=True))


def extract_links_from_html(html: str, base_url: str, root_domain: str, follow_external: bool) -> List[str]:
    links = []
    try:
        soup = BeautifulSoup(html, "html.parser")
        for a in soup.find_all("a", href=True):
            href = (a.get("href") or "").strip()
            if not href or href.startswith(("mailto:", "tel:", "javascript:", "#")):
                continue

            absolute = urljoin(base_url, href)
            absolute = normalize_url(absolute)

            if is_valid_url(absolute, root_domain, follow_external):
                links.append(absolute)
    except Exception:
        pass

    seen = set()
    out = []
    for item in links:
        if item not in seen:
            seen.add(item)
            out.append(item)
    return out


class EnhancedWebsiteCrawler:
    def __init__(self, root_url: str, max_pages: Optional[int] = None,
                 max_depth: int = 5, follow_external: bool = False):
        self.root_url = normalize_url(root_url)
        self.max_pages = max_pages
        self.max_depth = max_depth
        self.follow_external = follow_external
        self.visited_urls: Set[str] = set()
        self.results: List[Dict] = []
        self.domain = urlparse(self.root_url).netloc
        self.errors: List[Dict] = []

    async def _fetch_html(self, session: aiohttp.ClientSession, url: str) -> str:
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=30), allow_redirects=True) as response:
            response.raise_for_status()
            return await response.text(errors="ignore")

    async def crawl_page(self, session: aiohttp.ClientSession, url: str, depth: int):
        if url in self.visited_urls:
            return

        if self.max_pages is not None and len(self.visited_urls) >= self.max_pages:
            return

        self.visited_urls.add(url)

        try:
            html = await self._fetch_html(session, url)
            title = extract_title_from_html(html, fallback=url)
            text = extract_text_from_html(html)
            stats = count_stats(text)

            self.results.append({
                "url": url,
                "title": title,
                "stats": stats
            })

            if depth >= self.max_depth:
                return

            links = extract_links_from_html(html, url, self.domain, self.follow_external)
            for link in links:
                if self.max_pages is not None and len(self.visited_urls) >= self.max_pages:
                    break
                if link not in self.visited_urls:
                    await self.crawl_page(session, link, depth + 1)

        except Exception as e:
            self.errors.append({
                "url": url,
                "error": str(e)
            })
            self.results.append({
                "url": url,
                "title": "Fetch failed",
                "stats": {
                    "count": 0,
                    "type": "words",
                    "language_group": f"Error: {str(e)}"
                }
            })

    async def crawl(self) -> List[Dict]:
        headers = {"User-Agent": USER_AGENT}
        connector = aiohttp.TCPConnector(ssl=False)

        async with aiohttp.ClientSession(headers=headers, connector=connector) as session:
            await self.crawl_page(session, self.root_url, 0)

        return self.results


async def crawl_site(root_url: str, max_pages: Optional[int] = None,
                    max_depth: int = 5, follow_external: bool = False) -> List[Dict]:
    crawler = EnhancedWebsiteCrawler(root_url, max_pages, max_depth, follow_external)
    results = await crawler.crawl()
    return results
