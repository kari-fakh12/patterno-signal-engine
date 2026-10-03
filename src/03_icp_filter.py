# -*- coding: utf-8 -*-
"""ICP v3: der Systemhaus-Test kommt aus den CPV-Codes, nicht aus dem Firmennamen.

Ein Systemhaus beschafft UND betreibt. In den gewonnenen Auftraegen heisst das:
mindestens eine Hardware- oder Netzwerk-CPV (30x, 32x, 516) UND mindestens eine
Software- oder Dienstleistungs-CPV (48x, 72x).

Reine Softwarehaeuser haben nur 48x/72x. Reine Haendler nur 30x.
Berater haben 794. Alle drei fallen damit automatisch raus.
"""
import json, os, re, collections

d = json.load(open(os.path.expanduser("~/Job finding/ted_firmen.json"),
                   encoding="utf-8"))
firmen = d["firmen"]
MONATE = 21.0

HARDWARE = {"300", "301", "302", "323", "324", "325", "516", "487"}
SOFTWARE = {"480", "481", "482", "483", "484", "485", "486", "488",
            "720", "722", "723", "724", "725", "726", "727"}
BERATUNG = {"794", "798", "731", "799", "792"}

KONZERN = re.compile(
    r"(?i)(^siemens|^sap\b|microsoft|^ibm|oracle|^atos|eviden|fujitsu|ricoh|"
    r"canon|konica|xerox|^ntt |^nttdata|^dell\b|^hp\b|hewlett|lenovo|cisco|"
    r"accenture|deloitte|kpmg|ernst & young|bearingpoint|capgemini|"
    r"pricewaterhouse|\bpwc\b|mckinsey|roland berger|sopra steria|"
    r"^cgi |infosys|wipro|tata consultancy|telekom|t-systems|vodafone|"
    r"telefonica|^bechtle|computacenter|^cancom|softwareone|^sva system|"
    r"^adesso|materna|^crayon|chg-meridian)")

BERATER_NAME = re.compile(
    r"(?i)(consulting|consultants?\b|\bconsult\b|beratung|advisory|"
    r"wirtschaftspr[uü]f|steuerberat|rechtsanwalt|kanzlei|^d-fine|^nortal)")

PERSONAL = re.compile(
    r"(?i)(^sthree|personaldienst|personalvermittl|zeitarbeit|staffing|"
    r"recruit|headhunt|randstad|adecco|hays|manpower|brunel|ferchau|"
    r"amadeus fire|\bdis ag\b|computer futures|progressive recruit)")

AUSLAND = re.compile(
    r"(?i)(\bd\.o\.o\.|\bs\.r\.o\.|sp\. ?z ?o\.?o\.|\bb\.v\.\b|\ba/s\b|"
    r"\boy\b|\bs\.p\.a\.|\bsrl\b|\bsas\b|\bsl\b$|\bltd\b|\bllc\b|\binc\b|"
    r"^setcor|^cloudferro|^vshn)")

g = collections.Counter()
kand = []
for r in firmen:
    n, name = r["zuschlaege"], r["name"]
    cpv = set(r["cpv_top"])
    if n < 2:
        g["1 Zuschlag, unbestaetigt"] += 1; continue
    if n > 30:
        g["ueber 30 Zuschlaege, eigenes Vergabeteam"] += 1; continue
    if KONZERN.search(name):
        g["Konzern, Hersteller, Telko"] += 1; continue
    if PERSONAL.search(name):
        g["Personaldienstleister"] += 1; continue
    if AUSLAND.search(name):
        g["auslaendische Rechtsform"] += 1; continue
    if BERATER_NAME.search(name):
        g["Beratung laut Firmenname"] += 1; continue
    if cpv & BERATUNG and not (cpv & HARDWARE):
        g["Beratung laut CPV, keine Hardware"] += 1; continue
    if not (cpv & HARDWARE):
        g["kein Hardware-CPV, also Softwarehaus"] += 1; continue
    if not (cpv & SOFTWARE):
        g["kein Software-CPV, also reiner Haendler"] += 1; continue
    kand.append(r)

print("Von 5.386 Firmen\n")
for k, v in g.most_common():
    print(f"  {v:>5}  raus: {k}")
print(f"  {len(kand):>5}  SYSTEMHAUS-KANDIDATEN\n")

ARPA = {"Starter": 99, "Team": 299, "Scale": 499}
plan = collections.Counter()
for r in kand:
    pj = r["zuschlaege"] / MONATE * 12
    ab = r["auftraggeber_anzahl"]
    r["plan"] = "Scale" if (pj >= 8 or ab >= 8) else ("Team" if (pj >= 3 or ab >= 3)
                                                      else "Starter")
    r["aktiv"] = r["letzter"] >= "2025-10-01"
    plan[r["plan"]] += 1

mrr = sum(ARPA[p] * v for p, v in plan.items())
print("Plan nach Aktivitaet und Reichweite\n")
for p in ("Scale", "Team", "Starter"):
    print(f"  {p:<9}{plan[p]:>5} Firmen   {ARPA[p]:>4} EUR/Mo")
print(f"\n  theoretisches Segment-MRR: {mrr:,} EUR")
aktiv = [r for r in kand if r["aktiv"]]
print(f"  aktiv (Zuschlag in 12 Monaten): {len(aktiv)}, verstummt: {len(kand)-len(aktiv)}\n")

kand.sort(key=lambda r: (-r["zuschlaege"], -r["auftraggeber_anzahl"]))
print("Top 35 Systemhaeuser\n")
for r in kand[:35]:
    a = "aktiv" if r["aktiv"] else "still"
    print(f"  {r['zuschlaege']:>3}x {r['plan']:<8}{r['name'][:42]:<44}"
          f"{r['ort'][:16]:<18}{r['auftraggeber_anzahl']:>3} AG  {a}")

json.dump({"systemhaeuser": kand},
          open(os.path.expanduser("~/Job finding/icp_systemhaeuser.json"), "w",
               encoding="utf-8"), ensure_ascii=False)
print(f"\n{len(kand)} geschrieben")
