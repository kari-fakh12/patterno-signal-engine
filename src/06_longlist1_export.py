# -*- coding: utf-8 -*-
"""Longlist 1 als CSV, mit Tier und einer Confidence je Feld. Aufgabe 1c.

Eine Zeile ist eine Firma, an die Patterno verkaufen kann.
Die Tier-Stufen heissen wie der erste Satz des SDR, nicht A bis D:

  1 Anlass   Fit belegt und ein datiertes Ereignis jetzt
  2 Luecke   Fit belegt, kein Ereignis, bietet aber regelmaessig
  3 Still    War aktiv, seit zwoelf Monaten kein Zuschlag, keine Stellenanzeige
  4 Pruefen  Fit belegt, aber die Firmendaten sind unsicher (keine Domain)
  X Raus     Hersteller oder Konzern, beim CPV-Test durchgerutscht

Confidence je Feld, weil der Case es verlangt und weil die Felder sehr
unterschiedlich belegt sind. Zuschlaege sind ein Rechtsakt. Die Domain ist
geraten. Das darf nicht in derselben Spalte landen.
"""
import csv, json, datetime as dt, re, collections

BASE = "/home/asusf/Job finding"
HEUTE = dt.date.today()
STILL_TAGE = 365

from ausschluss import RAUSCHEN, grund as raus_warum  # eine Quelle fuer alle

icp = json.load(open(f"{BASE}/icp_systemhaeuser.json", encoding="utf-8"))["systemhaeuser"]
dom = {d["firma_key"]: d for d in json.load(
    open(f"{BASE}/domains.json", encoding="utf-8"))["domains"]}
ll2 = {a["firma_key"]: a for a in json.load(
    open(f"{BASE}/patterno-signal-engine/data/longlist2_signale.json",
         encoding="utf-8"))["accounts"]}

zeilen, tz = [], collections.Counter()
for f in icp:
    k = f["key"]
    d = dom.get(k) or {}
    sig = ll2.get(k)
    letzter = dt.date.fromisoformat(f["letzter"]) if f.get("letzter") else None
    still = letzter and (HEUTE - letzter).days > STILL_TAGE

    # Nur eine durch das Impressum belegte Domain darf in eine Kampagne.
    # "geraten" heisst: die Seite lebt und der Name steht drauf, aber niemand
    # hat gegengelesen. Genau so sind aura.com und ergo.de entstanden.
    if RAUSCHEN.search(f["name"]):
        tier, warum = "X Raus", raus_warum(f["name"])
    elif d.get("confidence") == "fraglich":
        tier, warum = "4 Pruefen", (
            f"Domain gehoert laut Impressum zu \"{d.get('rechtsname_website')}\"")
    elif d.get("confidence") != "belegt":
        tier, warum = "4 Pruefen", (
            d.get("beleg") or "Domain nicht belegbar, zweite Quelle noetig")
    elif sig:
        tier, warum = "1 Anlass", sig["signale"][0]["signal"]
    elif still:
        tier, warum = "3 Still", f"letzter Zuschlag {f['letzter']}, seitdem nichts"
    else:
        tier, warum = "2 Luecke", "bietet regelmaessig, aktuell kein Ereignis"
    tz[tier] += 1

    q = f.get("quellen") or []
    zeilen.append({
        "Rechtsname": f["name"],
        "Domain": d.get("domain") or "",
        "Ort": f.get("ort") or "",
        "Tier": tier,
        "Tier_Begruendung": warum,
        "Plan_Vorschlag": f.get("plan") or "",
        "Zuschlaege_seit_2024": f["zuschlaege"],
        "Verschiedene_Auftraggeber": f.get("auftraggeber_anzahl"),
        "Auftragsvolumen_EUR": f.get("wert_summe") or "",
        "Erster_Zuschlag": f.get("erster") or "",
        "Letzter_Zuschlag": f.get("letzter") or "",
        "Aktiv_12_Monate": "nein" if still else "ja",
        "CPV_Schwerpunkt": ",".join(f.get("cpv_top") or []),
        "Top_Auftraggeber": " | ".join((f.get("auftraggeber_top") or [])[:3]),
        "Signal_Score": (sig or {}).get("score", ""),
        "Why_now": (sig or {}).get("why_now", ""),
        "Quelle_Beleg": q[0]["url"] if q else "",
        "Quelle_weitere": " ".join(x["url"] for x in q[1:4]),
        # Confidence je Feld
        "C_Rechtsname": "hoch, Freitext aus der Bekanntmachung, normalisiert",
        "Domain_verworfen": d.get("domain_verworfen") or "",
        "Rechtsname_Website": d.get("rechtsname_website") or "",
        "C_Domain": {
            "belegt": "belegt, Rechtsname im Impressum stimmt",
            "geraten": "geraten, kein Impressum zum Gegenlesen, nicht anrufen",
            "fraglich": "fraglich, Impressum nennt eine andere Firma",
            "offen": "offen, nicht belegbar",
        }.get(d.get("confidence", "offen"), d.get("confidence", "")),
        "C_Domain_Beleg": d.get("beleg") or "",
        "C_Zuschlaege": "hoch, gesetzliche Bekanntmachungspflicht, TED",
        "C_Volumen": ("hoch, Wert in der Bekanntmachung" if f.get("wert_summe")
                      else "fehlt, Bekanntmachung nennt keinen Wert"),
        "C_Plan_Vorschlag": "mittel, abgeleitet aus Zuschlagsfrequenz und Preisliste",
        # Beim Gegenlesen aufgefallen: TED nennt manchmal die Niederlassung
        # oder den Projektort, nicht den eingetragenen Sitz. rescuetrack steht
        # als Berlin, sitzt aber in Reutlingen. Also keine "hoch"-Confidence.
        "C_Ort": ("mittel, Ort aus der Bekanntmachung. Das ist nicht immer der "
                  "eingetragene Sitz, manchmal die Niederlassung oder der "
                  "Projektort"),
    })

