import re
from typing import Dict, List
from urllib.parse import urljoin

import aiohttp
from bs4 import BeautifulSoup


USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)


def _clean_text(text: str) -> str:
    if not text:
        return ""
    text = text.replace(" ", " ")
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _extract_visible_text(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "nav", "footer", "header", "aside", "noscript", "svg"]):
        tag.decompose()
    return _clean_text(soup.get_text(separator=" ", strip=True))


async def _fetch_html(url: str, timeout: int = 30) -> str:
    headers = {"User-Agent": USER_AGENT}
    async with aiohttp.ClientSession(headers=headers) as session:
        async with session.get(url, timeout=timeout, allow_redirects=True) as response:
            response.raise_for_status()
            return await response.text(errors="ignore")


async def fetch_website_text(url: str) -> str:
    html = await _fetch_html(url)
    return _extract_visible_text(html)


async def analyze_images_from_url(url: str) -> Dict:
    html = await _fetch_html(url)
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
    html = await _fetch_html(url)
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
