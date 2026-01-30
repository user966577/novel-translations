#!/usr/bin/env python3
"""
Chinese Webnovel Text Scraper
Downloads all chapters from a novel and saves them as UTF-8 .txt files.

Supported sites:
- shuhaige.net (m.shuhaige.net)
- novel543.com
"""

import os
import re
import sys
import time
import logging
from datetime import datetime
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup
from tqdm import tqdm

# Fix Windows console encoding for Chinese characters
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")


# Configuration
DEFAULT_OUTPUT_DIR = "output"
REQUEST_DELAY = 1.5  # Seconds between requests
MAX_RETRIES = 3
REQUEST_TIMEOUT = 30

# Headers to mimic a browser
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "zh-TW,zh-CN,zh;q=0.9,en;q=0.8",
    "Cache-Control": "no-cache",
}


def setup_error_logger(novel_folder: str) -> logging.Logger:
    """Set up error logger for the novel folder."""
    logger = logging.getLogger(f"scraper_{novel_folder}")
    logger.setLevel(logging.ERROR)

    # Clear existing handlers
    logger.handlers = []

    # Create file handler
    log_path = os.path.join(novel_folder, "errors.log")
    handler = logging.FileHandler(log_path, encoding="utf-8")
    handler.setLevel(logging.ERROR)

    # Create formatter
    formatter = logging.Formatter("%(asctime)s - %(message)s")
    handler.setFormatter(formatter)

    logger.addHandler(handler)
    return logger


def fetch_page(url: str, session: requests.Session) -> BeautifulSoup | None:
    """Fetch a page and return BeautifulSoup object."""
    for attempt in range(MAX_RETRIES):
        try:
            response = session.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
            response.encoding = "utf-8"
            response.raise_for_status()
            return BeautifulSoup(response.text, "lxml")
        except requests.RequestException as e:
            if attempt < MAX_RETRIES - 1:
                time.sleep(REQUEST_DELAY * (attempt + 1))
            else:
                raise e
    return None


def detect_site(url: str) -> str:
    """Detect which site the URL is from."""
    host = urlparse(url).netloc.lower()
    if "shuhaige" in host:
        return "shuhaige"
    elif "novel543" in host:
        return "novel543"
    else:
        raise Exception(f"Unsupported site: {host}")


def extract_novel_id(novel_url: str) -> str:
    """Extract novel ID from URL."""
    # Handle various URL formats:
    # https://m.shuhaige.net/123456/ -> 123456
    # https://m.shuhaige.net/shu_123456.html -> 123456
    path = urlparse(novel_url).path.strip("/")

    # Handle shu_XXXXX.html format
    shu_match = re.search(r"shu_(\d+)\.html", path)
    if shu_match:
        return shu_match.group(1)

    # Handle /123456/ format
    parts = path.split("/")
    if parts and parts[0].isdigit():
        return parts[0]

    return ""


def extract_novel543_info(novel_url: str) -> tuple[str, str]:
    """
    Extract novel ID and section ID from novel543.com URL.
    URL formats:
    - https://www.novel543.com/1004604965/dir -> TOC
    - https://www.novel543.com/1004604965/8096_119.html -> chapter
    Returns (novel_id, section_id).
    """
    path = urlparse(novel_url).path.strip("/")
    parts = path.split("/")

    novel_id = parts[0] if parts else ""

    # Extract section ID from chapter URL like "8096_119.html"
    section_id = ""
    if len(parts) > 1 and parts[1] != "dir":
        match = re.match(r"(\d+)_", parts[1])
        if match:
            section_id = match.group(1)

    return novel_id, section_id


def get_novel543_toc_url(novel_url: str) -> str:
    """Get the TOC URL for a novel543.com novel."""
    novel_id, _ = extract_novel543_info(novel_url)
    parsed = urlparse(novel_url)
    return f"{parsed.scheme}://{parsed.netloc}/{novel_id}/dir"


