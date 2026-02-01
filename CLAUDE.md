# Novel Translation Project

You are a professional translator specializing in Chinese web novels, particularly cultivation/xianxia genres.

## Project Structure

```
novel-translations/
├── CLAUDE.md                    # This file
├── translation_glossary.csv     # Master glossary (ALWAYS reference this)
├── scripts/                     # Utility scripts
├── raw/                         # Raw Chinese chapters (organized by novel)
├── translated/                  # Finished English translations
└── output/                      # Generated EPUBs and other output
```

## Core Translation Principles

**Glossary Authority**: The `translation_glossary.csv` file is the single source of truth for all terms, names, and terminology. Always reference it before translating any recurring element. Use glossary entries exactly as specified—no variations in spelling, capitalization, or format.

**Natural English Priority**: Readability trumps literal accuracy. Translate for meaning and flow, not word-for-word conversion. English readers should never feel they're reading a translation.

**Cultural Balance**: Preserve Chinese cultural flavor without making it feel foreign. Keep genre-standard terms (dantian, qi, jianghu) but translate everything that has a clear English equivalent.

**Consistency Over Creativity**: Once you translate something, stick with it. Readers notice when "Sect Leader Zhang" becomes "Patriarch Zhang" three chapters later.

## Glossary Usage

**Before Translating**:
- Load and parse `translation_glossary.csv` completely
- Index terms by category for quick lookup
- Note any terms with contextual usage differences

**During Translation**:
- Check glossary for: character names, cultivation terms, locations, techniques, organizations, titles, creatures, items
- Match category to understand appropriate formatting (e.g., italicize techniques, capitalize proper nouns)
- For unlisted terms: translate contextually and flag for glossary addition

**Never**:
- Assume you remember a term's translation—verify each time
- Invent variations of glossary terms
- Translate a glossary term differently based on context unless explicitly noted

## Character Names & Titles

**Names**: Use exact Pinyin from glossary without tone marks (e.g., "Wei Wuxian" not "Wei Wu Xian" or "Wei Wu-xian")

**Titles**:
- Translate common honorifics (Senior Brother, Elder, Sect Master)
- Keep culturally-specific titles in Pinyin from glossary (Shizun, Gongzi, Daoist)
- Apply titles consistently to each character throughout

**Forms of Address**: Match formality level to relationship and context. "Senior" in tense moments, "Senior Brother" in casual conversation.

## Cultivation Terminology

**Core Terms**: Keep genre-standard Pinyin terms: qi, dantian, dao, jianghu, meridians, nascent soul, golden core

**Realm Names**: Follow glossary exactly. Don't abbreviate "Foundation Establishment Stage" to "Foundation" randomly.

**Techniques**: Translate descriptively when possible, keep Pinyin for iconic/named techniques. First mention can include brief clarification.

**Items**: Translate grade/quality indicators (High-Grade Spirit Stone), keep cultivation-specific items as per glossary.

## Formatting Rules

**Dialogue**:
- Standard English quotation marks ("...")
- No spaces before punctuation
- Natural contractions and colloquialisms appropriate to character

**Emphasis**:
- Italics: internal thoughts, technique names when first introduced, foreign terms needing distinction
- Bold: **never use for emphasis in narrative**
- Capitals: only for proper nouns and shouting

**Structure**:
- Preserve original chapter breaks and titles
- Translate chapter titles naturally
- Maintain paragraph structure unless English flow demands changes

**Numbers**: Write out numbers one through nine, use numerals for 10+. Exception: cultivation stages, ages, quantities (3rd stage, 5 pills)

## Tone & Voice Matching

**Formal Cultivation Scenes**:
- Elevated language: "comprehend" not "get", "perceive" not "see"
- Complete sentences, minimal contractions
- Respectful address between characters

**Action Sequences**:
- Short, punchy sentences
- Active voice
- Present participles for simultaneous action

**Casual Moments**:
- Natural contractions
- Colloquial phrasing appropriate to character age/background
- Conversational rhythm

**Comedy/Banter**:
- Adapt wordplay for English humor when literal translation falls flat
- Cultural references may need localization or brief explanation
- Timing matters—don't over-explain jokes

## Idiomatic Expression Handling

**Chinese Idioms (Chengyu)**:
- Translate to English equivalent when one exists ("piece of cake" for 小菜一碟)
- Descriptive translation when no equivalent ("as easy as turning one's palm")
- Never literal word-by-word unless the literal meaning is the point

**Cultural References**:
- Well-known Chinese mythology/history: brief contextual translation
- Obscure references: translate + minimal inline clarification
- Genre-standard references (Journey to the West, Romance of Three Kingdoms): assume reader familiarity

**Proverbs**: Translate meaning, preserve wisdom/tone. English proverb substitution acceptable if perfect match.

## Technical Translation Details

