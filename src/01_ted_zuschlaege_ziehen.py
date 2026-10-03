# -*- coding: utf-8 -*-
"""Vollstaendiger Zug aller deutschen IT-Zuschlaege aus TED seit 2024.

Liefert den Beleg fuer Aufgabe 1c: Public-Sector-Aktivitaet mit Quelle,
und die Rohdaten fuer die Signale in Aufgabe 2.
Laeuft im Hintergrund, respektiert das Rate Limit.
"""
import json, os, time, urllib.request, urllib.error

API = "https://api.ted.europa.eu/v3/notices/search"
OUT = os.path.expanduser("~/Job finding/ted_zuschlaege.json")

CPV = ["72000000", "72200000", "72300000", "72400000", "72500000",
       "72600000", "72700000", "48000000", "30200000", "51600000"]

FIELDS = ["publication-number", "publication-date", "notice-title",
          "winner-name", "organisation-name-tenderer", "classification-cpv",
          "total-value", "buyer-name", "organisation-city-tenderer",
          "organisation-country-tenderer"]

Q = (f'classification-cpv IN ({" ".join(CPV)}) AND buyer-country IN (DEU) '
     f'AND notice-type IN (can-standard) AND publication-date>=20240101')


def frage(page, versuche=5):
    body = {"query": Q, "fields": FIELDS, "page": page,
            "limit": 100, "scope": "ALL"}
    req = urllib.request.Request(
        API, data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json", "Accept": "application/json"})
    warte = 4
    for a in range(versuche):
        try:
            with urllib.request.urlopen(req, timeout=120) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            if e.code == 429:
                print(f"    429 auf Seite {page}, warte {warte}s", flush=True)
                time.sleep(warte)
                warte = min(warte * 2, 90)
                continue
            print(f"    HTTP {e.code} auf Seite {page}", flush=True)
            return None
        except Exception as ex:
            if a == versuche - 1:
                print(f"    {type(ex).__name__} auf Seite {page}: {ex}", flush=True)
                return None
            time.sleep(warte)
            warte = min(warte * 2, 90)
    return None


alle, seite, gesamt = [], 1, None
while True:
    r = frage(seite)
    if not r:
        print(f"  Abbruch auf Seite {seite}", flush=True)
        break
    if gesamt is None:
        gesamt = r.get("totalNoticeCount")
        print(f"Insgesamt verfuegbar: {gesamt}", flush=True)
    ns = r.get("notices") or []
    alle.extend(ns)
    if seite % 10 == 0 or len(ns) < 100:
        print(f"  Seite {seite:>3}: gesamt {len(alle)}", flush=True)
    if len(ns) < 100:
        break
    seite += 1
    if seite > 200:
        print("  Sicherheitsstopp bei Seite 200", flush=True)
        break
    time.sleep(1.2)

json.dump({"stand": "2026-10-02", "query": Q, "felder": FIELDS,
           "gesamt_verfuegbar": gesamt, "notices": alle},
          open(OUT, "w", encoding="utf-8"), ensure_ascii=False)
print(f"\n{len(alle)} von {gesamt} Bekanntmachungen geschrieben nach {OUT}")
