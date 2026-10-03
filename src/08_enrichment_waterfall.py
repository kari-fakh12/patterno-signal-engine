# -*- coding: utf-8 -*-
"""Enrichment als Waterfall, ohne Budget. Aufgabe 1d und 2d.

Die Idee: in Deutschland ist das Impressum Pflicht. Jede GmbH muss dort
Rechtsform, Geschaeftsfuehrung, Telefon und eine Adresse nennen. Das ist
eine amtlich erzwungene Datenquelle mit 100 Prozent Abdeckung und
Quellenangabe inklusive. Dafuer braucht niemand Credits.

Stufen, in dieser Reihenfolge, jede mit eigener Trefferquote:

  1  Startseite holen, interne Links sammeln
  2  Impressum: Rechtsname, Geschaeftsfuehrung, Telefon, Mail, Adresse
     Nebeneffekt: der Rechtsname prueft die geratene Domain. Passt er nicht,
     war die Domain falsch, und das muss raus statt drinbleiben.
  3  Team-, Kontakt- und Ansprechpartnerseiten: Namen mit Titel
  4  Rollen zuordnen: Champion (Vergabe, Angebot, Bid, Tender), dann
     Vertriebsleitung, dann Geschaeftsfuehrung
  5  Mailmuster aus gefundenen Adressen ableiten, Status ehrlich setzen

Kein Schritt erfindet etwas. Was nicht auf der Seite stand, bleibt leer.
"""
import json, os, re, sys, time, unicodedata, collections
import urllib.request, urllib.error, urllib.parse, ssl, socket
import concurrent.futures as cf

BASE = "/home/asusf/Job finding"
P_ICP = f"{BASE}/icp_systemhaeuser.json"
P_DOM = f"{BASE}/domains.json"
# Die Signal-Engine schreibt jetzt ins Repo, damit der woechentliche Lauf in
# GitHub Actions dieselben Pfade nutzt wie lokal.
P_LL2 = f"{BASE}/patterno-signal-engine/data/longlist2_signale.json"
P_OUT = f"{BASE}/enrichment.json"

# Ein Server, der die Verbindung offen haelt, darf nicht den Lauf blockieren.
socket.setdefaulttimeout(8)

CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")

UML = str.maketrans({"ä": "ae", "ö": "oe", "ü": "ue", "ß": "ss",
                     "Ä": "Ae", "Ö": "Oe", "Ü": "Ue"})

# Hersteller und Konzerne, die beim CPV-Test durchgerutscht sind.
# Der Rauschpass gehoert hierher, nicht in eine Fussnote.
from ausschluss import RAUSCHEN  # eine Quelle fuer alle

# LinkedIn-Profile, per Websuche zu bereits bekannten Namen gefunden und
# einzeln geprueft: das Profil nennt dieselbe Firma. Kein LinkedIn-Konto, kein
# Scraping, kein Budget. Nur fuer Personen, die ohnehin schon mit Rolle und
# Fundstelle in der Liste stehen.
#
# Das schliesst genau die Luecke, die ich im README als die einzige benenne,
# fuer die Geld noetig waere: die Firmenwebsite nennt die Person, aber nicht
# ihre erreichbare Spur.
LINKEDIN = {
    ("navum", "andreas kopfmiller"):
        "https://de.linkedin.com/in/andreas-kopfmiller-48b74bb0",
    ("brodos", "stefan vitzithum"):
        "https://de.linkedin.com/in/stefan-vitzithum-310b07120",
    ("mediainterface", "robert groeber"):
        "https://de.linkedin.com/in/robertgroeber",
    ("netdescribe", "elmar prem"):
        "https://de.linkedin.com/in/elmar-prem-62b39854",
    ("greenbone", "elmar geese"):
        "https://de.linkedin.com/in/elmar-geese-44a52b2",
    ("medientechnik thomas", "christian kunick"):
        "https://de.linkedin.com/in/christian-kunick-88a462231",
    ("univention", "peter ganten"):
        "https://de.linkedin.com/in/pganten",
    ("public edge", "sebastian lorenz"):
        "https://www.linkedin.com/in/sebastian-lorenz-3010854/",
    ("roda computer", "frank scholz"):
        "https://de.linkedin.com/in/frank-scholz-546937119",
}


def linkedin_fuer(firma, name):
    f = fold(firma).lower()
    n = re.sub(r"[^a-z ]", "", fold(name).lower())
    for (f_teil, n_teil), url in LINKEDIN.items():
        if f_teil in f and all(w in n for w in n_teil.split()):
            return url
    return None

CHAMPION = re.compile(
    r"(?i)(vergab|ausschreib|angebotsmanagem|angebots-|bid[ -]?manag|"
    r"tender|proposal|submission|bietermanagem|offer[ -]?manag|"
    r"vertriebsinnendienst|sales operations|sales ops|innendienst)")
VERTRIEB = re.compile(
    r"(?i)(vertriebsleit|leiter vertrieb|leitung vertrieb|head of sales|"
    r"vp sales|vice president sales|sales director|verkaufsleit|"
    r"prokurist|vertriebsdirektor|key account manager|business development)")
GF = re.compile(
    r"(?i)(gesch[aä]ftsf[uü]hr|managing director|\bceo\b|inhaber|"
    r"vorstand|vorständ|founder|gr[uü]nder)")

SEITEN = [
    (re.compile(r"(?i)impressum|imprint|legal[-_]notice"), "impressum"),
    (re.compile(r"(?i)kontakt|contact|ansprechpartner"), "kontakt"),
    (re.compile(r"(?i)team|mitarbeiter|wir[-_ ]?[uü]ber|ueber[-_ ]?uns|"
                r"about[-_ ]?us|unternehmen|management|vorstand|"
                r"gesch[aä]ftsf[uü]hrung|f[uü]hrung"), "team"),
]

MAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
TEL = re.compile(r"(?:\+49|0049|\(0\)|\b0)[\d\s().\-/]{7,22}\d")
HR = re.compile(r"(?i)(HRB|HRA)\s*[:\s]*(\d{3,8})")
USTID = re.compile(r"(?i)DE\s?\d{9}")


def fold(s):
    s = (s or "").translate(UML)
    s = unicodedata.normalize("NFKD", s)
    return "".join(c for c in s if not unicodedata.combining(c))


