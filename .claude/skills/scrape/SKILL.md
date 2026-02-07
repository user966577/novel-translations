---
name: scrape
description: Download raw Chinese chapters from supported novel sites using scraper.py.
argument-hint: "[url]"
disable-model-invocation: true
---

# Scrape Novel Chapters

Download raw Chinese chapters using the project's scraper script.

## Arguments

- `$ARGUMENTS` should be a URL to a novel's chapter list page
- Example: `/scrape https://m.shuhaige.net/novel/12345/`

## Supported Sites

The scraper (`scripts/scraper.py`) supports:
- shuhaige.net (m.shuhaige.net)
- novel543.com
- wxdzs.net
- jpxs123.com
- wfxs.tw
- uukanshu.cc

## Steps

1. **Validate the URL** matches a supported site
2. **Run the scraper**:
   ```bash
   python scripts/scraper.py "$ARGUMENTS"
   ```
3. **Report results**: Number of chapters downloaded, output location, any errors
4. **Suggest next steps**: Remind user to organize files into `raw/<novel-name>/` if the scraper outputs elsewhere

## Notes

- The scraper adds a 1.5-second delay between requests to avoid blocking
- Chapters are saved as UTF-8 `.txt` files
- Errors are logged to `errors.log` in the output folder
- If a download fails partway through, the scraper can be re-run — it overwrites existing files
