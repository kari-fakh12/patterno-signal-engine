# -*- coding: utf-8 -*-
"""Signal-Engine fuer Patterno. Aufgabe 2b: ein Signal end-to-end, mit State.

Drei Signale, alle aus TED, alle mit Datum und Quelle:

  S2  Vertrag laeuft aus   Die Firma hat einen Auftrag gewonnen, dessen
                           Laufzeit in den naechsten Monaten endet. Die
                           Neuausschreibung kommt, und sie muessen den
                           Vertrag verteidigen. Feld: contract-duration-end-date-lot
  S4  Passende Ausschreibung ist offen
                           Ein Auftraggeber, fuer den sie schon gearbeitet
                           haben, schreibt gerade neu aus. Oder: eine
                           Ausschreibung im gleichen CPV im gleichen Bundesland.
  S1  Stellenanzeige       Kommt aus patterno_signals.json, wird nur
                           dazugelegt, damit der Score mehrere Quellen sieht.

State: signal_state.json merkt jedes schon ausgegebene (Firma, Signal, Bekanntmachung).
Der zweite Lauf gibt nur Neues aus. Kein Dedup per Hand, kein doppelter Anruf.

Lauf:  python3 signal_engine.py            normaler Lauf
       python3 signal_engine.py --reset    State loeschen
       python3 signal_engine.py --cache    gespeicherte TED-Antworten nutzen
"""
import json, os, re, sys, time, datetime as dt, collections
import urllib.request, urllib.error
from ausschluss import ausgeschlossen

BASE = "/home/asusf/Job finding"
P_ICP = f"{BASE}/icp_systemhaeuser.json"
P_DOM = f"{BASE}/domains.json"
P_JOBS = f"{BASE}/patterno_signals.json"
P_STATE = f"{BASE}/signal_state.json"
P_OUT = f"{BASE}/longlist2_signale.json"
P_CSV = f"{BASE}/longlist2_signale.csv"
P_HIST = f"{BASE}/firma_auftraggeber.json"
P_CACHE_CAN = f"{BASE}/cache_can_laufzeit.json"
P_CACHE_CN = f"{BASE}/cache_cn_offen.json"

API = "https://api.ted.europa.eu/v3/notices/search"
CPV = ("72000000", "48000000", "30200000", "51600000")
HEUTE = dt.date.today()

# Fenster
VORLAUF_TAGE = 180      # Vertragsende bis so weit in die Zukunft ist relevant
NACHLAUF_TAGE = 60      # gerade abgelaufen zaehlt auch, Neuausschreibung laeuft dann
AUSSCHREIBUNG_TAGE = 56  # "Signal aus 4 bis 8 Wochen", wie der Case es verlangt

# ---------------------------------------------------------------- TED

def ted(query, felder, limit=250, seiten_max=400, cache=None, nutze_cache=False):
    if nutze_cache and cache and os.path.exists(cache):
        print(f"  Cache: {os.path.basename(cache)}")
        return json.load(open(cache, encoding="utf-8"))
    alle, seite = [], 1
    while seite <= seiten_max:
        body = {"query": query, "fields": felder, "limit": limit,
                "page": seite, "scope": "ALL"}
        req = urllib.request.Request(
            API, data=json.dumps(body).encode(),
            headers={"Content-Type": "application/json",
                     "Accept": "application/json"})
        d = None
        for versuch in range(6):
            try:
                with urllib.request.urlopen(req, timeout=90) as r:
                    d = json.loads(r.read().decode())
                break
            except urllib.error.HTTPError as e:
                if e.code == 429:
                    w = min(90, 5 * 2 ** versuch)
                    print(f"    429, warte {w}s", flush=True)
                    time.sleep(w)
                    continue
                raise SystemExit(f"TED {e.code}: {e.read().decode()[:300]}")
            except Exception as e:
                time.sleep(4)
        if d is None:
            raise SystemExit("TED antwortet nicht")
        n = d.get("notices") or []
        alle += n
        gesamt = d.get("totalNoticeCount", 0)
        if seite == 1:
            print(f"  {gesamt} Bekanntmachungen, {-(-gesamt // limit)} Seiten",
                  flush=True)
        if len(alle) >= gesamt or not n:
            break
        seite += 1
        if seite % 10 == 0:
            print(f"    Seite {seite}, {len(alle)} geladen", flush=True)
        time.sleep(1.1)
    if cache:
        json.dump(alle, open(cache, "w", encoding="utf-8"), ensure_ascii=False)
    return alle


