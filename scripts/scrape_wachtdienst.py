#!/usr/bin/env python3
"""
scrape_wachtdienst.py
Scrapes RGD Suriname wachtdienst page -> data/wachtdienst.json
Source: http://www.rgd.sr/nl/zorg-aanbod/wachtdienst

Page structure:
  WACHTDIENST REGELING VOOR HUISARTSEN
  Datum: <date range>
  <District>                          ← standalone line (Paramaribo, Wanica, Para, ...)
  Drs. Name; Clinic
  Adres: <addr>; Telefoon: <phone>
  ...
  Wachtapotheken
  Apotheek Name
  Adres: <addr>; Telefoon: <phone>
  ...
  De wachtapotheken zijn ... open van ...
"""

import json, re, sys, urllib.request
from datetime import datetime, timezone
from pathlib import Path

URL = "http://www.rgd.sr/nl/zorg-aanbod/wachtdienst"
OUT = Path(__file__).parent.parent / "data" / "wachtdienst.json"
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; ExploreSuriname/1.0)"}

# Known district names (case-insensitive match against standalone lines)
DISTRICTS = {"paramaribo", "wanica", "para", "commewijne", "saramacca", "nickerie",
             "marowijne", "brokopondo", "sipaliwini", "coronie"}


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


def _split_adres(addr_line):
    """Parse 'Adres: X; Telefoon: Y' → (address, phone)."""
    m = re.match(r"Adres\s*[:]\s*([^;]+?)(?:\s*;\s*Telefoon\s*[:]\s*(.+))?$",
                 addr_line, re.IGNORECASE)
    if m:
        address = clean(m.group(1))
        phone_raw = clean(m.group(2) or "")
        # Take first number before "/" or ","
        phone = re.split(r"[/,]", phone_raw)[0].strip() if phone_raw else ""
        return address, phone
    return addr_line, ""


def parse(html):
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(html, "html.parser")
    full = soup.get_text(separator="\n")
    lines = [clean(l) for l in full.splitlines() if clean(l)]

    result = {
        "date_range":  None,
        "doctors":     [],   # [{"name", "clinic", "district", "address", "phone", "note"}]
        "pharmacies":  [],   # [{"name", "address", "phone"}]
        "doctor_hours":  "Spreekuren: zaterdag en zondag van 09:00 u-10:00 u en van 17:00 u-18:00 u",
        "pharmacy_hours": "Open op zaterdag en zon-/feestdagen van 09:00-10:00 en 17:00-18:00",
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
        if re.search(r"wachtapotheken\s+zijn", line, re.IGNORECASE) and re.search(r"\d{2}:\d{2}", line):
            result["pharmacy_hours"] = line
            break
    for line in lines:
        if re.search(r"spreekuren", line, re.IGNORECASE) and re.search(r"\d{2}:\d{2}", line):
            result["doctor_hours"] = line
            break

    # ── Parse doctors and pharmacies ──────────────────────────────────────────
    in_pharmacies = False
    current_district = "Paramaribo"  # default if page doesn't start with a district

    i = 0
    while i < len(lines):
        line = lines[i]

        # Detect "Wachtapotheken" section start
        if re.match(r"wachtapotheken$", line, re.IGNORECASE):
            in_pharmacies = True
            i += 1
            continue

        if not in_pharmacies:
            # Check if this line is a district header (standalone district name)
            if line.lower() in DISTRICTS and len(line) < 30:
                current_district = line
                i += 1
                continue

            # Check if this is a doctor line: "Drs. Name; Clinic"
            if re.match(r"Drs?\.\s+\w+", line, re.IGNORECASE):
                # Split name and clinic on ";"
                parts = line.split(";", 1)
                name = clean(parts[0])
                clinic = clean(parts[1]) if len(parts) > 1 else ""
                # Extract parenthetical note from clinic (e.g. "(Alleen zaterdag & zondag ochtend)")
                note = ""
                note_m = re.search(r"\(([^)]+)\)", clinic)
                if note_m:
                    note = note_m.group(1).strip()
                    clinic = clinic[:note_m.start()].strip()

                address, phone = "", ""
                # Check next line for Adres
                if i + 1 < len(lines) and re.match(r"Adres\s*[:]\s*", lines[i + 1], re.IGNORECASE):
                    address, phone = _split_adres(lines[i + 1])
                    i += 1  # consume adres line

                result["doctors"].append({
                    "name":     name,
                    "clinic":   clinic,
                    "district": current_district,
                    "address":  address,
                    "phone":    phone,
                    "note":     note,
                })
                i += 1
                continue

        else:
            # In pharmacy section
            if re.match(r"apotheek\s+\w+", line, re.IGNORECASE) and len(line) > 8:
                name = line
                address, phone = "", ""
                if i + 1 < len(lines) and re.match(r"Adres\s*[:]\s*", lines[i + 1], re.IGNORECASE):
                    address, phone = _split_adres(lines[i + 1])
                    i += 1
                result["pharmacies"].append({
                    "name":    name,
                    "address": address,
                    "phone":   phone,
                })
                i += 1
                continue

        i += 1

    # Deduplicate doctors by name
    seen, unique = set(), []
    for d in result["doctors"]:
        if d["name"] not in seen:
            seen.add(d["name"])
            unique.append(d)
    result["doctors"] = unique

    # Deduplicate pharmacies by name
    seen, unique = set(), []
    for p in result["pharmacies"]:
        if p["name"] not in seen:
            seen.add(p["name"])
            unique.append(p)
    result["pharmacies"] = unique

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
    print(f"  Date range: {data['date_range']}")
    print(f"  Doctors:    {len(data['doctors'])}")
    for d in data["doctors"]:
        print(f"    [{d['district']}] {d['name']} | {d['clinic']} | {d['phone']}")
    print(f"  Pharmacies: {len(data['pharmacies'])}")
    for p in data["pharmacies"]:
        print(f"    {p['name']} | {p['address']} | {p['phone']}")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"  Written: {OUT}")


if __name__ == "__main__":
    main()
