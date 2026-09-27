#!/usr/bin/env python3
"""Decide whether the biz_feeds workflow should commit (exit 0 = commit, 1 = skip).

The feeds job runs every few hours. Committing only because a "checked" time
moved would add ~8 noise commits a day, so a commit happens when:
  * any content changed (titles, links, prices, errors, fail counters), or
  * the stored timestamps are more than 12 hours old (keeps "Last checked"
    on the pages reasonably fresh).
Usage: python scripts/biz_commit_needed.py data/biz_feeds.json data/max_prices.json
"""
import datetime as dt
import json
import subprocess
import sys

TS_KEYS = {"ok", "checked", "updated", "fetched"}
MAX_AGE_H = 12


def strip(o):
    if isinstance(o, dict):
        return {k: strip(v) for k, v in o.items() if k not in TS_KEYS}
    if isinstance(o, list):
        return [strip(x) for x in o]
    return o


def stamps(o, out):
    if isinstance(o, dict):
        for k, v in o.items():
            if k in TS_KEYS and isinstance(v, str) and len(v) >= 16:
                out.append(v)
            else:
                stamps(v, out)
    elif isinstance(o, list):
        for x in o:
            stamps(x, out)
    return out


def main(paths):
    now = dt.datetime.now(dt.timezone.utc)
    for p in paths:
        try:
            new = json.load(open(p, encoding="utf-8"))
        except Exception:
            continue
        r = subprocess.run(["git", "show", f"HEAD:{p}"], capture_output=True, text=True)
        if r.returncode != 0:
            print(f"{p}: new file -> commit")
            return 0
        try:
            old = json.loads(r.stdout)
        except Exception:
            print(f"{p}: committed version unreadable -> commit")
            return 0
        if strip(old) != strip(new):
            print(f"{p}: content changed -> commit")
            return 0
        for s in stamps(old, []):
            try:
                t = dt.datetime.fromisoformat(s)
                if t.tzinfo is None:
                    t = t.replace(tzinfo=dt.timezone(dt.timedelta(hours=-3)))
                if (now - t).total_seconds() > MAX_AGE_H * 3600:
                    print(f"{p}: timestamps older than {MAX_AGE_H}h -> commit")
                    return 0
            except ValueError:
                pass
    print("only timestamps changed -> skip commit")
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