# ---------------------------------------------------------------- Namen

RF = re.compile(
    r"(?i)\s*\b(gmbh\s*&\s*co\.?\s*kgaa|gmbh\s*&\s*co\.?\s*kg|gmbh\s*&\s*co\.?\s*ohg|"
    r"ag\s*&\s*co\.?\s*kg|se\s*&\s*co\.?\s*kgaa|gmbh|mbh|\bag\b|\bse\b|\bkg\b|"
    r"\bohg\b|\bug\b|\bkgaa\b|\be\.?\s?v\.?\b|\bgbr\b)\b\.?")


def norm(name):
    s = re.sub(r"\s+", " ", (name or "").strip())
    s = RF.sub(" ", s)
    s = re.sub(r"(?i)\b(deutschland|germany|holding|group|gruppe|international)\b",
               " ", s)
    s = re.sub(r"[^a-z0-9äöüß ]+", " ", s.lower())
    return re.sub(r"\s+", " ", s).strip()


def namen_aus(feld):
    """TED liefert Namen als {"deu": [...]} oder als Liste oder als String."""
    if not feld:
        return []
    if isinstance(feld, str):
        return [feld]
    if isinstance(feld, list):
        out = []
        for x in feld:
            out += namen_aus(x)
        return out
    if isinstance(feld, dict):
        out = []
        for v in feld.values():
            out += namen_aus(v)
        return out
    return []


def datum(s):
    if not s:
        return None
    if isinstance(s, list):
        s = s[0] if s else None
    if not isinstance(s, str) or len(s) < 10:
        return None
    try:
        return dt.date.fromisoformat(s[:10])
    except ValueError:
        return None


SCHLUSSWORT = re.compile(
    r"(?i)[\s,;:\-–(]*\b(inklusive|inkl|einschl|einschliesslich|sowie|"
    r"und|oder|fuer|für|der|die|das|den|dem|des|von|vom|mit|im|in|am|"
    r"zur|zum|bei|auf|an|als|aus|nach|ueber|über|je|pro|ca|bzw|"
    r"vergab|vergabe|los|lot|teil|anstalt|standort)\s*[.,;:\-–(]*$")


def kuerzen(s, n):
    """Auf n Zeichen kuerzen, aber an der Wortgrenze.

    Vorher wurde hart nach Zeichen geschnitten. Ergebnis waren Saetze wie
    "Landesamt fuer Zentrale Polizeiliche Dienste Nordrhein-Westfa" und
    "von zwei KI-Serve". Das liest ein SDR laut vor.
    """
    s = re.sub(r"\s+", " ", (s or "")).strip()
    s = re.sub(r"\(m/w/d\)|\(m/w\)|\(w/m/d\)|\(m/./.\)", "", s).strip(" ,;-")
    if len(s) <= n:
        return s
    schnitt = s[:n]
    if " " in schnitt:
        schnitt = schnitt[:schnitt.rfind(" ")]
    # Haengende Bindewoerter und offene Klammern wegnehmen
    for _ in range(3):
        neu = SCHLUSSWORT.sub("", schnitt).strip(" ,;:-–(")
        if neu == schnitt:
            break
        schnitt = neu
    if schnitt.count("(") > schnitt.count(")"):
        schnitt = schnitt[:schnitt.rfind("(")].strip(" ,;:-")
    return schnitt.strip() + "..."


