# -*- coding: utf-8 -*-
"""Nachlauf fuer die Accounts, bei denen das Impressum nicht gefunden wurde.

Erster Lauf: Impressum bei rund 45 Prozent gefunden. Das ist zu wenig fuer
eine Pflichtangabe, also lag der Fehler bei mir, nicht bei den Firmen.

Drei Gruende, alle behebbar:
  a) Der Link steht in einem JavaScript-Menue und nicht im HTML
  b) Der Pfad heisst /impressum.html, /de/impressum oder /rechtliches
  c) Die Startseite leitet auf eine Sprachversion um

Loesung: sitemap.xml lesen. Die nennt alle Seiten im Klartext, auch bei
JavaScript-Seiten. Dazu eine laengere Pfadliste. Nur die Fehlschlaege
werden erneut angefasst, der Rest bleibt wie er ist.
"""
import json, re, socket, time, urllib.parse
import concurrent.futures as cf
import enrich as E   # Stufen, Regexe und Parser wiederverwenden

# Ein Server, der die Verbindung offen haelt, darf nicht den ganzen Lauf
# blockieren. Beim ersten Versuch hing genau daran eine Firma minutenlang.
socket.setdefaulttimeout(8)

P_OUT = "/home/asusf/Job finding/enrichment.json"

PFADE = ["/impressum", "/impressum/", "/impressum.html", "/impressum.php",
         "/impressum.htm", "/de/impressum", "/de/impressum/", "/imprint",
         "/imprint/", "/legal-notice", "/rechtliches", "/rechtliches/impressum",
         "/unternehmen/impressum", "/ueber-uns/impressum", "/kontakt/impressum",
         "/service/impressum", "/footer/impressum", "/legal", "/legal/impressum",
         "/datenschutz-impressum", "/impressum-datenschutz", "/de/imprint"]


def sitemap_urls(start_url):
    """sitemap.xml und robots.txt nach einer Impressum-URL fragen."""
    p = urllib.parse.urlparse(start_url)
    wurzel = f"{p.scheme}://{p.netloc}"
    kand, gesehen = [], set()
    smaps = [f"{wurzel}/sitemap.xml", f"{wurzel}/sitemap_index.xml",
             f"{wurzel}/sitemap-index.xml", f"{wurzel}/wp-sitemap.xml"]
    try:
        _, rb = E.hole(f"{wurzel}/robots.txt", 20000)
        smaps += re.findall(r"(?i)sitemap:\s*(\S+)", rb)[:3]
    except Exception:
        pass
    for sm in smaps[:5]:
        if sm in gesehen:
            continue
        gesehen.add(sm)
        try:
            _, x = E.hole(sm, 400000)
        except Exception:
            continue
        locs = re.findall(r"<loc>\s*([^<\s]+)\s*</loc>", x)
        # Verschachtelte Sitemaps einmal aufloesen
        unter = [u for u in locs if u.endswith(".xml")][:5]
        for u in unter[:3]:
            if u in gesehen:
                continue
            gesehen.add(u)
            try:
                _, x2 = E.hole(u, 400000)
                locs += re.findall(r"<loc>\s*([^<\s]+)\s*</loc>", x2)
            except Exception:
                pass
        for u in locs:
            if re.search(r"(?i)(impressum|imprint|legal[-_]?notice)", u):
                if u not in kand:
                    kand.append(u)
        if kand:
            break
    return kand