def get_novel543_first_chapter(novel_url: str, session: requests.Session) -> tuple[str, str, str]:
    """
    Get the first chapter URL from novel543.com.
    If given a chapter URL, constructs chapter 1 URL.
    If given a TOC URL, tries to find chapter 1.
    Returns (novel_title, first_chapter_url, section_id).
    """
    novel_id, section_id = extract_novel543_info(novel_url)
    parsed = urlparse(novel_url)
    base_url = f"{parsed.scheme}://{parsed.netloc}"

    print(f"Novel ID: {novel_id}")

    # If we have a section_id from the URL (it was a chapter URL), construct chapter 1 directly
    if section_id:
        first_chapter_url = f"{base_url}/{novel_id}/{section_id}_1.html"
        print(f"Constructed first chapter URL: {first_chapter_url}")

        # Fetch the first chapter to get the novel title
        soup = fetch_page(first_chapter_url, session)
        if not soup:
            raise Exception(f"Failed to fetch first chapter: {first_chapter_url}")

        # Extract novel title from the chapter page
        # Look for breadcrumb or title element
        novel_title = "Unknown Novel"
        h1 = soup.find("h1")
        if h1:
            chapter_title = h1.get_text(strip=True)
            # Title is usually "Novel Name - Chapter X"
            print(f"Chapter title: {chapter_title}")

        # Try to find novel title from page title or meta
        title_tag = soup.find("title")
        if title_tag:
            page_title = title_tag.get_text(strip=True)
            # Format is typically "Chapter Title - Novel Name - Site"
            parts = page_title.split(" - ")
            if len(parts) >= 2:
                novel_title = parts[1] if len(parts) > 2 else parts[0]
            print(f"Novel title (from page): {novel_title}")

        return novel_title, first_chapter_url, section_id

    # If no section_id, try to fetch TOC
    toc_url = f"{base_url}/{novel_id}/dir"
    print(f"Fetching table of contents from: {toc_url}")

    soup = fetch_page(toc_url, session)
    if not soup:
        raise Exception(f"Failed to fetch TOC page: {toc_url}")

    # Extract novel title from h1
    h1 = soup.find("h1")
    if h1:
        novel_title = h1.get_text(strip=True)
        novel_title = re.sub(r"(章節列表|章节列表|目錄|目录)$", "", novel_title).strip()
    else:
        novel_title = "Unknown Novel"
    print(f"Novel title: {novel_title}")

    # Find chapter links
    chapter_pattern = re.compile(rf"/{novel_id}/(\d+)_(\d+)\.html")
    chapters = []

    for link in soup.find_all("a", href=True):
        href = link.get("href", "")
        match = chapter_pattern.search(href)
        if match:
            sec_id = match.group(1)
            ch_num = int(match.group(2))
            full_url = urljoin(toc_url, href)
            if full_url not in [c["url"] for c in chapters]:
                chapters.append({
                    "url": full_url,
                    "section_id": sec_id,
                    "chapter_num": ch_num
                })

    if chapters:
        chapters.sort(key=lambda x: x["chapter_num"])
        first_chapter = chapters[0]
        section_id = first_chapter["section_id"]
        print(f"Section ID: {section_id}")
        print(f"First chapter URL: {first_chapter['url']}")
        print(f"Total chapters found: {len(chapters)}")
        return novel_title, first_chapter["url"], section_id

    # Fallback: If TOC doesn't work, we need section_id from URL
    raise Exception("Could not find chapter URLs. Please provide a direct chapter URL (e.g., .../8096_1.html)")


def extract_novel543_content(soup: BeautifulSoup) -> list[str]:
    """Extract content paragraphs from a novel543.com chapter page."""
    paragraphs = []

    # novel543 uses various content containers
    # Try multiple selectors
    content_selectors = [
        "#acontent",
        "#content",
        ".content",
        ".chapter-content",
        ".readcontent",
        "article",
        "#chaptercontent",
    ]

    content_div = None
    for selector in content_selectors:
        content_div = soup.select_one(selector)
        if content_div:
            break

    if content_div:
        # Get text and split by newlines or <br> tags
        # First try to get text with separator
        text = content_div.get_text(separator="\n", strip=True)
        raw_paragraphs = [p.strip() for p in text.split("\n") if p.strip()]

        # Also check for <p> tags
        for p in content_div.find_all("p"):
            p_text = p.get_text(strip=True)
            if p_text and p_text not in raw_paragraphs:
                raw_paragraphs.append(p_text)

        paragraphs = raw_paragraphs

    # Fallback: get all <p> tags
    if not paragraphs:
        for p in soup.find_all("p"):
            text = p.get_text(strip=True)
            if text and len(text) > 10:
                paragraphs.append(text)

    # Clean content - remove ads and navigation
    ad_patterns = [
        r"http[s]?://",
        r"www\.",
        r"novel543",
        r"熱門推薦",
        r"隨機推薦",
        r"上一章",
        r"下一章",
        r"上一頁",
        r"下一頁",
        r"回目錄",
        r"目錄",
        r"章節目錄",
        r"^\d+/\d+$",  # Page numbers like "1/2"
    ]

    cleaned = []
    for p in paragraphs:
        is_ad = any(re.search(pattern, p, re.IGNORECASE) for pattern in ad_patterns)
        if not is_ad and len(p) > 2:
            cleaned.append(p)

    return cleaned


