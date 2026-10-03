# Methode

Warum die Liste so aussieht, wie sie aussieht. Und was sie nicht kann.

---

## 1. Die Quelle

**Ein Zuschlag ist öffentlich, weil das Gesetz es verlangt.** Jede Vergabestelle
muss bekannt machen, wer den Auftrag bekommen hat. Oberhalb der EU-Schwelle
landet diese Bekanntmachung in TED, der EU-Vergabedatenbank mit offener API.

- **13.066** deutsche IT-Zuschläge seit Januar 2024
- Filter: `notice-type IN (can-standard)`, `buyer-country IN (DEU)`,
  CPV 72, 48, 302, 516
- **5.386** verschiedene Gewinner
- Jede Zeile mit TED-Nummer und PDF-Link

Keine Annahme. Wenn Computacenter auf 202 Bekanntmachungen steht, ist das ein
Rechtsakt mit Beleg.

### Zwei Fallen in der API

**`fields` ist Pflicht.** Fehlt es, kommt nur `Validation error`, ohne zu sagen
warum. Ein ungültiger Feldname gibt dieselbe Meldung. Deshalb testet
`src/00_felder_pruefen.py` jedes Feld einzeln, bevor der große Zug läuft.

**Die API verrät ihre Feldnamen selbst.** Fragt man absichtlich nach einem Feld,
das es nicht gibt, listet die Fehlermeldung alle 1.830 erlaubten Namen. So habe
ich `contract-duration-end-date-lot` gefunden, und damit erst das Signal
"Vertrag läuft aus".

---

## 2. Der Filter

Ein Systemhaus muss **beides** gewonnen haben: Hardware (CPV 30x, 32x, 516)
**und** Software oder Dienstleistung (48x, 72x).

Reine Softwarehäuser haben nur das zweite. Händler nur das erste. Berater haben
794. Alle drei fallen damit automatisch raus, ohne dass ich einen Firmennamen
lese.

| Schritt | raus |
|---|---|
| nur 1 Zuschlag | 3.559 |
| keine Hardware-CPV | 996 |
| keine Software-CPV | 165 |
| Beratung | 170 |
| Konzerne, Hersteller, Telkos | 97 |
| über 30 Zuschläge | 48 |
| Ausland, Personaldienstleister | 28 |
| **bleiben** | **323** |

Zwei Treffer heißen wörtlich Systemhaus: Albacon Systemhaus und
SHD System-Haus-Dresden. Der CPV-Test hat sie gefunden, ohne einen Namen zu lesen.

### Zu eurem Satz "kein CPV-Raten"

Ihr kritisiert CPV als Mittel, **Ausschreibungen zu finden**. Da ist Volltext
besser, da stimme ich zu.

Ich nutze CPV, um **Firmen danach zu sortieren, was sie bereits gewonnen haben**.
Rückspiegel statt Suchfilter. Das ist eine andere Aufgabe.

### Die Obergrenze kommt aus eurer Preisliste

Eine Qualifizierung ist bei euch eine geprüfte Ausschreibung. Starter erlaubt 3
im Monat, Scale 50. Euer Kunde prüft also 3 bis 50 Ausschreibungen monatlich.

Bechtle gewinnt 328 Aufträge in 21 Monaten, rund 15 pro Monat. Um 15 zu gewinnen,
bieten sie auf etwa 60 und prüfen davor vielleicht 200. Der größte Plan erlaubt 50.

Deshalb liegt die Grenze bei **30 Zuschlägen** im Zeitraum, rund 1,4 Gewinne im
Monat. Das ist keine Schätzung, das ist eure Preisliste.

---

## 3. Die Domain, ohne Budget

TED nennt den Gewinner als Freitext. Keine Domain, keine Registernummer.
Drei Stufen:

1. **Muster raten.** Rechtsform weg, Füllwörter weg, `.de` dran.
   `sysGen GmbH` wird `sysgen.de`
2. **Varianten testen.** Bindestrich, zusammengeschrieben, `.com`, `.eu`
3. **Suche**, für den Rest

