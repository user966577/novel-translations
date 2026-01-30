#!/usr/bin/env python3
"""
EPUB Creator for Translated Novels
Creates properly formatted EPUB files from translated chapter text.
"""

from ebooklib import epub
import os

def text_to_html(text: str) -> str:
    """Convert plain text to HTML paragraphs."""
    lines = text.strip().split('\n')
    html_parts = []

    for line in lines:
        line = line.strip()
        if not line:
            continue
        if line.startswith('='):  # Skip separator lines
            html_parts.append('<hr/>')
        elif line.startswith('[') and line.endswith(']'):  # System messages
            html_parts.append(f'<p class="system"><em>{line}</em></p>')
        elif line.startswith('"') or line.startswith('"'):  # Dialogue
            html_parts.append(f'<p class="dialogue">{line}</p>')
        else:
            html_parts.append(f'<p>{line}</p>')

    return '\n'.join(html_parts)

def create_chapter_epub(
    chapter_text: str,
    chapter_title: str,
    chapter_number: int,
    novel_title: str,
    author: str,
    output_path: str
):
    """Create an EPUB file for a single chapter."""

    book = epub.EpubBook()

    # Set metadata
    book.set_identifier(f'{novel_title.replace(" ", "_")}_ch{chapter_number}')
    book.set_title(f'{novel_title} - {chapter_title}')
    book.set_language('en')
    book.add_author(author)

    # Create CSS
    style = '''
    body {
        font-family: Georgia, serif;
        line-height: 1.6;
        margin: 5%;
    }
    h1 {
        text-align: center;
        margin-bottom: 2em;
        font-size: 1.5em;
    }
    p {
        text-indent: 1.5em;
        margin: 0.5em 0;
    }
    p.dialogue {
        text-indent: 1.5em;
    }
    p.system {
        text-align: center;
        text-indent: 0;
        margin: 1em 0;
        color: #555;
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

    # Create chapter content
    chapter_html = text_to_html(chapter_text)

    chapter = epub.EpubHtml(
        title=chapter_title,
        file_name='chapter1.xhtml',
        lang='en'
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

    # Add navigation
    book.toc = [epub.Link('chapter1.xhtml', chapter_title, 'ch1')]
    book.add_item(epub.EpubNcx())
    book.add_item(epub.EpubNav())

    # Set spine
    book.spine = ['nav', chapter]

    # Write EPUB
    epub.write_epub(output_path, book, {})
    print(f'Created: {output_path}')

def create_novel_epub(
    chapters: list,  # List of (chapter_title, chapter_text)
    novel_title: str,
    author: str,
    output_path: str,
    cover_image_path: str = None,
    description: str = None
):
    """Create an EPUB file containing multiple chapters with optional cover and description."""

    book = epub.EpubBook()

    # Set metadata
    book.set_identifier(novel_title.replace(" ", "_"))
    book.set_title(novel_title)
    book.set_language('en')
    book.add_author(author)

    if description:
        book.add_metadata('DC', 'description', description)

    # Create CSS
    style = '''
    body {
        font-family: Georgia, serif;
        line-height: 1.6;
        margin: 5%;
    }
    h1 {
        text-align: center;
        margin-bottom: 2em;
        font-size: 1.5em;
    }
    h2 {
        text-align: center;
        margin-bottom: 1em;
        font-size: 1.3em;
    }
    p {
        text-indent: 1.5em;
        margin: 0.5em 0;
    }
    p.dialogue {
        text-indent: 1.5em;
    }
    p.system {
        text-align: center;
        text-indent: 0;
        margin: 1em 0;
        color: #555;
    }
    p.synopsis {
        text-indent: 0;
        margin: 0.8em 0;
    }
    hr {
        border: none;
        border-top: 1px solid #ccc;
        margin: 2em auto;
        width: 50%;
    }
    .cover-page {
        text-align: center;
        padding: 0;
        margin: 0;
    }
    .cover-page img {
        max-width: 100%;
        max-height: 100%;
    }
    .title-page {
        text-align: center;
        margin-top: 30%;
    }
    .title-page h1 {
        font-size: 2em;
        margin-bottom: 0.5em;
    }
    .title-page .author {
        font-size: 1.2em;
        color: #666;
    }
    .synopsis-page {
        margin-top: 2em;
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

    # Add cover image if provided
    if cover_image_path and os.path.exists(cover_image_path):
        # Determine image type
        ext = cover_image_path.lower().split('.')[-1]
        if ext == 'jpg' or ext == 'jpeg':
            media_type = 'image/jpeg'
            ext = 'jpg'
        elif ext == 'png':
            media_type = 'image/png'
        else:
            media_type = 'image/jpeg'
            ext = 'jpg'

        # Read cover image
        with open(cover_image_path, 'rb') as img_file:
            cover_content = img_file.read()

        # Use set_cover which handles everything properly
        book.set_cover(f"cover.{ext}", cover_content)

    # Add title page with synopsis if description provided
    if description:
        # Convert description to HTML paragraphs
        desc_paragraphs = []
        for line in description.strip().split('\n'):
            line = line.strip()
            if line:
                desc_paragraphs.append(f'<p class="synopsis">{line}</p>')
        desc_html = '\n'.join(desc_paragraphs)

        title_page = epub.EpubHtml(
            title='Synopsis',
            file_name='synopsis.xhtml',
            lang='en'
        )
        title_page.content = f'''<html xmlns="http://www.w3.org/1999/xhtml">
<head>
    <title>{novel_title}</title>
    <link rel="stylesheet" type="text/css" href="style/main.css"/>
</head>
<body>
    <div class="title-page">
        <h1>{novel_title}</h1>
        <p class="author">by {author}</p>
    </div>
    <div class="synopsis-page">
        <h2>Synopsis</h2>
        {desc_html}
    </div>
</body>
</html>'''
        title_page.add_item(css)
        book.add_item(title_page)
        spine_items.append(title_page)
        # Don't add to TOC - synopsis is front matter, not a chapter

    # Create chapters
    epub_chapters = []

    for i, (chapter_title, chapter_text) in enumerate(chapters, 1):
        chapter_html = text_to_html(chapter_text)

        chapter = epub.EpubHtml(
            title=chapter_title,
            file_name=f'chapter{i}.xhtml',
            lang='en'
        )
        # Nav title includes chapter number, content title does not
        nav_title = f'Chapter {i}: {chapter_title}'

        chapter.content = f'''<html xmlns="http://www.w3.org/1999/xhtml">
<head>
    <title>{nav_title}</title>
    <link rel="stylesheet" type="text/css" href="style/main.css"/>
</head>
<body>
    {chapter_html}
</body>
</html>'''

        chapter.add_item(css)
        book.add_item(chapter)
        epub_chapters.append(chapter)
        toc.append(epub.Link(f'chapter{i}.xhtml', nav_title, f'ch{i}'))

    # Add navigation
    book.toc = toc
    book.add_item(epub.EpubNcx())
    book.add_item(epub.EpubNav())

    # Set spine
    book.spine = spine_items + epub_chapters

    # Write EPUB
    epub.write_epub(output_path, book, {})
    print(f'Created: {output_path}')


if __name__ == '__main__':
    import sys

    if len(sys.argv) < 2:
        print("Usage: python create_epub.py <text_file> [output_epub]")
        sys.exit(1)

    input_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else input_file.rsplit('.', 1)[0] + '.epub'

    with open(input_file, 'r', encoding='utf-8') as f:
        text = f.read()

    # Extract chapter title from first line
    lines = text.strip().split('\n')
    chapter_title = lines[0].strip()

    create_chapter_epub(
        chapter_text=text,
        chapter_title=chapter_title,
        chapter_number=1,
        novel_title="Translated Novel",
        author="Translator",
        output_path=output_file
    )
