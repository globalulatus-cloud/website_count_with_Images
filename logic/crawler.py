from urllib.parse import urljoin, urlparse, urlunparse

import httpx
import trafilatura
from bs4 import BeautifulSoup

from logic.counter import count_stats


def normalize_url(url):

    parsed = urlparse(url)

    return urlunparse((
        parsed.scheme,
        parsed.netloc,
        parsed.path,
        "",
        "",
        ""
    ))


def clean_text(text):

    if not text:
        return ""

    return " ".join(text.split())


async def crawl_site(root_url, max_pages=100):

    visited = set()
    queue = [root_url]

    results = []

    root_domain = urlparse(root_url).netloc

    headers = {
        "User-Agent": (
            "Mozilla/5.0 "
            "(Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 "
            "(KHTML, like Gecko) "
            "Chrome/124.0 Safari/537.36"
        )
    }

    async with httpx.AsyncClient(
        headers=headers,
        timeout=60,
        follow_redirects=True
    ) as client:

        while queue and len(visited) < max_pages:

            current_url = normalize_url(queue.pop(0))

            if current_url in visited:
                continue

            visited.add(current_url)

            try:

                response = await client.get(current_url)

                html = response.text

                soup = BeautifulSoup(html, "html.parser")

                title = (
                    soup.title.string.strip()
                    if soup.title and soup.title.string
                    else current_url
                )

                extracted = trafilatura.extract(html)

                if extracted:
                    text = clean_text(extracted)
                else:
                    text = clean_text(
                        soup.get_text(separator=" ", strip=True)
                    )

                stats = count_stats(text)

                results.append({
                    "url": current_url,
                    "title": title,
                    "stats": stats
                })

                for a in soup.find_all("a", href=True):

                    href = urljoin(current_url, a["href"])

                    parsed = urlparse(href)

                    if root_domain in parsed.netloc:

                        clean_url = normalize_url(href)

                        if clean_url not in visited:
                            queue.append(clean_url)

            except Exception as e:

                results.append({
                    "url": current_url,
                    "title": "Fetch failed",
                    "stats": {
                        "count": 0,
                        "type": "words",
                        "language_group": f"Error: {str(e)}"
                    }
                })

    return results
