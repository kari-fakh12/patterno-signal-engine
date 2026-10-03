# Der genutzte KI-Chat

**Was das hier ist:** ein auf diesen Case gefilterter Auszug aus meinem
Arbeitschat. Der Originalchat enthält auch andere Bewerbungen, Gehaltszahlen
und Notizen aus Kundenprojekten, die hier nichts verloren haben. Gekürzt wurde
nur, was nicht zu Patterno gehört. **Nichts wurde nachträglich geglättet:** die
Sackgassen, die Fehler und die Korrekturen stehen so drin, wie sie passiert
sind, weil genau die zeigen, wie ich mit einem Modell arbeite.

Ich arbeite mit Claude Code im Terminal, nicht in einem Chatfenster. Das Modell
schreibt und startet Skripte, liest die Ausgabe und korrigiert sich. Die
interessanten Stellen sind deshalb selten einzelne Prompts, sondern die
Schleifen: bauen, Ergebnis ansehen, merken dass es falsch ist, Ursache suchen.

---

## 1. Erst verstehen, was ihr verkauft

Mein erster Schritt war nicht die Datenbeschaffung, sondern eure Preisliste.

> **Ich:** Lies die Patterno-Website. Was kostet das, und was ist eine
> Qualifizierung?

Starter 89 €, 3 Qualifizierungen im Monat. Scale 499 €, 50. Daraus folgt eine
harte Obergrenze für den ICP, und zwar ohne zu raten:

**Bechtle gewinnt 328 Aufträge in 21 Monaten, also rund 15 im Monat.** Um 15 zu
gewinnen, bieten sie auf etwa 60 und prüfen davor vielleicht 200. Der größte
Plan erlaubt 50. Bechtle passt in keinen eurer Pläne.

Das war die wichtigste Entscheidung des ganzen Case und sie kam aus eurer
Preisseite, nicht aus den Daten. Ab da war die Obergrenze Rechnen statt Meinung.

---

## 2. Die Quelle finden, und zwei Fallen darin

> **Ich:** Zuschläge sind öffentlich. Wo liegen die maschinenlesbar?

TED, die EU-Vergabedatenbank, offene API, kein Schlüssel.

**Falle 1:** Die API gibt bei einem fehlenden `fields`-Parameter nur
"Validation error", und bei einem ungültigen Feldnamen dieselbe Meldung. Ohne
zu wissen, welches Feld das Problem ist.

> **Ich:** Teste jedes Feld einzeln, bevor du den großen Zug machst.

**Falle 2, und daraus wurde ein Fund:** fragt man absichtlich nach einem Feld,
das es nicht gibt, listet die Fehlermeldung **alle 1.830 erlaubten Feldnamen**.
So habe ich `contract-duration-end-date-lot` gefunden, und damit das Signal
"Vertrag läuft aus", das vorher nur eine Idee war.

Ergebnis: 13.066 deutsche IT-Zuschläge seit 2024, 5.386 verschiedene Gewinner.

---

## 3. Der Filter, der ohne Firmennamen auskommt

> **Ich:** Ein Systemhaus beschafft Hardware und betreibt Software. Kann man
> das aus den CPV-Codes ableiten, statt Namen zu lesen?

Ja. Wer **beides** gewonnen hat, Hardware (30x, 32x, 516) **und** Software oder
Dienstleistung (48x, 72x), ist ein Integrator. Reine Softwarehäuser haben nur
das zweite, Händler nur das erste, Berater haben 794.

5.386 → **323**, ohne dass ein Mensch einen Firmennamen gelesen hat. Zwei der
Treffer heißen wörtlich "Systemhaus", gefunden hat sie der CPV-Test.

Dazu eine Antwort auf euren eigenen Satz "kein CPV-Raten": ihr kritisiert CPV
als Mittel, **Ausschreibungen** zu finden. Ich nutze es, um **Firmen** nach dem
zu sortieren, was sie bereits gewonnen haben. Rückspiegel statt Suchfilter.

---

## 4. Der Test, den meine Liste nicht bestanden hat

> **Ich:** Patterno nennt genau einen Kunden öffentlich. Such Oracom in den
> 5.386 Gewinnern.

**Null Treffer.**

Der Grund ist strukturell und er war mir vorher nicht klar: **TED nennt
Gewinner, euer Kunde ist Bieter.** Wer regelmäßig bietet und selten gewinnt,
steht nirgends.

> **Ich:** Dann prüf die Kunden der Wettbewerber. Vergabepilot und DTAD nennen
> Namen.

22 Kunden, **genau einer** steht in meinen 323. 4,5 Prozent.

Das war der unangenehmste Moment im Case und der nützlichste. Mein Filter hätte
fast jeden bekannten Käufer dieser Produktkategorie aussortiert. Daraus kam
nebenbei die Erkenntnis, dass **DTAD gar nicht euer Wettbewerber ist**: deren
Logowand zeigt Bosch, Canon, Siemens. Vergabepilots Kunden sind bluechip und
KeepBlue, also genau euer Segment.