def strip_tags(h):
    h = re.sub(r"(?is)<(script|style|noscript|svg)[^>]*>.*?</\1>", " ", h)
    h = re.sub(r"(?i)<br\s*/?>|</(p|div|li|tr|h[1-6]|td)>", "\n", h)
    h = re.sub(r"(?s)<[^>]+>", " ", h)
    h = (h.replace("&amp;", "&").replace("&nbsp;", " ").replace("&uuml;", "ü")
         .replace("&auml;", "ä").replace("&ouml;", "ö")
         .replace("&szlig;", "ß").replace("&Uuml;", "Ü")
         .replace("&Auml;", "Ä").replace("&Ouml;", "Ö")
         .replace("&#039;", "'").replace("&quot;", '"').replace("&gt;", ">")
         .replace("&lt;", "<").replace("&#64;", "@").replace("&shy;", ""))
    h = re.sub(r"[ \t\xa0]+", " ", h)
    return re.sub(r"\n{2,}", "\n", h).strip()


def hole(url, n=400000):
    req = urllib.request.Request(url, headers={
        "User-Agent": UA, "Accept-Language": "de-DE,de;q=0.9",
        "Accept": "text/html,application/xhtml+xml"})
    with urllib.request.urlopen(req, timeout=14, context=CTX) as r:
        raw = r.read(n)
        enc = r.headers.get_content_charset()
        if not enc:
            m = re.search(rb'charset=["\']?([\w-]+)', raw[:3000], re.I)
            enc = m.group(1).decode() if m else "utf-8"
        return r.geturl(), raw.decode(enc, "replace")


def links(basis, html):
    out = []
    for m in re.finditer(r'(?is)<a\b[^>]*href=["\']([^"\'#]+)["\'][^>]*>(.{0,160}?)</a>',
                         html):
        href, text = m.group(1), strip_tags(m.group(2))
        u = urllib.parse.urljoin(basis, href)
        if urllib.parse.urlparse(u).netloc != urllib.parse.urlparse(basis).netloc:
            continue
        if re.search(r"(?i)\.(pdf|jpe?g|png|gif|zip|docx?|xlsx?|mp4)$", u):
            continue
        out.append((u, text, href))
    return out


# ------------------------------------------------------- Personen finden

NAME = re.compile(
    r"\b((?:Dr\.|Prof\.|Dipl\.-?\w+\.?|Dipl\.)?\s?"
    # Vorname, auch mit Bindestrich: Hans-Peter, Kai-Uwe. Ohne diese Gruppe
    # wurde "Hans-Peter Hellmann" als "Peter Hellmann" gelesen, also ein
    # falscher Name, der echt aussieht.
    r"[A-ZÄÖÜ][a-zäöüß]{1,15}"
    r"(?:-[A-ZÄÖÜ][a-zäöüß]{1,15})?"
    r"(?:\s+(?:von|van|de|der|zu|zur|al|el))?"
    r"\s+[A-ZÄÖÜ][a-zäöüß\-]{2,22}"
    # Zweiter Nachname: Ferre Hernandez. Optional, damit normale Namen
    # unveraendert bleiben.
    r"(?:\s+[A-ZÄÖÜ][a-zäöüß\-]{2,22})?)\b")

# Auf welchen Seiten darf ich ueberhaupt nach Mitarbeitern suchen?
#
# Auf einer Produktseite stehen Kundenstimmen. Bei DFC-SYSTEMS standen zwei
# Aerzte mit "Inhaber" im Titel in meiner Liste, weil sie das Produkt loben und
# Inhaber ihrer eigenen Praxis sind. Das ist kein Mitarbeiter, das ist eine
# Referenz. Dasselbe gilt fuer News und Pressemeldungen, die ueber andere
# Firmen berichten.
SEITE_ERLAUBT = re.compile(
    r"(?i)(impressum|imprint|legal|kontakt|contact|team|mitarbeiter|"
    r"ansprechpartner|ueber-?uns|\bueber\b|about|unternehmen|company|"
    r"management|vorstand|gesch[aä]ftsf[uü]hrung|f[uü]hrung|"
    r"standorte|organisation|wir\b)")
VERBOTEN_WORT = re.compile(
    r"(?i)^(l[oö]sung|solution|produkt|product|leistung|portfolio|"
    r"referenz|kundenstimme|testimonial|case|cases|success|"
    r"news|blog|presse|press|aktuell|magazin|artikel|story|stories|"
    r"veranstaltung|event|events|webinar|messe|karriere|career|careers|"
    r"job|jobs|stelle|stellen|shop|produkte|download|downloads)")


def seite_fuer_personen(url):
    """Darf ich auf dieser Seite nach Mitarbeitern suchen?

    Geprueft wird Abschnitt fuer Abschnitt, nicht als freier Text. Mit einer
    Textsuche war "/impressum" verboten, weil darin "press" steckt. Der Pfad
    ist aber kein Satz, er besteht aus Abschnitten, und genau so muss man ihn
    lesen.
    """
    pfad = re.sub(r"^https?://[^/]+", "", url or "").split("?")[0]
    teile = [t for t in re.split(r"[/]+", pfad) if t]
    if not teile:
        return True                      # Startseite
    for t in teile:
        for wort in re.split(r"[-_.]+", t):
            if VERBOTEN_WORT.match(wort):
                return False
    return bool(SEITE_ERLAUBT.search(pfad))


# Nachrichtensprache. Wer so schreibt, berichtet ueber eine Personalie,
# oft bei einer anderen Firma.
NEWS_SPRACHE = re.compile(
    r"(?i)(stellt sich .{0,40}neu auf|wird neuer|wird neue |uebernimmt die|"
    r"übernimmt die|verst[aä]rkt sich|holt sich|wechselt zu|"
    r"pressemitteilung|presseinformation|stellt weichen|neu im team bei|"
    r"ernennt|beruft|verabschiedet)")

