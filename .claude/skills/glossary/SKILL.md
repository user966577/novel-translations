---
name: glossary
description: Manage and maintain the translation glossary. Check for issues, search terms, view stats, or add new entries.
argument-hint: "[check|search|stats|add] [query]"
---

# Glossary Management

Maintain the split glossary system: `common_glossary.csv` (universal terms) + `translated/<novel>/glossary.md` (per-novel terms).

## Subcommands

### `/glossary check`

Audit the glossary for issues:

1. **Duplicate Chinese entries**: Same Chinese term across common glossary and novel glossaries, or within a single file, with different English translations
2. **Duplicate English entries**: Different Chinese terms mapping to the same English (may be intentional but worth flagging)
3. **Format issues**: Malformed CSV rows in `common_glossary.csv`, broken markdown tables in `glossary.md` files, empty English translations
4. **Category validation**: Flag entries with non-standard categories (compare against the established set: character_name, cultivation_term, cultivation_realm, cultivation_path, technique, item, location, organization, creature, race, title, genre, medical_term, skill, system, event, weapon, profession)
5. **Missing glossaries**: Flag novel folders in `translated/` that lack a `glossary.md` file
6. **Common vs novel-specific**: Flag entries in `common_glossary.csv` that look novel-specific (e.g., character names), or novel `glossary.md` entries that look universal

Output a report with issues grouped by severity (errors, warnings, suggestions).

### `/glossary search [query]`

Search the glossary:

- Search `common_glossary.csv` + all `translated/*/glossary.md` files
- Search by Chinese characters, English translation, or category
- Support partial matching
- Show all matching entries in a formatted table, noting which file each came from
- If `query` looks like a novel name, show that novel's full `glossary.md` contents

Examples:
- `/glossary search 林渊` — find by Chinese across all glossary files
- `/glossary search "Lin Yuan"` — find by English
- `/glossary search cultivation_realm` — list all cultivation realms (common + all novels)
- `/glossary search "Killing Spree"` — all terms from that novel's glossary.md

### `/glossary stats`

Show glossary statistics:

- Total entry count across all files
- `common_glossary.csv` count with breakdown by category
- Per-novel `glossary.md` counts (table with novel name and term count)
- Most recent additions (last 10 entries by position in each file)
- Flag any potential issues found during counting

### `/glossary add [chinese] [english] [category] [novel]`

Add a new term interactively:

1. Check if the Chinese term already exists in `common_glossary.csv` or any `glossary.md` (warn if duplicate)
2. Check if the English translation already exists for a different Chinese term
3. Validate the category against the standard set
4. Route to the correct file:
   - If `novel` is provided: append to `translated/<novel>/glossary.md` under the matching `## Category` section
   - If no `novel`: append to `common_glossary.csv`
5. Confirm the addition with the full entry shown

If arguments are incomplete, prompt for missing fields.

## File Formats

**common_glossary.csv**:
```
Chinese,English,Category,Notes
新术语,New Term,technique,Optional description
```

**translated/<novel>/glossary.md** (entries grouped under `## Category` headings):
```markdown
## Techniques

| Chinese | English | Notes |
|---------|---------|-------|
| 新术语 | New Term | Optional description |
```
