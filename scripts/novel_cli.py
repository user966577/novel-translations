#!/usr/bin/env python3
"""
Novel Chapter Manager — interactive CLI for tracking and updating novel sources.

Features:
- Arrow-key navigation through novels in raw/
- Check for missing chapters against remote sources
- Add new novels via URL (calls the scraper)
- Track, update, and delete source URLs

Usage: python scripts/novel_cli.py
"""

import json
import os
import re
import sys

# Resolve project root (parent of scripts/)
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
RAW_DIR = os.path.join(PROJECT_ROOT, "raw")
SOURCES_FILE = os.path.join(RAW_DIR, "sources.json")

# Add project root to path so we can import scraper
sys.path.insert(0, SCRIPT_DIR)

from scraper import (
    detect_site,
    get_existing_chapters,
    get_remote_chapter_count,
    scrape_novel_by_navigation,
)


# ---------------------------------------------------------------------------
# Sources file management
# ---------------------------------------------------------------------------

def load_sources() -> dict:
    if os.path.exists(SOURCES_FILE):
        with open(SOURCES_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_sources(sources: dict):
    with open(SOURCES_FILE, "w", encoding="utf-8") as f:
        json.dump(sources, f, ensure_ascii=False, indent=2)


# ---------------------------------------------------------------------------
# Novel list helpers
# ---------------------------------------------------------------------------

def list_novels() -> list[dict]:
    """Return sorted list of novel dicts with name and local chapter count."""
    novels = []
    if not os.path.isdir(RAW_DIR):
        return novels
    for name in sorted(os.listdir(RAW_DIR)):
        folder = os.path.join(RAW_DIR, name)
        if not os.path.isdir(folder):
            continue
        existing = get_existing_chapters(folder)
        novels.append({
            "name": name,
            "count": len(existing),
            "max_ch": max(existing) if existing else 0,
        })
    return novels


def site_label(sources: dict, name: str) -> str:
    entry = sources.get(name)
    if not entry:
        return "\u2014"
    return entry.get("site", "\u2014")


# ---------------------------------------------------------------------------
# Keyboard input (cross-platform)
# ---------------------------------------------------------------------------

if sys.platform == "win32":
    import msvcrt

    def get_key() -> str:
        """Return a logical key name: 'up', 'down', 'enter', 'escape', or the character."""
        ch = msvcrt.getwch()
        if ch in ("\x00", "\xe0"):
            ch2 = msvcrt.getwch()
            if ch2 == "H":
                return "up"
            elif ch2 == "P":
                return "down"
            return ""
        if ch == "\x1b":
            return "escape"
        if ch == "\r":
            return "enter"
        return ch

    def read_line(label: str) -> str | None:
        """Read a line character-by-character. Returns None if Escape is pressed."""
        sys.stdout.write(label)
        sys.stdout.flush()
        buf = []
        while True:
            ch = msvcrt.getwch()
            if ch == "\x1b":
                sys.stdout.write("\n")
                return None
            if ch == "\r":
                sys.stdout.write("\n")
                return "".join(buf)
            if ch == "\x08":  # backspace
                if buf:
                    buf.pop()
                    sys.stdout.write("\b \b")
                    sys.stdout.flush()
            elif ch in ("\x00", "\xe0"):
                msvcrt.getwch()  # consume second byte of special key
            else:
                buf.append(ch)
                sys.stdout.write(ch)
                sys.stdout.flush()
else:
    import termios
    import tty

    def get_key() -> str:
        fd = sys.stdin.fileno()
        old = termios.tcgetattr(fd)
        try:
            tty.setraw(fd)
            ch = sys.stdin.read(1)
            if ch == "\x1b":
                ch2 = sys.stdin.read(1)
                if ch2 == "[":
                    ch3 = sys.stdin.read(1)
                    if ch3 == "A":
                        return "up"
                    elif ch3 == "B":
                        return "down"
                return "escape"
            if ch in ("\r", "\n"):
                return "enter"
            return ch
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old)

    def read_line(label: str) -> str | None:
        """Read a line character-by-character. Returns None if Escape is pressed."""
        fd = sys.stdin.fileno()
        old = termios.tcgetattr(fd)
        sys.stdout.write(label)
        sys.stdout.flush()
        buf = []
        try:
            tty.setraw(fd)
            while True:
                ch = sys.stdin.read(1)
                if ch == "\x1b":
                    # Check if it's an arrow key sequence — consume and ignore
                    ch2 = sys.stdin.read(1)
                    if ch2 == "[":
                        sys.stdin.read(1)
                        continue
                    # Bare escape
                    sys.stdout.write("\n")
                    sys.stdout.flush()
                    return None
                if ch in ("\r", "\n"):
                    sys.stdout.write("\n")
                    sys.stdout.flush()
                    return "".join(buf)
                if ch in ("\x7f", "\x08"):  # backspace / delete
                    if buf:
                        buf.pop()
                        sys.stdout.write("\b \b")
                        sys.stdout.flush()
                elif ch >= " ":
                    buf.append(ch)
                    sys.stdout.write(ch)
                    sys.stdout.flush()
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old)