# Zwei grossgeschriebene Woerter nebeneinander sind im Deutschen kein Name,
# sondern meistens eine Ueberschrift. "Typische Fragen", "Key Account",
# "Digitale Verwaltung", "Technische Tiefe" sind alle so entstanden.
# Ein Wort aus dieser Liste schliesst den Treffer aus.
STOPP = set("""
unsere unser unserem unseren ihre ihr ihnen wir uns die der das dieser diese
dieses alle alles mehr jetzt hier neue neu neues zum zur beim mit von vom und
oder als weitere aktuelle offene cookie cookies datenschutz impressum kontakt
stellenangebot stellenangebote jobs job karriere news presse blog downloads
service services support leistungen loesungen loesung produkte produkt
referenzen partner partnerschaft standorte standort unternehmen firma team
geschaeftsfuehrer geschaeftsfuehrung geschaeftsfuehrerin vorstand inhaber
prokurist leiter leiterin leitung abteilung bereich key account manager
managerin management vertrieb verkauf einkauf technik technische technischer
technisches digitale digitaler digitales digital zentrale zentraler sicherer
sichere sicheres gepruefte geprueft klare klares hohe hoher hohes typische
typisch verstaendliche automatisierte zertifiziert individuelle persoenliche
schnelle einfache moderne nachhaltige professionelle umfassende komplette
beratung schulung wartung betrieb hosting cloud security sicherheit netzwerk
software hardware lizenzen lizenz ausschreibung ausschreibungen vergabe
angebot angebote anfrage anfragen auftrag auftraege projekt projekte
speicherung verarbeitung nutzung erhebung weitergabe loeschung auskunft
widerspruch betroffenenrechte rechtsgrundlage verantwortlicher
microsoft windows apple android google amazon cisco fortinet veeam vmware
deutsche deutscher deutsches deutschland germany gruppe group holding
lernen erfahren entdecken sprechen schreiben rufen besuchen folgen
verstaendlich transparenz qualitaet flexibilitaet prozesse nachweise
verwaltung zugriff identity international ein eine einen herr frau
ueber willkommen startseite home mehrwert vorteile vorteil warum wie was
""".split())

# Ein Vorname ist das zuverlaessigste Signal, dass eine Person gemeint ist.
VORNAMEN = set("""
alexander andre andreas andrea anja anke anna annett annette anton armin arno
axel barbara bastian benedikt benjamin bernd bernhard bettina birgit bjoern
boris brigitte britta burkhard carina carl carmen carsten christa christian
christiane christina christine christoph claudia clemens cornelia corinna
daniel daniela daniela david denis dennis detlef diana dieter dirk dominik
dorothea eckhard edgar eduard elena elke emil enrico erich erik ernst eva
fabian felix florian frank franz friedrich gabriele georg gerald gerd gerhard
gernot gisela goetz guenter guenther gregor gudrun hannes hans harald hartmut
heiko heike heinrich heinz helga helmut henning herbert hermann holger horst
hubert ines ingo ingrid iris isabel jan jana janina jens jessica joachim jochen
johann johanna johannes jonas jorg joerg josef juergen julia julian jutta
kai karin karl karsten katharina kathrin katja katrin kerstin klaus konrad
kristin kurt lars laura lena leon linda lothar lucas ludwig lukas lutz maik
manfred manuel manuela marc marcel marco marcus margit maria marina mario
marion marius mark marko markus marlene martin martina mathias matthias
maximilian melanie michael michaela mike mirco mirko monika nadine natalie
nicole nico niels nils nina norbert olaf oliver otto patrick paul peggy
peter petra philipp pia rainer ralf ralph ramona raphael regina reinhard
reinhold renate rene ricarda richard rita robert robin roland rolf romy
ronald rudolf ruediger ruth sabine sabrina sandra sascha sebastian silke
silvia simon simone soeren sonja stefan stefanie steffen stephan stephanie
sven svenja sylvia tanja thomas thorsten tim timo tina tobias tom torsten
udo ulf ulrich ulrike uwe vanessa veronika viktor volker waldemar walter
werner wilhelm wolfgang wolfram yvonne
ahmet ali ayse burak cem deniz emre fatma hakan hasan ibrahim kemal mehmet
murat mustafa omer osman serkan yusuf zeynep
adam agnieszka andrzej anna dariusz grzegorz jacek jan katarzyna krzysztof
marek pawel piotr tomasz wojciech
alex anne ben chris daniel ed george james jennifer john jonathan joseph
karen kevin laura lisa mark martin matthew michael nick patrick paul peter
richard robert sarah scott simon stephen steve thomas tim tony william
""".split())


import threading

# Mitzaehlen, was die strengen Regeln wegwerfen. Ohne diese Zahlen ist
# "nur belegte Kontakte" eine Behauptung. Mit ihnen ist es eine Bilanz.
VERWORFEN = collections.Counter()
_ZLOCK = threading.Lock()


def verwerfe(grund, n=1):
    with _ZLOCK:
        VERWORFEN[grund] += n


AKAD = re.compile(r"(?i)^(dr|prof|dipl|ing|mba|med|rer|pol|nat|habil|"
                  r"herr|frau|mr|mrs|ms)\.?$")

# Wortteile, die aus einem Namen eine Ueberschrift machen
NICHT_PERSON = re.compile(
    r"(?i)\b(gmbh|mbh|\bag\b|\bse\b|\bkg\b|ohg|verwaltung|gesellschaft|"
    r"abteilung|bereich|team|gruppe|stellt sich|unsere|unser|ihre|cookie|"
    r"datenschutz|impressum|kontakt|telefon|e-?mail|strasse|straße|"
    r"platz|weg\b|allee|postfach|www|http)\b")


# Verschachtelte Labels. "Vertretungsberechtigt: Geschaeftsfuehrer: Matthias
# Korber" hat vorher den Namen "Geschaeftsfuehrer: Matthias Korber" ergeben,
# weil nur das aeussere Label abgeschnitten wurde.
LABEL_PREFIX = re.compile(
    r"(?i)^\s*(gesch[aä]ftsf[uü]hr\w*|vorstand\w*|vorst[aä]nde|"
    r"inhaber\w*|prokurist\w*|vertretungsberechtigt\w*|vertreten durch|"
    r"alleinvertretungsberechtigt\w*|managing director|direktor\w*|"
    r"gf|ceo|cto|coo)\s*[:–-]?\s*")


