#!/usr/bin/env python3
"""
Chinese Webnovel Text Scraper
Downloads all chapters from a novel and saves them as UTF-8 .txt files.

Supported sites:
- shuhaige.net (m.shuhaige.net)
- novel543.com
- wxdzs.net (无线电子书)
- jpxs123.com (精品小说网)
- wfxs.tw (m.wfxs.tw) - 無妨小說
- uukanshu.cc (UU看书)
"""

import os
import re
import sys
import time
import logging
from datetime import datetime
from urllib.parse import urljoin, urlparse

import requests
import urllib3
from bs4 import BeautifulSoup
from tqdm import tqdm

# Suppress SSL warnings for sites with certificate issues (like wxdzs.net)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

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


def fetch_page(url: str, session: requests.Session, verify_ssl: bool = True, encoding: str | None = None) -> BeautifulSoup | None:
    """Fetch a page and return BeautifulSoup object.

    Args:
        url: The URL to fetch
        session: requests Session object
        verify_ssl: Whether to verify SSL certificates
        encoding: Force a specific encoding. If None, uses apparent_encoding for Chinese sites.
    """
    for attempt in range(MAX_RETRIES):
        try:
            response = session.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT, verify=verify_ssl)

            # Determine encoding: use provided encoding, apparent_encoding for Chinese sites, or UTF-8
            if encoding:
                response.encoding = encoding
            elif response.apparent_encoding and response.apparent_encoding.lower() in ("gb18030", "gb2312", "gbk"):
                # Chinese encoding detected - use it
                response.encoding = response.apparent_encoding
            else:
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
    elif "wxdzs" in host:
        return "wxdzs"
    elif "jpxs123" in host:
        return "jpxs123"
    elif "wfxs" in host:
        return "wfxs"
    elif "uukanshu" in host:
        return "uukanshu"
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


