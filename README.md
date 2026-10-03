# Public-Sector-Signal-Engine

Zwei Listen und ein Grund, heute anzurufen.

**Longlist 1** sind deutsche IT-Systemhäuser, die seit 2024 nachweislich einen
öffentlichen Auftrag gewonnen haben **und** deren Webseite über das Impressum
bestätigt ist. **Longlist 2** sagt, bei welchen davon gerade etwas passiert, mit
Datum und Quelle.

Keine bezahlten Tools. Keine Credits. Python-Standardbibliothek, zwei offene
APIs und das Impressum, das in Deutschland Pflicht ist.

```
pip install -r requirements.txt   # leer, es gibt keine Abhängigkeiten
```

**Die wichtigste Zahl zuerst, und sie ist nicht von mir geprüft, sondern gegen
die Quelle:** alle **1.477 Quellenlinks** in beiden Longlists wurden gegen das
TED-XML geprüft, nicht gegen die API-Felder. In allen 1.477 Fällen ist die
genannte Firma der **Gewinner** der Bekanntmachung, nicht nur ein Bieter.
Keine falsche Zuordnung, kein toter Link.

Das ist die Zahl, die den Rest trägt. Wenn sie nicht stimmt, ist alles andere
egal.

---

## Der ICP in einem Satz

> Ein regionales IT-Systemhaus, das Hardware beschafft und betreibt, seit 2024
> zwischen zwei und dreißig öffentliche Aufträge gewonnen hat, überwiegend von
> Städten, Hochschulen und Kliniken, und das noch kein eigenes Vergabeteam
> beschäftigt.

Median: 4 Zuschläge, 3 verschiedene Auftraggeber, 2 Mio. Euro Volumen in zwei
Jahren. Auftraggeber sind zu 26 Prozent Kommunen, zu 10 Prozent Hochschulen, zu
9 Prozent Kliniken. Der Bund spielt mit 3 Prozent kaum eine Rolle. Größter Markt
ist NRW mit 55 Firmen, dann Bayern mit 26.

**Die Obergrenze von 30 Zuschlägen ist geraten? Nein, sie steht in eurer
Preisliste.** Scale erlaubt 50 Qualifizierungen im Monat. Bechtle gewinnt 15 pro
Monat und prüft davor vielleicht 200. Der größte Plan reicht dafür nicht, also
ist Bechtle kein Kunde. Das ist Rechnen, nicht Meinung.

---

## Lauf

Die Nummern im Dateinamen sind die Reihenfolge.

```bash
python3 src/01_ted_zuschlaege_ziehen.py     # 13.066 Zuschläge aus TED
python3 src/02_gewinner_aggregieren.py      # 5.386 Gewinner, normalisiert
python3 src/03_icp_filter.py                # 323 Systemhäuser
python3 src/04_domains_raten.py             # Domain raten und belegen
python3 src/05_domains_suche.py             # Rest über Suche
python3 src/06_longlist1_export.py          # data/longlist1_markt.csv
python3 src/07_signal_engine.py             # data/longlist2_signale.csv
python3 src/08_enrichment_waterfall.py      # Kontakte, Telefon, Mailmuster
python3 src/09_enrichment_nachlauf.py       # Impressum über sitemap.xml
python3 src/10_mailmuster.py                # Mailmuster verfeinern
```

`07_signal_engine.py --cache` nutzt die gespeicherten TED-Antworten,
`--reset` leert den State.

---

## Ergebnis

| Datei | Inhalt | Umfang |
|---|---|---|
| `data/longlist1_markt.csv` | Der Markt. Tier, Plan-Vorschlag, Beleg, Confidence je Feld | **148 Firmen** |
| `data/longlist2_signale.csv` | Das Timing. Signal, Datum, Quelle, Score, Why-now | **245 Signale bei 95 Firmen** |
| `data/enrichment_longlist1_alle.csv` | Kontakte für **alle 148**, nicht nur die Spitze | 148 Firmen, 184 Personen |
| `data/enrichment_longlist1_top40.csv` | Top 40 mit Kontakten, Telefon, Mailstatus | 40 Firmen, 51 Personen |
| `data/enrichment_longlist2_top20.csv` | Top 20 nach Score, mit Why-now-Satz für den SDR | 20 Firmen, 24 Personen |
| `data/pruefen_domain_offen.csv` | **Nicht Teil der Abgabe.** Die 175 aussortierten Firmen mit Grund | 175 Firmen |

**Tier in Longlist 1:**

| Tier | Firmen | Heißt |
|---|---|---|
| 1 Anlass | **95** | Fit belegt und ein datiertes Ereignis jetzt |
| 2 Lücke | **34** | Fit belegt, kein Ereignis |
| 3 Still | **19** | War aktiv, seit zwölf Monaten nichts |