def titel_weg(s):
    """Akademische Titel, Anreden und verschachtelte Rollenlabels abtrennen."""
    s = re.sub(r"\s+", " ", (s or "")).strip(" ,.;:")
    for _ in range(3):           # mehrfach, bei zwei verschachtelten Labels
        neu = LABEL_PREFIX.sub("", s)
        if neu == s:
            break
        s = neu
    # Titel am Anfang als Kette abschneiden, nicht Token fuer Token.
    # "Dipl.-Ing." ist ein einziges Token mit Bindestrich und wurde deshalb
    # vorher nicht erkannt.
    s = re.sub(r"(?i)^((?:dr|prof|dipl|ing|mag|mba|msc|bsc|med|rer|pol|nat|"
               r"habil|h\.?c|herr|frau|mr|mrs|ms)\.?\s*[-–]?\s*)+",
               "", s).strip(" ,.;:-")
    teile = [t for t in s.split() if not AKAD.match(t.strip("."))]
    return " ".join(teile).strip(" ,.;:")


def ist_person(nm):
    """Ist das plausibel eine Person und keine Ueberschrift?"""
    teile = nm.replace(".", " ").split()
    teile = [t for t in teile if t]
    titel = {"dr", "prof", "dipl", "ing", "mba", "med", "rer", "pol", "nat"}
    rein = [t for t in teile if fold(t).lower().strip(".") not in titel]
    if not (2 <= len(rein) <= 4):
        return False
    klein = [fold(t).lower() for t in rein]
    if any(t in STOPP for t in klein):
        return False
    hatte_titel = len(rein) < len(teile)
    # Vorname belegt die Person. Ohne Vorname nur mit akademischem Titel.
    return klein[0] in VORNAMEN or (hatte_titel and klein[0] not in STOPP)


def tel_bei_person(zeilen, i, fenster=3):
    """Telefonnummer im Block dieser Person.

    Ansprechpartnerseiten stellen Menschen als Karte dar: Name, Rolle, Telefon,
    Mail. Die Durchwahl steht also neben der Person, nicht im Impressum. Das
    Impressum kennt nur die Zentrale, und genau deshalb stand in der Abgabe
    "Durchwahl: 0 Prozent". Das war wahr fuer das Impressum und falsch fuer
    die Firma.

    Vorsichtsregel: nur bis zum naechsten Namen suchen. Sonst bekommt Person A
    die Durchwahl von Person B, und das ist schlimmer als keine Nummer.
    """
    for j in range(i, min(i + fenster + 1, len(zeilen))):
        z = zeilen[j]
        if j > i and NAME.search(z) and not TEL.search(z):
            break                      # naechste Person beginnt
        m = TEL.search(z)
        if m:
            return m.group(0)
        if j > i and NAME.search(z):
            break
    return None


BILDUNTERSCHRIFT = re.compile(r"(?i)\bv\.\s?l\.\s?n\.\s?r\.|von links|"
                              r"\bv\.\s?r\.\s?n\.\s?l\.")
NAME_KLAMMER = re.compile(
    r"([A-ZÄÖÜ][\wäöüß.-]+"
    r"(?:\s+[A-ZÄÖÜ][\wäöüß.-]+){1,2})"
    r"\s*\(([^)]{3,60})\)")


def aus_bildunterschrift(zeile, quelle=None):
    """Bildunterschriften nennen mehrere Personen mit Rolle in Klammern.

    "v.l.n.r. Daniel Bravo (Sales Director), Manuela X (Marketing), ..."
    Vorher bekamen alle drei Personen die komplette Zeile als Titel, also auch
    die Rolle der jeweils anderen. Hier wird je Person nur ihre eigene Klammer
    genommen.
    """
    out = []
    for m in NAME_KLAMMER.finditer(zeile):
        nm, rolle_txt = titel_weg(m.group(1)), m.group(2).strip()
        if not nm or NICHT_PERSON.search(nm) or len(nm.split()) < 2:
            continue
        for rx, rolle in ((CHAMPION, "Champion"), (VERTRIEB, "Vertriebsleitung"),
                          (GF, "Geschaeftsfuehrung")):
            if rx.search(rolle_txt):
                out.append({"name": nm, "rolle": rolle,
                            "titel": rolle_txt[:90], "quelle": quelle})
                break
    return out


FREMDFIRMA = re.compile(
    r"([A-ZÄÖÜ][\wäöüß.&-]{2,30}"
    r"(?:\s+[A-ZÄÖÜ][\wäöüß.&-]{1,30}){0,3})"
    r"\s+(?:GmbH|AG|SE|mbH|KGaA|OHG)\b")


def fremde_firma(umfeld, firma):
    """Nennt der Text eine ANDERE Firma als die, die ich gerade anreichere?

    Bei NetDescribe stand im Titelumfeld "Die nicos GmbH stellt sich im
    Vertrieb vor". Die gefundenen Personen waren damit sehr wahrscheinlich
    Leute der nicos GmbH, nicht von NetDescribe. Ein Kontakt, der der
    falschen Firma zugeordnet ist, ist schlimmer als kein Kontakt: er sieht
    richtig aus.
    """
    eigen = kennwoerter(firma)
    for m in FREMDFIRMA.finditer(umfeld or ""):
        genannt = kennwoerter(m.group(1))
        if not genannt:
            continue
        if not (genannt & eigen):
            return m.group(1).strip()
    return None


