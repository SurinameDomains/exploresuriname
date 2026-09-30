#!/usr/bin/env python3
"""
List site text that has no Simplified Chinese (zh) translation yet.

The /zh/ tree is hand-translated (not machine-translated): translate_cache.py
only fills nl/es, so new listings, events and page copy stay English on /zh/
until someone adds a "zh" value to translations.json.

Usage:
    python3 zh_pending.py            # writes zh_pending.json (stable page text first)
    python3 zh_pending.py --count    # just print the number

Reads i18n_segments.json (written by build_i18n.py on every full build) and
skips business names, addresses and other proper nouns that stay verbatim.
Live-feed text (news headlines, fixtures) is listed last and can be ignored.
"""
import json, sys
from pathlib import Path

ROOT = Path(__file__).parent
sys.argv = [sys.argv[0]] + [a for a in sys.argv[1:] if a == "--count"]
import build_i18n as B   # noqa: E402  (reuses translatable() / PROTECTED / tr())

segs = json.load(open(ROOT / "i18n_segments.json", encoding="utf-8"))
def _real_text(s):
    """Skip names, codes and dictionary glosses: text NL/ES also left as-is."""
    e = B.cache.get(s) or {}
    if e.get("nl") and e["nl"] != s:
        return True
    return not e and len(s.split()) >= 4

todo = [s for s in segs if B.translatable(s) and B.tr(s, "zh") == s and _real_text(s)]
if "--count" in sys.argv:
    print(len(todo))
else:
    (ROOT / "zh_pending.json").write_text(json.dumps(todo, ensure_ascii=False, indent=0), encoding="utf-8")
    print(f"zh_pending.json: {len(todo)} segments without a zh translation")
