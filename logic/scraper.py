import re
import httpx
import trafilatura
from bs4 import BeautifulSoup


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
            return soup.title.string.strip()

    except Exception:
        pass

    return fallback


async def fetch_website_text(url: str):

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

        response = await client.get(url)

        html = response.text

    title = extract_title_from_html(html, fallback=url)

    extracted = trafilatura.extract(
        html,
        include_comments=False,
        include_tables=False,
        include_links=False,
        include_images=False,
        output_format="txt"
    )

    if extracted:
        text = clean_text(extracted)

    else:
        soup = BeautifulSoup(html, "html.parser")

        for tag in soup([
            "script",
            "style",
            "nav",
            "footer",
            "header",
            "aside",
            "noscript"
        ]):
            tag.decompose()

        text = clean_text(
            soup.get_text(separator=" ", strip=True)
        )

    return text, title, html