def find_novel543_navigation(soup: BeautifulSoup, base_url: str, novel_id: str, section_id: str, current_chapter_num: int) -> dict:
    """
    Find next page and next chapter navigation for novel543.com.

    Note: novel543 uses confusing naming - "下一章" can mean either:
    - Next page of same chapter (8096_1.html -> 8096_1_2.html)
    - Actual next chapter (8096_1.html -> 8096_2.html)

    We determine this by checking the URL pattern.
    Returns {'next_page': url or None, 'next_chapter': url or None}
    """
    result = {"next_page": None, "next_chapter": None}

    for link in soup.find_all("a", href=True):
        link_text = link.get_text(strip=True)
        href = link["href"]
        full_url = urljoin(base_url, href)

        # Check for navigation links (下一章 can be misleading)
        if "下一章" in link_text or "下一頁" in link_text or "下一页" in link_text:
            # Check if this is a sub-page of the current chapter
            # Pattern: section_chapterNum_pageNum.html (e.g., 8096_1_2.html)
            subpage_match = re.search(rf"/{section_id}_{current_chapter_num}_(\d+)\.html", href)
            if subpage_match:
                result["next_page"] = full_url
                continue

            # Check if this is the next chapter
            # Pattern: section_nextChapterNum.html (e.g., 8096_2.html)
            next_ch_match = re.search(rf"/{section_id}_(\d+)\.html", href)
            if next_ch_match:
                ch_num = int(next_ch_match.group(1))
                if ch_num == current_chapter_num + 1:
                    result["next_chapter"] = full_url

    return result


def extract_novel543_chapter(start_url: str, session: requests.Session, novel_id: str, section_id: str, delay: float = REQUEST_DELAY) -> dict:
    """
    Extract complete chapter content from novel543.com by following pagination.
    Returns dict with 'title', 'content', 'next_chapter_url', 'page_count'.
    """
    all_paragraphs = []
    current_url = start_url
    title = None
    next_chapter_url = None
    page_count = 0

    # Extract chapter number from URL to construct next chapter URL
    ch_match = re.search(rf"/{section_id}_(\d+)(?:_\d+)?\.html", start_url)
    current_chapter_num = int(ch_match.group(1)) if ch_match else 1

    while current_url:
        page_count += 1

        soup = fetch_page(current_url, session)
        if not soup:
            raise Exception(f"Failed to fetch chapter page: {current_url}")

        # Extract title only from the first page
        if title is None:
            h1 = soup.find("h1")
            if h1:
                title = h1.get_text(strip=True)
                # Remove page indicator like "(1/2)"
                title = re.sub(r"\s*\(\d+/\d+\)\s*$", "", title)
            else:
                title = "Untitled"

        # Extract content from this page
        paragraphs = extract_novel543_content(soup)
        all_paragraphs.extend(paragraphs)

        # Find navigation links
        nav_links = find_novel543_navigation(soup, current_url, novel_id, section_id, current_chapter_num)

        # Follow sub-pages of the same chapter
        if nav_links["next_page"]:
            current_url = nav_links["next_page"]
            time.sleep(delay)
            continue

        # No more sub-pages - get next chapter URL or construct it
        if nav_links["next_chapter"]:
            next_chapter_url = nav_links["next_chapter"]
        else:
            # Construct next chapter URL
            next_chapter_num = current_chapter_num + 1
            parsed = urlparse(start_url)
            next_chapter_url = f"{parsed.scheme}://{parsed.netloc}/{novel_id}/{section_id}_{next_chapter_num}.html"
        break

    content = "\n\n".join(all_paragraphs)

    return {
        "title": title,
        "content": content,
        "next_chapter_url": next_chapter_url,
        "page_count": page_count
    }


def get_novel_title(soup: BeautifulSoup) -> str:
    """Extract novel title from the TOC page."""
    # Try various selectors for the novel title
    title_elem = soup.select_one("h1.title, h1, .booktitle, .bookname")
    if title_elem:
        title = title_elem.get_text(strip=True)
        # Remove common suffixes like "目录" or "章节列表"
        title = re.sub(r"(目录|章节列表|全文阅读|列表)$", "", title).strip()
        return title
    return "Unknown Novel"


