#!/usr/bin/env python3
"""Migrate translation_glossary.csv into common_glossary.csv + per-novel glossary.md files.

One-time migration script. Splits the single monolithic glossary into:
- common_glossary.csv: Universal terms (empty Novel column)
- translated/<novel-folder>/glossary.md: Novel-specific terms as markdown tables
"""

import csv
import os
import sys
from collections import defaultdict
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
GLOSSARY_CSV = PROJECT_ROOT / 'translation_glossary.csv'
COMMON_CSV = PROJECT_ROOT / 'common_glossary.csv'
TRANSLATED_DIR = PROJECT_ROOT / 'translated'

# Map glossary short names to actual folder names
NOVEL_FOLDER_MAP = {
    '10000x Return': '10,000x Return—When My Disciple Reaches Foundation Establishment, I Instantly Ascend to Immortality',
    'Dual Cultivation': 'After Joining the Sect, I Raised Geniuses Through Dual Cultivation',
    'Hospital Sign In': 'Hospital Sign In, First Operation Shocked the Nation',
    'Killing Spree': 'Recognized by His Family, the True Young Master Went on a Killing Spree',
    'No Daughter of Luck': 'No Daughter of Luck Shall Be Spared!',
    'Sole Immortal': 'Sole Immortal—My Leisurely Cultivation After Rebirth',
    'Villain Campus Belle': 'Villain—Suppressing the Protagonist and Stealing the Campus Belle from the Start',
    'Villain Kiss': 'Villain—Before Dying, I Forced a Kiss on My Master',
    'Villain Refused Script': 'The Villain Refused To Play By the Script',
    'Villain Snatched Master': 'The Villain Snatched the Protagonist\'s Master at the Start',
}

# Category display order and nice names
CATEGORY_ORDER = [
    'character_name',
    'cultivation_realm',
    'cultivation_term',
    'cultivation_path',
    'technique',
    'skill',
    'item',
    'weapon',
    'location',
    'organization',
    'creature',
    'race',
    'title',
    'profession',
    'medical_term',
    'system',
    'event',
    'genre',
]

CATEGORY_DISPLAY = {
    'character_name': 'Characters',
    'cultivation_realm': 'Cultivation Realms',
    'cultivation_term': 'Cultivation Terms',
    'cultivation_path': 'Cultivation Paths',
    'technique': 'Techniques',
    'skill': 'Skills',
    'item': 'Items',
    'weapon': 'Weapons',
    'location': 'Locations',
    'organization': 'Organizations',
    'creature': 'Creatures',
    'race': 'Races',
    'title': 'Titles',
    'profession': 'Professions',
    'medical_term': 'Medical Terms',
    'system': 'System',
    'event': 'Events',
    'genre': 'Genre Terms',
}


