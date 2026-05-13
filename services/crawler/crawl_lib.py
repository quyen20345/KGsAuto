"""Reusable crawl function extracted from services/crawler/crawlv2.py logic."""

from __future__ import annotations

import re
import time
from pathlib import Path
from typing import Any
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup


_SESSION_USER_AGENT = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"
_CRAWL_DELAY = 0.5


def _safe_filename(name: str) -> str:
    name = re.sub(r'[\\/*?:"<>|]', "", name)
    return name.strip()[:150]


def _clean_content(html: str) -> str:
    from services.crawler.crawlv2 import clean_content
    return clean_content(html)


def _get_metadata_from_api(url: str, session: requests.Session, base_url: str):
    from services.crawler.crawlv2 import get_metadata_from_api, format_metadata_section
    # Temporarily patch BASE_URL for the function
    import services.crawler.crawlv2 as mod
    original = mod.BASE_URL
    mod.BASE_URL = base_url
    try:
        metadata = get_metadata_from_api(url, session)
        return metadata
    finally:
        mod.BASE_URL = original


def crawl_urls(urls: list[str], output_dir: Path) -> tuple[list[str], list[str]]:
    """Crawl a list of URLs and save as markdown files.

    Returns (files_created, errors).
    """
    from services.crawler.crawlv2 import (
        clean_content,
        format_metadata_section,
    )

    output_dir.mkdir(parents=True, exist_ok=True)
    existing_count = len(list(output_dir.glob("*.md")))

    session = requests.Session()
    session.headers.update({"User-Agent": _SESSION_USER_AGENT})

    files_created = []
    errors = []

    for i, url in enumerate(urls):
        try:
            parsed = urlparse(url)
            base_url = f"{parsed.scheme}://{parsed.netloc}"

            resp = session.get(url, timeout=15)
            if resp.status_code != 200:
                errors.append(f"{url}: HTTP {resp.status_code}")
                continue

            soup = BeautifulSoup(resp.text, "html.parser")

            # Try WordPress API metadata
            import services.crawler.crawlv2 as mod
            original_base = mod.BASE_URL
            original_domain = mod.BASE_DOMAIN
            mod.BASE_URL = base_url
            mod.BASE_DOMAIN = parsed.netloc
            try:
                from services.crawler.crawlv2 import get_metadata_from_api
                metadata = get_metadata_from_api(url, session)
            finally:
                mod.BASE_URL = original_base
                mod.BASE_DOMAIN = original_domain

            # Extract title
            if metadata and "title" in metadata:
                title = metadata["title"].get("rendered", "Untitled")
                title = BeautifulSoup(title, "html.parser").get_text()
            else:
                title_tag = soup.find("title")
                title = title_tag.get_text(strip=True) if title_tag else "Untitled"

            # Find main content
            content = None
            for selector in [".entry-content", "article", ".content", "main", "#content"]:
                content = soup.select_one(selector)
                if content:
                    break
            if not content:
                content = soup.find("body")

            if not content:
                errors.append(f"{url}: no content found")
                continue

            markdown_content = clean_content(str(content))

            # Generate filename
            file_num = existing_count + i + 1
            safe_name = _safe_filename(title)
            filename = f"{file_num:03d}_{safe_name}.md"
            filepath = output_dir / filename

            with open(filepath, "w", encoding="utf-8") as f:
                f.write(f"# {title}\n\n")
                f.write("## Metadata\n\n")
                f.write(f"- **URL**: {url}\n")
                metadata_section = format_metadata_section(metadata)
                if metadata_section:
                    f.write(metadata_section + "\n")
                f.write("\n## Content\n\n")
                f.write(markdown_content)

            files_created.append(filename)

            if i < len(urls) - 1:
                time.sleep(_CRAWL_DELAY)

        except Exception as e:
            errors.append(f"{url}: {type(e).__name__}: {e}")

    return files_created, errors