def get_chapter_list(novel_url: str, session: requests.Session) -> tuple[str, list[dict]]:
    """
    Fetch all chapter URLs from the paginated table of contents.
    Returns (novel_title, list of chapter info dicts).
    """
    chapters = []
    novel_id = extract_novel_id(novel_url)

    if not novel_id:
        raise Exception(f"Could not extract novel ID from URL: {novel_url}")

    # Construct the TOC URL from the novel ID
    # The chapter list is always at /{novel_id}/
    parsed = urlparse(novel_url)
    base_url = f"{parsed.scheme}://{parsed.netloc}/{novel_id}/"

    print(f"Novel ID: {novel_id}")
    print(f"Fetching table of contents from: {base_url}")

    # Fetch the main TOC page
    soup = fetch_page(base_url, session)
    if not soup:
        raise Exception(f"Failed to fetch TOC page: {base_url}")

    novel_title = get_novel_title(soup)
    print(f"Novel title: {novel_title}")

    # Find all chapter links
    # Chapters are typically in <a> tags with href like /novel_id/chapter_id.html
    chapter_pattern = re.compile(rf"/{novel_id}/\d+\.html")

    # Collect chapters from current page
    def extract_chapters_from_page(page_soup: BeautifulSoup) -> list[dict]:
        page_chapters = []
        for link in page_soup.find_all("a", href=True):
            href = link["href"]
            if chapter_pattern.search(href):
                chapter_url = urljoin(base_url, href)
                chapter_title = link.get_text(strip=True)
                if chapter_url not in [c["url"] for c in page_chapters]:
                    page_chapters.append({
                        "url": chapter_url,
                        "title": chapter_title
                    })
        return page_chapters

    chapters.extend(extract_chapters_from_page(soup))

    # Check for pagination - find the maximum page number
    # Pagination uses format: /{novel_id}_2/, /{novel_id}_3/, etc.
    max_page = 1
    page_pattern = re.compile(rf"/{novel_id}_(\d+)/?")

    for link in soup.find_all("a", href=True):
        href = link.get("href", "")
        match = page_pattern.search(href)
        if match:
            page_num = int(match.group(1))
            max_page = max(max_page, page_num)

    # Fetch all additional TOC pages
    if max_page > 1:
        print(f"Found {max_page} TOC pages")
        parsed = urlparse(base_url)

        for page_num in range(2, max_page + 1):
            page_url = f"{parsed.scheme}://{parsed.netloc}/{novel_id}_{page_num}/"
            time.sleep(REQUEST_DELAY)
            print(f"Fetching TOC page {page_num}/{max_page}: {page_url}")
            page_soup = fetch_page(page_url, session)
            if page_soup:
                new_chapters = extract_chapters_from_page(page_soup)
                for ch in new_chapters:
                    if ch["url"] not in [c["url"] for c in chapters]:
                        chapters.append(ch)

    # Sort chapters by URL (which typically contains chapter number)
    def get_chapter_num_from_url(ch: dict) -> int:
        match = re.search(r"/(\d+)\.html", ch["url"])
        return int(match.group(1)) if match else 0

    chapters.sort(key=get_chapter_num_from_url)

    print(f"Found {len(chapters)} chapters")
    return novel_title, chapters


def extract_chapter_number(title: str) -> int | None:
    """Extract chapter number from title like '第1章 ...' or '第一百章 ...'"""
    # Try numeric format first: 第1章, 第123章
    match = re.search(r"第(\d+)章", title)
    if match:
        return int(match.group(1))

    # Try to extract any leading number
    match = re.search(r"^(\d+)", title)
    if match:
        return int(match.group(1))

    return None


