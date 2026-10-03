# -*- coding: utf-8 -*-
"""Mailmuster aus allen Adressen auf der Domain ableiten, nicht nur aus Treffern.

Erster Lauf: Muster bei 2,5 Prozent belegt. Der Fehler war die Bedingung.
Ich habe nur dann ein Muster akzeptiert, wenn eine gefundene Adresse zu einer
gefundenen Person passt. Das ist zu streng.

Besser: die Form jeder personenbezogenen Adresse auf der Domain lesen.
Wenn irgendwo m.mueller@firma.de steht, ist das Muster v.nachname, auch wenn
Herr Mueller nicht in meiner Kontaktliste steht. Zwei Stufen Sicherheit:

  belegt      Adresse passt zu einer Person, die ich namentlich habe
  abgeleitet  Form einer anderen Adresse auf derselben Domain

Beides ist nicht verifiziert. Das steht auch so in der Datei. Eine Adresse,
die ich nicht geprueft habe, darf nicht aussehen wie eine gepruefte.
"""
import json, re, collections
import concurrent.futures as cf
import urllib.parse
import enrich as E

P_OUT = "/home/asusf/Job finding/enrichment.json"

PFADE = ["", "/impressum", "/kontakt", "/contact", "/team", "/ansprechpartner",
         "/ueber-uns", "/unternehmen", "/kontakt/ansprechpartner",
         "/standorte", "/vertrieb", "/karriere"]

GENERISCH = re.compile(
    r"(?i)^(info|kontakt|contact|office|mail|email|service|support|hello|"
    r"hallo|zentrale|empfang|vertrieb|sales|einkauf|bewerbung|jobs|karriere|"
    r"presse|marketing|buchhaltung|rechnung|invoice|datenschutz|dsb|"
    r"webmaster|admin|noreply|no-reply|newsletter|post|team|anfrage|"
    r"beratung|technik|helpdesk|hotline|ausschreibung|vergabe)[0-9]*$")


# Deutsche Seiten schreiben Adressen gegen Spam gern um:
# "name(at)firma.de", "name [ät] firma punkt de", "name&#64;firma.de".
# Ohne das zu entschluesseln findet man fast nichts.
AT = re.compile(r"(?i)\s*(?:\(|\[|&lt;|&#40;)?\s*(?:at|ät|aet|@)\s*"
                r"(?:\)|\]|&gt;|&#41;)?\s*")
DOT = re.compile(r"(?i)\s*(?:\(|\[)\s*(?:dot|punkt)\s*(?:\)|\])\s*")


def entschluesseln(t):
    t = t.replace("&#64;", "@").replace("&commat;", "@")
    t = re.sub(r"(?i)([A-Za-z0-9._%+-]{2,})\s*(?:\(|\[)\s*(?:at|ät|aet)\s*"
               r"(?:\)|\])\s*([A-Za-z0-9.-]{3,})", r"\1@\2", t)
    t = re.sub(r"(?i)([A-Za-z0-9._%+-]{2,})\s+(?:at|ät)\s+"
               r"([A-Za-z0-9-]{3,}\s*(?:\(|\[)?\s*(?:dot|punkt)\s*(?:\)|\])?"
               r"\s*[a-z]{2,4})", r"\1@\2", t)
    t = DOT.sub(".", t)
    return t


def form(lokal):
    """Welche Form hat der Teil vor dem @?"""
    l = lokal.lower()
    if re.fullmatch(r"[a-z]{2,}\.[a-z]{2,}", l):
        return "vorname.nachname"
    if re.fullmatch(r"[a-z]\.[a-z]{2,}", l):
        return "v.nachname"
    if re.fullmatch(r"[a-z]{2,}_[a-z]{2,}", l):
        return "vorname_nachname"
    if re.fullmatch(r"[a-z]{2,}\.[a-z]", l):
        return "vorname.n"
    return None


