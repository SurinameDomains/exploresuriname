#!/usr/bin/env python3
"""Rules radar: keeps the Business tools accurate.

Daily (.github/workflows/rules_radar.yml). Watches the OFFICIAL sources behind
data/business_rules.json and opens a GitHub issue (label 'rules-radar') when
something changes. It NEVER edits a rule: a human verifies and updates
business_rules.json, and the CI tests (tests/biz_engine.test.cjs) guard the
result.

Sentinels are configured in data/rules_radar_config.json. State (what was seen,
failure counters, which alerts were already raised) lives in
data/rules_radar_state.json and is committed by the workflow.

Also checks "expected updates": things that SHOULD change on a schedule
(new APF rate each year, holiday coverage, stale 'verified' dates).

Usage:  python scripts/rules_radar.py            (opens issues if GITHUB_TOKEN set)
        python scripts/rules_radar.py --dry-run  (prints alerts only)
"""
import datetime as dt
import hashlib
import html
import json
import os
import re
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
CFG = json.loads((ROOT / "data" / "rules_radar_config.json").read_text(encoding="utf-8"))
RULES = json.loads((ROOT / "data" / "business_rules.json").read_text(encoding="utf-8"))
STATE_PATH = ROOT / "data" / "rules_radar_state.json"
UA = {"User-Agent": "Mozilla/5.0 (ExploreSuriname rules radar; +https://exploresuriname.com)"}
DRY = "--dry-run" in sys.argv or not os.environ.get("GITHUB_TOKEN")
TODAY = dt.datetime.now(dt.timezone(dt.timedelta(hours=-3))).date()

alerts = []   # (key, title, body)


def get(url, timeout=60, tries=3):
    last = None
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return b""
            last = e
        except Exception as e:  # noqa: BLE001
            last = e
        time.sleep(5 * (i + 1))
    raise RuntimeError(str(last))


def page_text(raw):
    t = raw.decode("utf-8", "replace")
    t = re.sub(r"<script.*?</script>|<style.*?</style>", " ", t, flags=re.S | re.I)
    t = re.sub(r"<[^>]+>", " ", t)
    return re.sub(r"\s+", " ", html.unescape(t))


def pdf_text(raw):
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "x.pdf"
        p.write_bytes(raw)
        return subprocess.run(["pdftotext", str(p), "-"], capture_output=True, text=True, check=True).stdout


def rss_items(raw):
    root = ET.fromstring(raw)
    out = []
    for it in root.iter("item"):
        out.append({"title": html.unescape((it.findtext("title") or "").strip()),
                    "link": (it.findtext("link") or "").strip(),
                    "date": (it.findtext("pubDate") or "").strip()})
    return out


def norm_num(s):
    s = s.strip().rstrip(",.")
    if re.fullmatch(r"\d{1,3}(\.\d{3})+", s):
        s = s.replace(".", "")
    return s.replace(",", ".").rstrip("0").rstrip(".") if "," in s or "." in s else s


def alert(key, title, body):
    alerts.append((key, title, body))


def expected_values(s):
    src = s.get("expect_from_rules")
    if src == "apf":
        last = RULES["apf"][-1]
        return [str(last["published_for_year"]), norm_num(str(last["pct_total"]))]
    if src == "minimum_wage":
        return [f'{RULES["minimum_wage_hourly"][-1]["value"]:.2f}'.replace(".", ",")]
    return s.get("expect")


# ── sentinel runners: return (value_for_state, alert_or_None) ────────────────
def run_regex(s, text):
    m = re.search(s["regex"], text, re.I)
    if not m:
        raise RuntimeError("pattern not found on the page (layout changed?)")
    if "expect_text_contains" in s:
        v = m.group(1).strip()
        missing = [x for x in s["expect_text_contains"] if x not in v]
        return v, (f"Found: `{v}`; expected to contain {missing}" if missing else None)
    got = [norm_num(g) for g in m.groups()]
    exp = [norm_num(x) for x in expected_values(s)]
    return got, (None if got == exp else f"Found `{got}`, rules file expects `{exp}`.")