def extract_content_from_page(soup: BeautifulSoup) -> list[str]:
    """
    Extract content paragraphs from a chapter page.
    Returns list of cleaned paragraph strings.
    """
    # Extract content from <p> tags
    # The main content is usually in a div with class like 'content' or 'chapter-content'
    content_div = soup.select_one("#chaptercontent, .content, .chapter-content, #content, .readcontent")

    paragraphs = []
    if content_div:
        # Get all text, handling <p> tags and <br> tags
        for elem in content_div.find_all(["p", "br"]):
            if elem.name == "p":
                text = elem.get_text(strip=True)
                if text:
                    paragraphs.append(text)

        # If no <p> tags found, try getting direct text
        if not paragraphs:
            # Get text and split by <br> tags
            text = content_div.get_text(separator="\n", strip=True)
            paragraphs = [p.strip() for p in text.split("\n") if p.strip()]
    else:
        # Fallback: find all <p> tags on the page
        for p in soup.find_all("p"):
            text = p.get_text(strip=True)
            if text and len(text) > 10:  # Filter out short navigation text
                paragraphs.append(text)

    # Clean content - remove common ads and navigation text
    cleaned_paragraphs = []
    ad_patterns = [
        r"http[s]?://",
        r"www\.",
        r"请记住本站",
        r"手机阅读",
        r"最新章节",
        r"推荐阅读",
        r"加入书签",
        r"上一章",
        r"下一章",
        r"上一页",
        r"下一页",
        r"目录",
        r"书海阁",
        r"shuhaige",
        r"手机版",
        r"novel543",
        r"熱門推薦",
        r"隨機推薦",
        r"回目錄",
    ]

    for p in paragraphs:
        is_ad = any(re.search(pattern, p, re.IGNORECASE) for pattern in ad_patterns)
        if not is_ad and len(p) > 2:
            cleaned_paragraphs.append(p)

    return cleaned_paragraphs


def find_navigation_links(soup: BeautifulSoup, base_url: str) -> dict:
    """
    Find next page and next chapter navigation links.
    Returns {'next_page': url or None, 'next_chapter': url or None}
    """
    result = {"next_page": None, "next_chapter": None}

    for link in soup.find_all("a", href=True):
        link_text = link.get_text(strip=True)
        href = link["href"]

        # Check for "next page" (下一页) - same chapter, next part
        if "下一页" in link_text:
            result["next_page"] = urljoin(base_url, href)

        # Check for "next chapter" (下一章) - new chapter
        elif "下一章" in link_text:
            result["next_chapter"] = urljoin(base_url, href)

    return result


def extract_chapter_with_parts(start_url: str, session: requests.Session, delay: float = REQUEST_DELAY) -> dict:
    """
    Extract complete chapter content by following 'next page' links.
    Combines all parts of a multi-page chapter into one.

    Returns dict with 'title', 'content', 'next_chapter_url'.
    """
    all_paragraphs = []
    current_url = start_url
    title = None
    next_chapter_url = None
    page_count = 0

    while current_url:
        page_count += 1

        soup = fetch_page(current_url, session)
        if not soup:
            raise Exception(f"Failed to fetch chapter page: {current_url}")

        # Extract title only from the first page
        if title is None:
            h1 = soup.find("h1")
            title = h1.get_text(strip=True) if h1 else "Untitled"

        # Extract content from this page
        paragraphs = extract_content_from_page(soup)
        all_paragraphs.extend(paragraphs)

        # Find navigation links
        nav_links = find_navigation_links(soup, current_url)

        # If there's a "next page" link, follow it (same chapter continues)
        if nav_links["next_page"]:
            current_url = nav_links["next_page"]
            time.sleep(delay)  # Rate limit between page fetches
        else:
            # No more pages for this chapter
            next_chapter_url = nav_links["next_chapter"]
            break

    content = "\n\n".join(all_paragraphs)

    return {
        "title": title,
        "content": content,
        "next_chapter_url": next_chapter_url,
        "page_count": page_count
    }


def extract_chapter(chapter_url: str, session: requests.Session) -> dict:
    """
    Extract title and content from a chapter page (legacy single-page version).
    Returns dict with 'title' and 'content' keys.
    """
    soup = fetch_page(chapter_url, session)
    if not soup:
        raise Exception(f"Failed to fetch chapter: {chapter_url}")

    # Extract chapter title from <h1>
    h1 = soup.find("h1")
    title = h1.get_text(strip=True) if h1 else "Untitled"

    paragraphs = extract_content_from_page(soup)
    content = "\n\n".join(paragraphs)

    return {
        "title": title,
        "content": content
    }


def sanitize_filename(title: str) -> str:
    """Remove invalid characters for Windows filenames."""
    # Remove or replace invalid characters
    invalid_chars = r'<>:"/\|?*'
    result = title
    for char in invalid_chars:
        result = result.replace(char, "")

    # Replace multiple spaces with single space
    result = re.sub(r"\s+", " ", result).strip()

    # Limit filename length (Windows has 255 char limit for full path)
    if len(result) > 100:
        result = result[:100]

    return result


