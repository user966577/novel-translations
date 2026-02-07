---
name: glossary
description: Manage and maintain the translation glossary. Check for issues, search terms, view stats, or add new entries.
argument-hint: "[check|search|stats|add] [query]"
---

# Glossary Management

Maintain `translation_glossary.csv` — the single source of truth for all translation terms.

## Subcommands

### `/glossary check`

Audit the glossary for issues:

1. **Duplicate Chinese entries**: Same Chinese term with different English translations (potential inconsistency)
2. **Duplicate English entries**: Different Chinese terms mapping to the same English (may be intentional but worth flagging)
3. **Format issues**: Missing fields, malformed CSV rows, empty English translations
4. **Category validation**: Flag entries with non-standard categories (compare against the established set: character_name, cultivation_term, cultivation_realm, cultivation_path, technique, item, location, organization, creature, race, title, genre, medical_term)
5. **Novel column validation**: Flag entries where the Novel column doesn't match any known novel folder in `translated/`
6. **Orphaned notes**: Entries where novel-specific info is still in Notes instead of the Novel column (migration leftovers)

Output a report with issues grouped by severity (errors, warnings, suggestions).

### `/glossary search [query]`

Search the glossary:

- Search by Chinese characters, English translation, or category
- Support partial matching
- Show all matching entries in a formatted table
- If `query` looks like a novel name, filter to that novel's entries

Examples:
- `/glossary search 林渊` — find by Chinese
- `/glossary search "Lin Yuan"` — find by English
- `/glossary search cultivation_realm` — list all cultivation realms
- `/glossary search "Killing Spree"` — all terms for that novel

### `/glossary stats`

Show glossary statistics:

- Total entry count
- Breakdown by category (table with counts)
- Breakdown by novel (table with counts, including universal/unscoped terms)
- Most recent additions (last 20 entries by position in file)
- Flag any potential issues found during counting

### `/glossary add [chinese] [english] [category] [novel]`

Add a new term interactively:

1. Check if the Chinese term already exists (warn if duplicate)
2. Check if the English translation already exists for a different Chinese term
3. Validate the category against the standard set
4. If novel is provided, validate against known novel folders
5. Append the new row to `translation_glossary.csv`
6. Confirm the addition with the full entry shown

If arguments are incomplete, prompt for missing fields.

## CSV Format

```
Chinese,English,Category,Novel,Notes
新术语,New Term,technique,Novel Name,Optional description
```

- **Chinese**: Exact characters as they appear in source text
- **English**: Translated term (use exactly as specified everywhere)
- **Category**: One of the standard categories listed above
- **Novel**: Short novel name (empty for universal terms shared across novels)
- **Notes**: Only for universally applicable context (e.g., "Energy center in the body")