def personen(text, quelle=None, firma=None):
    """Name plus Titel aus einem Textblock. Titel steht in der Zeile davor,
    danach, oder hinter einem Komma. Alle drei Faelle pruefen."""
    out = []
    zeilen = [z.strip() for z in text.split("\n")]
    # Bildunterschriften zuerst, die haben eine eigene Struktur
    for z in zeilen:
        if BILDUNTERSCHRIFT.search(z) or z.count("(") >= 2:
            out += aus_bildunterschrift(z, quelle)
    # Block statt Zeile, aber nur nach vorne.
    #
    # Erst habe ich die Zeile davor und zwei danach gelesen: dann erbte jemand
    # die Rolle seines Vorgaengers. Dann nur noch dieselbe Zeile: damit fielen
    # Ansprechpartnerkarten komplett aus, denn dort steht der Name in einer
    # Zeile, die Rolle in der naechsten und das Telefon in der dritten. Von
    # 167 Kontakten kamen danach 164 aus dem Impressum, also war die ganze
    # Teamseite praktisch blind.
    #
    # Richtig ist der Block: ab dem Namen vorwaerts bis zum naechsten Namen.
    # Was dazwischen steht, gehoert zu dieser Person. Nach hinten wird nie
    # gelesen, deshalb kann niemand die Rolle des Vorgaengers erben.
    namenszeilen = [i for i, z in enumerate(zeilen)
                    if 2 < len(z) < 220
                    and any(ist_person(m.group(1).strip())
                            for m in NAME.finditer(z))]
    for idx, i in enumerate(namenszeilen):
        z = zeilen[i]
        ende = namenszeilen[idx + 1] if idx + 1 < len(namenszeilen) else len(zeilen)
        block = " | ".join(zeilen[i:min(ende, i + 6)])
        for m in NAME.finditer(z):
            nm = m.group(1).strip()
            if not ist_person(nm):
                verwerfe("kein Personenname, sondern Seitentext")
                continue
            umfeld = block
            titel = None
            for rx, rolle in ((CHAMPION, "Champion"), (VERTRIEB, "Vertriebsleitung"),
                              (GF, "Geschaeftsfuehrung")):
                t = rx.search(umfeld)
                if t:
                    # Den KURZEN Abschnitt nehmen, in dem das Rollenwort steht,
                    # nicht den laengsten. Vorher stand bei Secusmart ein ganzer
                    # Satz als Titel, und bei pdv-systeme eine Unternehmens-
                    # beschreibung. Ein Titel ist "Prokurist", kein Absatz.
                    teile = [s.strip() for s in re.split(r"[|/;•,\n]", umfeld)
                             if rx.search(s)]
                    seg = min(teile, key=len) if teile else t.group(0)
                    # Den Namen selbst aus dem Titel nehmen
                    seg = seg.replace(nm, "").strip(" ,.;:-–")
                    titel = (rolle, (seg or t.group(0))[:70])
                    break
            if not titel:
                verwerfe("keine Rolle im Block dieser Person")
                continue
            fremd = fremde_firma(umfeld, firma) if firma else None
            if fremd:
                verwerfe("Text nennt eine andere Firma")
                continue
            if NEWS_SPRACHE.search(umfeld):
                verwerfe("Personalie oder Pressetext, kein Mitarbeiterprofil")
                continue
            tel_m = TEL.search(block)
            out.append({"name": nm, "rolle": titel[0], "titel": titel[1],
                        "quelle": quelle,
                        "telefon_roh": tel_m.group(0) if tel_m else None})
    # doppelte Namen zusammenfassen, beste Rolle behalten
    rang = {"Champion": 0, "Vertriebsleitung": 1, "Geschaeftsfuehrung": 2}
    best = {}
    for p in out:
        k = fold(p["name"]).lower()
        if k not in best or rang[p["rolle"]] < rang[best[k]["rolle"]]:
            best[k] = p
    return list(best.values())


def gf_aus_impressum(text, quelle=None):
    """Geschaeftsfuehrung aus dem Impressum, hinter ihrem Label.

    Wichtig: hier gilt die Vornamensliste NICHT. Das Label ist der Beweis.
    Wenn im Impressum "Geschaeftsfuehrung: Gunter Ernst, Carsten Rausch,
    Andreas Meyer" steht, sind alle drei Geschaeftsfuehrer, auch wenn mein
    Vornamensverzeichnis Gunter nicht kennt.

    Vorher hat genau das echte Menschen gekostet: Gunter Ernst bei medDV,
    Mukesh Unadcath bei itiso, und bei MEGWARE beide Geschaeftsfuehrer, womit
    die Firma auf null Kontakte fiel. Eine Liste, die zwei von drei
    Geschaeftsfuehrern nennt, sieht aus wie ein Datenproblem, und sie ist eins.
    """
    out = []
    for m in re.finditer(
            r"(?i)(gesch[aä]ftsf[uü]hr\w*|vertretungsberechtigt\w*|"
            r"vertreten durch|inhaber|vorstand\w*|vorst[aä]nde|"
            r"managing director|direktor\w*)\s*(?:\([^)]{0,40}\))?\s*[:\n]\s*"
            r"(.{0,220})", text):
        rolle_wort = m.group(1)
        rest = m.group(2)
        rest = re.split(r"(?i)\b(registergericht|handelsregister|ust|umsatzsteuer|"
                        r"telefon|tel\.|e-?mail|sitz der|amtsgericht|hrb|hra|"
                        r"aufsichtsrat|vorsitzende|datenschutz|adresse)\b",
                        rest)[0]
        rolle = ("Geschaeftsfuehrung"
                 if not re.search(r"(?i)vorstand|direktor", rolle_wort)
                 else "Geschaeftsfuehrung")
        # Liste auftrennen: Komma, Semikolon, "und", "&", Zeilenumbruch
        for stueck in re.split(r"\s*(?:,|;|\bund\b|&|\n|\||/)\s*", rest):
            stueck = stueck.strip(" .–-")
            if not (4 < len(stueck) < 70):
                continue
            n = titel_weg(stueck)
            if not n or NICHT_PERSON.search(n):
                continue
            teile = n.split()
            if not (2 <= len(teile) <= 4):
                continue
            if any(fold(t).lower().strip(".") in STOPP for t in teile):
                continue
            if not all(re.match(r"^[A-ZÄÖÜ]", t) or t.lower() in
                       ("von", "van", "de", "der", "zu", "zur", "el", "al")
                       for t in teile):
                continue
            out.append({"name": n, "rolle": rolle,
                        "titel": f"{rolle_wort.strip()} (Impressum)",
                        "quelle": quelle})
    sehen, u = set(), []
    for p in out:
        k = fold(p["name"]).lower()
        if k not in sehen:
            sehen.add(k)
            u.append(p)
    return u[:3]


STOPP_FIRMA = {
    "gmbh", "mbh", "aktiengesellschaft", "deutschland", "germany", "holding",
    "group", "gruppe", "systemhaus", "systeme", "system", "vertriebsgesellschaft",
    "vertriebs", "vertrieb", "service", "services", "consulting", "solutions",
    "technologies", "computer", "datentechnik", "informationstechnik",
    "handelsgesellschaft", "gesellschaft", "unternehmen", "impressum",
    "imprint", "edv", "international", "digital", "kontakt", "home",
    "startseite", "angewandte",
}


def kennwoerter(name):
    s = re.sub(r"[^a-z0-9 ]+", " ", fold(name).lower())
    return {w for w in s.split() if len(w) > 3 and w not in STOPP_FIRMA}


