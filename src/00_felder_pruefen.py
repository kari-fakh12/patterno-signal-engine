# -*- coding: utf-8 -*-
"""Probe 4: echte Abfrage, und welches Feld traegt den Zuschlagsempfaenger?"""
import json, urllib.request, urllib.error

API = "https://api.ted.europa.eu/v3/notices/search"
Q = ('classification-cpv IN (72000000) AND buyer-country IN (DEU) '
     'AND notice-type IN (can-standard) AND publication-date>=20250101')


def hol(fields, label, limit=2, zeige=False):
    body = {"query": Q, "fields": fields, "page": 1, "limit": limit, "scope": "ALL"}
    req = urllib.request.Request(
        API, data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json", "Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            d = json.load(r)
        print(f"=== {label}: OK total={d.get('totalNoticeCount')}")
        if zeige:
            for n in (d.get("notices") or [])[:limit]:
                print(json.dumps(n, ensure_ascii=False, indent=1)[:3000])
                print("-" * 40)
        return d
    except urllib.error.HTTPError as e:
        msg = e.read().decode("utf-8", "replace")
        try:
            print(f"=== {label}: {e.code} :: {json.loads(msg).get('message')}")
        except Exception:
            print(f"=== {label}: {e.code} :: {msg[:260]}")
    return None


hol(["publication-number"], "Basis: wie viele deutsche IT-Zuschlaege seit 2025")

for f in ["winner-name", "organisation-name-tenderer", "tenderer-name",
          "winner", "organisation-name", "contractor-name",
          "organisation-name-serv-prov", "notice-title", "buyer-name",
          "contract-duration", "total-value", "publication-date"]:
    hol(["publication-number", f], f"Feld {f}")

print("\n\n### Volle Notice mit den funktionierenden Feldern ###")
hol(["publication-number", "publication-date", "notice-title", "buyer-name",
     "organisation-name", "total-value", "classification-cpv"],
    "VOLL", limit=2, zeige=True)