Ich habe das nicht weggelassen. Es steht in `docs/methode.md` unter "Die zwei
Tests, die meine Liste nicht besteht".

---

## 5. Domains: dreimal falsch, bevor es stimmte

Das ist die längste Schleife im ganzen Projekt und die lehrreichste.

**Versuch 1, zu gutgläubig.** Domain raten, dann prüfen ob der Firmenname
irgendwo auf der Seite steht. Klingt vernünftig, war in rund 40 von 290 Fällen
falsch:

- `aura Computersysteme` wurde `aura.com`, ein US-Anbieter für
  Identitätsschutz. Das Wort "aura" steht auf der Seite, also galt es als
  Treffer
- Geparkte Domains bestanden den Test **immer**, weil der Verkäufer den
  Firmennamen in den Titel schreibt

> **Ich:** Dreh die Prüfung um. Lies den Rechtsnamen aus dem Impressum und
> vergleich den.

**Versuch 2, zu streng.** Jetzt fielen 141 Firmen durch, darunter WBS
IT-Service, dessen Impressum wörtlich "WBS IT-Service GmbH" sagt. Drei
Ursachen, alle meine:

- Der Extraktor nahm den **längsten** Firmennamen der Seite. Bei datagroup.de
  ist das "AXA Versicherung AG", weil ein Impressum weiter unten den Versicherer
  nennt
- Der Vergleich hielt das **längste** Wort für das kennzeichnende, deshalb
  scheiterte "secunet Security Networks AG" gegen "secunet AG"
- Rechtsformen zählten als Namenswörter, deshalb sahen "DATAGROUP SE" und
  "DATAGROUP Stuttgart GmbH" wie zwei Firmen aus

**Versuch 3, zu lasch.** Nach der Korrektur galt "aura" gleich "aura" als
Beleg. Wahr und wertlos.

**Die Lösung ist zweistufig:**

1. Das kennzeichnende Wort ist das **erste**, nicht das längste. Firmennamen
   fangen mit dem Namen an und hören mit Beschreibung auf
2. Teilen zwei Namen nur ein einziges Wort, entscheidet der **Ort**. Steht die
   TED-Stadt im Impressum, ist es dieselbe Firma

> **Ich:** Teste das gegen die Fälle, die wir kennen, bevor du 25 Minuten
> laufen lässt.

27 Fälle als Test. Die sechs, die ein Namensvergleich grundsätzlich nicht
entscheiden kann (aura, ergo, SHD Solutions, ]init[, Dr. Hansen, DIE CREW),
fallen alle über den Ort.

**Nebenbefund, der mehr wert ist als die Domain:** der Vergleich findet Firmen,
die es unter dem Namen nicht mehr gibt. WTG communication ist heute T&N AG,
Systempartner ist DNS GmbH. Ein TED-Gewinner von 2024 kann 2026 eine andere
Firma sein, und das muss ein Vertriebler wissen, bevor er anruft.

---

## 6. Eine zweite KI-Sitzung als Gegenprüfung

Ab einem gewissen Punkt habe ich eine **zweite Claude-Sitzung** aufgesetzt, die
nichts bauen durfte, sondern nur prüfen. Sie hat gegen die Originalquellen
gearbeitet, nicht gegen meine Dateien.

Das hat Fehler gefunden, die ich nicht gefunden hätte:

| Fund | Warum ich es übersehen habe |
|---|---|
| Telefonnummern wie `+49025429558250` | Verkehrsnull nach der Landesvorwahl, sieht in der Tabelle plausibel aus |
| ~30 erfundene Personen | "Typische Fragen", "Key Account", "Digitale Verwaltung". Mein Parser hielt Überschriften für Menschen, einer bekam `typische.fragen@` als Adresse |
| Zwei Ärzte bei einem Anbieter | Kundenstimmen auf einer Produktseite. "Inhaber" bezog sich auf ihre eigene Praxis |
| `Hans-Peter Hellmann` als `Peter Hellmann` | Mein Namensmuster erlaubte keinen Bindestrich im Vornamen |
| Longlist 2 lieferte Firmen aus, die Longlist 1 korrekt ausschloss | Die Ausschlussliste stand zweimal im Code und in der dritten Datei gar nicht |

Der Bindestrich-Fall ist der gefährlichste Fehlertyp überhaupt: **eine fehlende
Zeile merkt man, eine falsche Nummer merkt man beim Wählen, einen halben
Vornamen merkt man erst, wenn der Angerufene ihn korrigiert.**

Einmal lag die Gegenprüfung auch falsch, und das ist genauso wichtig: sie
meldete drei erfundene Mailadressen. Ich habe alle Seiten abgerufen statt es zu
glauben. Die Adressen standen wörtlich auf der **Ansprechpartnerseite**, nur
meine Quellenangabe zeigte aufs Impressum. Die Daten waren richtig, die
Fußnote war falsch. Die Korrektur war die Fußnote, nicht das Löschen.

---

## 7. Die Entscheidung, 174 Firmen wegzuwerfen