def namen_gleich(ted_name, web_name):
    """Ist das dieselbe Firma? Streng, weil ein Fehler hier einen fremden
    Ansprechpartner in die Liste schreibt."""
    a, b = kennwoerter(ted_name), kennwoerter(web_name)
    if not a or not b:
        return False, "zu wenig kennzeichnende Woerter"
    gem = a & b
    if not gem:
        return False, f"kein gemeinsames Wort: {sorted(a)} gegen {sorted(b)}"
    kenn = max(a, key=len)
    if kenn not in gem:
        return False, f"kennzeichnendes Wort \"{kenn}\" fehlt, nur {sorted(gem)}"
    if len(gem) / min(len(a), len(b)) < 0.5:
        return False, f"nur {len(gem)} von {min(len(a), len(b))}: {sorted(gem)}"
    return True, f"gemeinsam: {sorted(gem)}"


def rechtsname(text):
    m = re.search(r"(?m)^\s*([A-ZÄÖÜ][^\n]{2,80}?"
                  r"(?:GmbH(?:\s*&\s*Co\.?\s*KG)?|AG|SE|KG|mbH|OHG|UG)"
                  r"(?:\s*&\s*Co\.?\s*KG)?)\s*$", text)
    return m.group(1).strip() if m else None


def tel_saubern(t):
    """Nummer auf E.164 bringen.

    Die Falle: Impressen schreiben "0049 (0) 2542 ..." oder "+49 (0) 2542 ...".
    Nach dem Entfernen der Sonderzeichen bleibt die fuehrende Verkehrsnull im
    nationalen Teil stehen. Ergebnis war +49025429558250, eine Nummer, die
    niemand waehlen kann. Die Null muss nach der Landesvorwahl weg.
    """
    t = re.sub(r"[^\d+]", "", t)
    if t.startswith("+49"):
        rest = t[3:]
    elif t.startswith("0049"):
        rest = t[4:]
    elif t.startswith("00"):
        return None                      # Ausland, nicht mein Markt
    elif t.startswith("0"):
        rest = t[1:]
    else:
        return None                      # ohne Vorwahl nicht brauchbar
    rest = rest.lstrip("0")              # Verkehrsnull raus, genau hier
    if not (6 <= len(rest) <= 13):
        return None
    return "+49" + rest


def mailmuster(mails, personen_liste):
    """Aus gefundenen personenbezogenen Adressen das Muster ableiten."""
    for m in mails:
        lokal = m.split("@")[0].lower()
        for p in personen_liste:
            teile = fold(p["name"]).lower().split()
            if len(teile) < 2:
                continue
            v, n = teile[0], teile[-1]
            for muster, bau in (
                    ("vorname.nachname", f"{v}.{n}"),
                    ("v.nachname", f"{v[0]}.{n}"),
                    ("vnachname", f"{v[0]}{n}"),
                    ("nachname", n),
                    ("vorname", v),
                    ("vorname_nachname", f"{v}_{n}")):
                if lokal == bau:
                    return muster, m
    return None, None


TITEL = {"dr", "prof", "dipl", "ing", "mba", "med", "rer", "pol", "nat",
         "herr", "frau", "mr", "mrs", "ms"}


def bau_mail(muster, name, domain):
    """Adresse aus dem Muster bauen.

    "Dr." ist kein Vorname. Ohne diese Zeile kam dr.fuerth@netgo.de heraus.
    """
    teile = [re.sub(r"[^a-z]", "", t) for t in fold(name).lower().split()]
    teile = [t for t in teile if len(t) > 1 and t not in TITEL]
    if len(teile) < 2:
        return None
    v, n = teile[0], teile[-1]
    lokal = {"vorname.nachname": f"{v}.{n}", "v.nachname": f"{v[0]}.{n}",
             "vnachname": f"{v[0]}{n}", "nachname": n, "vorname": v,
             "vorname_nachname": f"{v}_{n}"}.get(muster)
    return f"{lokal}@{domain}" if lokal else None


# ------------------------------------------------------- ein Account