def bundesland(ort):
    """Grob, nur fuer den schwachen Regionstreffer. Bewusst nicht vollstaendig."""
    o = (ort or "").lower()
    BL = {
        "NRW": "köln|koeln|düsseldorf|duesseldorf|dortmund|essen|duisburg|bochum|wuppertal|bielefeld|bonn|münster|muenster|aachen|gelsenkirchen|mönchengladbach|krefeld|oberhausen|hagen|hamm|siegen|paderborn|neuss|leverkusen|solingen|herne|witten|iserlohn|gescher|eschweiler|brilon|lippstadt|erwitte|gummersbach|hattingen|wiehl|meerbusch|langenfeld|kerpen|bottrop|recklinghausen|horstmar|bönen|arnsberg|detmold|minden|gütersloh|guetersloh|unna|soest|coesfeld|borken|kleve|wesel|viersen|heinsberg|düren|dueren|euskirchen|olpe|höxter|hoexter|warendorf|steinfurt|lippe",
        "Bayern": "münchen|muenchen|nürnberg|nuernberg|augsburg|würzburg|wuerzburg|regensburg|ingolstadt|erlangen|fürth|fuerth|bamberg|bayreuth|baiersdorf|jettingen|grasbrunn|ottobrunn|winhöring|kirchheim|garching|ismaning|rosenheim|deggendorf|landshut|aschaffenburg|kempten|passau|schweinfurt|coburg|hof|ansbach|amberg|weiden|straubing",
        "BW": "stuttgart|karlsruhe|mannheim|freiburg|heidelberg|heilbronn|ulm|pforzheim|reutlingen|esslingen|ludwigsburg|tübingen|tuebingen|konstanz|metzingen|eislingen|möglingen|leinfelden|kenzingen|bensheim|süßen|glatten|ostfildern|leonberg|backnang|hemmingen|wolpertshausen|ladenburg|aalen|schwäbisch|offenburg|villingen|rastatt|baden-baden|sindelfingen|böblingen|goeppingen|göppingen",
        "Berlin": "berlin",
        "Hamburg": "hamburg|reinbek",
        "Hessen": "frankfurt|wiesbaden|kassel|darmstadt|offenbach|hanau|gießen|giessen|marburg|dietzenbach|dreieich|eschborn|langen|bad homburg|wölfersheim|leuterod|fulda|rüsselsheim|wetzlar|limburg",
        "Niedersachsen": "hannover|braunschweig|osnabrück|osnabrueck|oldenburg|göttingen|goettingen|wolfsburg|hildesheim|springe|lohne|achim|wolfenbüttel|barleben|celle|lüneburg|lueneburg|emden|delmenhorst|salzgitter|goslar|cuxhaven",
        "Sachsen": "dresden|leipzig|chemnitz|zwickau|görlitz|goerlitz|plauen|freiberg|bautzen|röhrsdorf",
        "Bremen": "bremen|bremerhaven",
        "RLP": "mainz|ludwigshafen|koblenz|trier|kaiserslautern|züsch|zuesch|frankenthal|viernheim|worms|neuwied|speyer|pirmasens|bad kreuznach",
        "SH": "kiel|lübeck|luebeck|flensburg|neumünster|neumuenster|norderstedt|elmshorn|pinneberg|itzehoe",
        "Brandenburg": "potsdam|cottbus|schönefeld|schoenefeld|brandenburg an der|frankfurt \\(oder\\)|oranienburg|falkensee|eberswalde",
        "Sachsen-Anhalt": "magdeburg|halle|dessau|stendal|wittenberg|halberstadt|bernburg",
        "Thüringen": "erfurt|jena|gera|nordhausen|weimar|gotha|suhl|eisenach",
        "MV": "rostock|schwerin|stralsund|bad doberan|greifswald|neubrandenburg|wismar",
        "Saarland": "saarbrücken|saarbruecken|bexbach|neunkirchen|homburg",
    }
    for k, p in BL.items():
        if re.search(p, o):
            return k
    return None


# ---------------------------------------------------------------- Firmenindex

def lade_firmen():
    s = json.load(open(P_ICP, encoding="utf-8"))["systemhaeuser"]
    idx = {}
    for f in s:
        for n in [f["name"]] + (f.get("namensvarianten") or []):
            k = norm(n)
            if k and len(k) > 3:
                idx.setdefault(k, f)
    dom = {}
    if os.path.exists(P_DOM):
        for d in json.load(open(P_DOM, encoding="utf-8"))["domains"]:
            dom[d["firma_key"]] = d
    return s, idx, dom


