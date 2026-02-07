"""Generate translated/index.json for the LNReader plugin.

Scans translated/ and outputs a JSON array of novel entries with their files,
replacing the GitHub API calls the plugin previously used.
"""

import json
import os
import sys

TRANSLATED_DIR = os.path.join(os.path.dirname(__file__), '..', 'translated')


def generate_index():
    translated = os.path.normpath(TRANSLATED_DIR)
    if not os.path.isdir(translated):
        print(f"Error: {translated} is not a directory", file=sys.stderr)
        sys.exit(1)

    entries = []
    for name in sorted(os.listdir(translated)):
        novel_path = os.path.join(translated, name)
        if not os.path.isdir(novel_path):
            continue

        files = sorted(
            f for f in os.listdir(novel_path)
            if os.path.isfile(os.path.join(novel_path, f))
        )

        entries.append({
            "name": name,
            "type": "dir",
            "files": files,
        })

    output_path = os.path.join(translated, 'index.json')
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(entries, f, indent=2, ensure_ascii=False)

    print(f"Generated {output_path} with {len(entries)} novels")
    for entry in entries:
        print(f"  {entry['name']}: {len(entry['files'])} files")


if __name__ == '__main__':
    generate_index()
