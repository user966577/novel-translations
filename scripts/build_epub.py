#!/usr/bin/env python3
"""Build EPUB from translated chapters using metadata.json for novel info."""

import json
import os
import sys
from pathlib import Path

# Add scripts directory to path for create_epub import
SCRIPT_DIR = Path(__file__).parent
sys.path.insert(0, str(SCRIPT_DIR))

from create_epub import create_novel_epub


def build_novel_epub(novel_folder: str, output_dir: str = None):
    """
    Build an EPUB from a novel folder containing translated chapters and metadata.json.

    Args:
        novel_folder: Path to the novel folder (e.g., 'translated/after-villain-lies-low')
        output_dir: Optional output directory (defaults to 'output/')
    """
    novel_path = Path(novel_folder)

    # Load metadata
    metadata_file = novel_path / 'metadata.json'
    if not metadata_file.exists():
        print(f"Error: metadata.json not found in {novel_folder}")
        return

    with open(metadata_file, 'r', encoding='utf-8') as f:
        metadata = json.load(f)

    title = metadata.get('title', 'Unknown Novel')
    author = metadata.get('author', 'Unknown')
    synopsis = metadata.get('synopsis', '')
    chapter_titles = metadata.get('chapter_titles', {})
    cover_image = metadata.get('cover_image')

    # Find cover image
    cover_path = None
    if cover_image:
        potential_cover = novel_path / cover_image
        if potential_cover.exists():
            cover_path = str(potential_cover)

    # Find and load all chapter files
    chapter_files = sorted(
        novel_path.glob('chapter*.txt'),
        key=lambda x: int(x.stem.replace('chapter', ''))
    )

    if not chapter_files:
        print(f"Error: No chapter files found in {novel_folder}")
        return

    chapters = []
    for chapter_file in chapter_files:
        chapter_num = chapter_file.stem.replace('chapter', '')

        with open(chapter_file, 'r', encoding='utf-8') as f:
            content = f.read()

        # Get title from metadata or use default
        chapter_title = chapter_titles.get(chapter_num, f"Chapter {chapter_num}")

        chapters.append((chapter_title, content))
        print(f"Loaded Chapter {chapter_num}: {chapter_title[:50]}...")

    # Determine output path
    if output_dir is None:
        output_dir = SCRIPT_DIR.parent / 'output'
    else:
        output_dir = Path(output_dir)

    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{title}.epub"

    # Create EPUB
    create_novel_epub(
        chapters=chapters,
        novel_title=title,
        author=author,
        output_path=str(output_path),
        cover_image_path=cover_path,
        description=synopsis
    )

    print(f"\nEPUB created with {len(chapters)} chapters: {output_path}")


def main():
    import argparse

    parser = argparse.ArgumentParser(description='Build EPUB from translated novel folder')
    parser.add_argument('novel_folder', help='Path to the novel folder containing chapters and metadata.json')
    parser.add_argument('-o', '--output', help='Output directory (default: output/)')

    args = parser.parse_args()

    build_novel_epub(args.novel_folder, args.output)


if __name__ == '__main__':
    # If no arguments, build the default novel
    if len(sys.argv) == 1:
        # Default to building after-villain-lies-low
        project_root = SCRIPT_DIR.parent
        novel_folder = project_root / 'translated' / 'after-villain-lies-low'
        build_novel_epub(str(novel_folder))
    else:
        main()