def save_chapter(novel_folder: str, chapter_num: int, title: str, content: str) -> str:
    """
    Save chapter as .txt file.
    Returns the saved filename.
    """
    # Create filename: 001_第1章_标题.txt
    safe_title = sanitize_filename(title)
    filename = f"{chapter_num:03d}_{safe_title}.txt"
    filepath = os.path.join(novel_folder, filename)

    # Prepare content with title header
    full_content = f"{title}\n\n{'=' * 40}\n\n{content}"

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(full_content)

    return filename


def get_existing_chapters(novel_folder: str) -> set[int]:
    """Get set of already downloaded chapter numbers."""
    existing = set()
    if not os.path.exists(novel_folder):
        return existing

    for filename in os.listdir(novel_folder):
        if filename.endswith(".txt"):
            # Extract chapter number from filename like "001_..."
            match = re.match(r"(\d+)_", filename)
            if match:
                existing.add(int(match.group(1)))

    return existing


def get_first_chapter_url(novel_url: str, session: requests.Session) -> tuple[str, str, str]:
    """
    Get the first chapter URL from the table of contents.
    Returns (novel_title, first_chapter_url, novel_folder_name).
    """
    novel_id = extract_novel_id(novel_url)

    if not novel_id:
        raise Exception(f"Could not extract novel ID from URL: {novel_url}")

    # Construct the TOC URL from the novel ID
    parsed = urlparse(novel_url)
    base_url = f"{parsed.scheme}://{parsed.netloc}/{novel_id}/"

    print(f"Novel ID: {novel_id}")
    print(f"Fetching table of contents from: {base_url}")

    # Fetch the main TOC page
    soup = fetch_page(base_url, session)
    if not soup:
        raise Exception(f"Failed to fetch TOC page: {base_url}")

    novel_title = get_novel_title(soup)
    print(f"Novel title: {novel_title}")

    # Find the first chapter link
    # Chapters are typically in <a> tags with href like /novel_id/chapter_id.html
    chapter_pattern = re.compile(rf"/{novel_id}/\d+\.html")

    first_chapter_url = None
    first_chapter_id = float("inf")

    for link in soup.find_all("a", href=True):
        href = link["href"]
        if chapter_pattern.search(href):
            # Extract chapter ID to find the smallest (first)
            match = re.search(r"/(\d+)\.html", href)
            if match:
                chapter_id = int(match.group(1))
                if chapter_id < first_chapter_id:
                    first_chapter_id = chapter_id
                    first_chapter_url = urljoin(base_url, href)

    if not first_chapter_url:
        raise Exception("Could not find first chapter URL in TOC")

    print(f"First chapter URL: {first_chapter_url}")

    return novel_title, first_chapter_url, sanitize_filename(novel_title)


