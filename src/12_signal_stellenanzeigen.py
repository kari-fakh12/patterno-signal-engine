# -*- coding: utf-8 -*-
"""Kaufsignale fuer Patterno: wer gerade Vergabe- oder Angebotsmanagement einstellt.

Patterno verkauft Software an Firmen, die sich auf oeffentliche Ausschreibungen BEWERBEN.
Wer gerade eine Stelle fuer Vergabe- oder Angebotsmanagement ausschreibt, hat gerade
entschieden, dass das Thema eine eigene Person wert ist. Genau dann lohnt das Gespraech.

DER ENTSCHEIDENDE FILTER: oeffentliche Auftraggeber stellen dieselben Rollen ein, sitzen
aber auf der KAUFENDEN Seite. Eine Stadt, die einen Vergabemanager sucht, schreibt
Auftraege aus, sie bewirbt sich nicht darauf. Die muessen raus, sonst sieht die Liste
gut aus und ist falsch.

Quelle: Bundesagentur fuer Arbeit, API v6, oeffentlich und kostenlos.
Keine Gedankenstriche.
"""
import json, os, re, time, datetime, urllib.parse, urllib.request
from collections import defaultdict

API = "https://rest.arbeitsagentur.de/jobboerse/jobsuche-service/pc/v6/jobs"
HDR = {"X-API-Key": "jobboerse-jobsuche", "Accept": "application/json"}
OUT = os.path.expanduser("~/Job finding/patterno_signals.json")
TODAY = datetime.date(2026, 9, 30)
DAYS = 100

TERMS = [
    ("Vergabemanagement", "vergabe", 10),
    ("Ausschreibungsmanagement", "ausschreibung", 10),
    ("Angebotsmanagement", "angebot", 9),
    ("Bid Manager", "bid", 10),
    ("Referent Vergabe", "vergabe", 9),
    ("Vergabereferent", "vergabe", 9),
    ("Submissionsbearbeitung", "submission", 8),
    ("Tender Management", "bid", 9),
    ("Kalkulator Ausschreibung", "kalkulation", 7),
    ("Bearbeitung Ausschreibungen", "ausschreibung", 8),
]

TITEL_OK = re.compile(r"(?i)(vergabe|ausschreibung|angebotsmanagement|bid[ -]?manager|"
                      r"submission|tender|angebotsbearbeit|angebotsingenieur|bietermanagement)")
TITEL_RAUS = re.compile(r"(?i)(praktik|werkstudent|ausbildung|minijob|aushilfe|"
                        r"duales studium|trainee|sch[uü]ler)")

# Personaldienstleister: die Anzeige gehoert dem Kunden.
PERSONAL = re.compile(r"(?i)(personaldienstleist|personalservice|personalvermittl|"
                      r"personalberat|zeitarbeit|arbeitnehmer|staffing|recruit|headhunt|"
                      r"randstad|adecco|hays|manpower|orizon|piening|tempton|gulp|brunel|"
                      r"ferchau|amadeus fire|robert half|expertum|\bdis ag\b|univativ|bestwork|"
                      r"rasant|humancapital|human capital|leasing|interim|\bpersonal\b)")

# DER WICHTIGSTE FILTER: oeffentliche Auftraggeber. Die schreiben AUS, sie bieten nicht.
AUFTRAGGEBER = re.compile(
    r"(?i)(^stadt |^stadtverwaltung|^gemeinde|^landkreis|^kreis |^bezirk|"
    r"^land |^landes|^bundes|ministerium|beh[oö]rde|^amt |landratsamt|"
    r"universit[aä]t|hochschule|^der b[uü]rgermeister|regierungspr[aä]sidium|"
    r"zweckverband|^bundesagentur|^deutsche rentenversicherung|krankenkasse|"
    r"^senat|magistrat|kommunal|eigenbetrieb|anstalt des [oö]ffentlichen|"
    r"polizei|klinikum|krankenhaus|^gesundheit |bundeswehr|^bw |bekleidungsmanagement|"
    r"klimaschutzagentur|energieagentur|^agentur f[uü]r|stadtwerke|verkehrsbetrieb|"
    r"^deutsche bahn|^bundesanstalt|^bundesamt|justizvollzug|feuerwehr)")


def fetch(term, page):
    q = urllib.parse.urlencode({"was": term, "size": 100, "page": page,
                                "veroeffentlichtseit": DAYS, "angebotsart": 1})
    req = urllib.request.Request(f"{API}?{q}", headers=HDR)
    for a in range(3):
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.load(r)
        except Exception as e:
            if a == 2:
                print(f"    ! {term} S.{page}: {e}", flush=True)
                return {}
            time.sleep(4 * (a + 1))
    return {}


def norm(name):
    s = re.sub(r"(?i)\b(gmbh|ag|se|kg|mbh|co|ohg|ug|e\.?\s?v\.?|e\.?\s?g\.?|"
               r"holding|deutschland|germany|group|gruppe)\b", " ", name or "")
    return re.sub(r"[^a-z0-9]+", "", s.lower())[:36]


