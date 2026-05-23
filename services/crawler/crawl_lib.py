"""Reusable crawl function extracted from services/crawler/crawlv2.py logic."""

from __future__ import annotations

import hashlib
import re
import threading
import time
from pathlib import Path
from typing import Any
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup


_SESSION_USER_AGENT = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"
_CRAWL_DELAY = 0.5
_METADATA_LOCK = threading.Lock()


def _safe_filename(name: str) -> str:
    name = re.sub(r'[\\/*?:"<>|]', "", name)
    return name.strip()[:120] or "untitled"


def _filename_for_url(title: str, url: str) -> str:
    digest = hashlib.sha1(url.encode("utf-8")).hexdigest()[:10]
    return f"{_safe_filename(title)}_{digest}.md"


def _clean_content(html: str) -> str:
    from services.crawler.crawlv2 import clean_content
    return clean_content(html)


def _get_metadata_from_api(url: str, session: requests.Session, base_url: str):
    from services.crawler.crawlv2 import get_metadata_from_api, format_metadata_section
    # Temporarily patch BASE_URL for the function
    import services.crawler.crawlv2 as mod
    with _METADATA_LOCK:
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

            import services.crawler.crawlv2 as mod
            with _METADATA_LOCK:
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

            filename = _filename_for_url(title, url)
            filepath = output_dir / filename

            try:
                with open(filepath, "x", encoding="utf-8") as f:
                    f.write(f"# {title}\n\n")
                    f.write("## Metadata\n\n")
                    f.write(f"- **URL**: {url}\n")
                    metadata_section = format_metadata_section(metadata)
                    if metadata_section:
                        f.write(metadata_section + "\n")
                    f.write("\n## Content\n\n")
                    f.write(markdown_content)
            except FileExistsError:
                errors.append(f"{url}: file already exists ({filename})")
                continue

            files_created.append(filename)

            if i < len(urls) - 1:
                time.sleep(_CRAWL_DELAY)

        except Exception as e:
            errors.append(f"{url}: {type(e).__name__}: {e}")

    return files_created, errors
