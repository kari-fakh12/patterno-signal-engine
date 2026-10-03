# -*- coding: utf-8 -*-
"""Domain je Firma aufloesen, ohne Budget.

TED nennt den Gewinner als Freitext. Keine Domain, keine Registernummer.
Drei Stufen, wie in 1c beschrieben:
  1. Muster raten: Rechtsform weg, .de dran
  2. Varianten testen: Bindestrich, zusammen, .com, .eu
  3. Rest bleibt offen und geht in Stufe 3 (Suche)

Jede Domain bekommt eine Confidence. Geraten und per Namenstreffer auf der
Seite bestaetigt ist etwas anderes als "die Seite antwortet".
"""
import json, os, re, sys, unicodedata, concurrent.futures as cf
import urllib.request, urllib.error, ssl, socket

SRC = "/home/asusf/Job finding/icp_systemhaeuser.json"
OUT = "/home/asusf/Job finding/domains.json"

RF = re.compile(
    r"(?i)\s*\b(gmbh\s*&\s*co\.?\s*kgaa|gmbh\s*&\s*co\.?\s*kg|gmbh\s*&\s*co\.?\s*ohg|"
    r"ag\s*&\s*co\.?\s*kg|se\s*&\s*co\.?\s*kgaa|gmbh|mbh|\bag\b|\bse\b|\bkg\b|"
    r"\bohg\b|\bug\b|\bkgaa\b|\be\.?\s?v\.?\b|\bgbr\b|\bco\b|\bkgaa\b)\b\.?")

# Woerter, die fast nie im Domainnamen stehen
FUELL = re.compile(
    r"(?i)\b(vertriebs|vertrieb|und|service|services|systeme|system|systemhaus|"
    r"gesellschaft|fuer|für|informationstechnik|informationstechnologie|"
    r"datentechnik|technik|solutions|solution|deutschland|germany|holding|group|"
    r"gruppe|international|computer|consulting|beratung|handels|handel|"
    r"elektronik|technologies|technologie|the)\b")

UML = str.maketrans({"ä": "ae", "ö": "oe", "ü": "ue", "ß": "ss",
                     "Ä": "ae", "Ö": "oe", "Ü": "ue"})


def ascii_fold(s):
    s = (s or "").translate(UML)
    s = unicodedata.normalize("NFKD", s)
    return "".join(c for c in s if not unicodedata.combining(c))


def tokens(name, drop_fuell=True):
    s = ascii_fold(name)
    s = RF.sub(" ", s)
    if drop_fuell:
        s = FUELL.sub(" ", s)
    s = re.sub(r"[^A-Za-z0-9 ]+", " ", s)
    return [t.lower() for t in s.split() if len(t) > 1]


def kandidaten(name):
    """Kandidaten in der Reihenfolge, in der ich sie glauben wuerde."""
    t_kern = tokens(name, True)
    t_voll = tokens(name, False)
    k = []

    def add(stem):
        if not stem or len(stem) < 3:
            return
        for tld in (".de", ".com", ".eu", ".net"):
            d = stem + tld
            if d not in k:
                k.append(d)

    for toks in (t_kern, t_voll):
        if not toks:
            continue
        add("".join(toks[:3]))
        add("-".join(toks[:3]))
        if len(toks) >= 2:
            add("".join(toks[:2]))
            add("-".join(toks[:2]))
        add(toks[0])
    return k[:26]


CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")


def hole(url, n=60000):
    req = urllib.request.Request(url, headers={
        "User-Agent": UA, "Accept-Language": "de-DE,de;q=0.9,en;q=0.8"})
    with urllib.request.urlopen(req, timeout=8, context=CTX) as r:
        raw = r.read(n)
        enc = r.headers.get_content_charset() or "utf-8"
        return r.geturl(), raw.decode(enc, "replace")


def pruefe(domain, name):
    """Lebt die Domain und steht der Firmenname drauf?"""
    for schema in ("https://", "http://"):
        try:
            final, html = hole(schema + domain)
        except (urllib.error.HTTPError, urllib.error.URLError, socket.timeout,
                ssl.SSLError, ConnectionResetError, UnicodeError, OSError):
            continue
        txt = ascii_fold(html).lower()
        # Parkseiten und Verkaufsseiten aussortieren
        if re.search(r"(diese domain (kann|steht)|domain for sale|sedoparking|"
                     r"jetzt kaufen.{0,20}domain|parkingcrew|afternic)", txt):
            return None
        kern = [t for t in tokens(name, True) if len(t) > 3]
        if any(t in txt for t in kern):
            return {"domain": domain, "url": final, "confidence": "hoch",
                    "beleg": "geraten, Firmenname auf der Seite"}
        voll = [t for t in tokens(name, False) if len(t) > 4]
        if any(t in txt for t in voll):
            return {"domain": domain, "url": final, "confidence": "mittel",
                    "beleg": "geraten, Teilname auf der Seite"}
        return {"domain": domain, "url": final, "confidence": "niedrig",
                "beleg": "Seite lebt, Name nicht gefunden"}
    return None


def loese(firma):
    name = firma["name"]
    for d in kandidaten(name):
        r = pruefe(d, name)
        if r and r["confidence"] in ("hoch", "mittel"):
            r["kandidaten_geprueft"] = d
            return dict(firma_key=firma["key"], firma=name, **r)
        if r and r["confidence"] == "niedrig":
            # weitersuchen, aber als Rueckfalloption behalten
            firma.setdefault("_schwach", r)
    if "_schwach" in firma:
        return dict(firma_key=firma["key"], firma=name, **firma["_schwach"])
    return dict(firma_key=firma["key"], firma=name, domain=None,
                confidence="offen", beleg="kein Kandidat hat geantwortet")


def main():
    s = json.load(open(SRC, encoding="utf-8"))["systemhaeuser"]
    print(f"{len(s)} Firmen, Domain aufloesen", flush=True)
    res = []
    with cf.ThreadPoolExecutor(max_workers=16) as ex:
        for i, r in enumerate(ex.map(loese, s), 1):
            res.append(r)
            if i % 25 == 0:
                print(f"  {i}/{len(s)}", flush=True)

    c = {}
    for r in res:
        c[r["confidence"]] = c.get(r["confidence"], 0) + 1
    print("\nErgebnis")
    for k in ("hoch", "mittel", "niedrig", "offen"):
        if k in c:
            print(f"  {k:<10}{c[k]:>4}  {c[k]/len(res)*100:>5.1f}%")

    json.dump({"domains": res}, open(OUT, "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    print(f"\ngeschrieben: {OUT}")
    print("\nOffen geblieben:")
    for r in res:
        if r["confidence"] in ("offen", "niedrig"):
            print(f"  {r['firma'][:52]:<54}{r.get('domain') or '-'}")


if __name__ == "__main__":
    main()