rang = {"1 Anlass": 0, "2 Luecke": 1, "3 Still": 2, "4 Pruefen": 3, "X Raus": 4}
zeilen.sort(key=lambda z: (rang[z["Tier"]], -(z["Signal_Score"] or 0),
                           -z["Zuschlaege_seit_2024"]))

# Entscheidung von Karim: in die Lieferliste kommt nur, wessen Domain durch
# das Impressum belegt ist. Nicht als Tier 4 mitlaufen lassen, sondern raus.
#
# Die Begruendung ist verkaeuferisch, nicht technisch: Patterno prueft
# stichprobenartig. Eine Liste, in der jede Zeile einen Test uebersteht, ist
# mehr wert als eine laengere mit einem Zweifel-Eimer. Der Preis ist hoch,
# rund 170 Firmen mit belegten TED-Zuschlaegen fallen raus, nur weil ich ihre
# Webseite nicht verifizieren konnte.
#
# Nichts davon wird geloescht. Die Aussortierten landen in einer zweiten
# Datei mit Grund, damit die Methode nachvollziehbar bleibt und die Arbeit
# nicht verloren ist. Diese Datei geht nicht an den Kunden.
liefern = [z for z in zeilen if z["C_Domain"].startswith("belegt")
           and z["Tier"] != "X Raus"]
pruefen = [z for z in zeilen if z not in liefern]

p = f"{BASE}/longlist1_markt.csv"
with open(p, "w", encoding="utf-8-sig", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=list(zeilen[0].keys()), delimiter=";")
    w.writeheader()
    w.writerows(liefern)

p2 = f"{BASE}/pruefen_domain_offen.csv"
with open(p2, "w", encoding="utf-8-sig", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=list(zeilen[0].keys()), delimiter=";")
    w.writeheader()
    w.writerows(pruefen)

tz_l = collections.Counter(z["Tier"] for z in liefern)
print(f"{len(liefern)} Zeilen -> {p}")
print(f"{len(pruefen)} Zeilen -> {p2}  (nicht Teil der Abgabe)\n")

print("Lieferliste, Tier-Verteilung")
for t in ("1 Anlass", "2 Luecke", "3 Still"):
    if tz_l[t]:
        print(f"  {t:<12}{tz_l[t]:>4}  {tz_l[t]/max(len(liefern),1)*100:>5.1f}%  "
              f"{'#' * min(tz_l[t] // 2, 50)}")
print(f"\nAnrufbar heute (Tier 1 und 2): {tz_l['1 Anlass'] + tz_l['2 Luecke']}")
print(f"Davon mit datiertem Anlass:    {tz_l['1 Anlass']}")

print(f"\nAussortiert, nach Grund")
gr = collections.Counter()
for z in pruefen:
    if z["Tier"] == "X Raus":
        gr["X Raus, kein Systemhaus"] += 1
    else:
        gr[z["C_Domain"].split(",")[0]] += 1
for k, v in gr.most_common():
    print(f"  {k:<46}{v:>4}")
print(f"\nVorher insgesamt: {len(zeilen)}. Davon lieferbar: {len(liefern)} "
      f"({len(liefern)/len(zeilen)*100:.0f} %)")