def tage(a):
    d = (a.get("datumErsteVeroeffentlichung") or "")[:10]
    try:
        return (TODAY - datetime.date.fromisoformat(d)).days
    except Exception:
        return None


firmen = defaultdict(lambda: {"name": "", "ads": [], "kat": set(), "orte": set()})
gesehen = set()
raus = {"auftraggeber": 0, "personal": 0}

for term, kat, gewicht in TERMS:
    neu = 0
    for page in range(1, 5):
        d = fetch(term, page)
        ads = d.get("ergebnisliste") or []
        if not ads:
            break
        for a in ads:
            ref, firma = a.get("referenznummer"), (a.get("firma") or "").strip()
            titel = (a.get("stellenangebotsTitel") or "").strip()
            if (not ref or not firma or ref in gesehen
                    or not TITEL_OK.search(titel) or TITEL_RAUS.search(titel)):
                continue
            gesehen.add(ref)
            if AUFTRAGGEBER.search(firma):
                raus["auftraggeber"] += 1
                continue
            if PERSONAL.search(firma):
                raus["personal"] += 1
                continue
            adr = ((a.get("stellenlokationen") or [{}])[0].get("adresse") or {})
            ort = adr.get("ort") or ""
            key = a.get("arbeitgeberKundennummerHash") or norm(firma)
            if not key:
                continue
            f = firmen[key]
            f["name"] = f["name"] or firma
            f["kat"].add(kat)
            if ort:
                f["orte"].add(ort)
            f["ads"].append({
                "titel": titel, "kat": kat, "gewicht": gewicht, "ort": ort,
                "erste": (a.get("datumErsteVeroeffentlichung") or "")[:10],
                "tage_offen": tage(a),
                "url": "https://www.arbeitsagentur.de/jobsuche/jobdetail/"
                       + urllib.parse.quote(ref, safe=""),
            })
            neu += 1
        if len(ads) < 100:
            break
        time.sleep(0.4)
    print(f"  {term:<28} +{neu:>3}   Firmen bisher {len(firmen)}", flush=True)
    time.sleep(0.6)

zeilen = []
for key, f in firmen.items():
    ads = f["ads"]
    if len(ads) > 6:
        continue
    if max((a["tage_offen"] or 0) for a in ads) > 365:   # Dauerausschreibung, kein Signal
        continue
    score = max(a["gewicht"] for a in ads)
    signale = []
    aelteste = max((a["tage_offen"] or 0) for a in ads)
    neueste = min((a["tage_offen"] or 999) for a in ads)
    if aelteste >= 45:
        score += 6
        signale.append(f"seit {aelteste} Tagen unbesetzt")
    elif aelteste >= 21:
        score += 3
        signale.append(f"seit {aelteste} Tagen offen")
    if neueste <= 14:
        score += 4
        signale.append(f"vor {neueste} Tagen ausgeschrieben")
    if len(ads) > 1:
        score += 4
        signale.append(f"{len(ads)} Stellen im Vergabeumfeld")
    if "vergabe" in f["kat"] or "ausschreibung" in f["kat"]:
        score += 3
        signale.append("Vergabe oder Ausschreibung im Titel")
    if "bid" in f["kat"]:
        signale.append("Bid Management, oft international")
    zeilen.append({
        "firma": f["name"], "score": score, "orte": sorted(f["orte"])[:2],
        "rollen": sorted({a["titel"] for a in ads})[:3],
        "signale": signale, "aelteste_tage": aelteste, "neueste_tage": neueste,
        "quelle": max(ads, key=lambda x: x["tage_offen"] or 0)["url"],
        "anzahl": len(ads),
    })

zeilen.sort(key=lambda r: (-r["score"], -r["aelteste_tage"]))
json.dump({"stand": str(TODAY), "zeitraum_tage": DAYS, "anzeigen": len(gesehen),
           "raus": raus, "firmen": zeilen}, open(OUT, "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)

frisch = sum(1 for r in zeilen if r["neueste_tage"] <= 14)
lang = sum(1 for r in zeilen if r["aelteste_tage"] >= 45)
print(f"\n{len(zeilen)} Firmen aus {len(gesehen)} Anzeigen. "
      f"{frisch} in den letzten 14 Tagen, {lang} seit 45+ Tagen offen", flush=True)
print(f"entfernt: {raus['auftraggeber']} oeffentliche Auftraggeber, "
      f"{raus['personal']} Personaldienstleister", flush=True)
print("\nTop 30:", flush=True)
for r in zeilen[:30]:
    print(f"  {r['score']:>3}  {r['firma'][:40]:<42}{(r['orte'] or [''])[0][:16]:<18}"
          f"{r['aelteste_tage']:>4}T  {r['rollen'][0][:44]}", flush=True)
print(f"\ngeschrieben: {OUT}", flush=True)