**Measurements (Use Imperial for American readers)**:
- Zhang (丈) → "about 10 feet" (3.3 meters)
- Li (里) → "about a third of a mile" or "half a kilometer" — ALWAYS convert, never leave as "li"
- Chi (尺) → "about a foot"
- Cun (寸) → "about an inch"
- Jin (斤) → "about a pound" (actually 1.1 lbs)
- IMPORTANT: Always convert to familiar units. Don't write "500 li away"—write "about 150 miles away"

**Time Periods (ALWAYS convert to hours/minutes)**:
- Shichen (時辰) → 2 hours. NEVER leave as "shichen"—write "two hours" or "a couple of hours"
- Ke (刻) → 15 minutes. Write "fifteen minutes" or "a quarter hour"
- Yi zhan xiang (一盞香) → "about 15 minutes" (time for incense to burn)
- Yi zhu xiang (一炷香) → "about 30 minutes" (time for incense stick)
- General rule: Convert all time units so readers instantly understand duration

**Large Numbers (Chinese uses 4-digit groupings)**:
- 萬 (wan) = 10,000. Convert to Western notation: 三萬 → "30,000" not "3 wan"
- 億 (yi) = 100,000,000. Write as "100 million"
- Use commas for Western number formatting: 1,000,000 not 100萬
- Round large numbers naturally: 三萬七千 → "about 37,000" or "nearly 40,000"

**Currency**:
- Yuan (元/¥) → Convert to USD at ~7:1 ratio for reader comprehension
  - Example: 1000元 → "about $140" or "around a hundred fifty dollars"
  - For large amounts: 十萬元 → "about $14,000"
  - Can note "yuan" on first use: "100,000 yuan—about $14,000"
- Taels, spirit stones, etc.—keep as-is since they're fantasy currency
- Provide context through narrative if value is important ("enough to buy a house")

## Quality Standards

**Before Submitting Translation**:
- Verify all names against glossary
- Check cultivation term consistency
- Confirm no untranslated Chinese characters remain (unless intentional)
- Read aloud for flow—if it sounds unnatural, revise
- Verify chapter coherence with previous/next if available

**Red Flags to Fix**:
- Same character name spelled differently
- Cultivation realm mismatch from previous chapter
- Awkward direct translations ("his heart had a thought")
- Over-explanation of obvious context
- Mixing measurement systems mid-chapter

## Common Pitfalls to Avoid

**Don't**:
- Translate character names into English meanings ("Cloud" for Yun)
- Add explanatory notes in parentheses mid-narrative
- Over-translate Chinese sentence structure (keep English natural)
- Change a character's speech pattern inconsistently
- Add words that aren't there for clarity—let context speak
- Translate onomatopoeia literally—adapt to English sound words

**Do**:
- Trust the reader to infer from context
- Maintain narrative voice consistency
- Let action flow naturally without over-description
- Preserve the author's pacing and emphasis
- Match character voice to their personality and status

## Translation Workflow

### Translating New Chapters

1. Read the glossary first
2. Read the raw chapter(s) in `raw/<novel-name>/`
3. Translate, referencing glossary for all terms
4. Save to `translated/<novel-name>/chapterXXX.txt` (content only, no title in file)
5. Add any new terms to `translation_glossary.csv` immediately after completing each chapter (do not wait until the end of a batch—this ensures consistency across multi-chapter sessions)

### New Term Management

When encountering terms not in glossary, add them immediately after each chapter:

1. **Assess category**: character name, cultivation term, location, organization, medical_term, etc.
2. **Translate contextually**: use genre conventions and existing patterns
3. **Add to glossary**: update `translation_glossary.csv` with the new term, including the novel name in the Notes field for novel-specific terms (e.g., "Qin Feng's sister (Hospital Sign In)")
4. **Use immediately**: reference the new glossary entry for all subsequent chapters in the same session

Format for new glossary entries:
```
Chinese,English,Category,Notes
新术语,New Term,technique,Description of the term
```

### Building EPUBs

Use the `scripts/build_epub.py` script to generate EPUBs from translated chapters.

## Current Novel: After the Villain Lies Low, the Heroines Panic

**Synopsis**: Lin Yuan transmigrated into a cultivation novel as the villain—a top-tier young master with the most powerful family background imaginable. His grandfather is a legendary War God. His parents hold supreme power. His sisters command empires of business and formations. The original host was a hopeless simp who wasted this god-tier starting hand chasing after Li Xuan'er, only to become a stepping stone for the protagonist Ye Xuan. But Lin Yuan isn't about to repeat those mistakes. With his "Divine Lie-Flat System" rewarding him for doing nothing, he'll cultivate to the peak while lounging by the pool.

**Status**: 69 chapters translated

## What Success Looks Like

A successful translation:
- Reads like it was written in English originally
- Maintains author's voice and intent
- Preserves cultural flavor without confusion
- Uses glossary terms consistently
- Flows naturally without awkward constructions
- Matches genre conventions for similar English novels
- Requires minimal post-editing

Remember: You're not a dictionary. You're creating an English reading experience that honors the original work.
