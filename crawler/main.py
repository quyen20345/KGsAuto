#!/usr/bin/env python3
"""
Simple WordPress REST API crawler for a site (saves each post as a markdown file).
Designed for demo and small crawls. Adjust constants below as needed.
"""

import os
import time
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional

import requests
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# -------------------------
# Configuration (edit these)
# -------------------------
BASE_URL = "http://uet.edu.vn"  # target site
PER_PAGE = 10                   # posts per page (wp API)
DATA_DIR = Path("uet_crawled_data")  # output directory
LOG_FILE = DATA_DIR / "crawl_log.json"

CRAWL_DELAY_SECONDS = 0.8      # pause between pages (be polite)
SESSION_USER_AGENT = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36"
REQUEST_TIMEOUT = 15
MAX_RETRIES = 4                # sensible number of retries for network error
STATUS_FORCELIST = (429, 500, 502, 503, 504)  # retry on these HTTP status codes

# -------------------------
# Setup logging
# -------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
logger = logging.getLogger(__name__)

# -------------------------
# Helpers
# -------------------------
def make_session() -> requests.Session:
    s = requests.Session()
    s.headers.update({"User-Agent": SESSION_USER_AGENT})
    retries = Retry(
        total=MAX_RETRIES,
        backoff_factor=1,
        status_forcelist=STATUS_FORCELIST,
        allowed_methods=frozenset(["GET", "POST"]),
        raise_on_status=False,
    )
    adapter = HTTPAdapter(max_retries=retries)
    s.mount("https://", adapter)
    s.mount("http://", adapter)
    return s

def safe_filename(name: str) -> str:
    import re
    name = re.sub(r'[\\/*?:"<>|]', "", name)
    name = name.replace("\t", "").replace("\n", "")
    return name.strip()[:150]

def convert_table_to_markdown(table_soup) -> str:
    """Convert HTML table to Markdown table format."""
    rows = table_soup.find_all('tr')
    if not rows:
        return ""

    markdown_lines = []

    # Check if first row is header
    first_row = rows[0]
    has_header = bool(first_row.find_all('th'))

    if has_header:
        # Process header row
        headers = first_row.find_all(['th', 'td'])
        header_texts = [cell.get_text(strip=True) for cell in headers]
        markdown_lines.append('| ' + ' | '.join(header_texts) + ' |')
        markdown_lines.append('|' + '|'.join(['-----'] * len(header_texts)) + '|')
        start_idx = 1
    else:
        # No header, create generic one
        first_cells = first_row.find_all(['td', 'th'])
        num_cols = len(first_cells)
        markdown_lines.append('| ' + ' | '.join([f'Col{i+1}' for i in range(num_cols)]) + ' |')
        markdown_lines.append('|' + '|'.join(['-----'] * num_cols) + '|')
        start_idx = 0

    # Process data rows
    for row in rows[start_idx:]:
        cells = row.find_all(['td', 'th'])
        cell_texts = [cell.get_text(strip=True) for cell in cells]
        markdown_lines.append('| ' + ' | '.join(cell_texts) + ' |')

    return '\n'.join(markdown_lines)

def convert_list_to_markdown(list_soup, ordered=False, indent_level=0) -> str:
    """Convert HTML list (ul/ol) to Markdown list format."""
    items = list_soup.find_all('li', recursive=False)
    markdown_lines = []
    indent = '  ' * indent_level

    for i, item in enumerate(items, 1):
        # Get direct text content (not from nested lists)
        text_parts = []
        for content in item.children:
            if isinstance(content, str):
                text = content.strip()
                if text:
                    text_parts.append(text)
            elif content.name not in ['ul', 'ol']:
                text = content.get_text(strip=True)
                if text:
                    text_parts.append(text)

        item_text = ' '.join(text_parts)

        # Create list marker
        if ordered:
            marker = f"{i}."
        else:
            marker = "-"

        if item_text:
            markdown_lines.append(f"{indent}{marker} {item_text}")

        # Process nested lists
        nested_ul = item.find('ul', recursive=False)
        nested_ol = item.find('ol', recursive=False)

        if nested_ul:
            nested_md = convert_list_to_markdown(nested_ul, ordered=False, indent_level=indent_level+1)
            markdown_lines.append(nested_md)

        if nested_ol:
            nested_md = convert_list_to_markdown(nested_ol, ordered=True, indent_level=indent_level+1)
            markdown_lines.append(nested_md)

    return '\n'.join(markdown_lines)

