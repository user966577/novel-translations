---
name: novel-status
description: Show a dashboard of all novels in the project with translation progress, chapter counts, and glossary coverage.
---

# Novel Status Dashboard

Provide a quick overview of every novel in the project.

## Steps

1. **Scan `translated/` directory**: List all novel folders
2. **For each novel**, gather:
   - Total translated chapters (count `chapter*.txt` files)
   - Chapter title coverage (count entries in `metadata.json` `chapter_titles` vs actual chapter files)
   - Latest chapter number translated
   - Cover image present? (check for cover.jpg or cover.png)
3. **Scan `raw/` directory**: For each novel, count raw chapter files available
4. **Scan glossary**: Count terms from each novel's `glossary.md` file (count table rows). Also note total universal terms in `common_glossary.csv`.
5. **Check `output/`**: Note which novels have EPUBs built and their file sizes

## Output Format

```
## Novel Translation Dashboard

| Novel | Raw | Translated | Latest | Glossary Terms | EPUB |
|-------|-----|------------|--------|----------------|------|
| After the Villain Lies Low... | 636 | 97 | Ch.97 | 142 | 386 KB |
| No Daughter of Luck... | 400 | 293 | Ch.293 | 87 | 1.1 MB |
| ... | ... | ... | ... | ... | ... |

### Notes
- [Novel X]: metadata.json missing 3 chapter titles
- [Novel Y]: No cover image found
- [Novel Z]: EPUB is outdated (translated chapters > EPUB chapters)
```

## Additional Details

If the user asks about a specific novel (e.g., `/novel-status "Killing Spree"`), show expanded info:
- Full title and author from metadata.json
- Synopsis (first 2 sentences)
- Complete chapter range (first to last)
- All glossary terms for that novel (grouped by category)
- Any gaps in chapter numbering