def sammeln(r):
    dom = r.get("domain")
    if not dom:
        return r
    apex = ".".join(dom.split(".")[-2:])
    # Adresse -> Seite, auf der sie steht. Vorher war das ein Set ohne Herkunft,
    # und als Quelle wurde die Seite der Person eingetragen. Die Adressen waren
    # echt und wortwoertlich vorhanden, nur auf der Ansprechpartnerseite statt
    # im Impressum. Eine falsche Fundstelle macht einen richtigen Wert
    # unpruefbar, und unpruefbar ist in dieser Abgabe dasselbe wie falsch.
    fund = {}
    basis = None

    def ernten(h, url):
        t = E.strip_tags(h)
        for m in (set(re.findall(r"(?i)mailto:([^\"'?>\s]+)", h))
                  | set(E.MAIL.findall(t))
                  | set(E.MAIL.findall(entschluesseln(t)))
                  | set(E.MAIL.findall(entschluesseln(h)))):
            fund.setdefault(m.strip().lower().rstrip(".,;)"), url)

    for schema in ("https://", "http://"):
        try:
            basis, h = E.hole(schema + dom)
            ernten(h, basis)
            break
        except Exception:
            continue
    if not basis:
        return r
    for p in PFADE[1:]:
        u = urllib.parse.urljoin(basis, p)
        try:
            fin, h = E.hole(u)
        except Exception:
            continue
        ernten(h, fin)
    # Auch die Seiten, die der Waterfall schon gelesen hat, zum Beispiel die
    # Ansprechpartnerseite, die ueber einen Link gefunden wurde
    for u in (r.get("seiten_gelesen") or [])[:8]:
        if u in fund.values():
            continue
        try:
            fin, h = E.hole(u)
        except Exception:
            continue
        ernten(h, fin)
    mails = set(fund)

    eigen = set()
    for m in mails:
        m = m.strip().lower().rstrip(".,;)")
        if "@" not in m or not m.split("@")[-1].endswith(apex):
            continue
        if re.search(r"(?i)\.(png|jpg|gif|svg|webp)$|sentry|wixpress", m):
            continue
        eigen.add(m)
    r["mails_auf_domain"] = sorted(eigen)[:25]

    # Stufe A: Adresse passt zu einer Person, die ich habe
    muster, beleg, guete = None, None, None
    kon = r.get("kontakte") or []
    muster, beleg = E.mailmuster(eigen, kon)
    if muster:
        guete = "belegt, Adresse passt zu einer namentlich gefundenen Person"

    # Stufe B: Form einer anderen Adresse auf derselben Domain
    if not muster:
        formen = collections.Counter()
        quelle = {}
        for m in eigen:
            lokal = m.split("@")[0]
            if GENERISCH.match(lokal):
                continue
            f = form(lokal)
            if f:
                formen[f] += 1
                quelle.setdefault(f, m)
        if formen:
            muster = formen.most_common(1)[0][0]
            beleg = quelle[muster]
            guete = "abgeleitet aus der Form anderer Adressen auf der Domain"

    r["mail_muster"], r["mail_muster_beleg"] = muster, beleg
    r["mail_muster_guete"] = guete or "keines, keine personenbezogene Adresse gefunden"

    # Entscheidung von Karim: in die Abgabe kommt nur, was wortwoertlich auf
    # der Seite steht. Keine abgeleiteten Adressen mehr, auch nicht mit
    # Hinweis "nicht verifiziert".
    #
    # Das kostet fast nichts, weil die Ableitung ohnehin nur bei 3 Prozent
    # griff, und es nimmt die einzige Spalte aus der Datei, in der eine
    # erfundene Zeichenkette wie ein Fakt aussah. Das Muster bleibt als
    # Information stehen, aber es wird nicht mehr auf Personen angewandt.
    for p in kon:
        treffer = None
        teile = [t for t in re.sub(r"[^a-z ]", " ", E.fold(p["name"]).lower()).split()
                 if len(t) > 1]
        if len(teile) >= 2:
            v, n = teile[0], teile[-1]
            for m in eigen:
                lokal = m.split("@")[0].lower()
                if GENERISCH.match(lokal):
                    continue
                # Die Adresse muss zu diesem Menschen gehoeren, nicht nur
                # zur Firma. Nachname muss vorkommen.
                if n in lokal and (v in lokal or v[0] == lokal[0]):
                    treffer = m
                    break
        p["mail"] = treffer
        p["mail_status"] = ("wortwoertlich auf der Seite gefunden" if treffer
                            else "keine persoenliche Adresse auf der Seite")
        # Die Seite, auf der die Adresse steht, nicht die Seite, auf der der
        # Name stand. Das sind oft zwei verschiedene.
        p["mail_quelle"] = fund.get(treffer) if treffer else None
    return r


def main():
    d = json.load(open(P_OUT, encoding="utf-8"))
    for schluessel in ("alle",):
        rows = d[schluessel]
        print(f"\n{schluessel}: {len(rows)} Accounts", flush=True)
        with cf.ThreadPoolExecutor(max_workers=7) as ex:
            fut = {ex.submit(sammeln, r): r for r in rows}
            for i, f in enumerate(cf.as_completed(fut), 1):
                r = fut[f]
                try:
                    f.result()
                except Exception as e:
                    r["mail_muster_guete"] = f"Fehler: {str(e)[:70]}"
                print(f"  {i:>3}/{len(rows)}  {r['firma'][:34]:<36}"
                      f"{str(r.get('mail_muster')):<20}"
                      f"{len(r.get('mails_auf_domain') or []):>3} Adressen  "
                      f"{(r.get('mail_muster_guete') or '')[:34]}", flush=True)

    json.dump(d, open(P_OUT, "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    print(f"\naktualisiert: {P_OUT}")

    nk = {r["firma_key"]: r for r in d["alle"]}
    for nm, rs in (("alle Firmen", d["alle"]),
                   ("Longlist 1 Top 40", [nk[k] for k in d["top40_keys"] if k in nk]),
                   ("Longlist 2 Top 20", [nk[k] for k in d["top20_keys"] if k in nk])):
        n = len(rs)
        print(f"\n--- {nm} ({n}) ---")
        for label, fn in (
                ("Mailmuster belegt oder abgeleitet", lambda r: r.get("mail_muster")),
                ("davon belegt", lambda r: (r.get("mail_muster_guete") or "")
                 .startswith("belegt")),
                ("mindestens eine Adresse abgeleitet",
                 lambda r: any(p.get("mail") for p in r.get("kontakte") or [])),
                ("allgemeine Adresse (info@, kontakt@)",
                 lambda r: r.get("mail_allgemein")),
                ("Telefon mit Quelle", lambda r: r.get("telefon"))):
            v = sum(1 for r in rs if fn(r))
            print(f"  {label:<44}{v:>3}/{n}  {v/n*100:>5.1f}%")


if __name__ == "__main__":
    main()