Die Stufen heißen nach dem ersten Satz des SDR, nicht nach Buchstaben. "Tier A"
sagt niemandem etwas, "Anlass" sagt ihm, dass es ein Ereignis gibt.

**129 Firmen kann der Vertrieb heute anrufen, 95 davon mit einem Datum im Satz.**

Die Aufgabe fragt in 1.1 nach Kontakten für die Liste, nicht für die Spitze.
Deshalb ist **jede** der 148 Firmen angereichert und nicht nur die 60 aus den
beiden Top-Dateien. Jede Firma wird einmal geholt, die drei Dateien sind
Sichten auf einen Lauf.

### Warum nur 148 und nicht 323

Der CPV-Filter lässt 323 Firmen übrig. In der Abgabe stehen 148. Der
Unterschied ist eine Entscheidung, keine Datenlücke:

**In die Liste kommt nur, wessen Webseite über das Impressum bestätigt ist.**
Nicht als Tier 4 mitlaufen, sondern draußen.

| Aussortiert | Firmen | Warum |
|---|---|---|
| Domain nicht belegt | 122 | Impressum nicht lesbar, Kürzel-Name, oder Seite nennt eine andere Firma |
| Kein Systemhaus | 53 | Hersteller, Konzern, Staatsbetrieb, Ausland, Möbel, Kabel |

**Der Preis dieser Regel ist hoch und soll hier stehen:** die 122 haben
belegte TED-Zuschläge. Es sind echte Systemhäuser, die echte öffentliche
Aufträge gewonnen haben. Sie fehlen allein deshalb, weil ich ihre Webseite
nicht maschinell bestätigen konnte.

**Der Grund dafür ist verkäuferisch, nicht technisch.** Ihr prüft
stichprobenartig. Eine Liste, in der jede Zeile einen Test übersteht, ist mehr
wert als eine längere mit einem Zweifel-Eimer. Und ein SDR, der die falsche
Firma anruft, verliert das Gespräch im ersten Satz.

Nichts ist gelöscht. Die 172 stehen mit Begründung je Zeile in
`data/pruefen_domain_offen.csv`. Wer in sechs Monaten fragt, warum Bechtle oder
Dräger fehlt, findet die Antwort in der Datei statt in jemandes Kopf.

**Daraus folgt eine Zahl, die ich nicht liefere:** 148 ist nicht die Marktgröße.
Die Marktgröße liegt über 323, weil 88 Prozent der Vergaben unterhalb der
EU-Schwelle gar nicht in TED stehen. 148 ist die Zahl der Firmen, die **heute
anrufbar** sind.

---

## Die Signale

| | Signal | Quelle | In der Abgabe |
|---|---|---|---|
| **S2** | Vertrag läuft aus | `contract-duration-end-date-lot` in der Zuschlagsbekanntmachung | 25 |
| **S4** | Ausschreibung beim bekannten Auftraggeber | offene Bekanntmachungen der letzten 56 Tage | 219 |
| **S1** | Stellenanzeige Vergabe oder Bid Management | Bundesagentur für Arbeit | 1 |

S2 ist das schärfste: der Vertrag endet, die Neuausschreibung kommt, und der
Gewinner muss ihn verteidigen. Das ist ein Termin, kein Thema.

### Jeder Satz trägt seinen Beleg

Ein S4-Satz lautet nicht "dort habt ihr schon geliefert", sondern:

> Fraunhofer-Gesellschaft, Einkauf B12 schreibt gerade Serversystem für
> KI-Workloads aus. Frist 16.10.2026. Dort habt ihr 09/2025 schon geliefert
> (ted.europa.eu/de/notice/622533-2025/pdf).

Die Zeile hat dafür eigene Spalten: `Auftraggeber_Treffer`,
`Beleg_fruehererer_Auftrag`, `Beleg_Rolle`, `Beleg_Mitauftraggeber`. Der
Vertrieb kann den Satz vor dem Anruf selbst nachlesen.

**Gewonnen und geboten sind zwei verschiedene Sätze.** TED nennt beides:
Gewinner und Bieter. Wer geboten und verloren hat, bekommt "dort habt ihr schon
**geboten**", nicht "geliefert". Das ist nicht nur korrekt, es ist oft der
bessere Einstieg.

**Gegengeprüft:** alle 219 S4-Zeilen wurden gegen das XML der zitierten
Bekanntmachung geprüft. In jedem Fall existiert die Bekanntmachung, der genannte
Auftraggeber kommt darin vor, und die Firma hat genau die Rolle, die in der
Zeile steht. Kein "geliefert" ohne Zuschlag.