def convert_heading_to_markdown(heading_soup) -> str:
    """Convert HTML heading (h1-h6) to Markdown heading."""
    level = int(heading_soup.name[1])  # Extract number from h1, h2, etc.
    text = heading_soup.get_text(strip=True)
    return '#' * level + ' ' + text

def process_element_recursively(element) -> str:
    """Process element and its children, converting structure to Markdown."""
    parts = []

    for child in element.children:
        if isinstance(child, str):
            text = child.strip()
            if text:
                parts.append(text)
        elif child.name == 'table':
            parts.append(convert_table_to_markdown(child))
        elif child.name in ['ul', 'ol']:
            ordered = child.name == 'ol'
            parts.append(convert_list_to_markdown(child, ordered=ordered))
        elif child.name in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
            parts.append(convert_heading_to_markdown(child))
        elif child.name in ['p', 'div', 'section', 'article']:
            nested = process_element_recursively(child)
            if nested:
                parts.append(nested)
        else:
            text = child.get_text(strip=True)
            if text:
                parts.append(text)

    return '\n\n'.join(parts)

def normalize_whitespace(text: str) -> str:
    """Clean up excessive whitespace while preserving structure."""
    lines = text.split('\n')
    cleaned = []
    blank_count = 0

    for line in lines:
        # Preserve indentation for lists
        if line.strip():
            cleaned.append(line.rstrip())
            blank_count = 0
        else:
            blank_count += 1
            # Allow max 2 consecutive blank lines
            if blank_count <= 2:
                cleaned.append('')

    # Remove trailing blank lines
    while cleaned and not cleaned[-1]:
        cleaned.pop()

    return '\n'.join(cleaned)

def clean_content(html: str) -> str:
    """
    Convert HTML to well-structured Markdown.
    Preserves tables, headings, lists, and paragraph structure.
    """
    soup = BeautifulSoup(html or "", "html.parser")

    # Remove unwanted elements
    for tag in soup(["script", "style", "noscript", "iframe"]):
        tag.decompose()

    parts = []

    # Process top-level elements
    for element in soup.children:
        if isinstance(element, str):
            text = element.strip()
            if text:
                parts.append(text)
            continue

        if not hasattr(element, 'name'):
            continue

        # Handle different element types
        if element.name in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
            parts.append(convert_heading_to_markdown(element))

        elif element.name == 'table':
            parts.append(convert_table_to_markdown(element))

        elif element.name == 'ul':
            parts.append(convert_list_to_markdown(element, ordered=False))

        elif element.name == 'ol':
            parts.append(convert_list_to_markdown(element, ordered=True))

        elif element.name in ['p', 'div', 'section', 'article', 'main']:
            nested = process_element_recursively(element)
            if nested:
                parts.append(nested)

        else:
            text = element.get_text(strip=True)
            if text:
                parts.append(text)

    # Join parts with double newlines
    result = '\n\n'.join(parts)

    # Normalize whitespace
    result = normalize_whitespace(result)

    return result

def save_markdown(out_dir: Path, post: Dict[str, Any], content_text: str) -> None:
    post_id = post.get("id", "unknown")
    title = post.get("title", {}).get("rendered", "Untitled")
    date = post.get("date", "")
    link = post.get("link", "")
    # Categories & tags from _embedded (if present)
    cats = []
    tags = []
    terms = post.get("_embedded", {}).get("wp:term", [])
    if terms:
        if len(terms) > 0:
            cats = [c.get("name") for c in terms[0]]
        if len(terms) > 1:
            tags = [t.get("name") for t in terms[1]]

    safe_name = safe_filename(title)
    filename = out_dir / f"{post_id}_{safe_name}.md"
    with open(filename, "w", encoding="utf-8") as f:
        f.write(f"# {title}\n\n")
        f.write(f"- ID: {post_id}\n")
        f.write(f"- Date: {date}\n")
        f.write(f"- URL: {link}\n")
        f.write(f"- Categories: {', '.join(cats)}\n")
        f.write(f"- Tags: {', '.join(tags)}\n\n")
        f.write("## Content\n\n")
        f.write(content_text)

