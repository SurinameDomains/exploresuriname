#!/usr/bin/env python3
"""
scrape_wachtdienst.py
Scrapes RGD Suriname wachtdienst page -> data/wachtdienst.json
Source: http://www.rgd.sr/nl/zorg-aanbod/wachtdienst
"""

import json, re, sys, urllib.request
from datetime import datetime, timezone
from pathlib import Path

URL = "http://www.rgd.sr/nl/zorg-aanbod/wachtdienst"
OUT = Path(__file__).parent.parent / "data" / "wachtdienst.json"
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; ExploreSuriname/1.0)"}


def fetch_html(url):
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=20) as r:
        raw = r.read()
    for enc in ("utf-8", "latin-1", "iso-8859-1"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="replace")


def clean(t):
    return re.sub(r"\s+", " ", str(t)).strip()


def parse(html):
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(html, "html.parser")
    full = soup.get_text(separator="\n")
    lines = [clean(l) for l in full.splitlines() if clean(l)]

    result = {
        "date_range": None,
        "pharmacies": [],
        "doctors": [],
        "hours": "Open op zaterdag en zon-/feestdagen van 09:00-10:00 en 17:00-18:00",
        "last_updated": datetime.now(timezone.utc).isoformat(),
        "source": URL,
    }

    # ── Date range ────────────────────────────────────────────────────────────
    for line in lines:
        m = re.search(r"Datum\s*[:]\s*(.+)", line, re.IGNORECASE)
        if m:
            result["date_range"] = clean(m.group(1))
            break

    # ── Hours ─────────────────────────────────────────────────────────────────
    for line in lines:
        if re.search(r"wachtapotheken zijn", line, re.IGNORECASE) and re.search(r"\d{2}:\d{2}", line):
            result["hours"] = line
            break

    # ── Pharmacies ────────────────────────────────────────────────────────────
    # Pattern: "Apotheek Name" line immediately followed by "Adres: X; Telefoon: Y" line
    # (as seen in the actual page: lines 36-39)
    for i, line in enumerate(lines):
        if re.match(r"apotheek\s+\w+", line, re.IGNORECASE) and len(line) > 10:
            # Look ahead for the Adres line (should be very next non-empty line)
            for j in range(i + 1, min(i + 4, len(lines))):
                addr_line = lines[j]
                if re.match(r"Adres\s*[:]\s*", addr_line, re.IGNORECASE):
                    # Parse: "Adres: X; Telefoon: Y"
                    addr_m = re.match(r"Adres\s*[:]\s*([^;]+?)(?:\s*;\s*Telefoon\s*[:]\s*(.+))?$", addr_line, re.IGNORECASE)
                    if addr_m:
                        address = clean(addr_m.group(1))
                        phone_raw = clean(addr_m.group(2) or "")
                        # Take first number before "/" or ","
                        phone = re.split(r"[/,]", phone_raw)[0].strip() if phone_raw else ""
                        result["pharmacies"].append({
                            "name":    line,
                            "address": address,
                            "phone":   phone,
                        })
                    break

    # Deduplicate by name
    seen, unique = set(), []
    for p in result["pharmacies"]:
        if p["name"] not in seen:
            seen.add(p["name"])
            unique.append(p)
    result["pharmacies"] = unique

    # ── Doctors (names only for now) ──────────────────────────────────────────
    for bold in soup.find_all(["strong", "b"]):
        t = clean(bold.get_text())
        if re.match(r"Drs?\.\s+\w+\s+\w+", t, re.IGNORECASE):
            result["doctors"].append({"name": t})

    return result


def main():
    print(f"Fetching {URL}")
    try:
        html = fetch_html(URL)
    except Exception as e:
        print(f"ERROR fetching: {e}")
        if OUT.exists():
            print("Keeping existing data.")
        sys.exit(0)

    data = parse(html)
    print(f"  Pharmacies: {len(data['pharmacies'])}")
    for p in data["pharmacies"]:
        print(f"    - {p['name']} | {p['address']} | {p['phone']}")
    print(f"  Doctors:    {len(data['doctors'])}")
    print(f"  Date range: {data['date_range']}")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"  Written: {OUT}")


if __name__ == "__main__":
    main()