def run(s, state):
    t = s["type"]
    if t == "pdf_regex":
        return run_regex(s, pdf_text(get(s["url"], timeout=120)))
    if t == "html_regex":
        return run_regex(s, page_text(get(s["url"])))
    if t == "html_contains":
        # Facts shown in the guides (addresses, phone numbers, amounts): each must still
        # appear verbatim on the official page. A missing one means the page changed.
        text = page_text(get(s["url"]))
        if len(text) < 300:
            raise RuntimeError("page almost empty (blocked or layout changed?)")
        missing = [x for x in s["must_contain"] if x not in text]
        if not missing:
            return "ok", None
        return missing, ("No longer found verbatim on the official page: " + ", ".join(f"`{m}`" for m in missing)
                         + f".\n\nCheck the page, then update `{s.get('rules_key', '?')}` in data/business_rules.json "
                         "(the guides read it) and the `must_contain` list of this sentinel.")
    if t == "rss_value":
        items = rss_items(get(s["url"]))
        for it in items:  # newest first
            m = re.search(s["regex"], it["title"])
            if m:
                exp = expected_values(s)[0]
                return m.group(1), (None if m.group(1) == exp else
                                    f"Newest item: [{it['title']}]({it['link']}) ({it['date']}). Rules file has SRD {exp}.")
        raise RuntimeError("no item with an amount in the feed")
    if t == "link_list":
        found = []
        for u in s["pages"]:
            raw = get(u)
            for l in re.findall(s["link_regex"], raw.decode("utf-8", "replace")):
                if l not in found:
                    found.append(l)
        if len(found) < s.get("min_links", 1):
            raise RuntimeError(f"only {len(found)} links found (layout changed?)")
        prev = state.get("value")
        if prev is None:
            return found, None                      # first run: baseline, no alert
        new = [l for l in found if l not in prev]
        gone = [l for l in prev if l not in found] if s.get("alert_on_removed") else []
        if not new and not gone:
            return found, None
        pr = re.compile(s["priority_regex"], re.I) if s.get("priority_regex") else None
        def fmt(l):
            url = l if l.startswith("http") else "https://www.dna.sr" + l
            flag = " **(belasting/arbeid/handel)**" if pr and pr.search(l) else ""
            return f"- {url}{flag}"
        body = ""
        if new:
            body += "New:\n" + "\n".join(fmt(l) for l in new) + "\n"
        if gone:
            body += "\nNo longer in this list (moved on, e.g. approved or withdrawn):\n" + "\n".join(fmt(l) for l in gone)
        return found, body
    if t in ("rss_terms", "rss_filtered"):
        urls = ([s["url"].replace("{q}", urllib.parse.quote_plus(q)) for q in s["terms"]]
                if t == "rss_terms" else [s["url"]])
        seen = set(state.get("value") or [])
        first = not seen
        new = []
        rx = re.compile(s["regex"], re.I) if t == "rss_filtered" else None
        for u in urls:
            for it in rss_items(get(u)):
                if not it["link"] or it["link"] in seen:
                    continue
                seen.add(it["link"])
                if rx and not rx.search(it["title"]):
                    continue
                new.append(it)
            time.sleep(2)  # be gentle with gov.sr
        keep = sorted(seen)[-800:]
        if first or not new:
            return keep, None
        return keep, "\n".join(f"- [{i['title']}]({i['link']}) ({i['date'][:16]})" for i in new[:40])
    raise RuntimeError(f"unknown sentinel type {t}")


def expected_update_checks():
    eu = CFG["expected_updates"]
    y = TODAY.year
    if TODAY.isoformat()[5:] >= eu["apf_new_year_by"] and RULES["apf"][-1]["published_for_year"] < y:
        alert(f"apf_year_{y}", f"APF-premie {y} ontbreekt in business_rules.json",
              f"It is {TODAY}. The newest APF rule is for {RULES['apf'][-1]['published_for_year']}. "
              "Check https://www.pensioen.sr/ for the new premium and add an entry to `apf` "
              "(and update `expect` of the apf_rate sentinel). Until then the tools show the latest published rate with its year.")
    # holiday coverage
    hol = json.loads((ROOT / "data" / "holidays.json").read_text(encoding="utf-8"))
    extra = json.loads((ROOT / "data" / "biz_holidays_extra.json").read_text(encoding="utf-8"))
    complete = {str(hol["year"])} | {k for k, v in extra["years"].items() if not v.get("incomplete")}
    horizon = TODAY + dt.timedelta(days=eu["holidays_days_ahead"])
    for yr in sorted({str(TODAY.year), str(horizon.year)}):
        if yr not in complete:
            state = "incomplete" if yr in extra["years"] else "missing"
            alert(f"holidays_{yr}_{TODAY.year}Q{(TODAY.month - 1) // 3 + 1}", f"Feestdagen {yr} {state}",
                  f"Business tools need all public holidays of {yr} (working-day and deadline maths). "
                  f"Add officially announced dates to data/biz_holidays_extra.json (or holidays.json for the events page) "
                  f"and set incomplete=false when the year is complete.")
    # minimum wage age
    mw = RULES["minimum_wage_hourly"][-1]
    age = (TODAY - dt.date.fromisoformat(mw["from"])).days
    if age > eu["minimum_wage_max_age_days"]:
        alert(f"minwage_age_{TODAY:%Y-%m}", "Minimumuurloon al lang ongewijzigd",
              f"The newest minimum wage rule is from {mw['from']} ({age} days). Check gov.sr for a new beschikking.")
    # time-bound texts (e.g. a notice about a coming change): remind on 'review_by'
    for k, v in RULES.items():
        e = v[-1] if isinstance(v, list) and v and isinstance(v[-1], dict) else (v if isinstance(v, dict) else None)
        if e and e.get("review_by") and TODAY.isoformat() >= e["review_by"]:
            alert(f"review_{k}_{e['review_by']}", f"Tekst herzien: {k}",
                  f"`{k}` in data/business_rules.json has review_by {e['review_by']}. Check the official source "
                  f"({e.get('url', '')}) and update the rule and the page text; then move or remove review_by.")
    # stale verified dates
    stale = []
    for k, v in RULES.items():
        e = v[-1] if isinstance(v, list) and v and isinstance(v[-1], dict) else (v if isinstance(v, dict) else None)
        if e and "verified" in e:
            d = dt.date.fromisoformat(e["verified"])
            if (TODAY - d).days > eu["rule_verified_max_age_days"]:
                stale.append(f"- `{k}` last verified {d}")
    if stale:
        alert(f"stale_{TODAY:%Y-%m}", "Regels langer dan 180 dagen niet gecontroleerd",
              "Re-check these against their sources and update `verified`:\n" + "\n".join(stale))