def treffer(feld_namen, idx):
    for n in namen_aus(feld_namen):
        f = idx.get(norm(n))
        if f:
            return f
    return None


# ---------------------------------------------------------------- Signale

def signal_vertragsende(idx, nutze_cache):
    """S2: gewonnener Auftrag, dessen Laufzeit bald endet."""
    print("\nS2  Vertrag laeuft aus")
    q = ("notice-type IN (can-standard) AND buyer-country IN (DEU) "
         "AND publication-date >= 20240101 "
         "AND classification-cpv IN (" + " ".join(CPV) + ")")
    felder = ["publication-number", "publication-date", "winner-name",
              "organisation-name-tenderer", "contract-duration-end-date-lot",
              "contract-duration-start-date-lot", "framework-agreement-lot",
              "title-lot", "buyer-name", "classification-cpv",
              "estimated-value-lot"]
    n = ted(q, felder, cache=P_CACHE_CAN, nutze_cache=nutze_cache)
    print(f"  {len(n)} geladen")

    raus, ohne_ende, kein_fit = [], 0, 0
    for x in n:
        ende = datum(x.get("contract-duration-end-date-lot"))
        if not ende:
            ohne_ende += 1
            continue
        f = (treffer(x.get("winner-name"), idx)
             or treffer(x.get("organisation-name-tenderer"), idx))
        if not f:
            kein_fit += 1
            continue
        tage = (ende - HEUTE).days
        if not (-NACHLAUF_TAGE <= tage <= VORLAUF_TAGE):
            continue
        rahmen = any(v and v != "none" for v in
                     (x.get("framework-agreement-lot") or []))
        if tage < 0:
            score, lage = 70, f"Vertrag endete vor {abs(tage)} Tagen"
        elif tage <= 90:
            score, lage = (90 if rahmen else 80), f"Vertrag endet in {tage} Tagen"
        else:
            score, lage = 60, f"Vertrag endet in {tage} Tagen"
        titel = (namen_aus(x.get("title-lot")) or [""])[0]
        ag = (namen_aus(x.get("buyer-name")) or [""])[0]
        # Zeitform nach dem Datum richten. "endet am 15.09." ist falsch,
        # wenn der 15.09. vorbei ist, und der Kunde merkt es sofort.
        endet = "endet am" if tage >= 0 else "endete am"
        raus.append({
            "firma_key": f["key"], "firma": f["name"], "signal": "S2 Vertragsende",
            "signal_datum": ende.isoformat(), "score": score,
            "rahmenvertrag": rahmen,
            "beleg": f"{lage}. Auftraggeber {kuerzen(ag, 70)}. {kuerzen(titel, 90)}",
            "quelle": f"https://ted.europa.eu/de/notice/{x['publication-number']}/pdf",
            "bekanntmachung": x["publication-number"],
            "why_now": (f"Ihr Vertrag mit {kuerzen(ag, 60)} "
                        f"({kuerzen(titel, 60)}) {endet} "
                        f"{ende.strftime('%d.%m.%Y')}."
                        + (" Rahmenvertrag, die Neuausschreibung kommt."
                           if rahmen else " Die Neuausschreibung steht an.")),
        })
    print(f"  ohne Vertragsende: {ohne_ende}, kein ICP-Treffer: {kein_fit}")
    print(f"  Signal S2: {len(raus)} Treffer")
    return raus


