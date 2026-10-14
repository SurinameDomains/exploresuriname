#!/usr/bin/env python3
"""Site heartbeat (Phase 1 of the homepage freshness programme, 14 Oct 2026).

Reads https://exploresuriname.com/data/home_live.json and checks how old the
last build is. The site is supposed to rebuild every ~15 minutes; a stalled
pipeline would otherwise go unnoticed while the rail, rates and events quietly
age. When the build is older than STALE_MIN (or the file cannot be read) one
GitHub issue labeled "site-stale" is opened (or the open one gets a comment);
when the build is healthy again the open issue is closed with a note. Also
reports which live items are not ok, so a dead scraper shows up in the issue.

Runs from .github/workflows/heartbeat.yml. Needs GITHUB_TOKEN with issues:write.
Exit code is always 0 unless the GitHub API itself fails: the check must not
look like a broken workflow when the SITE is the thing that is broken.
"""
import json, os, sys, urllib.request, urllib.error
from datetime import datetime, timezone

URL        = "https://exploresuriname.com/data/home_live.json"
STALE_MIN  = int(os.environ.get("HEARTBEAT_STALE_MIN", "90"))
LABEL      = "site-stale"
TITLE      = "Site build stale: exploresuriname.com is not rebuilding"
UA         = {"User-Agent": "ExploreSuriname-heartbeat/1.0"}


def fetch_live():
    req = urllib.request.Request(URL + "?hb=" + str(int(datetime.now().timestamp())), headers=UA)
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def gh(method, path, payload=None):
    repo = os.environ.get("GITHUB_REPOSITORY", "")
    token = os.environ.get("GITHUB_TOKEN", "")
    if not (repo and token):
        sys.exit("GITHUB_REPOSITORY / GITHUB_TOKEN not set")
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(f"https://api.github.com/repos/{repo}{path}", data=data, method=method,
                                 headers={"Authorization": f"Bearer {token}",
                                          "Accept": "application/vnd.github+json", **UA})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r) if r.status != 204 else None


def open_issue_for_label():
    items = gh("GET", f"/issues?state=open&labels={LABEL}&per_page=5")
    return items[0] if items else None


def main():
    now = datetime.now(timezone.utc)
    problem, detail = None, ""
    try:
        live = fetch_live()
        built = datetime.fromtimestamp(int(live["built_epoch"]), timezone.utc)
        age_min = (now - built).total_seconds() / 60
        bad = [k for k, v in (live.get("items") or {}).items() if not v.get("ok")]
        print(f"last build: {live.get('built')} ({age_min:.0f} min ago); items not ok: {bad or 'none'}")
        if age_min > STALE_MIN:
            problem = f"The last build finished at `{live.get('built')}` SR, **{age_min:.0f} minutes ago** (limit {STALE_MIN})."
        detail = (f"Live items not ok at check time: `{', '.join(bad)}`." if bad else "All live items ok at check time.")
    except Exception as e:
        problem = f"`{URL}` could not be read: `{e}`."
        print("fetch failed:", e)

    existing = open_issue_for_label()
    stamp = now.strftime("%Y-%m-%d %H:%M UTC")
    if problem:
        body = (f"{problem}\n\n{detail}\n\nWhat to check: the GitHub Actions 'Update Site' runs "
                f"(are they being triggered, did the last one fail?), then the external trigger that "
                f"dispatches them. This issue closes itself once a fresh build is seen.\n\n_Heartbeat {stamp}_")
        if existing:
            gh("POST", f"/issues/{existing['number']}/comments", {"body": f"Still stale at {stamp}. {problem}"})
            print("commented on open issue", existing["html_url"])
        else:
            r = gh("POST", "/issues", {"title": TITLE, "body": body, "labels": [LABEL]})
            print("issue opened:", r.get("html_url"))
    elif existing:
        gh("POST", f"/issues/{existing['number']}/comments",
           {"body": f"Fresh build seen at {stamp}. {detail} Closing."})
        gh("PATCH", f"/issues/{existing['number']}", {"state": "closed"})
        print("closed", existing["html_url"])
    else:
        print("healthy")


if __name__ == "__main__":
    main()
