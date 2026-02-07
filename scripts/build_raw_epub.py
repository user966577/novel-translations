#!/usr/bin/env python3
"""Build EPUB from raw (untranslated) Chinese chapters."""

import re
import sys
from pathlib import Path

# Add scripts directory to path for create_epub import
SCRIPT_DIR = Path(__file__).parent
sys.path.insert(0, str(SCRIPT_DIR))

from create_epub import create_novel_epub


def extract_chapter_info(filename: str) -> tuple:
    """
    Extract chapter number and title from raw chapter filename.

    Example: "116_第116章 姬傾雪的修行，巫神宗的來曆.txt"
    Returns: (116, "第116章 姬傾雪的修行，巫神宗的來曆")
    """
    stem = Path(filename).stem

    # Pattern: number_title
    match = re.match(r'^(\d+)_(.+)$', stem)
    if match:
        chapter_num = int(match.group(1))
        title = match.group(2)
        return chapter_num, title

    # Fallback: just try to get a number from the start
    match = re.match(r'^(\d+)', stem)
    if match:
        return int(match.group(1)), stem

    return 0, stem


def build_raw_epub(raw_folder: str, output_path: str = None, title: str = None, author: str = "Unknown"):
    """
    Build an EPUB from a folder containing raw Chinese chapter files.

    Args:
        raw_folder: Path to the folder containing raw chapter .txt files
        output_path: Optional output path for the EPUB file
        title: Novel title (defaults to folder name)
        author: Author name
    """
    raw_path = Path(raw_folder)

    if not raw_path.exists():
        print(f"Error: Folder not found: {raw_folder}")
        return

    # Get novel title from folder name if not specified
    if title is None:
        title = raw_path.name

    # Find all .txt chapter files (excluding errors.log and other non-chapter files)
    chapter_files = []
    for f in raw_path.glob('*.txt'):
        if f.name == 'errors.log':
            continue
        chapter_num, chapter_title = extract_chapter_info(f.name)
        if chapter_num > 0:
            chapter_files.append((chapter_num, chapter_title, f))

    # Sort by chapter number
    chapter_files.sort(key=lambda x: x[0])

    if not chapter_files:
        print(f"Error: No chapter files found in {raw_folder}")
        return

    print(f"Found {len(chapter_files)} chapters")

    # Load chapters
    chapters = []
    for chapter_num, chapter_title, chapter_file in chapter_files:
        with open(chapter_file, 'r', encoding='utf-8') as f:
            content = f.read()

        chapters.append((chapter_title, content))
        # Use ascii-safe print for Windows console compatibility
        try:
            print(f"Loaded: {chapter_title[:50]}...")
        except UnicodeEncodeError:
            print(f"Loaded chapter {chapter_num}...")

    # Determine output path
    if output_path is None:
        output_dir = SCRIPT_DIR.parent / 'output'
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / f"{title} (Raw).epub"
    else:
        output_path = Path(output_path)

    # Create EPUB - modify create_novel_epub call for Chinese
    create_raw_novel_epub(
        chapters=chapters,
        novel_title=title,
        author=author,
        output_path=str(output_path)
    )

    print(f"\nEPUB created with {len(chapters)} chapters: {output_path}")


def create_raw_novel_epub(
    chapters: list,
    novel_title: str,
    author: str,
    output_path: str
):
    """Create an EPUB file for raw Chinese chapters."""
    from ebooklib import epub

    book = epub.EpubBook()

    # Set metadata
    book.set_identifier(novel_title.replace(" ", "_") + "_raw")
    book.set_title(novel_title)
    book.set_language('zh')  # Chinese language
    book.add_author(author)

    # Create CSS optimized for Chinese text
    style = '''
    body {
        font-family: "Source Han Sans", "Noto Sans CJK", "Microsoft YaHei", "SimSun", sans-serif;
        line-height: 1.8;
        margin: 5%;
    }
    h1 {
        text-align: center;
        margin-bottom: 2em;
        font-size: 1.3em;
    }
    p {
        text-indent: 2em;
        margin: 0.5em 0;
    }
    hr {
        border: none;
        border-top: 1px solid #ccc;
        margin: 2em auto;
        width: 50%;
    }
    '''

    css = epub.EpubItem(
        uid="style",
        file_name="style/main.css",
        media_type="text/css",
        content=style
    )
    book.add_item(css)

    spine_items = ['nav']
    toc = []

    # Create chapters
    epub_chapters = []

    for i, (chapter_title, chapter_text) in enumerate(chapters, 1):
        # Convert text to HTML paragraphs
        lines = chapter_text.strip().split('\n')
        html_parts = []
        for line in lines:
            line = line.strip()
            if not line:
                continue
            if line.startswith('='):
                html_parts.append('<hr/>')
            else:
                html_parts.append(f'<p>{line}</p>')
        chapter_html = '\n'.join(html_parts)

        chapter = epub.EpubHtml(
            title=chapter_title,
            file_name=f'chapter{i}.xhtml',
            lang='zh'
        )

        chapter.content = f'''<html xmlns="http://www.w3.org/1999/xhtml">
<head>
    <title>{chapter_title}</title>
    <link rel="stylesheet" type="text/css" href="style/main.css"/>
</head>
<body>
    <h1>{chapter_title}</h1>
    {chapter_html}
</body>
</html>'''

        chapter.add_item(css)
        book.add_item(chapter)
        epub_chapters.append(chapter)
        toc.append(epub.Link(f'chapter{i}.xhtml', chapter_title, f'ch{i}'))

    # Add navigation
    book.toc = toc
    book.add_item(epub.EpubNcx())
    book.add_item(epub.EpubNav())

    # Set spine
    book.spine = spine_items + epub_chapters

    # Write EPUB
    epub.write_epub(output_path, book, {})
    print(f'Created: {output_path}')


def main():
    import argparse

    parser = argparse.ArgumentParser(description='Build EPUB from raw Chinese chapter files')
    parser.add_argument('raw_folder', help='Path to the folder containing raw .txt chapter files')
    parser.add_argument('-o', '--output', help='Output EPUB file path')
    parser.add_argument('-t', '--title', help='Novel title (defaults to folder name)')
    parser.add_argument('-a', '--author', default='Unknown', help='Author name')

    args = parser.parse_args()

    build_raw_epub(args.raw_folder, args.output, args.title, args.author)


if __name__ == '__main__':
    if len(sys.argv) == 1:
        print("Usage: python build_raw_epub.py <raw_folder> [-o output.epub] [-t title] [-a author]")
        sys.exit(1)
    else:
        main()
