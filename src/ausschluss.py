# -*- coding: utf-8 -*-
"""Wer kein Kunde ist, und warum. Eine Stelle, drei Verwender.

Vorher stand diese Liste zweimal da, in longlist1_csv.py und in enrich.py, und
in signal_engine.py gar nicht. Ergebnis: Longlist 1 hat Lufthansa Technik,
DXC und Rohde & Schwarz korrekt aussortiert, Longlist 2 hat sie weiter
ausgegeben, weil dort nur die Domain geprueft wurde. Eine Regel, die nicht an
einer Stelle steht, gilt irgendwann nicht mehr ueberall.
"""
import re

RAUSCHEN = re.compile(
    r"(?i)^("
    # Hersteller. Ihr Produkt steht oft namentlich in der Ausschreibung,
    # sie bieten nicht darauf, sie werden hineingeschrieben.
    r"philips|nec deutschland|dr[aä]ger|frequentis|abb ag|netapp|"
    r"conrad electronic|siemens|canon|ricoh|kyocera|xerox|lenovo|dell|"
    r"hewlett|fujitsu|cisco|ibm|oracle|sap |microsoft|honeywell|swarco|"
    r"gantner electronic|eos gmbh|carl zeiss|schenker technologies|"
    r"scientific games|psi software|keysight|rohde ?& ?schwarz|"
    # Druck und Output-Management. Dieselbe Begruendung wie Kyocera und Xerox.
    r"ta triumph-?adler|triumph-?adler|x-nrw|"
    # Konzerne, Telkos und Staatsbetriebe. Eigenes Vergabeteam, anderes Geschaeft.
    r"1&1|telekom|t-systems|dxc|spie|first data|atos|lufthansa|"
    r"bundesdruckerei|gelsen-net|"
    # Tochter einer Firma, die ich schon ausschliesse.
    r"s\.i\.g\.|comparex|"
    # Reiner Softwarehersteller oder Haendler, kein Integrator.
    r"set gmbh|afb gemeinn[uü]tzige|"
    # Gar kein Systemhaus. Beim Pruefen der Webseiten aufgefallen.
    r"dr\.?-?ing\.? paul christiani|urban lighting|rud\.? otto meyer|"
    r"vs vereinigte spezialm[oö]belfabriken|lur sl|fs elektronik|"
    r"arnulf betzold|sonah|rescuetrack|epa-cc|lep ag|ict ag|we are xr|"
    r"steckerfertig|harich|"
    # Ausland. Der Case fragt nach deutschen Systemhaeusern.
    r"tradex systems|trapeze switzerland|cloudferro|vshn|telematix"
    r")")

GRUENDE = [
    (r"(?i)^(philips|nec deutschland|dr[aä]ger|frequentis|abb|netapp|"
     r"conrad|siemens|canon|ricoh|kyocera|xerox|lenovo|dell|hewlett|fujitsu|"
     r"cisco|ibm|oracle|sap |microsoft|honeywell|swarco|gantner|eos gmbh|"
     r"carl zeiss|schenker|scientific games|psi software|keysight|"
     r"rohde ?& ?schwarz)",
     "Hersteller. Steht oft namentlich in der Ausschreibung, bietet nicht darauf"),
    (r"(?i)^(ta triumph-?adler|triumph-?adler|x-nrw)",
     "Druck und Output-Management, wie Kyocera, Xerox und Ricoh"),
    (r"(?i)^(1&1|telekom|t-systems|dxc|spie|first data|atos|lufthansa|"
     r"bundesdruckerei|gelsen-net)",
     "Konzern, Telko oder Staatsbetrieb. Eigenes Vergabeteam"),
    (r"(?i)^(s\.i\.g\.|comparex)",
     "Tochter einer bereits ausgeschlossenen Firma (Bechtle, SoftwareONE)"),
    (r"(?i)^(set gmbh|afb gemeinn)",
     "Softwarehersteller oder Haendler, kein Integrator"),
    (r"(?i)^(tradex|trapeze switzerland|cloudferro|vshn|telematix|lep ag)",
     "Sitz im Ausland"),
    (r"(?i)^harich",
     "Werkzeug- und Maschinenhandel. Website verkauft Fraes-, Dreh- und "
     "Schleifmaschinen, keine IT"),
    (r"(?i)^(vs vereinigte|lur sl|fs elektronik|arnulf betzold|sonah|"
     r"rescuetrack|epa-cc|ict ag|we are xr|dr\.?-?ing\.? paul christiani|"
     r"urban lighting|rud\.? otto meyer|steckerfertig)",
     "Keine IT. Moebel, Kabel, Schulbedarf, Sensorik, AV-Technik oder Pflegesoftware"),
]
GRUENDE = [(re.compile(p), g) for p, g in GRUENDE]


def ausgeschlossen(name):
    return bool(RAUSCHEN.search(name or ""))


def grund(name):
    for p, g in GRUENDE:
        if p.search(name or ""):
            return g
    return "Hersteller, Konzern oder kein Systemhaus"
