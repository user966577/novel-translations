---
name: translate
description: Translate Chinese web novel chapters to English. Use when the user wants to translate raw chapters, provides Chinese text, or references chapter numbers to translate.
argument-hint: "[novel-folder] [chapter-range]"
---

# Translate Chapters

Translate raw Chinese chapters into polished English following all rules in CLAUDE.md.

## Arguments

- `$ARGUMENTS` should specify the novel folder name and chapter range
- Examples: `/translate after-villain-lies-low 98-102`, `/translate "No Daughter of Luck Shall Be Spared!" 294`
- If no arguments given, ask the user which novel and chapter(s) to translate

## Workflow

### 1. Setup

- Load and parse `translation_glossary.csv` completely
- Filter to entries relevant to this novel (matching Novel column + entries with empty Novel column for universal terms)
- Identify the novel's folder in `raw/` and `translated/`
- Read `translated/<novel>/metadata.json` to check existing chapter titles and find where translation left off

### 2. Identify Chapters

- Parse the chapter range from arguments (e.g., "98-102" = chapters 98 through 102, "294" = single chapter)
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
- **Update glossary**: Append any new terms encountered to `translation_glossary.csv` with proper categorization:
  ```
  Chinese,English,Category,Novel,Notes
  新术语,New Term,technique,Novel Name Here,Optional description
  ```
- Use the novel's short name in the Novel column (match existing entries for that novel)

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
