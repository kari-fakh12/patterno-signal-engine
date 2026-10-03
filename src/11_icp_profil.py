# -*- coding: utf-8 -*-
"""Wer sind die 323? Fakten fuer ein ICP-Profil, nicht fuer eine Methodenbeschreibung."""
import json, os, re, collections, statistics

s = json.load(open(os.path.expanduser("~/Job finding/icp_systemhaeuser.json"),
                   encoding="utf-8"))["systemhaeuser"]
print(f"{len(s)} Systemhaeuser\n")

# Auftraggeber-Typen
TYP = [
    ("Kommune", r"(?i)^stadt|^gemeinde|^landkreis|^kreis |^bezirk|magistrat|"
                r"b[uü]rgermeister|kommunal|^stadtverwaltung"),
    ("Hochschule", r"(?i)universit[aä]t|hochschule|fachhochschule|^tu |studierendenwerk"),
    ("Klinik", r"(?i)klinik|krankenhaus|universit[aä]tsmedizin|gesundheit"),
    ("Land", r"(?i)^land |^landes|^freistaat|ministerium|^der senator|^senats|"
             r"regierungspr[aä]sidium|landesamt|landesbetrieb"),
    ("Bund", r"(?i)^bundes|^bmi\b|bundeswehr|bundesamt|bundesanstalt|^bwi\b|"
             r"bundesagentur|^deutsche rentenversicherung"),
    ("Stadtwerke/Verkehr", r"(?i)stadtwerke|verkehrsbetrieb|verkehrsgesellschaft|"
                           r"wasser|energie|entsorgung|abfall"),
    ("Sozial/Kasse", r"(?i)krankenkasse|^aok|^barmer|^tk\b|sozialversicherung|"
                     r"berufsgenossenschaft"),
]
TYPC = [(n, re.compile(p)) for n, p in TYP]

ag_typ = collections.Counter()
for r in s:
    for a in r.get("auftraggeber_top") or []:
        hit = False
        for n, p in TYPC:
            if p.search(a):
                ag_typ[n] += 1
                hit = True
                break
        if not hit:
            ag_typ["sonstige"] += 1

print("Welche Auftraggeber bedienen sie (aus den Top-3 je Firma)\n")
tot = sum(ag_typ.values())
for n, v in ag_typ.most_common():
    print(f"  {n:<22}{v:>5}  {v/tot*100:>5.1f}%")

# Geografie
BL = {
    "Bayern": "münchen|nürnberg|augsburg|würzburg|regensburg|ingolstadt|erlangen|fürth|bamberg|bayreuth|baiersdorf|jettingen|grasbrunn|ottobrunn|winhöring|kirchheim|garching|ismaning|rosenheim|deggendorf|alsfeld",
    "NRW": "köln|düsseldorf|dortmund|essen|duisburg|bochum|wuppertal|bielefeld|bonn|münster|aachen|gelsenkirchen|mönchengladbach|krefeld|oberhausen|hagen|hamm|siegen|paderborn|neuss|leverkusen|solingen|herne|witten|iserlohn|gescher|eschweiler|brilon|lippstadt|erwitte|gummersbach|hattingen|wiehl|meerbusch|langenfeld|kerpen|bottrop|recklinghausen|horstmar|bönen",
    "Baden-Württemberg": "stuttgart|karlsruhe|mannheim|freiburg|heidelberg|heilbronn|ulm|pforzheim|reutlingen|esslingen|ludwigsburg|tübingen|konstanz|metzingen|eislingen|möglingen|leinfelden|kenzingen|bensheim|süßen|glatten|ostfildern|leonberg|backnang|hemmingen|wolpertshausen|ladenburg",
    "Berlin": "berlin",
    "Hamburg": "hamburg|reinbek",
    "Hessen": "frankfurt|wiesbaden|kassel|darmstadt|offenbach|hanau|gießen|marburg|dietzenbach|dreieich|eschborn|langen|bad homburg|wölfersheim|leuterod",
    "Niedersachsen": "hannover|braunschweig|osnabrück|oldenburg|göttingen|wolfsburg|hildesheim|springe|lohne|achim|wolfenbüttel|barleben",
    "Sachsen": "dresden|leipzig|chemnitz|zwickau|görlitz",
    "Bremen": "bremen|bremerhaven",
    "Rheinland-Pfalz": "mainz|ludwigshafen|koblenz|trier|kaiserslautern|züsch|frankenthal|viernheim",
    "Schleswig-Holstein": "kiel|lübeck|flensburg|neumünster",
    "Brandenburg": "potsdam|cottbus|schönefeld",
    "Sachsen-Anhalt": "magdeburg|halle|dessau",
    "Thüringen": "erfurt|jena|gera|nordhausen",
    "Mecklenburg-Vorpommern": "rostock|schwerin|stralsund|bad doberan",
    "Saarland": "saarbrücken|bexbach",
}
BLC = {k: re.compile(v) for k, v in BL.items()}
geo = collections.Counter()
for r in s:
    o = (r["ort"] or "").lower()
    hit = False
    for k, p in BLC.items():
        if p.search(o):
            geo[k] += 1
            hit = True
            break
    if not hit:
        geo["unklar"] += 1

print("\nWo sitzen sie\n")
for k, v in geo.most_common():
    print(f"  {k:<24}{v:>4}  {'#' * min(v, 50)}")

# Werte
werte = [r["wert_summe"] for r in s if r.get("wert_summe")]
print(f"\nAuftragsvolumen (Summe je Firma, {len(werte)} von {len(s)} haben Werte)")
if werte:
    werte.sort()
    print(f"  Median:  {statistics.median(werte):>15,.0f} EUR")
    print(f"  25%:     {werte[len(werte)//4]:>15,.0f} EUR")
    print(f"  75%:     {werte[3*len(werte)//4]:>15,.0f} EUR")

z = [r["zuschlaege"] for r in s]
a = [r["auftraggeber_anzahl"] for r in s]
print(f"\nZuschlaege: Median {statistics.median(z):.0f}, "
      f"Spanne {min(z)} bis {max(z)}")
print(f"Verschiedene Auftraggeber: Median {statistics.median(a):.0f}, "
      f"Spanne {min(a)} bis {max(a)}")
