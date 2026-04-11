#!/usr/bin/env python3
"""
Crawl specific pages and their related posts with full metadata.
Uses WordPress REST API to get complete metadata.
"""

import requests
from bs4 import BeautifulSoup
from pathlib import Path
import re
import time
import json
from urllib.parse import urljoin, urlparse
from typing import Optional, Dict, Any

# Configuration
TARGET_URLS = [
    "https://uet-test.uet.edu.vn/dang-uy/",
    "https://uet-test.uet.edu.vn/hoi-dong-truong/",
    "https://uet-test.uet.edu.vn/ban-giam-hieu/",
    "https://uet-test.uet.edu.vn/hoi-dong-khoa-hoc-va-dao-tao/",
    "https://uet-test.uet.edu.vn/khoa-cong-nghe-thong-tin/",
    "https://uet-test.uet.edu.vn/khoa-dien-tu-vien-thong",
    "https://uet-test.uet.edu.vn/khoa-vat-ly-ky-thuat-va-cong-nghe-nano/",
    "https://uet-test.uet.edu.vn/khoa-co-hoc-ky-thuat-va-tu-dong-hoa/",
    "https://uet-test.uet.edu.vn/khoa-cong-nghe-nong-nghiep/",
    "https://uet-test.uet.edu.vn/bo-mon-cong-nghe-xay-dung-giao-thong/",
    "https://uet-test.uet.edu.vn/vien-cong-nghe-hang-khong-vu-tru-2/",
    "https://uet-test.uet.edu.vn/vien-tri-tue-nhan-tao/",
    "https://uet-test.uet.edu.vn/?p=5208&preview=true",
    "https://uet-test.uet.edu.vn/phong-cong-tac-sinh-vien/",
    "https://uet-test.uet.edu.vn/phong-hanh-chinh-quan-tri-va-to-chuc-can-bo/",
    "https://uet-test.uet.edu.vn/phong-khoa-hoc-cong-nghe-va-hop-tac-phat-trien/",
    "https://uet-test.uet.edu.vn/phong-ke-hoach-tai-chinh/",
    "https://uet-test.uet.edu.vn/trung-tam-dai-hoc-so/",
]

BASE_DOMAIN = "uet-test.uet.edu.vn"
BASE_URL = "https://uet-test.uet.edu.vn"
OUTPUT_DIR = Path("data/raw/uet")
PROGRESS_FILE = OUTPUT_DIR / "crawl_progress.json"
SESSION_USER_AGENT = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"
CRAWL_DELAY = 0.5  # seconds between requests

visited_urls = set()
crawled_count = 0