# ---------------------------------------------------------------------------
# Screen rendering
# ---------------------------------------------------------------------------

def clear_screen():
    if sys.platform == "win32":
        os.system("cls")
    else:
        sys.stdout.write("\033[2J\033[H")
        sys.stdout.flush()


def truncate(text: str, width: int) -> str:
    if len(text) <= width:
        return text
    return text[: width - 3] + "..."


def render(novels: list[dict], sources: dict, cursor: int, status: str = ""):
    clear_screen()
    print("=== Novel Chapter Manager ===\n")

    if not novels:
        print("  (no novels found in raw/)\n")
    else:
        # Compute column widths
        name_width = 58
        for i, novel in enumerate(novels):
            prefix = " > " if i == cursor else "   "
            name = truncate(novel["name"], name_width)
            count = str(novel["count"]).rjust(6)
            site = site_label(sources, novel["name"])
            print(f"{prefix}{name:<{name_width}}  {count}  {site}")
        print()

    if status:
        print(f"  {status}\n")

    print(" \u2191\u2193 Navigate  [Enter] Check  [a] Add  [d] Delete  [u] Update  [q/Esc] Quit")


# ---------------------------------------------------------------------------
# Prompt helpers (used in actions)
# ---------------------------------------------------------------------------

def prompt_line(label: str) -> str | None:
    """Read a line with Escape-to-cancel support. Returns None on Escape."""
    return read_line(label)


def prompt_yn(label: str, default_yes: bool = False) -> bool | None:
    """Yes/no prompt. Returns None on Escape, bool otherwise."""
    hint = "[Y/n]" if default_yes else "[y/N]"
    ans = read_line(f"{label} {hint} ")
    if ans is None:
        return None
    ans = ans.strip().lower()
    if not ans:
        return default_yes
    return ans.startswith("y")


# ---------------------------------------------------------------------------
# Action handlers
# ---------------------------------------------------------------------------

def action_check(novel: dict, sources: dict) -> str:
    name = novel["name"]
    entry = sources.get(name)
    if not entry:
        return f"No source URL tracked for \"{name}\"."

    url = entry["url"]
    print(f"\n  Checking \"{name}\"...\n")
    try:
        _, remote_count = get_remote_chapter_count(url)
    except Exception as e:
        return f"Error checking remote: {e}"

    local_max = novel["max_ch"]
    local_count = novel["count"]

    if remote_count > local_max:
        missing = remote_count - local_max
        print(f"  Local: {local_count} chapters (up to #{local_max})")
        print(f"  Remote: {remote_count} chapters")
        print(f"  Missing: {missing} chapter(s)\n")
        answer = prompt_yn("  Scrape missing chapters?", default_yes=True)
        if answer is None:
            return "Cancelled."
        if answer:
            try:
                scrape_novel_by_navigation(
                    url,
                    output_dir=RAW_DIR,
                    english_title=name,
                    start_chapter=local_max + 1,
                )
                return f"Scraping complete."
            except Exception as e:
                return f"Scraping error: {e}"
        return "Skipped."
    elif remote_count == local_max:
        return f"Up to date — {local_count} chapters locally, {remote_count} remote."
    else:
        return f"Local has more chapters than remote ({local_max} vs {remote_count})."