def signal_offene_ausschreibung(firmen, idx, nutze_cache):
    """S4: offene Ausschreibung bei einem Auftraggeber, den sie schon kennen."""
    print("\nS4  Passende Ausschreibung ist offen")
    seit = (HEUTE - dt.timedelta(days=AUSSCHREIBUNG_TAGE)).strftime("%Y%m%d")
    q = ("notice-type IN (cn-standard) AND buyer-country IN (DEU) "
         f"AND publication-date >= {seit} "
         "AND classification-cpv IN (" + " ".join(CPV) + ")")
    felder = ["publication-number", "publication-date", "buyer-name",
              "organisation-city-buyer", "classification-cpv", "title-lot",
              "deadline-receipt-tender-date-lot", "estimated-value-lot"]
    n = ted(q, felder, cache=P_CACHE_CN, nutze_cache=nutze_cache)
    print(f"  {len(n)} offene Ausschreibungen der letzten {AUSSCHREIBUNG_TAGE} Tage")

    # Auftraggeber-Index je Firma. Jetzt mit Beleg: welcher Auftraggeber,
    # wann, und welche Bekanntmachung. Ohne den Beleg kann der Satz
    # "dort habt ihr schon geliefert" nicht geprueft werden, und ein Satz,
    # den niemand pruefen kann, gehoert nicht in eine Kampagne.
    ag_idx = collections.defaultdict(dict)      # norm(ag) -> {key: beleg}
    cpv_idx = collections.defaultdict(set)
    bl_idx = {}

    # Volle Historie, erzeugt von firma_auftraggeber.py. Vorher kam das aus
    # der Stichprobe in icp_systemhaeuser.json, also 5 Bekanntmachungen und
    # 3 Top-Auftraggeber je Firma. Damit blieben zwei Drittel der Beziehungen
    # ohne Beleg, und ein Satz ohne Beleg ist eine Behauptung.
    if os.path.exists(P_HIST):
        hist = json.load(open(P_HIST, encoding="utf-8"))
        for key, belege in hist.items():
            for b in belege:
                ag_idx[norm(b["auftraggeber"])].setdefault(key, b)
        print(f"  Historie: {sum(len(v) for v in hist.values())} "
              f"Firma-Auftraggeber-Paare mit Beleg")
    else:
        print("  WARNUNG: firma_auftraggeber.json fehlt, nutze nur die Stichprobe")
        for f in firmen:
            for q_ in f.get("quellen") or []:
                a = q_.get("auftraggeber")
                if a:
                    ag_idx[norm(a)].setdefault(f["key"], {
                        "auftraggeber": a, "datum": q_.get("datum"),
                        "rolle": "gewinner", "mit_auftraggebern": 1,
                        "quelle": q_.get("url")})
            for a in f.get("auftraggeber_top") or []:
                ag_idx[norm(a)].setdefault(f["key"], {
                    "auftraggeber": a, "datum": None, "rolle": "gewinner",
                    "mit_auftraggebern": 1, "quelle": None})

    for f in firmen:
        for c in f.get("cpv_top") or []:
            cpv_idx[c].add(f["key"])
        bl_idx[f["key"]] = bundesland(f.get("ort"))
    nach_key = {f["key"]: f for f in firmen}

    raus, verworfen = [], [0]
    for x in n:
        ag_namen = namen_aus(x.get("buyer-name"))
        ag = ag_namen[0] if ag_namen else ""
        titel = (namen_aus(x.get("title-lot")) or [""])[0]
        frist = datum(x.get("deadline-receipt-tender-date-lot"))
        stadt = (x.get("organisation-city-buyer") or [None])[0]
        cpv3 = {str(c)[:3] for c in (x.get("classification-cpv") or [])}
        pub = datum(x.get("publication-date"))

        # stark: gleicher Auftraggeber wie frueher. Das ist eine Beziehung,
        # kein Themenfilter. Die Firma hat dort nachweislich geliefert.
        #
        # Wichtig: eine Bekanntmachung kann mehrere Auftraggeber haben. Die
        # ARD beschafft gemeinsam, eine Bekanntmachung nennt dann zehn Sender.
        # Vorher stand im Satz immer Auftraggeber Nummer eins, getroffen hatte
        # aber vielleicht Nummer neun. Dann behauptet der Satz eine Beziehung
        # zur falschen Behoerde. Also merken, welcher Name getroffen hat.
        keys_stark = {}
        for n_ag in ag_namen:
            for k, beleg in ag_idx.get(norm(n_ag), {}).items():
                keys_stark.setdefault(k, (n_ag, beleg))

        # Verworfen: gleicher CPV plus gleiches Bundesland. Siehe unten.
        bl_ag = bundesland(stadt)
        if bl_ag:
            for c in cpv3:
                for k in cpv_idx.get(c, set()):
                    if bl_idx.get(k) == bl_ag and k not in keys_stark:
                        verworfen[0] += 1

        for k, (ag_treffer, beleg) in keys_stark.items():
            f = nach_key.get(k)
            if not f:
                continue
            if frist and frist < HEUTE:
                continue  # Frist vorbei, kein Anlass mehr
            score = 85 + (5 if frist and (frist - HEUTE).days <= 21 else 0)
            fr = f" Frist {frist.strftime('%d.%m.%Y')}." if frist else ""
            # Nur behaupten, was belegt ist. Mit Datum und Bekanntmachung
            # kann der Vertrieb den Satz vor dem Anruf selbst nachlesen.
            # Gewonnen und geboten sind zwei verschiedene Saetze. Wer geboten
            # und verloren hat, ist oft der besser ansprechbare Kontakt, aber
            # man darf ihm nicht sagen, er habe geliefert.
            verb = ("schon geliefert" if beleg.get("rolle") == "gewinner"
                    else "schon geboten")
            dat = (dt.date.fromisoformat(beleg["datum"]).strftime("%m/%Y")
                   if beleg.get("datum") else None)
            frueher = (f" Dort habt ihr {dat + ' ' if dat else ''}{verb}"
                       + (f" ({beleg['quelle']})" if beleg.get("quelle") else "")
                       + ".")
            # Wenn der fruehere Auftrag eine gemeinsame Beschaffung vieler
            # Stellen war, ist die Beziehung schwaecher. Das muss dastehen.
            if (beleg.get("mit_auftraggebern") or 1) > 3:
                frueher += (f" Hinweis: das war eine gemeinsame Beschaffung von "
                            f"{beleg['mit_auftraggebern']} Stellen, die Beziehung "
                            f"ist also moeglicherweise indirekt.")
            gemeinsam = (f" Gemeinsame Beschaffung von {len(set(ag_namen))} "
                         f"Stellen." if len(set(ag_namen)) > 1 else "")
            raus.append({
                "firma_key": k, "firma": f["name"],
                "signal": "S4 Ausschreibung beim bekannten Auftraggeber",
                "signal_datum": (pub or HEUTE).isoformat(), "score": min(score, 100),
                "auftraggeber_treffer": ag_treffer,
                "beleg_frueherer_auftrag": beleg.get("quelle"),
                "beleg_rolle": beleg.get("rolle"),
                "beleg_mit_auftraggebern": beleg.get("mit_auftraggebern"),
                "beleg": f"{kuerzen(ag_treffer, 70)}: {kuerzen(titel, 90)}.{fr}",
                "quelle": f"https://ted.europa.eu/de/notice/{x['publication-number']}/pdf",
                "bekanntmachung": x["publication-number"],
                "why_now": (f"{kuerzen(ag_treffer, 60)} schreibt gerade "
                            f"{kuerzen(titel, 60)} aus.{fr}{gemeinsam}{frueher}"),
            })

    # Pro Firma nur die drei frischesten. Wer 60 offene Ausschreibungen hat,
    # braucht keine Liste mit 60 Zeilen, sondern einen Aufhaenger.
    raus.sort(key=lambda r: (r["firma_key"], r["signal_datum"]), reverse=True)
    je, gekappt = collections.Counter(), []
    for r in raus:
        if je[r["firma_key"]] < 3:
            je[r["firma_key"]] += 1
            gekappt.append(r)

    print(f"  Signal S4: {len(raus)} Treffer bei {len(je)} Firmen, "
          f"auf 3 je Firma gekappt: {len(gekappt)}")
    print(f"  Verworfen: {verworfen[0]} Treffer aus 'gleicher CPV, gleiches "
          f"Bundesland'. Das war Rauschen, nicht Signal.")
    return gekappt