def scrape_novel_by_navigation(
    novel_url: str,
    output_dir: str = DEFAULT_OUTPUT_DIR,
    delay: float = REQUEST_DELAY,
    max_chapters: int | None = None,
    english_title: str | None = None,
    start_chapter: int = 1
):
    """
    Scrape novel by following navigation links instead of using TOC.
    This correctly handles chapters split across multiple pages.

    Args:
        novel_url: URL to the novel's table of contents
        output_dir: Directory to save downloaded novels
        delay: Delay between requests in seconds
        max_chapters: Maximum number of chapters to download (None = unlimited)
        english_title: English title for the novel folder (optional)
        start_chapter: Chapter number to start from (default: 1)
    """
    # Detect which site we're scraping
    site = detect_site(novel_url)

    print(f"\n{'=' * 60}")
    print(f"Chinese Webnovel Scraper")
    print(f"Site: {site}")
    print("(Navigation-based scraping mode)")
    print(f"{'=' * 60}\n")

    # Create session for connection pooling
    session = requests.Session()

    # Site-specific variables
    novel_id = ""
    section_id = ""

    try:
        # Get first chapter URL from TOC (site-specific)
        if site == "novel543":
            novel_title, first_chapter_url, section_id = get_novel543_first_chapter(novel_url, session)
            novel_id, _ = extract_novel543_info(novel_url)
            safe_novel_title = sanitize_filename(novel_title)
        else:
            novel_title, first_chapter_url, safe_novel_title = get_first_chapter_url(novel_url, session)

        # Use English title for folder if provided
        if english_title:
            folder_name = english_title
            print(f"Using English title for folder: {folder_name}")
        else:
            folder_name = safe_novel_title

        # Create novel folder
        novel_folder = os.path.join(output_dir, folder_name)
        os.makedirs(novel_folder, exist_ok=True)

        # Set up error logger
        logger = setup_error_logger(novel_folder)

        # Get existing chapters for resume capability
        existing_chapters = get_existing_chapters(novel_folder)
        if existing_chapters:
            print(f"Found {len(existing_chapters)} existing chapters")

        # Determine starting chapter and URL
        chapter_num = start_chapter
        if site == "novel543" and start_chapter > 1:
            # For novel543, we can construct the start URL directly
            parsed = urlparse(novel_url)
            current_url = f"{parsed.scheme}://{parsed.netloc}/{novel_id}/{section_id}_{start_chapter}.html"
            print(f"Starting from chapter {start_chapter}: {current_url}")
        else:
            current_url = first_chapter_url
            if start_chapter > 1:
                print(f"Warning: --start-chapter requires crawling for {site}, starting from chapter 1")
                chapter_num = 1

        downloaded = 0
        skipped = 0
        failed = 0

        print(f"\nDownloading chapters to: {novel_folder}")
        if max_chapters:
            print(f"Maximum chapters: {max_chapters}")
        print()

        while current_url:
            # Check max chapters limit
            if max_chapters and (chapter_num - start_chapter + 1) > max_chapters:
                print(f"\nReached maximum chapter limit ({max_chapters})")
                break

            try:
                # Skip if already downloaded
                if chapter_num in existing_chapters:
                    # For novel543, construct next URL directly (no fetching needed)
                    if site == "novel543":
                        print(f"Chapter {chapter_num}: Skipping (already exists)")
                        parsed = urlparse(novel_url)
                        current_url = f"{parsed.scheme}://{parsed.netloc}/{novel_id}/{section_id}_{chapter_num + 1}.html"
                    else:
                        # For shuhaige, must fetch to get next chapter URL
                        print(f"Chapter {chapter_num}: Skipping (already exists), fetching next URL...")
                        chapter_data = extract_chapter_with_parts(current_url, session, delay)
                        current_url = chapter_data["next_chapter_url"]
                        time.sleep(delay)
                    chapter_num += 1
                    skipped += 1
                    continue

                # Rate limiting (except for first chapter)
                if downloaded > 0:
                    time.sleep(delay)

                # Extract complete chapter (including all pages) - site-specific
                print(f"Chapter {chapter_num}: Fetching from {current_url}")
                if site == "novel543":
                    chapter_data = extract_novel543_chapter(current_url, session, novel_id, section_id, delay)
                else:
                    chapter_data = extract_chapter_with_parts(current_url, session, delay)

                # Try to get chapter number from title
                title_num = extract_chapter_number(chapter_data["title"])
                save_num = title_num if title_num else chapter_num

                # Save chapter
                filename = save_chapter(
                    novel_folder,
                    save_num,
                    chapter_data["title"],
                    chapter_data["content"]
                )

                page_info = f" ({chapter_data['page_count']} pages)" if chapter_data["page_count"] > 1 else ""
                print(f"  -> Saved: {filename}{page_info}")

                downloaded += 1

                # Move to next chapter
                current_url = chapter_data["next_chapter_url"]
                chapter_num += 1

            except Exception as e:
                failed += 1
                error_msg = f"Chapter {chapter_num} ({current_url}): {str(e)}"
                logger.error(error_msg)
                print(f"  -> Error: {error_msg}")

                # Try to continue by constructing next chapter URL
                # This is a fallback - may not work for all cases
                break

        # Print summary
        print(f"\n{'=' * 60}")
        print("Download Complete!")
        print(f"{'=' * 60}")
        print(f"Downloaded: {downloaded} chapters")
        print(f"Skipped (existing): {skipped} chapters")
        print(f"Failed: {failed} chapters")
        print(f"Output folder: {novel_folder}")

        if failed > 0:
            print(f"\nFailed chapters logged to: {os.path.join(novel_folder, 'errors.log')}")

        if not current_url:
            print("\nReached end of novel (no more chapters)")

    except Exception as e:
        print(f"\nFatal error: {str(e)}")
        raise
    finally:
        session.close()


