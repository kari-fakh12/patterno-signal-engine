# -*- coding: utf-8 -*-
"""Stufe 3 der Domainauflosung: die 41 Faelle, die das Raten nicht geloest hat.

Stufe 1 und 2 (Muster raten, Varianten testen) haben 282 von 323 sauber
getroffen. Bleiben 33 schwache und 8 offene. Schwach heisst: die Domain lebt,
aber der Firmenname steht nicht drauf. Genau da liegen die Fehltreffer,
zum Beispiel nrw.de fuer X-NRW GmbH oder dring.de fuer Dr.-Ing. Christiani.

Also: Suche mit dem Firmennamen, erstes plausibles Ergebnis nehmen, und dann
dieselbe Pruefung wie vorher, Name muss auf der Seite stehen.
"""
import json, os, re, time, unicodedata, html as htmllib
import urllib.request, urllib.error, urllib.parse, ssl, socket

P_DOM = "/home/asusf/Job finding/domains.json"

UML = str.maketrans({"ä": "ae", "ö": "oe", "ü": "ue", "ß": "ss"})
CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")

# Portale, Register und Jobbrosen sind nie die Firmenseite
MUELL = re.compile(
    r"(?i)(linkedin|xing|facebook|instagram|youtube|twitter|wikipedia|"
    r"northdata|firmenwissen|dnb\.com|bundesanzeiger|unternehmensregister|"
    r"handelsregister|wer-zu-wem|cylex|gelbeseiten|dastelefonbuch|11880|"
    r"kununu|glassdoor|indeed|stepstone|kimeta|jobware|trustpilot|"
    r"bloomberg|crunchbase|zoominfo|apollo\.io|lusha|rocketreach|"
    r"ted\.europa|europa\.eu|vergabe|bund\.de|amazon|ebay|idealo|"
    r"google\.|bing\.com|duckduckgo|github|sedo|afternic|dnsrsearch)")


def fold(s):
    s = (s or "").translate(UML)
    s = unicodedata.normalize("NFKD", s)
    return "".join(c for c in s if not unicodedata.combining(c))


RF = re.compile(r"(?i)\s*\b(gmbh|mbh|\bag\b|\bse\b|\bkg\b|\bohg\b|\bug\b|"
                r"\bkgaa\b|\bco\b|\bgbr\b|e\.?\s?v\.?)\b\.?")


def kern(name):
    s = fold(name)
    s = RF.sub(" ", s)
    s = re.sub(r"[^A-Za-z0-9 ]+", " ", s)
    return [t.lower() for t in s.split() if len(t) > 3]


def hole(url, n=70000):
    req = urllib.request.Request(url, headers={
        "User-Agent": UA, "Accept-Language": "de-DE,de;q=0.9",
        "Accept": "text/html,application/xhtml+xml"})
    with urllib.request.urlopen(req, timeout=12, context=CTX) as r:
        raw = r.read(n)
        enc = r.headers.get_content_charset() or "utf-8"
        return r.geturl(), raw.decode(enc, "replace")


def suche(name, ort):
    """DuckDuckGo HTML, kein Schluessel, kein Konto."""
    q = urllib.parse.quote_plus(f"{name} {ort or ''} Impressum")
    for url in (f"https://html.duckduckgo.com/html/?q={q}",
                f"https://lite.duckduckgo.com/lite/?q={q}"):
        try:
            _, h = hole(url, 300000)
        except Exception:
            time.sleep(2)
            continue
        roh = re.findall(r'uddg=([^"&]+)', h)
        out = []
        for r in roh:
            u = htmllib.unescape(urllib.parse.unquote(r))
            m = re.match(r"https?://([^/]+)", u)
            if not m:
                continue
            d = m.group(1).lower().replace("www.", "")
            if MUELL.search(d) or d in out:
                continue
            out.append(d)
            if len(out) >= 8:
                break
        if out:
            return out
        time.sleep(2)
    return []


def pruefe(domain, name):
    for schema in ("https://", "http://"):
        try:
            final, h = hole(schema + domain)
        except (urllib.error.HTTPError, urllib.error.URLError, socket.timeout,
                ssl.SSLError, ConnectionResetError, UnicodeError, OSError):
            continue
        t = fold(h).lower()
        if re.search(r"(diese domain|domain for sale|sedoparking|parkingcrew)", t):
            return None
        k = kern(name)
        if any(x in t for x in k):
            return {"domain": domain, "url": final, "confidence": "hoch",
                    "beleg": "ueber Suche gefunden, Firmenname auf der Seite"}
        return {"domain": domain, "url": final, "confidence": "niedrig",
                "beleg": "ueber Suche gefunden, Name nicht auf der Startseite"}
    return None


def main():
    d = json.load(open(P_DOM, encoding="utf-8"))
    rows = d["domains"]
    icp = {f["key"]: f for f in json.load(
        open("/home/asusf/Job finding/icp_systemhaeuser.json",
             encoding="utf-8"))["systemhaeuser"]}

    offen = [r for r in rows if r["confidence"] in ("offen", "niedrig")]
    print(f"{len(offen)} Faelle fuer Stufe 3\n")

    gefixt = 0
    for i, r in enumerate(offen, 1):
        ort = (icp.get(r["firma_key"]) or {}).get("ort")
        kand = suche(r["firma"], ort)
        alt = r.get("domain")
        neu = None
        for k in kand:
            p = pruefe(k, r["firma"])
            if p and p["confidence"] == "hoch":
                neu = p
                break
        if neu:
            r.update(neu)
            r["vorher"] = alt
            gefixt += 1
            mark = "FIX "
        else:
            # Raten hat nichts belegt und die Suche auch nicht: ehrlich offen lassen
            r["domain"] = None
            r["confidence"] = "offen"
            r["beleg"] = "weder Muster noch Suche konnten die Domain belegen"
            r["vorher"] = alt
            r["kandidaten_suche"] = kand[:5]
            mark = "    "
        print(f"{mark}{i:>3}/{len(offen)}  {r['firma'][:42]:<44}"
              f"{str(alt)[:20]:<22}-> {str(r['domain'])[:26]}", flush=True)
        time.sleep(1.5)

    c = {}
    for r in rows:
        c[r["confidence"]] = c.get(r["confidence"], 0) + 1
    print(f"\n{gefixt} von {len(offen)} per Suche belegt\n")
    print("Endstand Domains")
    for k in ("hoch", "mittel", "niedrig", "offen"):
        if k in c:
            print(f"  {k:<10}{c[k]:>4}  {c[k]/len(rows)*100:>5.1f}%")

    json.dump({"domains": rows}, open(P_DOM, "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    print(f"\naktualisiert: {P_DOM}")


if __name__ == "__main__":
    main()