def signal_stellenanzeige(idx):
    """S1: bereits gebaut, hier nur dazugelegt."""
    print("\nS1  Stellenanzeige Vergabe oder Bid Management")
    if not os.path.exists(P_JOBS):
        print("  Datei fehlt, uebersprungen")
        return []
    sig = json.load(open(P_JOBS, encoding="utf-8"))["firmen"]
    raus = []
    for s in sig:
        f = idx.get(norm(s["firma"]))
        if not f:
            continue
        rolle = (s.get("rollen") or [""])[0]
        # Datum aus dem Alter der Anzeige, nicht "heute". Und die Quelle ist
        # die Anzeige selbst, nicht der Name der API. Ein Beleg, den der
        # Pruefer nicht anklicken kann, ist kein Beleg.
        tage = s.get("neueste_tage")
        datum_s = ((HEUTE - dt.timedelta(days=int(tage))).isoformat()
                   if isinstance(tage, (int, float)) else HEUTE.isoformat())
        raus.append({
            "firma_key": f["key"], "firma": f["name"],
            "signal": "S1 Stellenanzeige Vergabe", "signal_datum": datum_s,
            "score": 75,
            "beleg": (f"Offene Stelle: {kuerzen(rolle, 80)}"
                      + (f", seit {tage} Tagen online" if tage else "")),
            "quelle": s.get("quelle") or "Bundesagentur fuer Arbeit, Jobsuche-API",
            "bekanntmachung": "ba:" + re.sub(r"\W+", "", s["firma"].lower())[:40],
            "why_now": f"Ihr sucht gerade {kuerzen(rolle, 60)}. Genau die Arbeit "
                       "nimmt euch das Werkzeug ab.",
        })
    print(f"  Signal S1: {len(raus)} Treffer in den 323")
    return raus