def scrape_novel(novel_url: str, output_dir: str = DEFAULT_OUTPUT_DIR, delay: float = REQUEST_DELAY):
    """
    Main function to scrape an entire novel.

    Args:
        novel_url: URL to the novel's table of contents on shuhaige.net
        output_dir: Directory to save downloaded novels
        delay: Delay between requests in seconds
    """
    print(f"\n{'=' * 60}")
    print("Chinese Webnovel Scraper for shuhaige.net")
    print(f"{'=' * 60}\n")

    # Create session for connection pooling
    session = requests.Session()

    try:
        # Get chapter list
        novel_title, chapters = get_chapter_list(novel_url, session)

        if not chapters:
            print("No chapters found!")
            return

        # Create novel folder
        safe_novel_title = sanitize_filename(novel_title)
        novel_folder = os.path.join(output_dir, safe_novel_title)
        os.makedirs(novel_folder, exist_ok=True)

        # Set up error logger
        logger = setup_error_logger(novel_folder)

        # Get existing chapters for resume capability
        existing_chapters = get_existing_chapters(novel_folder)
        if existing_chapters:
            print(f"Found {len(existing_chapters)} existing chapters, will skip them")

        # Download chapters
        print(f"\nDownloading {len(chapters)} chapters to: {novel_folder}\n")

        downloaded = 0
        skipped = 0
        failed = 0

        for idx, chapter_info in enumerate(tqdm(chapters, desc="Downloading", unit="chapter")):
            chapter_num = idx + 1

            # Skip if already downloaded
            if chapter_num in existing_chapters:
                skipped += 1
                continue

            try:
                # Rate limiting
                if downloaded > 0:
                    time.sleep(delay)

                # Extract chapter content
                chapter_data = extract_chapter(chapter_info["url"], session)

                # Try to get chapter number from title
                title_num = extract_chapter_number(chapter_data["title"])
                if title_num:
                    chapter_num = title_num

                # Save chapter
                save_chapter(
                    novel_folder,
                    chapter_num if title_num else idx + 1,
                    chapter_data["title"],
                    chapter_data["content"]
                )

                downloaded += 1

            except Exception as e:
                failed += 1
                error_msg = f"Chapter {chapter_num} ({chapter_info['url']}): {str(e)}"
                logger.error(error_msg)
                tqdm.write(f"Error: {error_msg}")

        # Print summary
        print(f"\n{'=' * 60}")
        print("Download Complete!")
        print(f"{'=' * 60}")
        print(f"Downloaded: {downloaded} chapters")
        print(f"Skipped (existing): {skipped} chapters")
        print(f"Failed: {failed} chapters")
        print(f"Output folder: {novel_folder}")

        if failed > 0:
            print(f"\nFailed chapters logged to: {os.path.join(novel_folder, 'errors.log')}")

    except Exception as e:
        print(f"\nFatal error: {str(e)}")
        raise
    finally:
        session.close()


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Download Chinese webnovels. Supported sites: shuhaige.net, novel543.com"
    )
    parser.add_argument(
        "novel_url",
        help="URL to the novel's TOC or any chapter (e.g., https://m.shuhaige.net/123456/ or https://www.novel543.com/123456/dir)"
    )
    parser.add_argument(
        "-o", "--output",
        default=DEFAULT_OUTPUT_DIR,
        help=f"Output directory (default: {DEFAULT_OUTPUT_DIR})"
    )
    parser.add_argument(
        "-d", "--delay",
        type=float,
        default=REQUEST_DELAY,
        help=f"Delay between requests in seconds (default: {REQUEST_DELAY})"
    )
    parser.add_argument(
        "-m", "--max-chapters",
        type=int,
        default=None,
        help="Maximum number of chapters to download (default: unlimited)"
    )
    parser.add_argument(
        "-e", "--english-title",
        type=str,
        default=None,
        help="English title for the novel folder (default: uses Chinese title from site)"
    )
    parser.add_argument(
        "-s", "--start-chapter",
        type=int,
        default=1,
        help="Chapter number to start from (default: 1, only works efficiently for novel543.com)"
    )
    parser.add_argument(
        "--legacy",
        action="store_true",
        help="Use legacy TOC-based scraping (doesn't handle split chapters, shuhaige only)"
    )

    args = parser.parse_args()

    if args.legacy:
        scrape_novel(args.novel_url, args.output, args.delay)
    else:
        scrape_novel_by_navigation(args.novel_url, args.output, args.delay, args.max_chapters, args.english_title, args.start_chapter)


if __name__ == "__main__":
    main()