Jede Stufe prüft danach: lebt die Seite, und **steht der Firmenname darauf**.
Parkseiten und Domain-Verkaufsseiten werden erkannt und verworfen.

| Confidence | Firmen | Bedeutung |
|---|---|---|
| **belegt** | 158 | Rechtsname im Impressum passt zum Gewinnernamen. Nur diese gehen raus |
| geraten | 17 | Kein lesbares Impressum, Name auf der Seite. Nicht anrufen |
| fraglich | 13 | Seite nennt eine andere Firma |
| offen | 135 | Nicht belegbar |

### Die erste Fassung hat geraten und sich selbst bestätigt

Sie prüfte, ob der Firmenname irgendwo auf der Seite steht. Das klingt
vernünftig und war in rund 40 von 290 Fällen falsch, aus zwei Gründen:

- **Raten aus einem einzelnen Wort.** `aura Computersysteme` wurde `aura.com`,
  ein US-Anbieter für Identitätsschutz. `ergo Computersysteme` wurde `ergo.de`,
  die Versicherung. Dasselbe bei carl, ralf, dirk, tree, rud, kramer, hansen.
  Das Wort steht auf der Seite, also galt es als Treffer
- **Geparkte Domains.** Wer eine Domain verkauft, schreibt den Firmennamen in
  den Titel. Genau die Prüfung, die ich gebaut hatte, hat das bestätigt

Deshalb prüft die Domainstufe jetzt umgekehrt: **Rechtsname aus dem Impressum
lesen und gegen den Gewinnernamen vergleichen.**

Dabei ist mir die Prüfung zweimal um die Ohren geflogen, und beide Fehler sind
lehrreicher als das Ergebnis:

**Zu streng.** Die erste strenge Fassung verwarf 141 Firmen, darunter
WBS IT-Service, PDV-Systemhaus, CES IT-Systemhaus und HKS Systeme, deren
Impressum den Namen exakt nennt. Drei Ursachen: der Extraktor nahm den
**längsten** Firmennamen der Seite (bei datagroup.de ist das "AXA Versicherung
AG", weil ein Impressum weiter unten den Versicherer nennt), der Vergleich hielt
das **längste** Wort für das kennzeichnende (deshalb scheiterte
"secunet Security Networks AG" gegen "secunet AG" am fehlenden "security"), und
Rechtsformen zählten als Namenswörter (deshalb sahen "DATAGROUP SE" und
"DATAGROUP Stuttgart GmbH" wie zwei verschiedene Firmen aus).

**Zu lasch.** Nach der Korrektur galt "aura" gleich "aura" als Beleg. Das ist
wahr und wertlos, weil aura Computersysteme und Aura Sub LLC beide auf "aura"
schrumpfen.

Die Lösung ist zweistufig, und sie ist der Kern dieses Schritts:

1. **Das kennzeichnende Wort ist das erste, nicht das längste.** Firmennamen
   fangen mit dem Namen an und hören mit Beschreibung auf
2. **Teilen zwei Namen nur ein einziges Wort, entscheidet der Ort.** Steht die
   TED-Stadt im Impressum, ist es dieselbe Firma, sonst nicht

Das trennt "SHD System-Haus-Dresden" von "SHD Solutions", was ein
Namensvergleich allein nicht kann. Geprüft habe ich das gegen 27 von Hand
belegte Fälle, bevor der Lauf startete. Die sechs, die der Namensvergleich nicht
entscheiden kann (aura, ergo, SHD Solutions, ]init[, Dr. Hansen, DIE CREW),
fallen alle über den Ort.

**Nebenbefund, der mehr wert ist als die Domain selbst:** der Vergleich findet
Firmen, die es unter diesem Namen nicht mehr gibt. WTG communication ist heute
T&N AG, Systempartner IT-Vertriebs ist DNS GmbH, DATAGROUP Stuttgart gehört zur
DATAGROUP SE. Ein TED-Gewinner von 2024 kann 2026 eine andere Firma sein, und
das muss ein SDR wissen, bevor er anruft.

---

## 4. Die Signale

Drei Signale, alle mit Datum und Quelle, alle reproduzierbar.

| | Signal | Woher | Treffer |
|---|---|---|---|
| **S2** | Vertrag läuft aus | `contract-duration-end-date-lot` aus der Zuschlagsbekanntmachung | 72 |
| **S4** | Ausschreibung beim bekannten Auftraggeber | offene `cn-standard` der letzten 56 Tage, Auftraggeber stimmt mit einem früheren überein | 357 |
| **S1** | Stellenanzeige Vergabe oder Bid Management | Bundesagentur für Arbeit, Jobsuche-API | 5 |

**S2 ist das schärfste.** Der Vertrag endet, die Neuausschreibung kommt, und der
Gewinner muss ihn verteidigen. Das ist ein Termin, kein Thema.

**S4 ist eine Beziehung, kein Themenfilter.** Die Firma hat für diesen
Auftraggeber nachweislich schon geliefert, und derselbe Auftraggeber schreibt
jetzt wieder aus.

### Das Signal, das ich weggeworfen habe

Ich hatte ein viertes: gleiche CPV-Gruppe plus gleiches Bundesland. Also "in
eurer Region wird etwas in eurem Bereich ausgeschrieben".

Es lieferte **16.216 Treffer**, bei einer Firma 134 gleichzeitig. Das ist kein
Signal, das ist ein Abo. Es ist genau das CPV-Raten, das ihr in der Aufgabe
kritisiert, nur auf der Firmenseite.

Es steht noch im Code, als Zähler, damit die Zahl nachprüfbar ist. Ausgegeben
wird es nicht.

**Dazu eine Deckelung:** pro Firma maximal drei S4-Signale, die frischesten.
Wer 60 offene Ausschreibungen hat, braucht keine Liste mit 60 Zeilen, sondern
einen Aufhänger.

### State

`signal_state.json` merkt jedes ausgegebene Tripel (Firma, Signalart,
Bekanntmachungsnummer). Der zweite Lauf findet dieselben 434 Signale und gibt
**0 neue** aus. Die Datei behält trotzdem das volle Bild, mit einer Spalte
`Neu_in_diesem_Lauf`. Sonst wäre die Liste nach dem zweiten Lauf leer und der
Vertrieb hätte nichts zum Anrufen.

---

## 5. Enrichment, ohne Budget

**In Deutschland ist das Impressum Pflicht.** Jede GmbH muss dort Rechtsform,
Geschäftsführung und eine Telefonnummer nennen. Das ist eine gesetzlich
erzwungene Datenquelle mit Quellenangabe inklusive. Dafür braucht niemand Credits.

Der Waterfall, jede Stufe mit eigener Trefferquote:

1. Startseite holen, interne Links sammeln
2. **Impressum**: Rechtsname, Geschäftsführung, Telefon, HRB
3. Team-, Kontakt- und Ansprechpartnerseiten: Namen mit Titel
4. Rollen zuordnen: Champion, dann Vertriebsleitung, dann Geschäftsführung
5. Mailmuster aus allen Adressen auf der Domain ableiten

**Nebeneffekt, der wichtiger ist als der Hauptzweck:** der Rechtsname im
Impressum prüft die geratene Domain. Passt er nicht, war die Domain falsch. So
sind die Fehltreffer aus Schritt 3 aufgefallen, nicht durch Nachsehen.

**Stufe 2 fand das Impressum zunächst nur bei 45 Prozent.** Bei einer
Pflichtangabe lag der Fehler also bei mir. Zwei Ursachen: der Link steckt in
einem JavaScript-Menü, oder der Pfad heißt `/impressum.html`. Lösung:
`sitemap.xml` lesen, die nennt alle Seiten im Klartext. Danach 75 Prozent.
Die restlichen zehn waren fast alle falsche Domains, kein fehlendes Impressum.

---

## 6. Was die Quelle nicht kann

**Euer eigener Report sagt es am klarsten: 88 Prozent aller deutschen Vergaben
liegen unter der EU-Schwelle und damit nicht auf TED.** Deutschlands TED-Quote
liegt bei 1,8 Prozent, der EU-Schnitt bei 5,8. Ich sehe die obersten 12 Prozent.

**Wichtig: die 88 Prozent zählen Aufträge, nicht Firmen.** Viele der 323 bieten
auch unterhalb der Schwelle, sie haben nur zusätzlich einmal etwas Großes
gewonnen. Wirklich unsichtbar ist nur die Firma, die **nie** oberhalb der
Schwelle gewonnen hat.

Zwei kleinere Lücken:

- Gewinnernamen sind Freitext ohne Registernummer. `netgo group` und `netgo Ost`
  stehen getrennt, obwohl es dieselbe Gruppe ist. Ich normalisiere und vergebe
  eine Confidence
- **1.545** Bekanntmachungen ohne auslesbaren Gewinner, meist Altformat
  `F03_2014` oder aufgehobene Verfahren

---

## 7. Die zwei Tests, die meine Liste nicht besteht

### Oracom

Euer einziger öffentlich genannter Kunde. **Null Treffer in 5.386 Gewinnern.**

Der Grund ist strukturell: **TED nennt Gewinner, euer Kunde ist Bieter.** Wer
regelmäßig bietet und nie gewinnt, steht nirgends.

### Die Kunden eurer Wettbewerber

Vergabepilot und DTAD nennen 22 Kunden mit Namen. Wer dort steht, hat bewiesen,
dass er für so ein Werkzeug zahlt. **Genau einer steht in meinen 323:**
Sinus Nachrichtentechnik mit 4 Zuschlägen. Das sind 4,5 Prozent.

Die übrigen fallen auf zwei Arten durch:

- **Vergabepilots Kunden sind gar nicht in TED.** bluechip Computer, KeepBlue,
  Venn Telecom: null Treffer. bluechip ist ein IT-Systemhaus und zahlt für genau
  dieses Produkt
- **DTADs Kunden sind in TED, aber über meiner Decke.** GISA 36 Zuschläge,
  Hays 33, beide über 30. Siemens, Canon, Atos als Konzerne raus

**Daraus folgt:** DTAD und ihr konkurriert kaum. DTAD bedient Konzerne, eure
Preisliste endet bei 2.499 Euro. **Der eigentliche Wettbewerber ist Vergabepilot**,
und dessen Kunden sind Firmen wie bluechip.

**Und die unangenehme Erkenntnis über meine eigene Liste:** mein Filter hätte
fast jeden bekannten Käufer dieser Kategorie aussortiert. Das macht den Filter
nicht falsch, DTADs Kunden sind die Enterprise-Hälfte, für die ihr nicht
bepreist seid. Aber es heißt: **die 323 sind logisch sauber und empirisch kaum
validiert.**

**Der Tipp daraus:** die Kundenseiten der Wettbewerber sind eine öffentliche
Liste validierter Käufer. Niemand nutzt sie als Quelle. Die Testimonials liefern
obendrein die Kaufpersona mit Titel.

---

## 8. Wie ich die unsichtbaren Firmen finden würde

| Quelle | Was sie liefert | Aufwand |
|---|---|---|
| Referenzseiten der Firmen | Selbstauskunft über öffentliche Auftraggeber | gering |
| Systemhaus-Rankings CRN, ChannelPartner | fertige Branchenliste zum Gegenlegen | gering |
| Vergabekammer-Entscheidungen | Antragstellerin steht namentlich drin. Hat geboten, verloren, sich beschwert | mittel |
| Präqualifizierungsverzeichnisse (PQ-VOB, AVPQ) | formal bietfähige Firmen, vor dem ersten Gebot | mittel |
| Regionale Portale: DTVP, Vergabe24, Vergabe.NRW | Zuschläge unterhalb der Schwelle | hoch |
| Ratsinformationssysteme der Kommunen | Stadtratsprotokolle nennen den Gewinner | hoch |

**Reihenfolge:** erst die Referenzseiten, weil sie in Stunden hunderte Firmen
abdecken. Dann die Vergabekammer, weil dort die heißesten Leads stehen. Die
Portale zuletzt, weil sie am meisten Arbeit machen und genau das sind, was ihr
bereits habt.