# ---------------------------------------------------------------- State

def lade_state():
    if os.path.exists(P_STATE):
        d = json.load(open(P_STATE, encoding="utf-8"))
        return set(tuple(x) for x in d.get("gesehen", [])), d.get("laeufe", [])
    return set(), []


def schreib_state(gesehen, laeufe):
    json.dump({"gesehen": sorted(list(g) for g in gesehen), "laeufe": laeufe},
              open(P_STATE, "w", encoding="utf-8"), ensure_ascii=False)


# ---------------------------------------------------------------- Lauf

def main():
    nutze_cache = "--cache" in sys.argv
    if "--reset" in sys.argv and os.path.exists(P_STATE):
        os.remove(P_STATE)
        print("State geloescht\n")

    firmen, idx, dom = lade_firmen()
    print(f"{len(firmen)} Firmen aus Longlist 1, "
          f"{len(dom)} mit Domain, Stand {HEUTE}")

    gesehen, laeufe = lade_state()
    print(f"State: {len(gesehen)} Signale aus {len(laeufe)} fruehere(n) Laeufen")

    alle = (signal_vertragsende(idx, nutze_cache)
            + signal_offene_ausschreibung(firmen, idx, nutze_cache)
            + signal_stellenanzeige(idx))

    # Die Datei haelt immer das volle Bild. Der State entscheidet nur,
    # was als neu markiert wird. Sonst waere die Liste nach dem zweiten
    # Lauf leer, und der Vertrieb haette nichts mehr zum Anrufen.
    neu = []
    for r in alle:
        sid = (r["firma_key"], r["signal"][:2], r["bekanntmachung"])
        r["neu_in_diesem_lauf"] = sid not in gesehen
        if r["neu_in_diesem_lauf"]:
            gesehen.add(sid)
            neu.append(r)

    print(f"\n{len(alle)} Signale gefunden, {len(neu)} davon neu seit dem letzten Lauf")

    # je Firma zusammenfassen
    je_firma = collections.defaultdict(list)
    for r in alle:
        je_firma[r["firma_key"]].append(r)

    nach_key = {f["key"]: f for f in firmen}
    accounts = []
    for k, rs in je_firma.items():
        f = nach_key[k]
        rs.sort(key=lambda r: -r["score"])
        best = rs[0]
        # Bonus nur fuer verschiedene Signalarten. Zehn Ausschreibungen sind
        # ein Signal, eine Ausschreibung plus ein auslaufender Vertrag sind zwei.
        arten = {r["signal"][:2] for r in rs}
        score = min(100, best["score"] + 8 * (len(arten) - 1))
        d = dom.get(k) or {}
        accounts.append({
            "firma": f["name"], "firma_key": k,
            "domain": d.get("domain"), "domain_confidence": d.get("confidence"),
            "ort": f.get("ort"), "plan": f.get("plan"),
            "zuschlaege": f.get("zuschlaege"),
            "in_longlist_1": True,
            "score": score, "anzahl_signale": len(rs),
            "signalarten": sorted(arten),
            "neue_signale": sum(1 for r in rs if r["neu_in_diesem_lauf"]),
            "signale": rs,
            "why_now": best["why_now"],
        })
    accounts.sort(key=lambda a: (-a["score"], -a["zuschlaege"]))

    laeufe.append({"zeit": dt.datetime.now().isoformat(timespec="seconds"),
                   "gefunden": len(alle), "neu": len(neu),
                   "accounts": len(accounts)})
    schreib_state(gesehen, laeufe)
    json.dump({"stand": HEUTE.isoformat(), "accounts": accounts},
              open(P_OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # CSV: eine Zeile je Signal, wie der Case es verlangt
    # (Signal, Datum, Quelle, Score, Ueberschneidung mit Longlist 1)
    import csv
    with open(P_CSV, "w", encoding="utf-8-sig", newline="") as fh:
        w = csv.writer(fh, delimiter=";")
        w.writerow(["Rechtsname", "Domain", "Domain_Confidence", "Ort",
                    "Signal", "Signal_Datum", "Score_Account", "Score_Signal",
                    "In_Longlist_1", "Zuschlaege_Longlist_1", "Plan",
                    "Neu_in_diesem_Lauf", "Beleg", "Quelle",
                    "Auftraggeber_Treffer", "Beleg_fruehererer_Auftrag",
                    "Beleg_Rolle", "Beleg_Mitauftraggeber", "Why_now"])
        # Dieselben zwei Regeln wie in Longlist 1, und zwar beide.
        #
        # Vorher stand hier nur die Domainregel. Deshalb hat Longlist 1
        # Lufthansa Technik, DXC und Rohde & Schwarz korrekt aussortiert und
        # Longlist 2 sie weiter ausgegeben. Derselbe Ausschluss muss an jeder
        # Ausgabe haengen, nicht an einer.
        for a in [x for x in accounts
                  if x["domain_confidence"] == "belegt"
                  and not ausgeschlossen(x["firma"])]:
            for r in a["signale"]:
                w.writerow([a["firma"], a["domain"] or "",
                            a["domain_confidence"] or "offen", a["ort"] or "",
                            r["signal"], r["signal_datum"], a["score"],
                            r["score"], "ja", a["zuschlaege"], a["plan"],
                            "ja" if r["neu_in_diesem_lauf"] else "nein",
                            r["beleg"], r["quelle"],
                            r.get("auftraggeber_treffer") or "",
                            r.get("beleg_frueherer_auftrag") or "",
                            r.get("beleg_rolle") or "",
                            r.get("beleg_mit_auftraggebern") or "",
                            r["why_now"]])
    print(f"geschrieben: {P_CSV}")

    print(f"\n{len(accounts)} Accounts mit mindestens einem neuen Signal")
    print(f"geschrieben: {P_OUT}")
    print(f"State: {P_STATE}\n")

    print(f"{'Score':<7}{'Sig':<5}{'Firma':<40}{'Domain':<26}Why now")
    print("-" * 136)
    for a in accounts[:30]:
        print(f"{a['score']:<7}{a['anzahl_signale']:<5}{a['firma'][:38]:<40}"
              f"{str(a['domain'])[:24]:<26}{a['why_now'][:56]}")

    c = collections.Counter(r["signal"] for a in accounts for r in a["signale"])
    print("\nSignale nach Typ")
    for s, v in c.most_common():
        print(f"  {v:>4}  {s}")


if __name__ == "__main__":
    main()