def action_add(sources: dict) -> str:
    clear_screen()
    print("=== Add New Novel ===  (Esc to cancel)\n")
    url = prompt_line("  Paste URL: ")
    if url is None:
        return "Cancelled."
    url = url.strip()
    if not url:
        return "Cancelled."

    try:
        site = detect_site(url)
    except Exception:
        return f"Unsupported URL."

    print(f"  Detected site: {site}\n")

    val = prompt_line("  English title [-e] (Enter to use Chinese title): ")
    if val is None:
        return "Cancelled."
    english_title = val.strip() or None

    val = prompt_line("  Request delay [-d] (default 1.5): ")
    if val is None:
        return "Cancelled."
    delay = float(val.strip()) if val.strip() else 1.5

    val = prompt_line("  Max chapters [-m] (default all): ")
    if val is None:
        return "Cancelled."
    max_chapters = int(val.strip()) if val.strip() else None

    val = prompt_line("  Start chapter [-s] (default 1): ")
    if val is None:
        return "Cancelled."
    start_chapter = int(val.strip()) if val.strip() else 1

    print()
    try:
        scrape_novel_by_navigation(
            url,
            output_dir=RAW_DIR,
            delay=delay,
            max_chapters=max_chapters,
            english_title=english_title,
            start_chapter=start_chapter,
        )
    except Exception as e:
        return f"Scraping error: {e}"

    # Determine folder name — find the most recently modified folder in raw/
    # that wasn't there before, or match english_title
    if english_title:
        folder_name = english_title
    else:
        # Find newest folder
        folders = []
        for name in os.listdir(RAW_DIR):
            path = os.path.join(RAW_DIR, name)
            if os.path.isdir(path) and name not in sources:
                folders.append((os.path.getmtime(path), name))
        if folders:
            folders.sort(reverse=True)
            folder_name = folders[0][1]
        else:
            return "Scraping complete, but could not determine folder name."

    sources[folder_name] = {"url": url, "site": site}
    save_sources(sources)
    return f"Added \"{folder_name}\" from {site}."


def action_delete(novel: dict, sources: dict) -> str:
    name = novel["name"]
    if name not in sources:
        return f"No source URL tracked for \"{name}\"."

    answer = prompt_yn(f"\n  Delete source URL for \"{name}\"?")
    if answer is None or not answer:
        return "Cancelled."
    del sources[name]
    save_sources(sources)
    return "Source URL removed."


def action_update(novel: dict, sources: dict) -> str:
    name = novel["name"]
    print()
    url = prompt_line(f"  New URL for \"{name}\": ")
    if url is None:
        return "Cancelled."
    url = url.strip()
    if not url:
        return "Cancelled."

    try:
        site = detect_site(url)
    except Exception:
        return "Unsupported URL."

    sources[name] = {"url": url, "site": site}
    save_sources(sources)
    return f"Source URL updated ({site})."


# ---------------------------------------------------------------------------
# Main loop
# ---------------------------------------------------------------------------

def main():
    # Fix Windows console encoding
    if sys.platform == "win32":
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")

    sources = load_sources()
    cursor = 0
    status = ""

    while True:
        novels = list_novels()
        if cursor >= len(novels):
            cursor = max(0, len(novels) - 1)

        render(novels, sources, cursor, status)
        status = ""

        key = get_key()

        if key in ("q", "escape"):
            clear_screen()
            break
        elif key == "up":
            if cursor > 0:
                cursor -= 1
        elif key == "down":
            if cursor < len(novels) - 1:
                cursor += 1
        elif key == "enter":
            if novels:
                status = action_check(novels[cursor], sources)
        elif key == "a":
            status = action_add(sources)
            sources = load_sources()
        elif key == "d":
            if novels:
                status = action_delete(novels[cursor], sources)
        elif key == "u":
            if novels:
                status = action_update(novels[cursor], sources)


if __name__ == "__main__":
    main()