def open_issue(title, body):
    repo = os.environ.get("GITHUB_REPOSITORY", "")
    token = os.environ.get("GITHUB_TOKEN", "")
    data = json.dumps({"title": f"Rules radar: {title}", "body": body + "\n\n_Opened by scripts/rules_radar.py. "
                       "Verify on the official source, update data/business_rules.json (new dated entry + source + verified) "
                       "and the matching `expect` in data/rules_radar_config.json, then close._",
                       "labels": [CFG["issue_label"]]}).encode()
    hdr = {"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json", "User-Agent": UA["User-Agent"]}
    url = f"https://api.github.com/repos/{repo}/issues"
    try:
        with urllib.request.urlopen(urllib.request.Request(url, data=data, headers=hdr), timeout=30) as r:
            print("issue created:", json.load(r).get("html_url"))
    except urllib.error.HTTPError as e:
        if e.code != 422:
            raise
        # 422: usually the label does not exist and could not be created. Open it without the label.
        d = json.loads(data)
        d.pop("labels", None)
        with urllib.request.urlopen(urllib.request.Request(url, data=json.dumps(d).encode(), headers=hdr), timeout=30) as r:
            print("issue created (without label):", json.load(r).get("html_url"))


def main():
    try:
        state = json.loads(STATE_PATH.read_text(encoding="utf-8"))
    except Exception:
        state = {}
    sent = state.setdefault("_alerted", {})
    for s in CFG["sentinels"]:
        st = state.setdefault(s["id"], {})
        try:
            value, problem = run(s, st)
            st.update(value=value, ok=TODAY.isoformat(), fails=0)
            st.pop("fail_alerted", None)
            if problem:
                h = hashlib.sha1(json.dumps([s["id"], problem], sort_keys=True).encode()).hexdigest()[:12]
                alert(f"{s['id']}_{h}", s["title"], f"Source: {s.get('url') or ', '.join(s.get('pages', []))}\n\n{problem}")
            print(f"ok   {s['id']}")
        except Exception as e:  # noqa: BLE001
            st["fails"] = int(st.get("fails", 0)) + 1
            st["error"] = str(e)[:300]
            print(f"FAIL {s['id']}: {e}")
            if st["fails"] >= CFG["fail_alert_after"] and not st.get("fail_alerted"):
                st["fail_alerted"] = TODAY.isoformat()
                alert(f"{s['id']}_down_{TODAY}", f"Sentinel '{s['id']}' kan bron niet lezen",
                      f"Failed {st['fails']} runs in a row: `{st['error']}`\nSource: {s.get('url') or s.get('pages')}\n"
                      "The source may have moved or changed layout. Fix the sentinel in data/rules_radar_config.json. "
                      "A silent sentinel is treated as a failure, not as 'no changes'.")
    expected_update_checks()

    for key, title, body in alerts:
        if key in sent:
            continue
        print(f"\nALERT {title}\n{body}\n")
        if DRY:
            continue            # dry run: never mark as sent, so the real run still opens it
        try:
            open_issue(title, body)
        except Exception as e:  # noqa: BLE001
            print("could not open issue:", e)
            continue
        sent[key] = TODAY.isoformat()
    # forget old alert keys after a year
    cutoff = (TODAY - dt.timedelta(days=366)).isoformat()
    state["_alerted"] = {k: v for k, v in sent.items() if v >= cutoff}
    state["_last_run"] = TODAY.isoformat()
    if DRY:
        print("dry-run: state file NOT written (a real run must still see every change)")
    else:
        STATE_PATH.write_text(json.dumps(state, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\n{len(alerts)} alert(s) this run ({'dry-run' if DRY else 'issues enabled'})")


if __name__ == "__main__":
    main()