def load_progress():
    """Load crawling progress from file."""
    global visited_urls, crawled_count

    if PROGRESS_FILE.exists():
        try:
            with open(PROGRESS_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                visited_urls = set(data.get('visited_urls', []))
                crawled_count = data.get('crawled_count', 0)
                print(f"  ✓ Resumed: {len(visited_urls)} URLs already visited, {crawled_count} pages crawled")
        except Exception as e:
            print(f"  ⚠ Could not load progress: {e}")
            visited_urls = set()
            crawled_count = 0
    else:
        print(f"  → Starting fresh crawl")

def save_progress():
    """Save crawling progress to file."""
    try:
        with open(PROGRESS_FILE, 'w', encoding='utf-8') as f:
            json.dump({
                'visited_urls': list(visited_urls),
                'crawled_count': crawled_count,
                'last_updated': time.strftime('%Y-%m-%d %H:%M:%S')
            }, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"  ⚠ Could not save progress: {e}")

def safe_filename(name: str) -> str:
    name = re.sub(r'[\\/*?:"<>|]', "", name)
    return name.strip()[:150]

def convert_table_to_markdown(table_soup) -> str:
    """Convert HTML table to Markdown table format."""
    rows = table_soup.find_all('tr')
    if not rows:
        return ""

    markdown_lines = []
    first_row = rows[0]
    has_header = bool(first_row.find_all('th'))

    if has_header:
        headers = first_row.find_all(['th', 'td'])
        header_texts = [cell.get_text(strip=True) for cell in headers]
        markdown_lines.append('| ' + ' | '.join(header_texts) + ' |')
        markdown_lines.append('|' + '|'.join(['-----'] * len(header_texts)) + '|')
        start_idx = 1
    else:
        first_cells = first_row.find_all(['td', 'th'])
        num_cols = len(first_cells)
        markdown_lines.append('| ' + ' | '.join([f'Col{i+1}' for i in range(num_cols)]) + ' |')
        markdown_lines.append('|' + '|'.join(['-----'] * num_cols) + '|')
        start_idx = 0

    for row in rows[start_idx:]:
        cells = row.find_all(['td', 'th'])
        cell_texts = [cell.get_text(strip=True) for cell in cells]
        markdown_lines.append('| ' + ' | '.join(cell_texts) + ' |')

    return '\n'.join(markdown_lines)

def convert_list_to_markdown(list_soup, ordered=False, indent_level=0) -> str:
    """Convert HTML list to Markdown."""
    items = list_soup.find_all('li', recursive=False)
    markdown_lines = []
    indent = '  ' * indent_level

    for i, item in enumerate(items, 1):
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
        marker = f"{i}." if ordered else "-"

        if item_text:
            markdown_lines.append(f"{indent}{marker} {item_text}")

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
    """Convert HTML heading to Markdown."""
    level = int(heading_soup.name[1])
    text = heading_soup.get_text(strip=True)
    return '#' * level + ' ' + text

def process_element_recursively(element) -> str:
    """Process element and children, converting to Markdown."""
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
    """Clean up excessive whitespace."""
    lines = text.split('\n')
    cleaned = []
    blank_count = 0

    for line in lines:
        if line.strip():
            cleaned.append(line.rstrip())
            blank_count = 0
        else:
            blank_count += 1
            if blank_count <= 2:
                cleaned.append('')

    while cleaned and not cleaned[-1]:
        cleaned.pop()

    return '\n'.join(cleaned)

def clean_content(html: str) -> str:
    """Convert HTML to Markdown."""
    soup = BeautifulSoup(html or "", "html.parser")

    for tag in soup(["script", "style", "noscript", "iframe"]):
        tag.decompose()

    parts = []

    for element in soup.children:
        if isinstance(element, str):
            text = element.strip()
            if text:
                parts.append(text)
            continue

        if not hasattr(element, 'name'):
            continue

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

    result = '\n\n'.join(parts)
    result = normalize_whitespace(result)
    return result

def get_metadata_from_api(url: str, session: requests.Session) -> Optional[Dict[str, Any]]:
    """Get full metadata from WordPress REST API."""
    try:
        # Extract slug from URL
        parsed = urlparse(url)
        path = parsed.path.strip('/')

        # Try to get page/post by slug
        for post_type in ['pages', 'posts']:
            api_url = f"{BASE_URL}/wp-json/wp/v2/{post_type}"
            params = {"slug": path, "_embed": ""}

            resp = session.get(api_url, params=params, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                if data and len(data) > 0:
                    return data[0]

        # If slug doesn't work, try to extract ID from URL
        if '?p=' in url:
            post_id = url.split('?p=')[1].split('&')[0]
            for post_type in ['pages', 'posts']:
                api_url = f"{BASE_URL}/wp-json/wp/v2/{post_type}/{post_id}"
                params = {"_embed": ""}

                resp = session.get(api_url, params=params, timeout=10)
                if resp.status_code == 200:
                    return resp.json()

        return None
    except Exception as e:
        print(f"  ⚠ API metadata error: {e}")
        return None

def extract_related_posts(soup, base_url):
    """Extract links from 'Bài viết liên quan' section."""
    related_links = set()

    # Look for sections with Vietnamese text
    for element in soup.find_all(['div', 'section', 'aside']):
        text = element.get_text(strip=True).lower()
        if 'bài viết liên quan' in text or 'tin liên quan' in text:
            for a_tag in element.find_all('a', href=True):
                href = a_tag['href']
                full_url = urljoin(base_url, href)
                parsed = urlparse(full_url)

                if parsed.netloc == BASE_DOMAIN:
                    clean_url = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
                    clean_url = clean_url.rstrip('/')
                    related_links.add(clean_url)

    # Also try standard selectors
    selectors = ['.related-posts', '.related-articles', '#related-posts', '[class*="related"]']
    for selector in selectors:
        elements = soup.select(selector)
        for element in elements:
            for a_tag in element.find_all('a', href=True):
                href = a_tag['href']
                full_url = urljoin(base_url, href)
                parsed = urlparse(full_url)

                if parsed.netloc == BASE_DOMAIN:
                    clean_url = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
                    clean_url = clean_url.rstrip('/')
                    related_links.add(clean_url)

    return related_links

def should_crawl_url(url):
    """Check if URL should be crawled."""
    skip_patterns = [
        '/wp-admin/', '/wp-content/', '/wp-includes/',
        '/feed/', '/rss/', '/xmlrpc.php',
        '.jpg', '.jpeg', '.png', '.gif', '.pdf', '.zip',
        '/tag/', '/category/', '/author/',
    ]

    for pattern in skip_patterns:
        if pattern in url:
            return False

    return True

def format_metadata_section(metadata: Optional[Dict[str, Any]]) -> str:
    """Format metadata as markdown section."""
    if not metadata:
        return ""

    lines = []

    # ID
    if 'id' in metadata:
        lines.append(f"- **ID**: {metadata['id']}")

    # Type
    if 'type' in metadata:
        lines.append(f"- **Type**: {metadata['type']}")

    # Status
    if 'status' in metadata:
        lines.append(f"- **Status**: {metadata['status']}")

    # Date published
    if 'date' in metadata:
        lines.append(f"- **Published**: {metadata['date']}")

    # Date modified
    if 'modified' in metadata:
        lines.append(f"- **Modified**: {metadata['modified']}")

    # Author
    if '_embedded' in metadata and 'author' in metadata['_embedded']:
        authors = metadata['_embedded']['author']
        if authors and len(authors) > 0:
            author_name = authors[0].get('name', 'Unknown')
            lines.append(f"- **Author**: {author_name}")
    elif 'author' in metadata:
        lines.append(f"- **Author ID**: {metadata['author']}")

    # Slug
    if 'slug' in metadata:
        lines.append(f"- **Slug**: {metadata['slug']}")

    # Parent
    if 'parent' in metadata and metadata['parent'] != 0:
        lines.append(f"- **Parent ID**: {metadata['parent']}")

    # Template
    if 'template' in metadata and metadata['template']:
        lines.append(f"- **Template**: {metadata['template']}")

    # Featured media
    if 'featured_media' in metadata and metadata['featured_media'] != 0:
        lines.append(f"- **Featured Media ID**: {metadata['featured_media']}")

        # Try to get featured image URL from _embedded
        if '_embedded' in metadata and 'wp:featuredmedia' in metadata['_embedded']:
            media = metadata['_embedded']['wp:featuredmedia']
            if media and len(media) > 0:
                media_url = media[0].get('source_url', '')
                if media_url:
                    lines.append(f"- **Featured Image**: {media_url}")

    # Categories
    if '_embedded' in metadata and 'wp:term' in metadata['_embedded']:
        terms = metadata['_embedded']['wp:term']
        if terms and len(terms) > 0:
            # First array is usually categories
            categories = [term.get('name') for term in terms[0] if 'name' in term]
            if categories:
                lines.append(f"- **Categories**: {', '.join(categories)}")

            # Second array is usually tags
            if len(terms) > 1:
                tags = [term.get('name') for term in terms[1] if 'name' in term]
                if tags:
                    lines.append(f"- **Tags**: {', '.join(tags)}")

    return '\n'.join(lines)

def crawl_page(url, session):
    """Crawl a single page and return related post links."""
    global crawled_count

    if url in visited_urls:
        return set()

    visited_urls.add(url)

    print(f"[{crawled_count + 1}] Crawling: {url}")

    try:
        # Get HTML content
        resp = session.get(url, timeout=15)

        if resp.status_code != 200:
            print(f"  ✗ Error: HTTP {resp.status_code}")
            return set()

        soup = BeautifulSoup(resp.text, "html.parser")

        # Get metadata from API
        metadata = get_metadata_from_api(url, session)

        # Extract title
        if metadata and 'title' in metadata:
            title = metadata['title'].get('rendered', 'Untitled')
            # Clean HTML entities
            title = BeautifulSoup(title, "html.parser").get_text()
        else:
            title_tag = soup.find('title')
            title = title_tag.get_text(strip=True) if title_tag else "Untitled"

        # Find main content
        content = None
        for selector in ['.entry-content', 'article', '.content', 'main', '#content']:
            content = soup.select_one(selector)
            if content:
                break

        if not content:
            content = soup.find('body')

        if content:
            # Convert to markdown
            content_html = str(content)
            markdown_content = clean_content(content_html)

            # Save to file
            safe_name = safe_filename(title)
            filename = OUTPUT_DIR / f"{crawled_count + 1:03d}_{safe_name}.md"

            with open(filename, "w", encoding="utf-8") as f:
                f.write(f"# {title}\n\n")

                # Write metadata section
                f.write("## Metadata\n\n")
                f.write(f"- **URL**: {url}\n")

                metadata_section = format_metadata_section(metadata)
                if metadata_section:
                    f.write(metadata_section + "\n")

                f.write("\n## Content\n\n")
                f.write(markdown_content)

            print(f"  ✓ Saved: {filename.name} ({len(markdown_content)} chars)")
            if metadata:
                print(f"    Metadata: ID={metadata.get('id')}, Type={metadata.get('type')}, Date={metadata.get('date', 'N/A')[:10]}")
            crawled_count += 1

            # Save progress after each successful crawl
            save_progress()

        # Extract related posts
        related_links = extract_related_posts(soup, url)

        # Filter links
        new_links = {link for link in related_links if should_crawl_url(link) and link not in visited_urls}

        if new_links:
            print(f"  → Found {len(new_links)} related posts")

        return new_links

    except Exception as e:
        print(f"  ✗ Exception: {e}")
        return set()

def crawl_with_related_posts(target_urls):
    """Crawl target URLs and their related posts recursively."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Load previous progress
    load_progress()

    session = requests.Session()
    session.headers.update({"User-Agent": SESSION_USER_AGENT})

    # Queue of URLs to crawl (skip already visited)
    to_crawl = [url for url in target_urls if url not in visited_urls]

    print(f"  → {len(to_crawl)} new URLs to crawl from target list\n")

    while to_crawl:
        url = to_crawl.pop(0)

        related_links = crawl_page(url, session)

        # Add related posts to queue (skip already visited)
        new_related = [link for link in related_links if link not in visited_urls]
        to_crawl.extend(new_related)

        # Be polite
        time.sleep(CRAWL_DELAY)

    # Final save
    save_progress()

    print(f"\n✓ Crawling complete! Total pages: {crawled_count}")
    print(f"  Output directory: {OUTPUT_DIR}")
    print(f"  Progress saved to: {PROGRESS_FILE}")

if __name__ == "__main__":
    print(f"Starting crawl of {len(TARGET_URLS)} target URLs")
    print(f"Will recursively crawl related posts with full metadata")
    print(f"Output: {OUTPUT_DIR}\n")

    crawl_with_related_posts(TARGET_URLS)