> **Ich:** Firmen ohne bestätigte Domain kommen raus. Nicht als Tier 4
> mitlaufen lassen, raus.

Das kostet 122 Firmen mit **belegten** TED-Zuschlägen. Echte Systemhäuser, die
echte öffentliche Aufträge gewonnen haben, nur ihre Website ließ sich nicht
maschinell bestätigen.

Die Begründung ist verkäuferisch, nicht technisch: Patterno prüft
stichprobenartig. Eine Liste, in der jede Zeile einen Test übersteht, ist mehr
wert als eine längere mit einem Zweifel-Eimer.

Gelöscht ist nichts. Die 174 stehen mit Begründung je Zeile in
`data/pruefen_domain_offen.csv`.

Daraus folgt eine Zahl, die ich **nicht** liefere: 148 ist nicht die
Marktgröße. Es ist die Zahl der Firmen, die heute anrufbar sind.

---

## 8. Kontakte: nur was belegt ist

> **Ich:** In die Kontaktdateien kommt nur, wovon wir zu hundert Prozent sicher
> sind. Keine abgeleiteten Adressen, auch nicht mit Hinweis.

Damit fiel die Mailmuster-Ableitung weg. Sie traf ohnehin nur bei 3 Prozent und
war die einzige Spalte, in der eine erzeugte Zeichenkette wie ein Fakt aussah.

Dann ein Fehler, der zwei Zahlen gleichzeitig kaputt machte. Um zu verhindern,
dass jemand die Rolle seines Nachbarn erbt, hatte ich verlangt: Rolle und Name
in **derselben Zeile**. Damit fielen alle Ansprechpartner-Karten aus, denn dort
steht der Name in Zeile eins, die Rolle in Zeile zwei, das Telefon in Zeile
drei. 164 von 167 Kontakten kamen aus dem Impressum, die Teamseiten waren blind.

Die Lösung ist der **Block nach vorne**: ab dem Namen bis zum nächsten Namen.
Nach hinten wird nie gelesen, deshalb kann niemand die Rolle des Vorgängers
erben.

Ein Fix, fünf Zahlen:

| | vorher | nachher |
|---|---|---|
| Personen | 167 | 184 |
| Vertriebsleitung | 7 | 22 |
| Champion | 0 | 1 |
| eigene Durchwahl | 0 | 4 |
| persönliche Mailadresse | 1 | 6 |

Die Erkennung war nie kaputt. Ich habe die Seiten nicht gelesen, auf denen
diese Rollen stehen.

---

## 9. Die Lücke, die zuletzt auffiel

> **Ich:** Die Aufgabe sagt "ein System, das **jede Woche automatisch**
> liefert". Meine Engine läuft nur, wenn ich sie starte.

Daraus wurde `.github/workflows/weekly.yml`: Montag 06:00 UTC, dazu ein
manueller Auslöser für das Gespräch. Der Lauf zieht live von TED und committet
das Ergebnis zurück ins Repo.

Dafür mussten die Pfade von meinem Rechner weg und ins Repo. Ein Skript, das
nur auf meinem Laptop läuft, ist kein wöchentliches System.

Zweite Lücke im selben Satz: "neue **oder veränderte** Treffer". Mein State
kannte Firma, Signalart und Bekanntmachung, das erkennt nur neu. **Wenn eine
Vergabestelle die Frist um eine Woche verschiebt, ist das Signal dasselbe und
trotzdem anders**, und genau das ist für den Anruf wichtig.

Jetzt je Tripel ein Fingerabdruck aus Frist, Datum, Titel, Auftraggeber.
Belegt durch vier Läufe:

| Lauf | gefunden | neu | geändert |
|---|---|---|---|
| 1, frischer State | 560 | 560 | 0 |
| 2, nichts verändert | 560 | 0 | 0 |
| 3, eine Frist +7 Tage | 560 | 0 | **9** |
| 4, in GitHub Actions | 560 | 0 | 0 |

Neun statt einer, weil diese Bekanntmachung eine gemeinsame Beschaffung von
neun Stellen ist. Die Verschiebung erreicht alle Betroffenen, nicht nur den
ersten Treffer.

---

## Was ich daraus mitnehme

**Die Fehler lagen fast nie im Modell, sondern in meiner Regel.** Jedes Mal,
wenn etwas falsch war, war die Ursache eine Prüfung, die ich zu lose oder zu
streng formuliert hatte. Das Modell hat genau das getan, was ich gesagt habe.

**Die eigenen Daten lesen schlägt jeden Test.** Den Hansen-Fehler, die
abgeschnittenen Vornamen und die blinden Teamseiten habe ich nicht durch einen
Test gefunden, sondern durch Hinsehen in der fertigen CSV.

**Eine zweite Instanz, die nur prüfen darf, ist mehr wert als eine zweite, die
mitbaut.** Und sie muss gegen die Originalquelle prüfen, nicht gegen meine
Ausgabe. Sonst prüft sie meine Fehler mit.