**State:** `signal_state.json` merkt jedes Tripel aus Firma, Signalart und
Bekanntmachungsnummer. Der zweite Lauf findet dieselben Signale und gibt
**0 neue** aus. Die CSV behält das volle Bild, mit einer Spalte
`Neu_in_diesem_Lauf`.

### Ein Signal habe ich weggeworfen

Gleiche CPV-Gruppe plus gleiches Bundesland, also "in eurer Region wird etwas in
eurem Bereich ausgeschrieben". Ergebnis: **16.216 Treffer, bei einer Firma 134
gleichzeitig.**

Das ist kein Signal, das ist ein Abo. Und es ist genau das CPV-Raten, das ihr in
der Aufgabe kritisiert, nur auf der Firmenseite statt auf der Ausschreibungsseite.
Der Zähler steht noch im Code, damit die Zahl nachprüfbar bleibt. Ausgegeben wird
sie nicht.

---

## Trefferquoten, ehrlich

Enrichment ohne Budget, über Startseite, Impressum und Teamseiten.

| Was | alle 148 | Top 40 | Top 20 |
|---|---|---|---|
| Website erreichbar | 148 (100 %) | 40 (100 %) | 20 (100 %) |
| **Zentrale, wörtlich auf der Seite** | **127 (86 %)** | 38 (95 %) | 17 (85 %) |
| allgemeine Adresse (info@, kontakt@) | 108 (73 %) | 30 (75 %) | 12 (60 %) |
| **mindestens eine Person mit belegter Rolle** | **107 (72 %)** | 31 (78 %) | 13 (65 %) |
| Personen insgesamt | **184** | 51 | 24 |
| davon Geschäftsführung | 161 | 44 | 20 |
| davon Vertriebsleitung | 22 | 7 | 3 |
| davon **Champion** (Vergabe, Angebot, Bid) | **1** | 0 | 1 |
| Personen mit eigener Durchwahl oder Mobil | 4 | 3 | 0 |
| persönliche Mailadresse, wörtlich belegt | 6 | 3 | 0 |
| Person ohne Fundstelle | **0** | 0 | 0 |

### Durchwahl oder Zentrale, die Frage aus 1.2

Die ehrliche Antwort hat zwei Teile. **127 Zentralen, 4 eigene Nummern**
(3 Durchwahlen, 1 Mobil). Klassifiziert wird über die Nummer selbst: wer
mindestens acht Stellen mit der Zentrale teilt und anders endet, hat eine
Durchwahl, +4915x bis +4917x ist mobil.

Dass es nur 4 sind, liegt an der Quelle, nicht am Verfahren. 161 der 184
Personen stehen im Impressum, und ein Impressum nennt die Zentrale. Eine
Durchwahl steht auf der Ansprechpartnerseite, und die haben die meisten
Mittelständler nicht.

**Diese Zeile stand vorher auf 0 Prozent, mit der Begründung "steht in keinem
Impressum".** Das war wahr für das Impressum und falsch für die Firma: bei
RapidMax stehen Durchwahl 118 und 202 direkt neben den Namen. Der Fehler war
mein Leseverfahren, nicht die Datenlage. Siehe unten.

### Der Fehler, der zwei Zahlen gleichzeitig kaputt gemacht hat

Um zu verhindern, dass jemand die Rolle seines Nachbarn erbt, hatte ich
verlangt: **Rolle und Name in derselben Zeile.** Damit fielen alle
Ansprechpartner-Karten aus, denn dort steht der Name in Zeile eins, die Rolle
in Zeile zwei und das Telefon in Zeile drei. Ergebnis: 164 von 167 Kontakten
kamen aus dem Impressum, die Teamseiten waren praktisch blind.

Die Lösung ist der **Block nach vorne**: ab dem Namen bis zum nächsten Namen.
Was dazwischen steht, gehört zu dieser Person. Nach hinten wird nie gelesen,
deshalb kann niemand die Rolle des Vorgängers erben, was der ursprüngliche
Fehler war.

Was dieser eine Fix bewegt hat:

| | vorher | nachher |
|---|---|---|
| Personen | 167 | **184** |
| Vertriebsleitung | 7 | **22** |
| Champion | 0 | **1** |
| eigene Durchwahl | 0 | **4** |
| persönliche Mailadresse | 1 | **6** |

Die Erkennung war nie kaputt. Ich habe die Seiten nicht gelesen, auf denen
diese Rollen stehen.

### Die Regel dahinter: nur was belegt ist