# -------------------------
# Crawler
# -------------------------
def crawl_site(base_url: str, per_page: int = PER_PAGE, max_pages: Optional[int] = None):
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    session = make_session()

    page = 1
    total_posts = 0
    errors = []
    tags_count = {}
    cats_count = {}

    # first request to learn total pages (if server provides header)
    while True:
        api_url = f"{base_url.rstrip('/')}/wp-json/wp/v2/posts"
        params = {"per_page": per_page, "page": page, "_embed": ""}

        try:
            resp = session.get(api_url, params=params, timeout=REQUEST_TIMEOUT)
        except Exception as e:
            logger.error("Request exception for page %s: %s", page, e)
            errors.append(f"page {page} exception: {e}")
            break

        if resp.status_code == 200:
            try:
                posts = resp.json()
            except Exception as e:
                logger.error("JSON parse error page %s: %s", page, e)
                errors.append(f"page {page} json error: {e}")
                break

            if not posts:
                logger.info("No posts on page %s — stopping.", page)
                break

            # update category/tag counters using _embedded field
            for post in posts:
                try:
                    # extract common fields
                    raw_html = post.get("content", {}).get("rendered", "")
                    content_text = clean_content(raw_html)
                    save_markdown(DATA_DIR, post, content_text)

                    # count categories/tags
                    terms = post.get("_embedded", {}).get("wp:term", [])
                    if terms:
                        if len(terms) > 0:
                            for c in terms[0]:
                                cid, cname = c.get("id"), c.get("name")
                                if cid:
                                    cats_count[cid] = {"name": cname, "count": cats_count.get(cid, {}).get("count", 0) + 1}
                        if len(terms) > 1:
                            for t in terms[1]:
                                tid, tname = t.get("id"), t.get("name")
                                if tid:
                                    tags_count[tid] = {"name": tname, "count": tags_count.get(tid, {}).get("count", 0) + 1}

                    total_posts += 1

                except Exception as e:
                    logger.exception("Error processing post: %s", e)
                    errors.append(f"post {post.get('id', 'unknown')} error: {e}")

            logger.info("Page %d done — crawled %d posts (total: %d)", page, len(posts), total_posts)

            # Save a small log periodically (e.g., every 50 posts)
            if total_posts % 50 == 0:
                _save_log(LOG_FILE, total_posts, errors, tags_count, cats_count)

            page += 1

            # If server gives X-WP-TotalPages header, optionally stop earlier
            total_pages_header = resp.headers.get("X-WP-TotalPages")
            if total_pages_header:
                try:
                    total_pages = int(total_pages_header)
                    if page > total_pages:
                        logger.info("Reached final page reported by server: %s", total_pages)
                        break
                except Exception:
                    pass

            if max_pages and page > max_pages:
                logger.info("Reached configured max_pages: %s", max_pages)
                break

            time.sleep(CRAWL_DELAY_SECONDS)
            continue

        elif resp.status_code in (429, 503):
            # polite backoff if rate limited or service unavailable
            logger.warning("Status %s at page %s — backing off a bit", resp.status_code, page)
            time.sleep(5)
            continue
        else:
            logger.error("HTTP %s for page %s — stopping", resp.status_code, page)
            errors.append(f"page {page} http {resp.status_code}")
            break

    # final save
    _save_log(LOG_FILE, total_posts, errors, tags_count, cats_count)

    logger.info("Crawl finished. total_posts=%d, errors=%d, tags=%d, cats=%d",
                total_posts, len(errors), len(tags_count), len(cats_count))


def _save_log(path: Path, total_posts: int, errors: List[str], tags: Dict, cats: Dict):
    import json
    path.parent.mkdir(parents=True, exist_ok=True)
    data = {
        "total_posts": total_posts,
        "errors_count": len(errors),
        "errors": errors,
        "total_tags": len(tags),
        "total_categories": len(cats),
        "tags": tags,
        "categories": cats,
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


# -------------------------
# Run
# -------------------------
if __name__ == "__main__":
    # For a quick demo: crawl the uet.edu.vn site
    crawl_site(BASE_URL, per_page=PER_PAGE, max_pages=None)