def get_novel543_first_chapter(novel_url: str, session: requests.Session, start_chapter: int = 1, skip_title_fetch: bool = False) -> tuple[str, str, str]:
    """
    Get the first chapter URL from novel543.com.
    If given a chapter URL, constructs chapter 1 URL (or start_chapter URL).
    If given a TOC URL, tries to find chapter 1.
    Returns (novel_title, first_chapter_url, section_id).
    """
    novel_id, section_id = extract_novel543_info(novel_url)
    parsed = urlparse(novel_url)
    base_url = f"{parsed.scheme}://{parsed.netloc}"

    print(f"Novel ID: {novel_id}")

    # If we have a section_id from the URL (it was a chapter URL), construct the start chapter URL
    if section_id:
        first_chapter_url = f"{base_url}/{novel_id}/{section_id}_{start_chapter}.html"
        print(f"Constructed chapter URL: {first_chapter_url}")

        # If english_title is provided, skip fetching just for the title
        if skip_title_fetch:
            print("Skipping title fetch (English title provided)")
            return "Unknown Novel", first_chapter_url, section_id

        # Fetch the chapter to get the novel title
        soup = fetch_page(first_chapter_url, session)
        if not soup:
            raise Exception(f"Failed to fetch chapter: {first_chapter_url}")

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
    Returns {'next_page': url or None, 'next_chapter': url or None, 'is_end': bool}
    """
    result = {"next_page": None, "next_chapter": None, "is_end": False}

    for link in soup.find_all("a", href=True):
        link_text = link.get_text(strip=True)
        href = link["href"]
        full_url = urljoin(base_url, href)

        # Check for navigation links (下一章 can be misleading)
        if "下一章" in link_text or "下一頁" in link_text or "下一页" in link_text:
            # Check if this links to the end page (novel finished)
            if "/end.html" in href:
                result["is_end"] = True
                continue

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

        # Check if we've reached the end of the novel
        if nav_links["is_end"]:
            next_chapter_url = None
            break

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


def extract_wxdzs_info(novel_url: str) -> tuple[str, str]:
    """
    Extract novel ID and chapter ID from wxdzs.net URL.
    URL formats:
    - https://www.wxdzs.net/wxbook/94900.html -> novel page
    - https://www.wxdzs.net/wxchapter/94900.html -> chapter list
    - https://www.wxdzs.net/wxread/94900_43871003.html -> chapter page
    Returns (novel_id, chapter_id).
    """
    path = urlparse(novel_url).path.strip("/")

    # Handle /wxbook/94900.html format (novel page)
    book_match = re.search(r"wxbook/(\d+)\.html", path)
    if book_match:
        return book_match.group(1), ""

    # Handle /wxchapter/94900.html format (chapter list)
    chapter_list_match = re.search(r"wxchapter/(\d+)\.html", path)
    if chapter_list_match:
        return chapter_list_match.group(1), ""

    # Handle /wxread/94900_43871003.html format (chapter page)
    read_match = re.search(r"wxread/(\d+)_(\d+)\.html", path)
    if read_match:
        return read_match.group(1), read_match.group(2)

    return "", ""


def get_wxdzs_first_chapter(novel_url: str, session: requests.Session, start_chapter: int = 1, skip_title_fetch: bool = False) -> tuple[str, str, list[dict]]:
    """
    Get the first chapter URL from wxdzs.net.
    Returns (novel_title, first_chapter_url, chapter_list).
    """
    novel_id, chapter_id = extract_wxdzs_info(novel_url)
    parsed = urlparse(novel_url)
    base_url = f"{parsed.scheme}://{parsed.netloc}"

    print(f"Novel ID: {novel_id}")

    # If we have a chapter_id from the URL (it was a chapter URL), use it directly
    if chapter_id:
        first_chapter_url = f"{base_url}/wxread/{novel_id}_{chapter_id}.html"
        print(f"Using provided chapter URL: {first_chapter_url}")

        if skip_title_fetch:
            print("Skipping title fetch (English title provided)")
            return "Unknown Novel", first_chapter_url, []

        # Fetch the chapter to get the novel title (wxdzs has SSL issues, so verify=False)
        soup = fetch_page(first_chapter_url, session, verify_ssl=False)
        if not soup:
            raise Exception(f"Failed to fetch chapter: {first_chapter_url}")

        # Extract novel title from page
        novel_title = "Unknown Novel"
        title_tag = soup.find("title")
        if title_tag:
            page_title = title_tag.get_text(strip=True)
            # Format is "小说名 章节名 无线电子书"
            parts = page_title.split()
            if len(parts) >= 2:
                novel_title = parts[0]
            print(f"Novel title (from page): {novel_title}")

        return novel_title, first_chapter_url, []

    # Fetch the chapter list page (wxdzs has SSL issues, so verify=False)
    chapter_list_url = f"{base_url}/wxchapter/{novel_id}.html"
    print(f"Fetching chapter list from: {chapter_list_url}")

    soup = fetch_page(chapter_list_url, session, verify_ssl=False)
    if not soup:
        raise Exception(f"Failed to fetch chapter list: {chapter_list_url}")

    # Extract novel title
    novel_title = "Unknown Novel"
    title_div = soup.select_one("div")
    for div in soup.find_all("div"):
        text = div.get_text(strip=True)
        if text and not text.startswith("当前位置") and not text.startswith("作者") and len(text) > 2 and len(text) < 50:
            # Check if this looks like a title (not navigation text)
            if "首页" not in text and ">" not in text:
                novel_title = text
                break

    # Try to get from page title
    title_tag = soup.find("title")
    if title_tag:
        page_title = title_tag.get_text(strip=True)
        # Format: "小说名章节目录 无线电子书"
        if "章节目录" in page_title:
            novel_title = page_title.split("章节目录")[0].strip()

    print(f"Novel title: {novel_title}")

    # Find all chapter links
    # wxdzs lists chapters in order on the page, but also has a "最新章节" section at top
    # We need to skip the "最新章节" section and only capture the main chapter list
    chapter_pattern = re.compile(rf"/wxread/{novel_id}_(\d+)\.html")
    chapters = []
    seen_urls = set()
    in_chapter_list = False

    for link in soup.find_all("a", href=True):
        href = link.get("href", "")
        ch_title = link.get_text(strip=True)

        # Start capturing once we see "第一章" or similar first chapter indicator
        if not in_chapter_list:
            if ch_title.startswith("第一章") or ch_title.startswith("第1章") or ch_title.startswith("第01章"):
                in_chapter_list = True
            else:
                continue

        match = chapter_pattern.search(href)
        if match:
            ch_id = match.group(1)
            full_url = urljoin(chapter_list_url, href)
            if full_url not in seen_urls:
                seen_urls.add(full_url)
                chapters.append({
                    "url": full_url,
                    "chapter_id": ch_id,
                    "title": ch_title
                })

    # Chapters should already be in order from the page, but let's verify
    # by checking if the first few are in sequence

    if chapters:
        # Start from the requested chapter (1-indexed)
        if start_chapter > 1 and start_chapter <= len(chapters):
            first_chapter = chapters[start_chapter - 1]
            print(f"Starting from chapter {start_chapter}: {first_chapter['title']}")
        else:
            first_chapter = chapters[0]

        print(f"First chapter URL: {first_chapter['url']}")
        print(f"Total chapters found: {len(chapters)}")
        return novel_title, first_chapter["url"], chapters

    raise Exception("Could not find chapter URLs. Please check the URL format.")


def extract_wxdzs_content(soup: BeautifulSoup) -> list[str]:
    """Extract content paragraphs from a wxdzs.net chapter page."""
    paragraphs = []

    # wxdzs uses paragraphs inside a container div
    # Find the main content area (after the h1 title)
    h1 = soup.find("h1")
    if h1:
        # Find the parent container and get paragraphs after h1
        parent = h1.parent
        if parent:
            for p in parent.find_all("p"):
                text = p.get_text(strip=True)
                if text:
                    paragraphs.append(text)

    # If no paragraphs found, try broader search
    if not paragraphs:
        for p in soup.find_all("p"):
            text = p.get_text(strip=True)
            if text and len(text) > 5:
                paragraphs.append(text)

    # Clean content - remove ads and navigation
    ad_patterns = [
        r"http[s]?://",
        r"www\.",
        r"wxdzs",
        r"无线电子书",
        r"上一章",
        r"下一章",
        r"书页",
        r"设置",
        r"点这里听书",
        r"已支持Chrome",
        r"^\*已支持",
    ]

    cleaned = []
    for p in paragraphs:
        is_ad = any(re.search(pattern, p, re.IGNORECASE) for pattern in ad_patterns)
        if not is_ad and len(p) > 2:
            cleaned.append(p)

    return cleaned


def find_wxdzs_navigation(soup: BeautifulSoup, base_url: str, novel_id: str) -> dict:
    """
    Find next chapter navigation for wxdzs.net.
    Returns {'next_chapter': url or None, 'is_end': bool}
    """
    result = {"next_chapter": None, "is_end": False}

    for link in soup.find_all("a", href=True):
        link_text = link.get_text(strip=True)
        href = link["href"]

        # Skip javascript links
        if href.startswith("javascript:"):
            continue

        # Check for "next chapter" (下一章)
        if "下一章" in link_text:
            # Check if it's an actual chapter URL
            if f"/wxread/{novel_id}_" in href:
                result["next_chapter"] = urljoin(base_url, href)

    # Also check for generic "下一章" divs that might be clickable
    for div in soup.find_all(["div", "generic"]):
        text = div.get_text(strip=True)
        if text == "下一章":
            # Check if parent is a link
            parent = div.parent
            if parent and parent.name == "a" and parent.get("href"):
                href = parent["href"]
                if f"/wxread/{novel_id}_" in href:
                    result["next_chapter"] = urljoin(base_url, href)

    return result


def extract_wxdzs_chapter(start_url: str, session: requests.Session, novel_id: str, chapters: list[dict], current_index: int, delay: float = REQUEST_DELAY) -> dict:
    """
    Extract complete chapter content from wxdzs.net.
    Returns dict with 'title', 'content', 'next_chapter_url', 'page_count'.
    """
    # wxdzs has SSL issues, so verify=False
    soup = fetch_page(start_url, session, verify_ssl=False)
    if not soup:
        raise Exception(f"Failed to fetch chapter page: {start_url}")

    # Extract title from h1
    title = "Untitled"
    h1 = soup.find("h1")
    if h1:
        title = h1.get_text(strip=True)

    # Extract content
    paragraphs = extract_wxdzs_content(soup)
    content = "\n\n".join(paragraphs)

    # Check if this is the final chapter (contains "完结" meaning "complete/finished")
    is_final_chapter = "完结" in title

    # Determine next chapter URL
    next_chapter_url = None

    # If this is the final chapter, don't look for next chapter
    if is_final_chapter:
        print(f"  -> Detected final chapter (完结)")
        next_chapter_url = None
    elif chapters and current_index + 1 < len(chapters):
        # Use chapter list to get next chapter (more reliable than navigation links)
        next_chapter_url = chapters[current_index + 1]["url"]
    else:
        # Fall back to navigation links
        nav_links = find_wxdzs_navigation(soup, start_url, novel_id)
        if nav_links["next_chapter"]:
            next_chapter_url = nav_links["next_chapter"]

    return {
        "title": title,
        "content": content,
        "next_chapter_url": next_chapter_url,
        "page_count": 1  # wxdzs doesn't seem to split chapters into multiple pages
    }


def extract_jpxs123_info(novel_url: str) -> tuple[str, str, str]:
    """
    Extract category, novel ID, and chapter number from jpxs123.com URL.
    URL formats:
    - https://jpxs123.com/cyjk/10524.html -> novel page
    - https://jpxs123.com/cyjk/10524/772.html -> chapter page
    Returns (category, novel_id, chapter_num).
    """
    path = urlparse(novel_url).path.strip("/")

    # Handle /category/novel_id/chapter.html format (chapter page)
    chapter_match = re.search(r"(\w+)/(\d+)/(\d+)\.html", path)
    if chapter_match:
        return chapter_match.group(1), chapter_match.group(2), chapter_match.group(3)

    # Handle /category/novel_id.html format (novel page)
    novel_match = re.search(r"(\w+)/(\d+)\.html", path)
    if novel_match:
        return novel_match.group(1), novel_match.group(2), ""

    return "", "", ""


def get_jpxs123_first_chapter(novel_url: str, session: requests.Session, start_chapter: int = 1, skip_title_fetch: bool = False) -> tuple[str, str, int]:
    """
    Get the first chapter URL from jpxs123.com.
    Returns (novel_title, first_chapter_url, total_chapters).
    """
    category, novel_id, chapter_num = extract_jpxs123_info(novel_url)
    parsed = urlparse(novel_url)
    base_url = f"{parsed.scheme}://{parsed.netloc}"

    print(f"Category: {category}")
    print(f"Novel ID: {novel_id}")

    # If we have a chapter_num from the URL (it was a chapter URL), use it to get info
    if chapter_num:
        first_chapter_url = f"{base_url}/{category}/{novel_id}/{start_chapter}.html"
        print(f"Constructed first chapter URL: {first_chapter_url}")

        if skip_title_fetch:
            print("Skipping title fetch (English title provided)")
            return "Unknown Novel", first_chapter_url, 0

        # Fetch the chapter to get the novel title and total chapters
        soup = fetch_page(first_chapter_url, session)
        if not soup:
            raise Exception(f"Failed to fetch chapter: {first_chapter_url}")

        # Extract novel title from h1 (format: "Novel Title 第X章")
        novel_title = "Unknown Novel"
        h1 = soup.find("h1")
        if h1:
            full_title = h1.get_text(strip=True)
            # Remove chapter part from title
            title_match = re.match(r"(.+?)\s*第\d+章", full_title)
            if title_match:
                novel_title = title_match.group(1).strip()
            else:
                novel_title = full_title
            print(f"Novel title: {novel_title}")

        # Try to get total chapters from "772/1574" text
        total_chapters = 0
        page_text = soup.get_text()
        total_match = re.search(r"\d+/(\d+)", page_text)
        if total_match:
            total_chapters = int(total_match.group(1))
            print(f"Total chapters: {total_chapters}")

        return novel_title, first_chapter_url, total_chapters

    # If no chapter_num, fetch the novel page to get info
    novel_page_url = f"{base_url}/{category}/{novel_id}.html"
    print(f"Fetching novel page from: {novel_page_url}")

    soup = fetch_page(novel_page_url, session)
    if not soup:
        raise Exception(f"Failed to fetch novel page: {novel_page_url}")

    # Extract novel title (usually in a heading or title)
    novel_title = "Unknown Novel"
    title_tag = soup.find("title")
    if title_tag:
        page_title = title_tag.get_text(strip=True)
        # Format: "Novel Title(1-827)_Category" or similar
        title_match = re.match(r"(.+?)\s*[\(（]", page_title)
        if title_match:
            novel_title = title_match.group(1).strip()
        else:
            novel_title = page_title.split("_")[0].strip()
        print(f"Novel title: {novel_title}")

    # Construct first chapter URL
    first_chapter_url = f"{base_url}/{category}/{novel_id}/{start_chapter}.html"
    print(f"First chapter URL: {first_chapter_url}")

    # Try to get total chapters by fetching the first chapter
    total_chapters = 0
    chapter_soup = fetch_page(first_chapter_url, session)
    if chapter_soup:
        page_text = chapter_soup.get_text()
        total_match = re.search(r"\d+/(\d+)", page_text)
        if total_match:
            total_chapters = int(total_match.group(1))
            print(f"Total chapters: {total_chapters}")

    return novel_title, first_chapter_url, total_chapters


def extract_jpxs123_content(soup: BeautifulSoup) -> list[str]:
    """Extract content paragraphs from a jpxs123.com chapter page."""
    paragraphs = []

    # jpxs123 uses div.read_chapterDetail to contain the chapter content
    content_div = soup.select_one(".read_chapterDetail")
    if content_div:
        for p in content_div.find_all("p"):
            text = p.get_text(strip=True)
            if text:
                paragraphs.append(text)

    # Fallback: look in h1's grandparent (the chapter wrapper div)
    if not paragraphs:
        h1 = soup.find("h1")
        if h1:
            grandparent = h1.parent.parent if h1.parent else None
            if grandparent:
                for p in grandparent.find_all("p"):
                    text = p.get_text(strip=True)
                    if text:
                        paragraphs.append(text)

    # Last resort: get all paragraphs on page
    if not paragraphs:
        for p in soup.find_all("p"):
            text = p.get_text(strip=True)
            if text and len(text) > 5:
                paragraphs.append(text)

    # Clean content - remove ads and navigation
    ad_patterns = [
        r"http[s]?://",
        r"www\.",
        r"jpxs123",
        r"精品小说",
        r"极品小说",
        r"上一章",
        r"下一章",
        r"上一篇",
        r"下一篇",
        r"目录",
        r"首章",
        r"尾章",
        r"作者：",
        r"Copyright",
        r"All Rights Reserved",
    ]

    cleaned = []
    for p in paragraphs:
        is_ad = any(re.search(pattern, p, re.IGNORECASE) for pattern in ad_patterns)
        if not is_ad and len(p) > 2:
            cleaned.append(p)

    return cleaned


def find_jpxs123_navigation(soup: BeautifulSoup, base_url: str, category: str, novel_id: str) -> dict:
    """
    Find next chapter navigation for jpxs123.com.
    Returns {'next_chapter': url or None, 'is_end': bool, 'current': int, 'total': int}
    """
    result = {"next_chapter": None, "is_end": False, "current": 0, "total": 0}

    for link in soup.find_all("a", href=True):
        link_text = link.get_text(strip=True)
        href = link["href"]

        # Check for "next chapter" (下一章)
        if "下一章" in link_text:
            # Check if it's an actual chapter URL
            if f"/{category}/{novel_id}/" in href:
                result["next_chapter"] = urljoin(base_url, href)

        # Check for "last chapter" (尾章) to know when we're at the end
        if "尾章" in link_text and f"/{category}/{novel_id}/" in href:
            # Extract the last chapter number
            last_match = re.search(r"/(\d+)\.html", href)
            if last_match:
                result["total"] = int(last_match.group(1))

    # Try to find current/total from text like "772/1574"
    page_text = soup.get_text()
    position_match = re.search(r"(\d+)/(\d+)", page_text)
    if position_match:
        result["current"] = int(position_match.group(1))
        result["total"] = int(position_match.group(2))

        # If we're at the last chapter
        if result["current"] >= result["total"]:
            result["is_end"] = True
            result["next_chapter"] = None

    return result


def extract_jpxs123_chapter(start_url: str, session: requests.Session, category: str, novel_id: str, total_chapters: int, delay: float = REQUEST_DELAY) -> dict:
    """
    Extract complete chapter content from jpxs123.com.
    Returns dict with 'title', 'content', 'next_chapter_url', 'page_count', 'current', 'total'.
    """
    soup = fetch_page(start_url, session)
    if not soup:
        raise Exception(f"Failed to fetch chapter page: {start_url}")

    # Extract title from h1
    title = "Untitled"
    h1 = soup.find("h1")
    if h1:
        title = h1.get_text(strip=True)

    # Extract content
    paragraphs = extract_jpxs123_content(soup)
    content = "\n\n".join(paragraphs)

    # Find navigation
    nav_links = find_jpxs123_navigation(soup, start_url, category, novel_id)

    # Check if this is the final chapter
    is_final_chapter = nav_links["is_end"]

    # Determine next chapter URL
    next_chapter_url = None
    if is_final_chapter:
        print(f"  -> Detected final chapter ({nav_links['current']}/{nav_links['total']})")
        next_chapter_url = None
    elif nav_links["next_chapter"]:
        next_chapter_url = nav_links["next_chapter"]
    else:
        # Construct next chapter URL from current
        if nav_links["current"] > 0 and nav_links["current"] < nav_links["total"]:
            parsed = urlparse(start_url)
            next_chapter_url = f"{parsed.scheme}://{parsed.netloc}/{category}/{novel_id}/{nav_links['current'] + 1}.html"

    return {
        "title": title,
        "content": content,
        "next_chapter_url": next_chapter_url,
        "page_count": 1,  # jpxs123 doesn't split chapters into multiple pages
        "current": nav_links["current"],
        "total": nav_links["total"]
    }


def extract_wfxs_info(novel_url: str) -> tuple[str, str]:
    """
    Extract novel ID and chapter ID from wfxs.tw URL.
    URL formats:
    - https://m.wfxs.tw/xs-2172679/ -> novel page
    - https://m.wfxs.tw/xs-2172679/du-152253409/ -> chapter page
    Returns (novel_id, chapter_id).
    """
    path = urlparse(novel_url).path.strip("/")

    # Handle /xs-{novel_id}/du-{chapter_id}/ format (chapter page)
    chapter_match = re.search(r"xs-(\d+)/du-(\d+)", path)
    if chapter_match:
        return chapter_match.group(1), chapter_match.group(2)

    # Handle /xs-{novel_id}/ format (novel page)
    novel_match = re.search(r"xs-(\d+)", path)
    if novel_match:
        return novel_match.group(1), ""

    return "", ""


def get_wfxs_first_chapter(novel_url: str, session: requests.Session, start_chapter: int = 1, skip_title_fetch: bool = False) -> tuple[str, str, list[dict]]:
    """
    Get the first chapter URL from wfxs.tw.
    Returns (novel_title, first_chapter_url, chapter_list).
    """
    novel_id, chapter_id = extract_wfxs_info(novel_url)
    parsed = urlparse(novel_url)
    base_url = f"{parsed.scheme}://{parsed.netloc}"

    print(f"Novel ID: {novel_id}")

    # If we have a chapter_id from the URL (it was a chapter URL), we need to get the chapter list
    # to know the order and find the correct starting chapter
    # Always fetch the novel page to get the chapter list

    # Fetch the novel page (TOC)
    novel_page_url = f"{base_url}/xs-{novel_id}/"
    print(f"Fetching table of contents from: {novel_page_url}")

    soup = fetch_page(novel_page_url, session)
    if not soup:
        raise Exception(f"Failed to fetch TOC page: {novel_page_url}")

    # Extract novel title from h1
    novel_title = "Unknown Novel"
    h1 = soup.find("h1")
    if h1:
        novel_title = h1.get_text(strip=True)
    else:
        # Try from page title
        title_tag = soup.find("title")
        if title_tag:
            novel_title = title_tag.get_text(strip=True).split(" - ")[0].strip()

    print(f"Novel title: {novel_title}")

    # Find all chapter links in <div class="list">
    chapter_list_div = soup.select_one("div.list")
    chapters = []
    seen_urls = set()

    if chapter_list_div:
        for link in chapter_list_div.find_all("a", href=True):
            href = link.get("href", "")
            ch_title = link.get_text(strip=True)

            # Match chapter URL pattern
            ch_match = re.search(r"/xs-\d+/du-(\d+)/", href)
            if ch_match:
                ch_id = ch_match.group(1)
                full_url = urljoin(novel_page_url, href)
                if full_url not in seen_urls:
                    seen_urls.add(full_url)
                    chapters.append({
                        "url": full_url,
                        "chapter_id": ch_id,
                        "title": ch_title
                    })

    if not chapters:
        # Fallback: search entire page for chapter links
        chapter_pattern = re.compile(rf"/xs-{novel_id}/du-(\d+)/")
        for link in soup.find_all("a", href=True):
            href = link.get("href", "")
            ch_title = link.get_text(strip=True)
            ch_match = chapter_pattern.search(href)
            if ch_match:
                ch_id = ch_match.group(1)
                full_url = urljoin(novel_page_url, href)
                if full_url not in seen_urls:
                    seen_urls.add(full_url)
                    chapters.append({
                        "url": full_url,
                        "chapter_id": ch_id,
                        "title": ch_title
                    })

    if chapters:
        # Start from the requested chapter (1-indexed)
        if start_chapter > 1 and start_chapter <= len(chapters):
            first_chapter = chapters[start_chapter - 1]
            print(f"Starting from chapter {start_chapter}: {first_chapter['title']}")
        else:
            first_chapter = chapters[0]

        print(f"First chapter URL: {first_chapter['url']}")
        print(f"Total chapters found: {len(chapters)}")
        return novel_title, first_chapter["url"], chapters

    raise Exception("Could not find chapter URLs. Please check the URL format.")


def extract_wfxs_content(soup: BeautifulSoup) -> list[str]:
    """Extract content paragraphs from a wfxs.tw chapter page."""
    paragraphs = []

    # wfxs uses <div class="articlebody"> for content
    content_div = soup.select_one("div.articlebody")
    if content_div:
        for p in content_div.find_all("p"):
            text = p.get_text(strip=True)
            if text:
                paragraphs.append(text)

    # Fallback: look for any content container
    if not paragraphs:
        for selector in ["#content", ".content", ".chapter-content"]:
            content_div = soup.select_one(selector)
            if content_div:
                for p in content_div.find_all("p"):
                    text = p.get_text(strip=True)
                    if text:
                        paragraphs.append(text)
                break

    # Last resort: get all paragraphs on page
    if not paragraphs:
        for p in soup.find_all("p"):
            text = p.get_text(strip=True)
            if text and len(text) > 5:
                paragraphs.append(text)

    # Clean content - remove ads and navigation
    ad_patterns = [
        r"http[s]?://",
        r"www\.",
        r"wfxs",
        r"無妨小說",
        r"上一章",
        r"下一章",
        r"上一頁",
        r"下一頁",
        r"目錄",
        r"章節目錄",
        r"加入書籤",
        r"分享到",
        r"Facebook",
        r"Twitter",
        r"Line",
        r"複製連結",
        r"設定",
        r"字體大小",
    ]

    cleaned = []
    for p in paragraphs:
        is_ad = any(re.search(pattern, p, re.IGNORECASE) for pattern in ad_patterns)
        if not is_ad and len(p) > 2:
            cleaned.append(p)

    return cleaned


def find_wfxs_navigation(soup: BeautifulSoup, base_url: str, novel_id: str) -> dict:
    """
    Find next chapter navigation for wfxs.tw.
    Returns {'next_chapter': url or None, 'is_end': bool}
    """
    result = {"next_chapter": None, "is_end": False}

    # Look for navigation in <div class="list_page">
    nav_div = soup.select_one("div.list_page")
    if nav_div:
        for link in nav_div.find_all("a", href=True):
            link_text = link.get_text(strip=True)
            href = link["href"]

            # Check for "next chapter" (下一章 or 下一頁)
            if "下一章" in link_text or "下一頁" in link_text:
                # Check if it's an actual chapter URL
                if f"/xs-{novel_id}/du-" in href:
                    result["next_chapter"] = urljoin(base_url, href)

    # Also check for generic navigation links if not found
    if not result["next_chapter"]:
        for link in soup.find_all("a", href=True):
            link_text = link.get_text(strip=True)
            href = link["href"]

            if ("下一章" in link_text or "下一頁" in link_text) and f"/xs-{novel_id}/du-" in href:
                result["next_chapter"] = urljoin(base_url, href)
                break

    return result


def extract_wfxs_chapter(start_url: str, session: requests.Session, novel_id: str, chapters: list[dict], current_index: int, delay: float = REQUEST_DELAY) -> dict:
    """
    Extract complete chapter content from wfxs.tw.
    Returns dict with 'title', 'content', 'next_chapter_url', 'page_count'.
    """
    soup = fetch_page(start_url, session)
    if not soup:
        raise Exception(f"Failed to fetch chapter page: {start_url}")

    # Extract title from h1
    title = "Untitled"
    h1 = soup.find("h1")
    if h1:
        title = h1.get_text(strip=True)

    # Extract content
    paragraphs = extract_wfxs_content(soup)
    content = "\n\n".join(paragraphs)

    # Check if this is the final chapter (contains "完結" or "大結局" meaning "complete/finished")
    is_final_chapter = "完結" in title or "大結局" in title

    # Determine next chapter URL
    next_chapter_url = None

    if is_final_chapter:
        print(f"  -> Detected final chapter")
        next_chapter_url = None
    elif chapters and current_index + 1 < len(chapters):
        # Use chapter list to get next chapter (more reliable than navigation links)
        next_chapter_url = chapters[current_index + 1]["url"]
    else:
        # Fall back to navigation links
        nav_links = find_wfxs_navigation(soup, start_url, novel_id)
        if nav_links["next_chapter"]:
            next_chapter_url = nav_links["next_chapter"]

    return {
        "title": title,
        "content": content,
        "next_chapter_url": next_chapter_url,
        "page_count": 1  # wfxs doesn't split chapters into multiple pages
    }


def extract_uukanshu_info(novel_url: str) -> tuple[str, str]:
    """
    Extract novel ID and chapter ID from uukanshu.cc URL.
    URL formats:
    - https://uukanshu.cc/book/25143/ -> novel page
    - https://uukanshu.cc/book/25143/16161315.html -> chapter page
    Returns (novel_id, chapter_id).
    """
    path = urlparse(novel_url).path.strip("/")

    # Handle /book/{novel_id}/{chapter_id}.html format (chapter page)
    chapter_match = re.search(r"book/(\d+)/(\d+)\.html", path)
    if chapter_match:
        return chapter_match.group(1), chapter_match.group(2)

    # Handle /book/{novel_id}/ format (novel page)
    novel_match = re.search(r"book/(\d+)", path)
    if novel_match:
        return novel_match.group(1), ""

    return "", ""


def get_uukanshu_first_chapter(novel_url: str, session: requests.Session, start_chapter: int = 1, skip_title_fetch: bool = False) -> tuple[str, str, list[dict]]:
    """
    Get the first chapter URL from uukanshu.cc.
    Returns (novel_title, first_chapter_url, chapter_list).
    """
    novel_id, chapter_id = extract_uukanshu_info(novel_url)
    parsed = urlparse(novel_url)
    base_url = f"{parsed.scheme}://{parsed.netloc}"

    print(f"Novel ID: {novel_id}")

    # Fetch the novel page (TOC)
    novel_page_url = f"{base_url}/book/{novel_id}/"
    print(f"Fetching table of contents from: {novel_page_url}")

    soup = fetch_page(novel_page_url, session)
    if not soup:
        raise Exception(f"Failed to fetch TOC page: {novel_page_url}")

    # Extract novel title - try multiple selectors
    novel_title = "Unknown Novel"
    # Try h1 first
    h1 = soup.find("h1")
    if h1:
        novel_title = h1.get_text(strip=True)
    else:
        # Try from page title
        title_tag = soup.find("title")
        if title_tag:
            page_title = title_tag.get_text(strip=True)
            # Title often contains "小说名_作者_UU看书" or similar
            novel_title = page_title.split("_")[0].strip()
            if not novel_title:
                novel_title = page_title.split("-")[0].strip()

    print(f"Novel title: {novel_title}")

    # Find all chapter links
    # uukanshu typically lists chapters in a container div
    chapters = []
    seen_urls = set()

    # Look for chapter links - pattern: /book/{novel_id}/{chapter_id}.html
    chapter_pattern = re.compile(rf"/book/{novel_id}/(\d+)\.html")

    # Try to find chapter list container first
    chapter_containers = soup.select("div.list, div.chapter-list, ul.chapter-list, div#list, div.listmain")

    if chapter_containers:
        for container in chapter_containers:
            for link in container.find_all("a", href=True):
                href = link.get("href", "")
                ch_title = link.get_text(strip=True)
                ch_match = chapter_pattern.search(href)
                if ch_match:
                    ch_id = ch_match.group(1)
                    full_url = urljoin(novel_page_url, href)
                    if full_url not in seen_urls:
                        seen_urls.add(full_url)
                        chapters.append({
                            "url": full_url,
                            "chapter_id": ch_id,
                            "title": ch_title
                        })

    # Fallback: search entire page for chapter links
    if not chapters:
        for link in soup.find_all("a", href=True):
            href = link.get("href", "")
            ch_title = link.get_text(strip=True)
            ch_match = chapter_pattern.search(href)
            if ch_match:
                ch_id = ch_match.group(1)
                full_url = urljoin(novel_page_url, href)
                if full_url not in seen_urls and ch_title:  # Only add if has title
                    seen_urls.add(full_url)
                    chapters.append({
                        "url": full_url,
                        "chapter_id": ch_id,
                        "title": ch_title
                    })

    if chapters:
        # Start from the requested chapter (1-indexed)
        if start_chapter > 1 and start_chapter <= len(chapters):
            first_chapter = chapters[start_chapter - 1]
            print(f"Starting from chapter {start_chapter}: {first_chapter['title']}")
        else:
            first_chapter = chapters[0]

        print(f"First chapter URL: {first_chapter['url']}")
        print(f"Total chapters found: {len(chapters)}")
        return novel_title, first_chapter["url"], chapters

    # If we had a chapter URL directly, use it
    if chapter_id:
        first_chapter_url = f"{base_url}/book/{novel_id}/{chapter_id}.html"
        print(f"Using provided chapter URL: {first_chapter_url}")
        return novel_title, first_chapter_url, []

    raise Exception("Could not find chapter URLs. Please check the URL format.")


def extract_uukanshu_content(soup: BeautifulSoup) -> list[str]:
    """Extract content paragraphs from a uukanshu.cc chapter page."""
    paragraphs = []

    # uukanshu typically uses a content div for chapter text
    content_selectors = [
        "#contentbox",
        "#content",
        ".content",
        ".chapter-content",
        "#bookContent",
        ".readcontent",
        "div.content",
    ]

    content_div = None
    for selector in content_selectors:
        content_div = soup.select_one(selector)
        if content_div:
            break

    if content_div:
        # Get text from paragraphs
        for p in content_div.find_all("p"):
            text = p.get_text(strip=True)
            if text:
                paragraphs.append(text)

        # If no <p> tags, try getting text with newline separator
        if not paragraphs:
            text = content_div.get_text(separator="\n", strip=True)
            paragraphs = [p.strip() for p in text.split("\n") if p.strip()]

    # Fallback: get all paragraphs on page
    if not paragraphs:
        for p in soup.find_all("p"):
            text = p.get_text(strip=True)
            if text and len(text) > 5:
                paragraphs.append(text)

    # Clean content - remove ads and navigation
    ad_patterns = [
        r"http[s]?://",
        r"www\.",
        r"uukanshu",
        r"UU看书",
        r"uu看书",
        r"上一章",
        r"下一章",
        r"上一頁",
        r"下一頁",
        r"目录",
        r"目錄",
        r"章节目录",
        r"加入书签",
        r"加入書籤",
        r"手机阅读",
        r"请记住",
        r"推荐阅读",
    ]

    cleaned = []
    for p in paragraphs:
        is_ad = any(re.search(pattern, p, re.IGNORECASE) for pattern in ad_patterns)
        if not is_ad and len(p) > 2:
            cleaned.append(p)

    return cleaned


def find_uukanshu_navigation(soup: BeautifulSoup, base_url: str, novel_id: str) -> dict:
    """
    Find next chapter navigation for uukanshu.cc.
    Returns {'next_chapter': url or None, 'is_end': bool}
    """
    result = {"next_chapter": None, "is_end": False}

    for link in soup.find_all("a", href=True):
        link_text = link.get_text(strip=True)
        href = link["href"]

        # Check for "next chapter" (下一章)
        if "下一章" in link_text:
            # Check if it's an actual chapter URL
            if f"/book/{novel_id}/" in href and href.endswith(".html"):
                result["next_chapter"] = urljoin(base_url, href)

    return result


def extract_uukanshu_chapter(start_url: str, session: requests.Session, novel_id: str, chapters: list[dict], current_index: int, delay: float = REQUEST_DELAY) -> dict:
    """
    Extract complete chapter content from uukanshu.cc.
    Returns dict with 'title', 'content', 'next_chapter_url', 'page_count'.
    """
    soup = fetch_page(start_url, session)
    if not soup:
        raise Exception(f"Failed to fetch chapter page: {start_url}")

    # Extract title from h1 or other heading
    title = "Untitled"
    h1 = soup.find("h1")
    if h1:
        title = h1.get_text(strip=True)
    else:
        # Try title tag
        title_tag = soup.find("title")
        if title_tag:
            page_title = title_tag.get_text(strip=True)
            # Extract chapter title from page title
            title = page_title.split("_")[0].strip()

    # Extract content
    paragraphs = extract_uukanshu_content(soup)
    content = "\n\n".join(paragraphs)

    # Check if this is the final chapter
    is_final_chapter = "完结" in title or "大结局" in title or "完本" in title

    # Determine next chapter URL
    next_chapter_url = None

    if is_final_chapter:
        print(f"  -> Detected final chapter")
        next_chapter_url = None
    elif chapters and current_index + 1 < len(chapters):
        # Use chapter list to get next chapter (more reliable than navigation links)
        next_chapter_url = chapters[current_index + 1]["url"]
    else:
        # Fall back to navigation links
        nav_links = find_uukanshu_navigation(soup, start_url, novel_id)
        if nav_links["next_chapter"]:
            next_chapter_url = nav_links["next_chapter"]

    return {
        "title": title,
        "content": content,
        "next_chapter_url": next_chapter_url,
        "page_count": 1  # uukanshu doesn't typically split chapters
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
    category = ""  # For jpxs123
    chapters = []  # For sites that provide chapter list
    total_chapters = 0  # For jpxs123

    try:
        # Get first chapter URL from TOC (site-specific)
        if site == "novel543":
            # Skip title fetch if english_title is provided (saves a request)
            skip_title = english_title is not None
            novel_title, first_chapter_url, section_id = get_novel543_first_chapter(
                novel_url, session, start_chapter, skip_title
            )
            novel_id, _ = extract_novel543_info(novel_url)
            safe_novel_title = sanitize_filename(novel_title)
        elif site == "wxdzs":
            # Skip title fetch if english_title is provided (saves a request)
            skip_title = english_title is not None
            novel_title, first_chapter_url, chapters = get_wxdzs_first_chapter(
                novel_url, session, start_chapter, skip_title
            )
            novel_id, _ = extract_wxdzs_info(novel_url)
            safe_novel_title = sanitize_filename(novel_title)
        elif site == "jpxs123":
            # Skip title fetch if english_title is provided (saves a request)
            skip_title = english_title is not None
            novel_title, first_chapter_url, total_chapters = get_jpxs123_first_chapter(
                novel_url, session, start_chapter, skip_title
            )
            category, novel_id, _ = extract_jpxs123_info(novel_url)
            safe_novel_title = sanitize_filename(novel_title)
        elif site == "wfxs":
            # Skip title fetch if english_title is provided (saves a request)
            skip_title = english_title is not None
            novel_title, first_chapter_url, chapters = get_wfxs_first_chapter(
                novel_url, session, start_chapter, skip_title
            )
            novel_id, _ = extract_wfxs_info(novel_url)
            safe_novel_title = sanitize_filename(novel_title)
        elif site == "uukanshu":
            # Skip title fetch if english_title is provided (saves a request)
            skip_title = english_title is not None
            novel_title, first_chapter_url, chapters = get_uukanshu_first_chapter(
                novel_url, session, start_chapter, skip_title
            )
            novel_id, _ = extract_uukanshu_info(novel_url)
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
        current_chapter_index = start_chapter - 1  # 0-indexed for chapter list
        if site == "novel543":
            # For novel543, first_chapter_url already points to start_chapter
            current_url = first_chapter_url
            if start_chapter > 1:
                print(f"Starting from chapter {start_chapter}")
        elif site == "wxdzs":
            # For wxdzs, first_chapter_url already points to start_chapter
            current_url = first_chapter_url
            if start_chapter > 1:
                print(f"Starting from chapter {start_chapter}")
        elif site == "jpxs123":
            # For jpxs123, first_chapter_url already points to start_chapter
            current_url = first_chapter_url
            if start_chapter > 1:
                print(f"Starting from chapter {start_chapter}")
        elif site == "wfxs":
            # For wfxs, first_chapter_url already points to start_chapter
            current_url = first_chapter_url
            if start_chapter > 1:
                print(f"Starting from chapter {start_chapter}")
        elif site == "uukanshu":
            # For uukanshu, first_chapter_url already points to start_chapter
            current_url = first_chapter_url
            if start_chapter > 1:
                print(f"Starting from chapter {start_chapter}")
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

        seen_urls = set()  # Track URLs to detect loops

        while current_url:
            # Check if URL is the end page (novel543 specific)
            if "/end.html" in current_url:
                print(f"\nReached end of novel (end.html detected)")
                break

            # Check for URL loops (same URL visited twice)
            if current_url in seen_urls:
                print(f"\nDetected loop (URL already visited), stopping")
                break
            seen_urls.add(current_url)

            # For wxdzs, check if we've exceeded the chapter list
            if site == "wxdzs" and chapters and current_chapter_index >= len(chapters):
                print(f"\nReached end of chapter list ({len(chapters)} chapters)")
                break

            # For wfxs, check if we've exceeded the chapter list
            if site == "wfxs" and chapters and current_chapter_index >= len(chapters):
                print(f"\nReached end of chapter list ({len(chapters)} chapters)")
                break

            # For uukanshu, check if we've exceeded the chapter list
            if site == "uukanshu" and chapters and current_chapter_index >= len(chapters):
                print(f"\nReached end of chapter list ({len(chapters)} chapters)")
                break

            # For jpxs123, check if we've exceeded the total chapters
            if site == "jpxs123" and total_chapters > 0 and chapter_num > total_chapters:
                print(f"\nReached end of novel ({total_chapters} chapters)")
                break

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
                    elif site == "wxdzs":
                        # For wxdzs, use chapter list if available
                        print(f"Chapter {chapter_num}: Skipping (already exists)")
                        current_chapter_index += 1
                        if chapters and current_chapter_index < len(chapters):
                            current_url = chapters[current_chapter_index]["url"]
                        else:
                            # Fall back to fetching to get next URL
                            chapter_data = extract_wxdzs_chapter(current_url, session, novel_id, chapters, current_chapter_index - 1, delay)
                            current_url = chapter_data["next_chapter_url"]
                            time.sleep(delay)
                    elif site == "wfxs":
                        # For wfxs, use chapter list if available
                        print(f"Chapter {chapter_num}: Skipping (already exists)")
                        current_chapter_index += 1
                        if chapters and current_chapter_index < len(chapters):
                            current_url = chapters[current_chapter_index]["url"]
                        else:
                            # Fall back to fetching to get next URL
                            chapter_data = extract_wfxs_chapter(current_url, session, novel_id, chapters, current_chapter_index - 1, delay)
                            current_url = chapter_data["next_chapter_url"]
                            time.sleep(delay)
                    elif site == "uukanshu":
                        # For uukanshu, use chapter list if available
                        print(f"Chapter {chapter_num}: Skipping (already exists)")
                        current_chapter_index += 1
                        if chapters and current_chapter_index < len(chapters):
                            current_url = chapters[current_chapter_index]["url"]
                        else:
                            # Fall back to fetching to get next URL
                            chapter_data = extract_uukanshu_chapter(current_url, session, novel_id, chapters, current_chapter_index - 1, delay)
                            current_url = chapter_data["next_chapter_url"]
                            time.sleep(delay)
                    elif site == "jpxs123":
                        # For jpxs123, construct next URL directly (simple numeric chapters)
                        print(f"Chapter {chapter_num}: Skipping (already exists)")
                        parsed = urlparse(novel_url)
                        current_url = f"{parsed.scheme}://{parsed.netloc}/{category}/{novel_id}/{chapter_num + 1}.html"
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
                elif site == "wxdzs":
                    chapter_data = extract_wxdzs_chapter(current_url, session, novel_id, chapters, current_chapter_index, delay)
                elif site == "jpxs123":
                    chapter_data = extract_jpxs123_chapter(current_url, session, category, novel_id, total_chapters, delay)
                elif site == "wfxs":
                    chapter_data = extract_wfxs_chapter(current_url, session, novel_id, chapters, current_chapter_index, delay)
                elif site == "uukanshu":
                    chapter_data = extract_uukanshu_chapter(current_url, session, novel_id, chapters, current_chapter_index, delay)
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
                current_chapter_index += 1

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
        description="Download Chinese webnovels. Supported sites: shuhaige.net, novel543.com, wxdzs.net, jpxs123.com, wfxs.tw, uukanshu.cc"
    )
    parser.add_argument(
        "novel_url",
        help="URL to the novel's TOC or any chapter (e.g., https://m.shuhaige.net/123456/, https://www.novel543.com/123456/dir, https://www.wxdzs.net/wxbook/94900.html, https://jpxs123.com/cyjk/10524.html, https://m.wfxs.tw/xs-2172679/, https://uukanshu.cc/book/25143/)"
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
        help="Chapter number to start from (default: 1, works efficiently for novel543.com, wxdzs.net, jpxs123.com, wfxs.tw, and uukanshu.cc)"
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