def enrich(acc):
    dom = acc.get("domain")
    r = {"firma": acc["firma"], "firma_key": acc["firma_key"], "domain": dom,
         "stufen": {}, "kontakte": [], "telefon": None, "telefon_quelle": None,
         "mail_allgemein": None, "mail_quelle": None, "mail_muster": None,
         "mail_muster_beleg": None, "rechtsname_website": None,
         "domain_geprueft": "nicht moeglich", "hrb": None,
         "seiten_gelesen": []}
    if not dom:
        r["stufen"]["1_startseite"] = "keine Domain"
        return r

    # Stufe 1
    start_url, html = None, None
    for schema in ("https://", "http://"):
        try:
            start_url, html = hole(schema + dom)
            break
        except Exception:
            continue
    if not html:
        r["stufen"]["1_startseite"] = "nicht erreichbar"
        return r
    r["stufen"]["1_startseite"] = "ok"
    r["seiten_gelesen"].append(start_url)

    kand = {"impressum": [], "kontakt": [], "team": []}
    for u, text, href in links(start_url, html):
        for rx, art in SEITEN:
            if rx.search(href) or rx.search(text):
                if u not in kand[art]:
                    kand[art].append(u)
    for art, pfade in (("impressum", ["/impressum", "/impressum/", "/imprint"]),
                       ("kontakt", ["/kontakt", "/kontakt/", "/contact"]),
                       ("team", ["/team", "/ueber-uns", "/unternehmen"])):
        if not kand[art]:
            kand[art] = [urllib.parse.urljoin(start_url, p) for p in pfade]

    texte = {"start": strip_tags(html)}

    # Stufe 2: Impressum
    imp = None
    for u in kand["impressum"][:3]:
        try:
            fin, h = hole(u)
        except Exception:
            continue
        t = strip_tags(h)
        if re.search(r"(?i)(impressum|angaben gem|§\s?5\s?(tmg|ddg)|"
                     r"registergericht|handelsregister)", t):
            imp, texte["impressum"] = t, t
            r["seiten_gelesen"].append(fin)
            break
    r["stufen"]["2_impressum"] = "ok" if imp else "nicht gefunden"

    if imp:
        rn = rechtsname(imp)
        r["rechtsname_website"] = rn
        if rn:
            # Streng vergleichen. Ein gemeinsames Wort ist kein Beleg:
            # "Hansen & Gieraths" und "Dr. Hansen EDV Consulting" sind
            # zwei Firmen, "Kramer & Crew" und "Kramer-Werke" auch.
            ok, warum = namen_gleich(acc["firma"], rn)
            r["domain_geprueft"] = "passt" if ok else "Name weicht ab"
            r["domain_geprueft_warum"] = warum
        m = HR.search(imp)
        if m:
            r["hrb"] = f"{m.group(1)} {m.group(2)}"
        for t in TEL.findall(imp):
            c = tel_saubern(t)
            if c:
                r["telefon"], r["telefon_quelle"] = c, r["seiten_gelesen"][-1]
                break
        for m_ in MAIL.findall(imp):
            if not re.search(r"(?i)(webmaster|hosting|agentur|example|sentry|"
                             r"\.png|\.jpg)", m_):
                r["mail_allgemein"] = m_.lower()
                r["mail_quelle"] = r["seiten_gelesen"][-1]
                break
        r["kontakte"] += gf_aus_impressum(imp, r["seiten_gelesen"][-1])

    # Stufe 3: Kontakt und Team
    gelesen = 0
    for art in ("kontakt", "team"):
        for u in kand[art][:4]:
            if gelesen >= 5:
                break
            try:
                fin, h = hole(u)
            except Exception:
                continue
            gelesen += 1
            t = strip_tags(h)
            texte[art] = t
            r["seiten_gelesen"].append(fin)
            # Nur auf Seiten suchen, die ueber die Firma selbst sprechen.
            if seite_fuer_personen(fin):
                r["kontakte"] += personen(t, fin, acc["firma"])
            else:
                verwerfe("Seite ist keine Team- oder Kontaktseite")
            if not r["telefon"]:
                for x in TEL.findall(t):
                    c = tel_saubern(x)
                    if c:
                        r["telefon"], r["telefon_quelle"] = c, fin
                        break
            time.sleep(0.4)
    r["stufen"]["3_team_kontakt"] = f"{gelesen} Seiten gelesen"

    # Stufe 4: entdoppeln und nach Rolle sortieren
    rang = {"Champion": 0, "Vertriebsleitung": 1, "Geschaeftsfuehrung": 2}
    best = {}
    for p in r["kontakte"]:
        k = fold(p["name"]).lower()
        if k not in best or rang[p["rolle"]] < rang[best[k]["rolle"]]:
            best[k] = p
    r["kontakte"] = sorted(best.values(), key=lambda p: rang[p["rolle"]])[:3]
    r["stufen"]["4_rollen"] = ", ".join(p["rolle"] for p in r["kontakte"]) or "keine"

    # LinkedIn, wo per Websuche ein Profil zu dieser Person gefunden wurde
    for p in r["kontakte"]:
        url = linkedin_fuer(acc["firma"], p["name"])
        p["linkedin"] = url
        p["linkedin_quelle"] = ("Websuche, Profil nennt die Firma" if url
                                else None)

    # Durchwahl, Mobil oder Zentrale? Die Aufgabe fragt das in 1.2 ausdruecklich.
    zentrale = r.get("telefon")
    for p in r["kontakte"]:
        roh = p.pop("telefon_roh", None)
        nummer = tel_saubern(roh) if roh else None
        p["telefon"] = nummer
        if not nummer:
            p["telefon_typ"] = None
            p["telefon_quelle"] = None
            continue
        p["telefon_quelle"] = p.get("quelle")
        if re.match(r"^\+491[5-7]", nummer):
            p["telefon_typ"] = "Mobil"
        elif zentrale and nummer != zentrale:
            # Gleiche Vorwahl plus Anlagennummer, andere Endung: Durchwahl.
            gemeinsam = 0
            for a, b in zip(nummer, zentrale):
                if a != b:
                    break
                gemeinsam += 1
            p["telefon_typ"] = ("Durchwahl" if gemeinsam >= 8
                                else "eigene Rufnummer")
        elif zentrale and nummer == zentrale:
            p["telefon_typ"] = "Zentrale"
        else:
            p["telefon_typ"] = "eigene Rufnummer"

    # Stufe 5: Mailmuster
    alle_mails = set()
    for t in texte.values():
        for m_ in MAIL.findall(t):
            if m_.lower().split("@")[-1].endswith(dom.split(".")[-2] + "." +
                                                  dom.split(".")[-1]):
                alle_mails.add(m_.lower())
    muster, beleg = mailmuster(alle_mails, r["kontakte"])
    if not muster and alle_mails:
        muster, beleg = mailmuster(alle_mails, personen(
            "\n".join(texte.values()))[:40])
    r["mail_muster"], r["mail_muster_beleg"] = muster, beleg
    for p in r["kontakte"]:
        if muster:
            p["mail"] = bau_mail(muster, p["name"], dom)
            p["mail_status"] = "Muster belegt, Adresse nicht verifiziert"
            p["mail_quelle"] = f"Muster {muster}, belegt durch {beleg}"
        else:
            p["mail"] = None
            p["mail_status"] = "kein Muster belegbar"
            p["mail_quelle"] = None
    r["stufen"]["5_mailmuster"] = muster or "keines belegbar"

    # Sicherung. Wenn das Impressum eine andere Firma nennt, gehoeren Telefon,
    # Mail und Ansprechpartner dieser anderen Firma. Dann darf nichts davon in
    # die Liste. Eine fremde Durchwahl ist schlimmer als eine leere Zelle.
    if r["domain_geprueft"] == "Name weicht ab":
        r["verworfen"] = {
            "grund": (f"Domain {dom} gehoert laut Impressum zu "
                      f"\"{r.get('rechtsname_website')}\""),
            "telefon": r["telefon"], "mail_allgemein": r["mail_allgemein"],
            "kontakte": r["kontakte"],
        }
        r["telefon"] = r["telefon_quelle"] = None
        r["mail_allgemein"] = r["mail_quelle"] = None
        r["mail_muster"] = r["mail_muster_beleg"] = None
        r["kontakte"] = []
        r["stufen"]["6_sicherung"] = "Kontaktdaten verworfen, fremde Firma"
    return r


# ------------------------------------------------------- Auswahl und Lauf

