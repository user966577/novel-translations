---
name: translate
description: Translate Chinese web novel chapters to English. Use when the user wants to translate raw chapters, provides Chinese text, or references chapter numbers to translate.
argument-hint: "[novel-folder] [chapter-range]"
---

# Translate Chapters

Translate raw Chinese chapters into polished English following all rules in CLAUDE.md.

## Arguments

- `$ARGUMENTS` should specify the novel folder name and chapter range
- The chapter specifier can be:
  - A range: `98-102` → chapters 98 through 102
  - A single chapter number: `294` → just chapter 294
  - A count (requires context): a standalone number that means "translate the next N chapters starting after the last translated chapter"
- **How to distinguish a single chapter vs. a count**: Check `metadata.json` for the highest existing chapter number. If the number given is **less than or equal to the highest chapter + 1**, treat it as a single chapter number. If it is **much smaller than the highest chapter** (e.g., highest is 543 and user writes `15`), treat it as a count of chapters. Use common sense—a user translating chapter 500+ is not asking for chapter 15.
- When interpreting as a count: read `metadata.json` to find the last translated chapter number, then translate chapters `(last + 1)` through `(last + N)`
- Examples:
  - `/translate after-villain-lies-low 98-102` → chapters 98–102
  - `/translate "No Daughter of Luck Shall Be Spared!" 294` → chapter 294
  - `/translate "The Villain Snatched the Protagonist's Master at the Start" 15` → next 15 chapters after the last translated one
- If no arguments given, ask the user which novel and chapter(s) to translate

## Workflow

### 1. Setup

- Load and parse `common_glossary.csv` (universal terms)
- Load and parse `translated/<novel>/glossary.md` (novel-specific terms)
- Identify the novel's folder in `raw/` and `translated/`
- Read `translated/<novel>/metadata.json` to check existing chapter titles and find where translation left off

### 2. Identify Chapters

- Parse the chapter specifier from arguments:
  - Range (`98-102`): chapters 98 through 102
  - Single chapter (`294`): just that chapter
  - Count (`15` when last translated chapter is 543): compute range as 544–558
- When interpreting as a count, read `metadata.json` to find the highest chapter number in `chapter_titles`, then set the range to `(last + 1)` through `(last + N)`. Report the computed range to the user before proceeding (e.g., "Last translated chapter is 543. Translating chapters 544–558.")
- Locate matching raw files in `raw/<novel>/` by chapter number prefix (format: `NNN_[title].txt`)
- If a chapter is already translated (file exists in `translated/<novel>/`), warn the user and skip unless they confirm overwrite

### 3. Translate Each Chapter

For each chapter in order:

- Read the raw Chinese text from `raw/<novel>/NNN_[title].txt`
- Translate the full chapter following all CLAUDE.md rules:
  - Reference glossary for every recurring term, name, location, technique
  - Natural English priority — it should read like it was written in English
  - Match tone to scene type (formal cultivation, action, comedy, casual)
  - Convert all measurements to imperial, all time units to hours/minutes, all currency to USD context
  - Translate meaningful proper nouns (sect names, locations) per CLAUDE.md guidelines
  - Keep character names in Pinyin
- Save the translation to `translated/<novel>/chapterN.txt` (content only, no title in file)
- Extract a natural English chapter title from the Chinese title (or from content context)

### 4. After EACH Chapter (not at the end of a batch)

- **Update metadata.json**: Add the chapter number and English title to `chapter_titles`
- **Update glossary**: Append any new novel-specific terms to `translated/<novel>/glossary.md` under the correct category heading:
  ```
  | 新术语 | New Term | Optional description |
  ```
  If a category section doesn't exist yet, create a new `## Category` section with the table header. Universal terms shared across novels go in `common_glossary.csv` instead.

### 5. Summary Report

After all chapters are complete, output:

```
## Translation Summary
- Novel: [name]
- Chapters translated: [range]
- Word count: ~[total] words
- New glossary terms added: [count]
  - [Chinese] -> [English] (category)
  - ...
- Flagged issues: [any inconsistencies, ambiguous terms, or questions]
```

## Important Rules

- NEVER leave Chinese characters untranslated in the output (unless intentional for effect)
- NEVER guess a glossary term — look it up every time
- ALWAYS save after each chapter (don't batch saves — a crash loses everything)
- ALWAYS update metadata.json and glossary after each chapter, not at the end
- If a raw chapter file is missing, report it and continue with the next chapter
- Match the existing chapter numbering in metadata.json (don't create gaps)