def repariere(r):
    dom = r.get("domain")
    if not dom:
        return r
    start = None
    for schema in ("https://", "http://"):
        try:
            start, _ = E.hole(schema + dom, 5000)
            break
        except Exception:
            continue
    if not start:
        return r

    kand = sitemap_urls(start) + [urllib.parse.urljoin(start, p) for p in PFADE]
    for u in kand[:16]:
        try:
            fin, h = E.hole(u)
        except Exception:
            continue
        t = E.strip_tags(h)
        if not re.search(r"(?i)(impressum|imprint|angaben gem|§\s?5\s?(tmg|ddg)|"
                         r"registergericht|handelsregister|vertreten durch)", t):
            continue
        r["stufen"]["2_impressum"] = "ok, ueber sitemap oder Pfadliste"
        r.setdefault("seiten_gelesen", []).append(fin)

        rn = E.rechtsname(t)
        if rn:
            r["rechtsname_website"] = rn
            a = set(re.findall(r"[a-z]{4,}", E.fold(rn).lower()))
            b = set(re.findall(r"[a-z]{4,}", E.fold(r["firma"]).lower()))
            b -= {"gmbh", "aktiengesellschaft", "deutschland"}
            r["domain_geprueft"] = "passt" if (a & b) else "Name weicht ab"
        m = E.HR.search(t)
        if m and not r.get("hrb"):
            r["hrb"] = f"{m.group(1)} {m.group(2)}"
        if not r.get("telefon"):
            for x in E.TEL.findall(t):
                c = E.tel_saubern(x)
                if c:
                    r["telefon"], r["telefon_quelle"] = c, fin
                    break
        if not r.get("mail_allgemein"):
            for m_ in E.MAIL.findall(t):
                if not re.search(r"(?i)(webmaster|hosting|agentur|example|"
                                 r"sentry|\.png|\.jpg)", m_):
                    r["mail_allgemein"], r["mail_quelle"] = m_.lower(), fin
                    break

        neu = E.gf_aus_impressum(t, fin)
        if neu:
            alle = (r.get("kontakte") or []) + neu
            rang = {"Champion": 0, "Vertriebsleitung": 1, "Geschaeftsfuehrung": 2}
            best = {}
            for p in alle:
                k = E.fold(p["name"]).lower()
                if k not in best or rang[p["rolle"]] < rang[best[k]["rolle"]]:
                    best[k] = p
            r["kontakte"] = sorted(best.values(),
                                   key=lambda p: rang[p["rolle"]])[:3]
            muster = r.get("mail_muster")
            for p in r["kontakte"]:
                if "mail" in p:
                    continue
                p["mail"] = E.bau_mail(muster, p["name"], dom) if muster else None
                p["mail_status"] = ("Muster belegt, Adresse nicht verifiziert"
                                   if muster else "kein Muster belegbar")
                p["mail_quelle"] = (f"Muster {muster}, belegt durch "
                                    f"{r.get('mail_muster_beleg')}"
                                    if muster else None)
        return r
    return r


def main():
    d = json.load(open(P_OUT, encoding="utf-8"))
    for schluessel in ("alle",):
        rows = d[schluessel]
        offen = [r for r in rows
                 if r.get("stufen", {}).get("2_impressum") != "ok"]
        print(f"\n{schluessel}: {len(offen)} von {len(rows)} ohne Impressum",
              flush=True)
        with cf.ThreadPoolExecutor(max_workers=6) as ex:
            fut = {ex.submit(repariere, r): r for r in offen}
            for i, f in enumerate(cf.as_completed(fut), 1):
                r = fut[f]
                try:
                    f.result()
                except Exception as e:
                    r.setdefault("fehler_fix", str(e)[:100])
                ok = r.get("stufen", {}).get("2_impressum", "").startswith("ok")
                print(f"  {'FIX ' if ok else '    '}{i:>3}/{len(offen)}  "
                      f"{r['firma'][:36]:<38}{len(r.get('kontakte') or []):>2} K  "
                      f"{r.get('telefon') or '-':<17}"
                      f"{r.get('domain_geprueft')}", flush=True)

    json.dump(d, open(P_OUT, "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    print(f"\naktualisiert: {P_OUT}")

    nk = {r["firma_key"]: r for r in d["alle"]}
    for nm, rs in (("alle Firmen", d["alle"]),
                   ("Longlist 1 Top 40", [nk[k] for k in d["top40_keys"] if k in nk]),
                   ("Longlist 2 Top 20", [nk[k] for k in d["top20_keys"] if k in nk])):
        n = len(rs)
        print(f"\n--- Trefferquoten {nm} ({n}) ---")

        def q(fn, label):
            v = sum(1 for r in rs if fn(r))
            print(f"  {label:<48}{v:>3}/{n}  {v/n*100:>5.1f}%")
        q(lambda r: r.get("stufen", {}).get("1_startseite") == "ok",
          "Website erreichbar")
        q(lambda r: str(r.get("stufen", {}).get("2_impressum", "")).startswith("ok"),
          "Impressum gefunden")
        q(lambda r: r.get("domain_geprueft") == "passt",
          "Domain durch Impressum bestaetigt")
        q(lambda r: r.get("domain_geprueft") == "Name weicht ab",
          "Domain fraglich, Name weicht ab")
        q(lambda r: r.get("telefon"), "Telefon mit Quelle")
        q(lambda r: r.get("hrb"), "Handelsregisternummer")
        q(lambda r: r.get("kontakte"), "mindestens ein Kontakt mit Rolle")
        q(lambda r: len(r.get("kontakte") or []) >= 2, "zwei oder mehr Kontakte")
        q(lambda r: any(p["rolle"] == "Champion" for p in r.get("kontakte") or []),
          "Champion (Vergabe, Angebot, Bid, Innendienst)")
        q(lambda r: any(p["rolle"] == "Vertriebsleitung"
                        for p in r.get("kontakte") or []), "Vertriebsleitung")
        q(lambda r: any(p["rolle"] == "Geschaeftsfuehrung"
                        for p in r.get("kontakte") or []), "Geschaeftsfuehrung")
        q(lambda r: r.get("mail_muster"), "Mailmuster belegt")
        q(lambda r: any(p.get("mail") for p in r.get("kontakte") or []),
          "mindestens eine persoenliche Adresse abgeleitet")


if __name__ == "__main__":
    main()
