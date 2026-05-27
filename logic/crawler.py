import asyncio
from typing import Set, List, Dict, Optional
from urllib.parse import urljoin, urlparse, urlunparse

from bs4 import BeautifulSoup
from playwright.async_api import async_playwright
import trafilatura

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


def same_domain(url: str, root_domain: str, follow_external: bool) -> bool:
    if follow_external:
        return True
    try:
        return urlparse(url).netloc.lower() == root_domain.lower()
    except Exception:
        return False


def is_valid_url(url: str, root_domain: str, follow_external: bool) -> bool:
    parsed = urlparse(url)

    if parsed.scheme not in ("http", "https"):
        return False

    if any(parsed.path.lower().endswith(ext) for ext in SKIP_EXTENSIONS):
        return False

    return same_domain(url, root_domain, follow_external)


def clean_text(text: str) -> str:
    if not text:
        return ""
    return " ".join(text.replace("\u00a0", " ").split())


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
    extracted = trafilatura.extract(
        html,
        include_comments=False,
        include_tables=False,
        include_links=False,
        include_images=False,
        output_format="txt",
    )

    if extracted:
        return clean_text(extracted)

    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "nav", "footer", "header", "aside", "noscript"]):
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

    async def crawl_page(self, page, url: str, depth: int):
        if url in self.visited_urls:
            return [], None

        self.visited_urls.add(url)

        try:
            await page.goto(url, wait_until="networkidle", timeout=60000)
            await page.wait_for_timeout(1200)
            html = await page.content()

            title = extract_title_from_html(html, fallback=url)
            text = extract_text_from_html(html)
            stats = count_stats(text)

            result = {
                "url": url,
                "title": title,
                "stats": stats,
                "depth": depth,
            }

            links = []
            if depth < self.max_depth:
                links = extract_links_from_html(html, url, self.domain, self.follow_external)

            return links, result

        except Exception as e:
            self.errors.append({"url": url, "error": str(e)})
            return [], {
                "url": url,
                "title": "Fetch failed",
                "stats": {
                    "count": 0,
                    "type": "words",
                    "language_group": f"Error: {str(e)}",
                    "word_count": 0,
                    "char_count": 0,
                },
                "depth": depth,
            }

    async def crawl(self):
        """
        Crawl using BFS and rendered HTML.
        """
        queue = [(self.root_url, 0)]

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page(
                user_agent=USER_AGENT,
                viewport={"width": 1440, "height": 1200},
            )

            try:
                while queue:
                    batch = queue[:2]
                    queue = queue[2:]

                    tasks = []
                    for url, depth in batch:
                        if self.max_pages and len(self.visited_urls) >= self.max_pages:
                            break
                        if url in self.visited_urls:
                            continue
                        tasks.append(self.crawl_page(page, url, depth))

                    if not tasks:
                        continue

                    results = await asyncio.gather(*tasks)

                    for links, result in results:
                        if result:
                            self.results.append(result)

                        if result is None:
                            continue

                        next_depth = result.get("depth", 0) + 1
                        for link in links:
                            if self.max_pages and len(self.visited_urls) >= self.max_pages:
                                break
                            if link not in self.visited_urls and link not in [u for u, _ in queue]:
                                queue.append((link, next_depth))

                    if self.max_pages and len(self.visited_urls) >= self.max_pages:
                        break

            finally:
                await browser.close()

        return self.results


async def crawl_site(root_url: str, max_pages: Optional[int] = None,
                    max_depth: int = 5, follow_external: bool = False) -> List[Dict]:
    crawler = EnhancedWebsiteCrawler(root_url, max_pages, max_depth, follow_external)
    return await crawler.crawl()
