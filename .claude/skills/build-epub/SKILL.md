---
name: build-epub
description: Build an EPUB file from translated chapters for a novel.
argument-hint: "[novel-folder]"
disable-model-invocation: true
---

# Build EPUB

Generate an EPUB from a novel's translated chapters using the build_epub.py script.

## Arguments

- `$ARGUMENTS` should be the novel folder name inside `translated/`
- Example: `/build-epub after-villain-lies-low`
- Example: `/build-epub "No Daughter of Luck Shall Be Spared!"`
- If no argument given, list available novels in `translated/` and ask which to build

## Steps

1. **Verify the novel folder exists** in `translated/` and has a `metadata.json`
2. **Check chapter count**: Report how many chapter files exist vs how many titles are in metadata.json. Warn if there's a mismatch (missing titles = missing metadata.json entries)
3. **Run the build script**:
   ```bash
   python scripts/build_epub.py "translated/$ARGUMENTS"
   ```
4. **Report results**: Confirm the EPUB was created, its location in `output/`, file size, and chapter count

## Troubleshooting

- If `metadata.json` is missing chapter titles, offer to generate them from context
- If `ebooklib` is not installed, run `pip install ebooklib`
- If the script fails, show the error and suggest fixes