Eine Person steht nur in der Datei, wenn **alle drei** Bedingungen gelten:

1. Der Name steht auf der Seite der Firma **unter einem ausdrücklichen Label**
   (Geschäftsführung, Vorstand, Inhaber, vertreten durch, Prokurist) oder mit
   seiner Rolle **in derselben Zeile**
2. Die Domain ist durch das Impressum belegt
3. Die **URL der Fundstelle** steht in der Zeile

Mailadressen und Telefonnummern stehen nur dann drin, wenn sie **wörtlich** auf
der zitierten Seite auftauchen. Es gibt keine abgeleiteten Adressen mehr, auch
nicht mit dem Hinweis "nicht verifiziert".

Dazu eine vierte Regel, die erst durch einen Fehler entstanden ist: **Personen
werden nur auf Seiten gesucht, die über die Firma selbst sprechen.** Impressum,
Kontakt, Team, Ansprechpartner, Über uns, Unternehmen, Management, Vorstand.
Nicht auf Produkt-, Lösungs-, Referenz-, News-, Presse- oder Karriereseiten.

Der Grund: bei einem Anbieter standen ein Orthopäde und eine Neurologin in der
Kontaktliste, mit "Inhaber" als Titel. Beide loben das Produkt auf einer
Lösungsseite und sind Inhaber ihrer eigenen Praxis. Das sind Kundenstimmen,
keine Mitarbeiter. Bei einem anderen standen zwei Personen aus einer
Pressemeldung über eine **andere** Firma in der Zeile.

**Was die Regeln weggeworfen haben, als Bilanz statt als Behauptung:**

| Grund | Anzahl |
|---|---|
| keine Rolle im Block dieser Person | 915 |
| kein Personenname, sondern Seitentext | 141 |
| Seite war keine Team- oder Kontaktseite | 89 |
| Personalie oder Pressetext | 5 |
| Text nennt eine andere Firma | 1 |
| **behalten** | **184** |

Auf einer Firmenwebsite stehen tausende großgeschriebene Wortpaare, und fast
keines davon ist ein Mensch mit einer Rolle. Eine frühere Fassung hat davon
rund 30 durchgelassen, darunter "Typische Fragen", "Key Account" und "Digitale
Verwaltung", und einer bekam die abgeleitete Adresse `typische.fragen@`.

**41 der 148 Firmen haben keinen Kontakt.** Gründe, gezählt:

| Grund | Firmen |
|---|---|
| Seiten gelesen, kein Name mit belegter Rolle | 39 |
| keine Team- oder Kontaktseite gefunden | 1 |
| Impressum nicht lesbar | 1 |

Bei diesen 41 steht die Telefonnummer der Zentrale und sonst nichts. Das ist
weniger, als eine Kaufliste verspricht, und es ist nachprüfbar.

### Ein Fehler, den man in Daten nicht sieht

Zwei Namen waren falsch und sahen richtig aus: "Hans-Peter Hellmann" stand als
"Peter Hellmann" in der Datei, "Kai-Uwe Schurig" als "Uwe Schurig". Mein
Namensmuster erlaubte keinen Bindestrich im Vornamen.

Das ist der gefährlichste Fehlertyp in einer Kontaktliste. Eine fehlende Zeile
merkt man, eine falsche Telefonnummer merkt man beim Wählen. Einen halben
Vornamen merkt man erst, wenn der Angerufene ihn korrigiert. Gefunden wurde er,
weil alle 184 Namen gegen ihre Fundstelle geprüft wurden, nicht weil er
aufgefallen wäre.

**Die 0 Prozent beim Champion sind die ehrlichste Zahl im Dokument.** In einer
früheren Fassung stand dort 5 Prozent. Diese Treffer waren keine Menschen:
"Typische Fragen", "Key Account", "Digitale Verwaltung", "Technische Tiefe".
Mein Parser hatte Überschriften für Personen gehalten, einer davon bekam die
abgeleitete Adresse `typische.fragen@...`. Rund 30 von 95 Kontakten waren so
entstanden. Nach dem Filter bleiben echte Namen, und der Champion ist nicht
dabei.

Keine Zeile ist geraten. Eine Mailadresse, die ich nicht geprüft habe, steht als
`abgeleitet, nicht verifiziert` in der Datei und sieht nicht aus wie eine
geprüfte. Jede Zahl hier ist nachrechenbar, die Skripte liegen daneben.

**Was das heißt:** die Website liefert zuverlässig den **Geschäftsführer und die
Telefonnummer**. Sie liefert fast nie den **Champion**, also die Person, die
heute die Ausschreibungen sucht. Die sitzt auf LinkedIn, nicht im Impressum.

