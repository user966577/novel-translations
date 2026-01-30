# Novel Translations

A repository for Chinese web novel translation projects, designed to work with Claude Code (both locally and via the web app).

## Project Structure

```
novel-translations/
├── CLAUDE.md                    # Translation style guide (auto-loaded by Claude)
├── translation_glossary.csv     # Master glossary for all novels
├── requirements.txt             # Python dependencies
├── scripts/
│   ├── scraper.py              # Chapter downloader
│   ├── create_epub.py          # EPUB generation library
│   └── build_epub.py           # Build EPUB from translated novel folder
├── raw/                         # Raw Chinese chapters
│   └── <novel-name>/
│       └── chapter001.txt, ...
├── translated/                  # Finished English translations
│   └── <novel-name>/
│       ├── metadata.json       # Novel info and chapter titles
│       ├── cover.jpg           # Cover image
│       └── chapter001.txt, ...
└── output/                      # Generated EPUBs
```

## Current Novels

### After the Villain Lies Low, the Heroines Panic
- **Status**: 80 chapters translated
- **Folder**: `translated/After the Villain Lies Low, the Heroines Panic/`

## How to Use

### With Claude Code Web App

1. Connect this repository via [claude.ai/code](https://claude.ai/code)
2. Ask Claude to translate chapters:
   ```
   Translate chapters 70-75 from raw/after-villain-lies-low/
   ```
3. Review the diff and approve the PR

### Locally with Claude Code CLI

1. Clone the repository
2. Install dependencies: `pip install -r requirements.txt`
3. Use Claude Code to translate or build EPUBs

### Building EPUBs

```bash
# Build EPUB for a specific novel
python scripts/build_epub.py translated/after-villain-lies-low

# Or run without arguments to build the default novel
python scripts/build_epub.py
```

## Translation Workflow

1. **Add raw chapters** to `raw/<novel-name>/`
2. **Translate** using Claude (reads glossary automatically)
3. **Save translations** to `translated/<novel-name>/chapterXXX.txt`
4. **Update metadata.json** with new chapter titles
5. **Update glossary** with any new terms
6. **Build EPUB** when ready

## Glossary

The `translation_glossary.csv` file contains all terms, names, and translations used across novels. Always reference it for consistency.

Format:
```csv
Chinese,English,Category,Notes
林渊,Lin Yuan,character_name,Main protagonist
气海境,Qi Sea Realm,cultivation_realm,
```

## Adding a New Novel

1. Create folders:
   ```
   raw/<novel-name>/
   translated/<novel-name>/
   ```

2. Add a `metadata.json` in the translated folder:
   ```json
   {
     "title": "Novel Title",
     "author": "Author Name",
     "cover_image": "cover.jpg",
     "synopsis": "Novel description...",
     "chapter_titles": {
       "1": "Chapter 1 Title",
       "2": "Chapter 2 Title"
     }
   }
   ```

3. Add cover image as `cover.jpg`

4. Start translating!
