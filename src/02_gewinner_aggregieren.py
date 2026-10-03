# -*- coding: utf-8 -*-
"""Aus 13.066 Bekanntmachungen die Firmen bauen, die tatsaechlich gewonnen haben.

Pro Firma: Anzahl Zuschlaege, CPV-Schwerpunkt, Auftraggeber, erster und letzter
Zuschlag, Summe der Auftragswerte, Belegt-URLs. Das ist Aufgabe 1c.
"""
import json, os, re, collections

SRC = os.path.expanduser("~/Job finding/ted_zuschlaege.json")
OUT = os.path.expanduser("~/Job finding/ted_firmen.json")

d = json.load(open(SRC, encoding="utf-8"))
notices = d["notices"]
print(f"{len(notices)} Bekanntmachungen geladen\n")

RECHTSFORM = re.compile(
    r"(?i)\s*\b(gmbh\s*&\s*co\.?\s*kgaa|gmbh\s*&\s*co\.?\s*og|gmbh\s*&\s*co\.?\s*kg|"
    r"gmbh\s*&\s*co\.?\s*ohg|ag\s*&\s*co\.?\s*kg|ag\s*&\s*co\.?\s*ohg|"
    r"se\s*&\s*co\.?\s*kgaa|gmbh|mbh|\bag\b|\bse\b|\bkg\b|\bohg\b|\bug\b|"
    r"\bkgaa\b|\be\.?\s?v\.?\b|\be\.?\s?g\.?\b|\bgbr\b|\bpartg\b|"
    r"\bs\.?r\.?l\.?\b|\bb\.?v\.?\b|\bltd\.?\b|\binc\.?\b|\bs\.?a\.?\b)\b\.?")


def norm(name):
    s = (name or "").strip()
    s = re.sub(r"\s+", " ", s)
    s = RECHTSFORM.sub(" ", s)
    s = re.sub(r"(?i)\b(deutschland|germany|holding|group|gruppe|international)\b",
               " ", s)
    s = re.sub(r"[^a-z0-9äöüß ]+", " ", s.lower())
    s = re.sub(r"\s+", " ", s).strip()
    return s


def namen_aus(feld):
    """winner-name und organisation-name-tenderer kommen als {'deu': [...]}."""
    if not feld:
        return []
    if isinstance(feld, dict):
        out = []
        for v in feld.values():
            if isinstance(v, list):
                out.extend(str(x) for x in v if x)
            elif v:
                out.append(str(v))
        return out
    if isinstance(feld, list):
        return [str(x) for x in feld if x]
    return [str(feld)]


def ersten(feld):
    v = namen_aus(feld)
    return v[0] if v else ""


firmen = collections.defaultdict(lambda: {
    "namen": collections.Counter(), "zuschlaege": 0, "cpv": collections.Counter(),
    "auftraggeber": collections.Counter(), "daten": [], "werte": [],
    "orte": collections.Counter(), "quellen": [],
})

ohne_gewinner = 0
for n in notices:
    gewinner = namen_aus(n.get("winner-name")) + namen_aus(n.get("organisation-name-tenderer"))
    # Innerhalb einer Bekanntmachung kann dieselbe Firma mehrere Lose gewinnen.
    gewinner = list(dict.fromkeys(g.strip() for g in gewinner if g and g.strip()))
    if not gewinner:
        ohne_gewinner += 1
        continue
    datum = (n.get("publication-date") or "")[:10]
    pub = n.get("publication-number") or ""
    url = f"https://ted.europa.eu/de/notice/{pub}/pdf" if pub else ""
    ag = ersten(n.get("buyer-name"))
    cpvs = n.get("classification-cpv") or []
    wert = n.get("total-value")
    ort = ersten(n.get("organisation-city-tenderer"))
    for g in gewinner:
        k = norm(g)
        if not k or len(k) < 3:
            continue
        f = firmen[k]
        f["namen"][g.strip()] += 1
        f["zuschlaege"] += 1
        for c in cpvs:
            f["cpv"][str(c)[:3]] += 1
        if ag:
            f["auftraggeber"][ag[:70]] += 1
        if datum:
            f["daten"].append(datum)
        if ort:
            f["orte"][ort] += 1
        if isinstance(wert, (int, float)):
            f["werte"].append(float(wert))
        if url and len(f["quellen"]) < 5:
            f["quellen"].append({"datum": datum, "url": url, "auftraggeber": ag[:70]})

zeilen = []
for k, f in firmen.items():
    daten = sorted(f["daten"])
    zeilen.append({
        "key": k,
        "name": f["namen"].most_common(1)[0][0],
        "namensvarianten": [n for n, _ in f["namen"].most_common(4)],
        "zuschlaege": f["zuschlaege"],
        "erster": daten[0] if daten else "",
        "letzter": daten[-1] if daten else "",
        "cpv_top": [c for c, _ in f["cpv"].most_common(4)],
        "auftraggeber_anzahl": len(f["auftraggeber"]),
        "auftraggeber_top": [a for a, _ in f["auftraggeber"].most_common(3)],
        "ort": f["orte"].most_common(1)[0][0] if f["orte"] else "",
        "wert_summe": round(sum(f["werte"])) if f["werte"] else None,
        "quellen": f["quellen"],
    })

zeilen.sort(key=lambda r: -r["zuschlaege"])
json.dump({"firmen": zeilen}, open(OUT, "w", encoding="utf-8"), ensure_ascii=False)

mehrfach = [r for r in zeilen if r["zuschlaege"] >= 2]
drei = [r for r in zeilen if r["zuschlaege"] >= 3]
print(f"{len(zeilen)} Firmen mit mindestens einem Zuschlag")
print(f"{len(mehrfach)} mit 2 oder mehr, {len(drei)} mit 3 oder mehr")
print(f"{ohne_gewinner} Bekanntmachungen ohne auslesbaren Gewinner\n")
print("Top 40 nach Anzahl Zuschlaege:\n")
for r in zeilen[:40]:
    w = f"{r['wert_summe']:>13,}" if r["wert_summe"] else "            ."
    print(f"  {r['zuschlaege']:>3}x  {r['name'][:44]:<46}{r['ort'][:14]:<16}"
          f"{w}  CPV {','.join(r['cpv_top'][:3])}  bis {r['letzter']}")
print(f"\ngeschrieben: {OUT}")