### Der Nebeneffekt, der mehr wert ist als die Kontakte

Der Rechtsname im Impressum prüft die geratene Domain. Das war als Kontrolle
gedacht und hat etwas anderes gefunden: **Firmen, die es unter diesem Namen
nicht mehr gibt.**

| TED-Gewinner 2024 | Impressum 2026 heute |
|---|---|
| WTG communication GmbH | T&N AG |
| Systempartner IT-Vertriebs GmbH & Co. KG | DNS GmbH |
| DATAGROUP Stuttgart GmbH | DATAGROUP SE |
| H&G Hansen & Gieraths EDV Vertriebsgesellschaft mbH | Dr. Hansen EDV Consulting GmbH |

Die ersten drei sind Übernahmen und Verschmelzungen, der vierte ist eine falsch
geratene Domain. **Beides muss man sehen, bevor ein SDR anruft.** Wer die
Tochter anspricht, die seit einem Jahr zur Mutter gehört, hat das Gespräch
verloren, bevor es anfängt.

Der erste Vergleich war zu grob: er akzeptierte "Hansen & Gieraths" und
"Dr. Hansen EDV Consulting" als gleich, weil beide das Wort "Hansen" enthalten.
Ein gemeinsames Wort ist kein Beleg. Jetzt muss das kennzeichnende Wort stimmen
**und** die Überschneidung mindestens die Hälfte abdecken. Gefunden habe ich den
Fehler beim Lesen der CSV, nicht durch einen Test. Deshalb liest man seine
eigenen Daten.

**Genau da, und nur da, ist Geld nötig.** Firmendaten sind kostenlos: TED ist ein
Rechtsakt, das Impressum ist Pflicht. Personendaten sind es nicht. Zum Vergleich,
gerechnet statt geschätzt: ein angebundener E-Mail-Finder kostet 15 Credits pro
Zeile, 40 Accounts also 600. Verfügbares Guthaben: 80. Deshalb liegt in diesem
Repo der kostenlose Pfad, vollständig und mit gemessenen Quoten, statt ein halb
befüllter bezahlter.

---

## Was die Liste nicht kann

**88 Prozent aller deutschen Vergaben liegen unter der EU-Schwelle und damit
nicht in TED.** Das ist eure Zahl, aus eurem Blog. Ich sehe die obersten
12 Prozent.

Wichtig: die 88 Prozent zählen **Aufträge, nicht Firmen**. Viele der 323 bieten
auch unterhalb der Schwelle, sie haben nur zusätzlich einmal etwas Großes
gewonnen. Unsichtbar ist nur die Firma, die nie oberhalb der Schwelle gewonnen hat.

Zwei Tests, die die Liste nicht besteht, beide in `docs/methode.md` gerechnet:

- **Oracom**, euer einziger öffentlich genannter Kunde, kommt in 5.386 Gewinnern
  null Mal vor. Grund: TED nennt Gewinner, euer Kunde ist Bieter
- **Von 22 namentlich genannten Kunden eurer Wettbewerber steht genau einer in
  meinen 323.** 4,5 Prozent. Der Filter ist logisch sauber und empirisch kaum
  validiert, und das sollte so dastehen

Dazu: 33 Domains nicht belegbar, 1.545 Bekanntmachungen ohne auslesbaren
Gewinner, etwa 10 Prozent Restrauschen aus Herstellern.

**Der Case sagt Präzision vor Volumen. Das ist der Tausch, den ich bewusst
gemacht habe.**

---

## Was ich als nächstes bauen würde

In dieser Reihenfolge, nach Nutzen pro Stunde:

1. **Referenzseiten der 323 auslesen.** Wer öffentliche Auftraggeber nennt, ist
   Kandidat. Erreicht die Firmen, die unterhalb der Schwelle bieten
2. **Kundenseiten der Wettbewerber auslesen.** bluechip, KeepBlue und Venn
   Telecom zahlen nachweislich für so ein Werkzeug und stehen nicht in TED. Eine
   öffentliche Liste validierter Käufer, die niemand als Quelle nutzt
3. **Vergabekammer-Entscheidungen.** Die Antragstellerin steht namentlich drin:
   hat geboten, verloren, sich beschwert. Heißester Lead, den es gibt
4. **Präqualifizierungsverzeichnisse.** Findet die Firma, die sich auf das erste
   Gebot vorbereitet, bevor sie zum ersten Mal bietet

Erst danach die regionalen Portale. Die machen die meiste Arbeit und sind genau
das, was ihr bereits habt.

---

Details zur Methode, zu den Fallen in der TED-API und zu beiden gescheiterten
Tests: **`docs/methode.md`**
