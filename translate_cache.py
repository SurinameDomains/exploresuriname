#!/usr/bin/env python3
"""
Fill translations.json for ExploreSuriname using the keyless Google translate
endpoint (no API key, no card, no signup). Threaded, resumable, incremental.

Re-run any time: it skips segments already cached (incl. hand translations) and
saves progress continuously, so it's safe to stop/restart. build_i18n.py reads
only the committed translations.json and falls back to English for anything
missing, so the site never depends on this at serve time.

Usage:
    python3 translate_cache.py                 # nl + es, all pending
    python3 translate_cache.py --langs nl      # one language
    python3 translate_cache.py --limit 800     # cap NEW translations this run
    python3 translate_cache.py --workers 6     # concurrency (default 6)
"""
import json, sys, time, threading, urllib.parse, urllib.request
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

ROOT     = Path(__file__).parent
SEGMENTS = ROOT / "i18n_segments.json" if (ROOT / "i18n_segments.json").exists() else ROOT / "translation_segments.json"
CACHE    = Path("/tmp/translations.work.json")   # authoritative (atomic local fs)
REPO     = ROOT / "translations.json"            # mirror on clean exit
TARGETS  = ["nl", "es"]
ENDPOINT = "https://translate.googleapis.com/translate_a/single"
MAXURL   = 1500          # split source longer than this on sentence boundaries

def arg(name, default=None):
    return sys.argv[sys.argv.index(name) + 1] if name in sys.argv else default
if arg("--langs"):   TARGETS = arg("--langs").split(",")
LIMIT   = int(arg("--limit"))   if arg("--limit")   else None
WORKERS = int(arg("--workers")) if arg("--workers") else 6

segments = json.load(open(SEGMENTS, encoding="utf-8"))
cache    = json.load(open(CACHE, encoding="utf-8")) if CACHE.exists() else (json.load(open(REPO, encoding="utf-8")) if REPO.exists() else {})
lock     = threading.Lock()

def split_long(text):
    if len(text) <= MAXURL: return [text]
    out, cur = [], ""
    for part in text.replace(". ", ".|").replace("! ", "!|").replace("? ", "?|").split("|"):
        if len(cur) + len(part) + 1 > MAXURL and cur:
            out.append(cur); cur = part
        else:
            cur = (cur + " " + part).strip()
    if cur: out.append(cur)
    return out

def g_translate(text, lang, retries=4):
    parts = []
    for chunk in split_long(text):
        q = urllib.parse.urlencode({"client": "gtx", "sl": "en", "tl": lang, "dt": "t", "q": chunk})
        url = ENDPOINT + "?" + q
        for attempt in range(retries):
            try:
                req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
                d = json.loads(urllib.request.urlopen(req, timeout=20).read().decode("utf-8"))
                parts.append("".join(seg[0] for seg in d[0] if seg[0]))
                break
            except Exception as e:
                code = getattr(e, "code", None)
                if attempt == retries - 1:
                    raise
                time.sleep((2 ** attempt) * (1.5 if code == 429 else 0.5))
    return " ".join(parts)

# build worklist of (segment, lang) pairs still missing
work = []
for seg in segments:
    e = cache.get(seg) or {}
    for lang in TARGETS:
        if not e.get(lang):
            work.append((seg, lang))
if LIMIT:
    work = work[:LIMIT]

print(f"translate_cache(google): {len(segments)} segs | {len(work)} pending pairs | workers={WORKERS}")
done = 0; errors = 0; stop = False

def task(pair):
    seg, lang = pair
    return seg, lang, g_translate(seg, lang)

def save():
    import os as _os
    with lock:
        tmp = str(CACHE) + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            f.write(json.dumps(cache, ensure_ascii=False, indent=0))
        _os.replace(tmp, CACHE)

with ThreadPoolExecutor(max_workers=WORKERS) as ex:
    futs = {ex.submit(task, p): p for p in work}
    for fut in as_completed(futs):
        seg, lang = futs[fut]
        try:
            s, l, txt = fut.result()
            with lock:
                cache.setdefault(s, {})[l] = txt
                done += 1
            if done % 50 == 0:
                save(); print(f"  ...{done}/{len(work)}")
        except Exception as e:
            errors += 1
            if errors <= 5: print(f"  !! {lang} err: {str(e)[:70]}")

save()
import shutil as _sh
_sh.copyfile(CACHE, REPO)   # clean mirror to repo only after run completes
remaining = sum(1 for s in segments for l in TARGETS if not (cache.get(s) or {}).get(l))
print(f"translate_cache: +{done} this run | errors={errors} | remaining={remaining} | cache={len(cache)} keys")