def read_glossary():
    """Read and return all entries from translation_glossary.csv."""
    entries = []
    with open(GLOSSARY_CSV, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            entries.append(row)
    return entries


def split_entries(entries):
    """Split entries into universal and per-novel groups."""
    universal = []
    per_novel = defaultdict(list)

    for entry in entries:
        novel = entry.get('Novel', '').strip()
        if not novel:
            universal.append(entry)
        else:
            per_novel[novel].append(entry)

    return universal, per_novel


def write_common_csv(universal_entries):
    """Write universal entries to common_glossary.csv."""
    with open(COMMON_CSV, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=['Chinese', 'English', 'Category', 'Notes'])
        writer.writeheader()
        for entry in universal_entries:
            writer.writerow({
                'Chinese': entry['Chinese'],
                'English': entry['English'],
                'Category': entry['Category'],
                'Notes': entry.get('Notes', ''),
            })
    print(f"Wrote {len(universal_entries)} universal entries to {COMMON_CSV}")


def generate_glossary_md(entries):
    """Generate markdown glossary content from a list of entries."""
    # Group by category
    by_category = defaultdict(list)
    for entry in entries:
        by_category[entry['Category']].append(entry)

    lines = ['# Glossary', '']

    # Use CATEGORY_ORDER for consistent ordering, then any remaining categories
    ordered_cats = [c for c in CATEGORY_ORDER if c in by_category]
    extra_cats = sorted(set(by_category.keys()) - set(CATEGORY_ORDER))
    ordered_cats.extend(extra_cats)

    for cat in ordered_cats:
        cat_entries = by_category[cat]
        display_name = CATEGORY_DISPLAY.get(cat, cat.replace('_', ' ').title())

        lines.append(f'## {display_name}')
        lines.append('')
        lines.append('| Chinese | English | Notes |')
        lines.append('|---------|---------|-------|')

        for entry in cat_entries:
            chinese = entry['Chinese']
            english = entry['English']
            notes = entry.get('Notes', '').strip()
            # Escape pipe characters in values
            chinese = chinese.replace('|', '\\|')
            english = english.replace('|', '\\|')
            notes = notes.replace('|', '\\|')
            lines.append(f'| {chinese} | {english} | {notes} |')

        lines.append('')

    return '\n'.join(lines)


def merge_existing_glossary_txt(md_content, novel_folder):
    """Merge existing glossary.txt content into the markdown glossary if present."""
    glossary_txt = novel_folder / 'glossary.txt'
    if not glossary_txt.exists():
        return md_content

    with open(glossary_txt, 'r', encoding='utf-8') as f:
        txt_content = f.read().strip()

    if not txt_content:
        return md_content

    # Append the old glossary.txt content as a reference section
    md_content += '\n## Reference Notes\n\n'
    md_content += 'The following reference material was preserved from the original glossary notes:\n\n'
    md_content += txt_content + '\n'

    return md_content


def write_novel_glossaries(per_novel):
    """Write per-novel glossary.md files."""
    unmapped = []

    for novel_short, entries in per_novel.items():
        folder_name = NOVEL_FOLDER_MAP.get(novel_short)
        if not folder_name:
            unmapped.append(novel_short)
            continue

        novel_folder = TRANSLATED_DIR / folder_name
        if not novel_folder.exists():
            print(f"  WARNING: Folder not found for '{novel_short}' -> {novel_folder}")
            continue

        md_content = generate_glossary_md(entries)

        # Check for existing glossary.txt to merge
        md_content = merge_existing_glossary_txt(md_content, novel_folder)

        glossary_md = novel_folder / 'glossary.md'
        with open(glossary_md, 'w', encoding='utf-8') as f:
            f.write(md_content)

        print(f"  {novel_short}: {len(entries)} entries -> {glossary_md.name}")

    if unmapped:
        print(f"\n  WARNING: No folder mapping for novels: {unmapped}")
        print("  These entries will remain only in the original CSV backup.")


def delete_old_files():
    """Delete the old translation_glossary.csv and any merged glossary.txt files."""
    # Delete old glossary.txt if it was merged
    glossary_txt = TRANSLATED_DIR / 'No Daughter of Luck Shall Be Spared!' / 'glossary.txt'
    if glossary_txt.exists():
        os.remove(glossary_txt)
        print(f"Deleted {glossary_txt}")

    # Delete old CSV
    if GLOSSARY_CSV.exists():
        os.remove(GLOSSARY_CSV)
        print(f"Deleted {GLOSSARY_CSV}")


def verify(original_count, universal_entries, per_novel):
    """Verify no data was lost."""
    novel_count = sum(len(entries) for entries in per_novel.values())
    total = len(universal_entries) + novel_count

    print(f"\nVerification:")
    print(f"  Original entries:  {original_count}")
    print(f"  Universal entries: {len(universal_entries)}")
    print(f"  Novel entries:     {novel_count}")
    print(f"  Total:             {total}")

    if total == original_count:
        print("  STATUS: OK — no data lost")
        return True
    else:
        print(f"  STATUS: MISMATCH — {original_count - total} entries unaccounted for")
        return False


def main():
    if not GLOSSARY_CSV.exists():
        print(f"Error: {GLOSSARY_CSV} not found")
        sys.exit(1)

    print("Reading translation_glossary.csv...")
    entries = read_glossary()
    original_count = len(entries)
    print(f"  Found {original_count} entries")

    print("\nSplitting entries...")
    universal, per_novel = split_entries(entries)

    print(f"\nWriting common_glossary.csv...")
    write_common_csv(universal)

    print(f"\nWriting per-novel glossary.md files...")
    write_novel_glossaries(per_novel)

    if not verify(original_count, universal, per_novel):
        print("\nAborting — data mismatch detected. Original file preserved.")
        # Clean up the common CSV we just wrote
        if COMMON_CSV.exists():
            os.remove(COMMON_CSV)
        sys.exit(1)

    print("\nCleaning up old files...")
    delete_old_files()

    print("\nMigration complete!")


if __name__ == '__main__':
    main()
