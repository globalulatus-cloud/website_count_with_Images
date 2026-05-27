import re
from typing import Dict, List
from urllib.parse import urljoin

from bs4 import BeautifulSoup
from playwright.async_api import async_playwright
import trafilatura


USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)


def clean_text(text: str) -> str:
    if not text:
        return ""
    text = text.replace("\u00a0", " ")
    text = re.sub(r"\s+", " ", text).strip()
    return text


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


async def fetch_rendered_html(url: str, timeout_ms: int = 60000) -> str:
    """
    Fetch fully rendered HTML using Playwright.
    This is needed for JavaScript-heavy websites.
    """
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        try:
            page = await browser.new_page(
                user_agent=USER_AGENT,
                viewport={"width": 1440, "height": 1200},
            )
            await page.goto(url, wait_until="networkidle", timeout=timeout_ms)
            await page.wait_for_timeout(1500)
            return await page.content()
        finally:
            await browser.close()


def extract_text_from_html(html: str, fallback_title: str = "") -> str:
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


async def fetch_website_text(url: str) -> str:
    """
    Fetch text content from a website after rendering JavaScript.
    """
    html = await fetch_rendered_html(url)
    return extract_text_from_html(html, fallback_title=url)


async def analyze_images_from_url(url: str) -> Dict:
    """
    Fetch and analyze images from a specific URL after rendering.
    """
    html = await fetch_rendered_html(url)
    soup = BeautifulSoup(html, "html.parser")
    images = soup.find_all("img")

    image_stats = {
        "total_images": len(images),
        "images_with_alt": 0,
        "images_without_alt": 0,
        "images_with_title": 0,
    }

    for img in images:
        alt = (img.get("alt") or "").strip()
        title = (img.get("title") or "").strip()

        if alt:
            image_stats["images_with_alt"] += 1
        else:
            image_stats["images_without_alt"] += 1

        if title:
            image_stats["images_with_title"] += 1

    return image_stats


async def get_image_details_from_url(url: str) -> List[Dict]:
    """
    Fetch detailed image information including URLs from a specific page.
    """
    html = await fetch_rendered_html(url)
    soup = BeautifulSoup(html, "html.parser")
    images = soup.find_all("img")
    image_details = []

    for img in images:
        src = (img.get("src") or "").strip()
        if src:
            src = urljoin(url, src)

        alt = (img.get("alt") or "").strip()
        title = (img.get("title") or "").strip()
        data_attrs = [k for k in img.attrs.keys() if k.startswith("data-")]

        image_details.append({
            "src": src,
            "alt": alt if alt else None,
            "title": title if title else None,
            "has_metadata": bool(alt or title or data_attrs),
            "data_attributes": data_attrs,
        })

    return image_details
