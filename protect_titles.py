#!/usr/bin/env python3
"""Re-translate listing <title>/meta segments with the business NAME shielded
from translation (sentinel token), so names stay verbatim in tab titles + search
snippets. Resumable; writes to the /tmp work cache then mirrors to repo."""
import json, sys, time, urllib.parse, urllib.request, threading
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

ROOT=Path(__file__).parent
WORK=Path("/tmp/translations.work.json"); REPO=ROOT/"translations.json"
ENDPOINT="https://translate.googleapis.com/translate_a/single"
SENT="ZQXNAMEXQZ"          # survives MT untouched
names=sorted({(b.get("name") or "").strip() for b in json.load(open(ROOT/"exploresuriname_listings.json",encoding="utf-8")) if (b.get("name") or "").strip()}, key=len, reverse=True)
cache=json.load(open(WORK,encoding="utf-8")) if WORK.exists() else json.load(open(REPO,encoding="utf-8"))
LIMIT=int(sys.argv[sys.argv.index("--limit")+1]) if "--limit" in sys.argv else None
lock=threading.Lock()

def g(text,lang,retries=4):
    q=urllib.parse.urlencode({"client":"gtx","sl":"en","tl":lang,"dt":"t","q":text})
    for a in range(retries):
        try:
            req=urllib.request.Request(ENDPOINT+"?"+q,headers={"User-Agent":"Mozilla/5.0"})
            d=json.loads(urllib.request.urlopen(req,timeout=20).read().decode("utf-8"))
            return "".join(s[0] for s in d[0] if s[0])
        except Exception:
            if a==retries-1: raise
            time.sleep(0.5*(2**a))

def find_name(key):
    for n in names:
        if n and n in key and (key.startswith(n) or f" {n} " in key or f"{n} in " in key or f"{n}," in key):
            return n
    return None

# build worklist: title/meta keys that embed a business name
work=[]
for k in cache:
    if "ExploreSuriname" in k or " in " in k or "," in k:
        n=find_name(k)
        bad_brand = any(x in (cache[k].get("nl","")+cache[k].get("es","")) for x in ["ExploreSurinam","Explore Surinam","Verken Suriname","ExplorarSurinam"])
        if n and (n not in (cache[k].get("nl","")) or n not in (cache[k].get("es","")) or bad_brand):
            work.append((k,n))
if LIMIT: work=work[:LIMIT]
print(f"protect_titles: {len(work)} name-bearing segments to repair")

BRAND_BAD=["Verken Suriname","Ontdek Suriname","ExplorarSurinam","Explorar Surinam","ExplorarSuriname","Explora Surinam","Explora Suriname"]
def repair(item):
    k,n=item; out={}
    shielded=k.replace(n,SENT).replace("ExploreSuriname","ZQXBRANDXQZ")
    for lang in ("nl","es"):
        t=g(shielded,lang)
        t=t.replace(SENT,n).replace("ZQXNAMEXQZ",n).replace("ZQXBRANDXQZ","ExploreSuriname")
        for b in BRAND_BAD: t=t.replace(b,"ExploreSuriname")
        out[lang]=t
    return k,out

done=0
def save():
    with lock:
        tmp=str(WORK)+".tmp2"
        open(tmp,"w",encoding="utf-8").write(json.dumps(cache,ensure_ascii=False,indent=0))
        import os; os.replace(tmp,WORK)

with ThreadPoolExecutor(max_workers=14) as ex:
    futs={ex.submit(repair,it):it for it in work}
    for f in as_completed(futs):
        try:
            k,out=f.result()
            with lock: cache[k].update(out); done+=1
            if done%50==0: save(); print(f"  ...{done}/{len(work)}")
        except Exception as e:
            print("  !!",str(e)[:60])
save()
import shutil; shutil.copyfile(WORK,REPO)
left=sum(1 for k,n in [(k,find_name(k)) for k in cache if 'ExploreSuriname' in k or ' in ' in k or ',' in k] if n and (n not in cache[k].get('nl','') or n not in cache[k].get('es','')))
print(f"protect_titles: repaired +{done} | name-missing remaining≈{left} | keys={len(cache)}")