def auswahl():
    icp = json.load(open(P_ICP, encoding="utf-8"))["systemhaeuser"]
    dom = {d["firma_key"]: d for d in json.load(
        open(P_DOM, encoding="utf-8"))["domains"]}
    ll2 = {a["firma_key"]: a for a in json.load(
        open(P_LL2, encoding="utf-8"))["accounts"]}

    kand = []
    for f in icp:
        if RAUSCHEN.search(f["name"]):
            continue                      # Rauschpass: Hersteller und Konzerne
        d = dom.get(f["key"]) or {}
        # Nur belegte Domains. "geraten" heisst, dass niemand gegengelesen hat,
        # und ein Anruf bei der falschen Firma ist teurer als eine Zeile weniger.
        if d.get("confidence") != "belegt":
            continue
        a = ll2.get(f["key"])
        kand.append({
            "firma": f["name"], "firma_key": f["key"], "domain": d["domain"],
            "domain_confidence": d["confidence"], "ort": f.get("ort"),
            "plan": f.get("plan"), "zuschlaege": f["zuschlaege"],
            "signal_score": (a or {}).get("score", 0),
            "why_now": (a or {}).get("why_now"),
            "signale": (a or {}).get("signale", []),
        })

    # Angereichert wird die ganze Liste, nicht nur die Spitze.
    #
    # Der Case fragt in 1.1 nach bis zu drei Kontakten fuer die Liste. Vorher
    # habe ich 60 von 151 gesucht und die Luecke im Dokument beschrieben.
    # Beschreiben ist nicht liefern. Jede Firma wird einmal geholt, die drei
    # Dateien entstehen danach als Sicht auf dasselbe Ergebnis.
    alle = sorted(kand, key=lambda x: (-x["signal_score"], -x["zuschlaege"]))
    keys40 = [x["firma_key"] for x in alle[:40]]
    drin = set(keys40)
    keys20 = [x["firma_key"] for x in alle
              if x["signal_score"] and x["firma_key"] not in drin][:20]
    return alle, keys40, keys20


def lauf(liste, titel):
    print(f"\n=== {titel}: {len(liste)} Accounts ===", flush=True)
    out = []
    with cf.ThreadPoolExecutor(max_workers=8) as ex:
        fut = {ex.submit(enrich, a): a for a in liste}
        for i, f in enumerate(cf.as_completed(fut), 1):
            a = fut[f]
            try:
                r = f.result()
            except Exception as e:
                r = {"firma": a["firma"], "firma_key": a["firma_key"],
                     "domain": a["domain"], "fehler": str(e)[:120],
                     "kontakte": [], "stufen": {}}
            r.update({k: a[k] for k in ("ort", "plan", "zuschlaege",
                                        "signal_score", "why_now",
                                        "domain_confidence")})
            r["signale"] = a.get("signale", [])
            out.append(r)
            print(f"  {i:>3}/{len(liste)}  {a['firma'][:34]:<36}"
                  f"{len(r.get('kontakte', [])):>2} Kontakte  "
                  f"{r.get('telefon') or '-':<17}"
                  f"{r.get('domain_geprueft', '?')}", flush=True)
    return out


def main():
    alle, keys40, keys20 = auswahl()
    r_alle = lauf(alle, "Longlist 1, alle Firmen")
    nach_key = {r["firma_key"]: r for r in r_alle}
    r1 = [nach_key[k] for k in keys40 if k in nach_key]
    r2 = [nach_key[k] for k in keys20 if k in nach_key]
    json.dump({"alle": r_alle, "top40_keys": keys40, "top20_keys": keys20},
              open(P_OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"\ngeschrieben: {P_OUT}")

    for nm, rs in (("alle Firmen", r_alle), ("Longlist 1 Top 40", r1),
                   ("Longlist 2 Top 20", r2)):
        n = len(rs)
        print(f"\n--- Trefferquoten {nm} ({n} Accounts) ---")
        def q(f, label):
            v = sum(1 for r in rs if f(r))
            print(f"  {label:<46}{v:>3}/{n}  {v/n*100:>5.1f}%")
        q(lambda r: r.get("stufen", {}).get("1_startseite") == "ok",
          "Website erreichbar")
        q(lambda r: r.get("stufen", {}).get("2_impressum") == "ok",
          "Impressum gefunden")
        q(lambda r: r.get("domain_geprueft") == "passt",
          "Domain durch Impressum bestaetigt")
        q(lambda r: r.get("domain_geprueft") == "Name weicht ab",
          "Domain falsch, Name weicht ab")
        q(lambda r: r.get("telefon"), "Telefon mit Quelle")
        q(lambda r: r.get("kontakte"), "mindestens ein Kontakt mit Rolle")
        q(lambda r: len(r.get("kontakte", [])) >= 2, "zwei oder mehr Kontakte")
        q(lambda r: any(p["rolle"] == "Champion" for p in r.get("kontakte", [])),
          "Champion gefunden (Vergabe, Angebot, Bid)")
        q(lambda r: any(p["rolle"] == "Vertriebsleitung"
                        for p in r.get("kontakte", [])), "Vertriebsleitung")
        q(lambda r: any(p["rolle"] == "Geschaeftsfuehrung"
                        for p in r.get("kontakte", [])), "Geschaeftsfuehrung")
        q(lambda r: r.get("mail_muster"), "Mailmuster belegt")
        q(lambda r: r.get("hrb"), "Handelsregisternummer")

    print("\n--- Was die strenge Regel weggeworfen hat ---")
    if not VERWORFEN:
        print("  nichts")
    for grund, n in VERWORFEN.most_common():
        print(f"  {grund:<46}{n:>5}")
    print(f"  {'Summe verworfene Namenskandidaten':<46}"
          f"{sum(VERWORFEN.values()):>5}")
    gefunden = sum(len(r.get("kontakte") or []) for r in r_alle)
    print(f"  {'behalten':<46}{gefunden:>5}")
    print(f"\n  {'Firmen ohne jeden Kontakt':<46}"
          f"{sum(1 for r in r_alle if not r.get('kontakte')):>5} von {len(r_alle)}")
    ohne = collections.Counter()
    for r in r_alle:
        if r.get("kontakte"):
            continue
        s = r.get("stufen") or {}
        if s.get("1_startseite") != "ok":
            ohne["Website nicht erreichbar"] += 1
        elif not str(s.get("2_impressum", "")).startswith("ok"):
            ohne["Impressum nicht lesbar"] += 1
        elif s.get("3_team_kontakt", "").startswith("0"):
            ohne["keine Team- oder Kontaktseite gefunden"] += 1
        else:
            ohne["Seiten gelesen, aber kein Name mit belegter Rolle"] += 1
    for grund, n in ohne.most_common():
        print(f"    {grund:<44}{n:>5}")


if __name__ == "__main__":
    main()
