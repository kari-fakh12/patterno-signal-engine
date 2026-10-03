# Patterno Case Study: Public-Sector-Signal-Engine

Zwei Listen, eine Pipeline, jede Zeile mit Quelle. Gebaut ohne Budget, nur aus Pflichtveröffentlichungen: TED-Zuschläge, Impressum, Jobsuche der Bundesagentur.

## ICP-Annahmen

- **Ein Systemhaus beschafft und betreibt.** Es muss in TED beides gewonnen haben, Hardware (CPV 30, 32, 516) und Software oder Dienstleistung (48, 72). Damit fallen reine Softwarehäuser, Händler und Berater ohne Namensraten raus.
- **Größe kommt aus eurer Preisliste.** Der größte Plan erlaubt 50 geprüfte Ausschreibungen im Monat. Wer mehr als 30 Zuschläge in 21 Monaten hat, hat ein eigenes Vergabeteam und ist raus, etwa Bechtle oder Computacenter. Wer nur einen Zuschlag hat, ist noch nicht belegt.
- **Beleg statt Annahme.** Eine Firma steht nur in der Liste, wenn ein Zuschlag in TED sie als Gewinner nennt und ihre Website über das Impressum bestätigt ist.
- **Tiers sind eine Arbeitsanweisung.** 1 Anlass: datiertes Ereignis jetzt. 2 Lücke: passt, aber gerade kein Ereignis. 3 Still: seit zwölf Monaten kein Zuschlag.

## Was funktioniert

- **157 Systemhäuser** mit belegtem Zuschlag und bestätigter Website, davon 103 mit aktuellem Anlass. Markt: rund 1.000 öffentlich bietende Systemhäuser, gerechnet aus der Vergabestatistik 2024 und TED.
- **223 Signale bei 94 Firmen**, vor allem „alter Kunde schreibt neu aus“: jede Zeile mit Link zur offenen Ausschreibung und zum früheren Auftrag.
- **Die Pipeline läuft jeden Montag automatisch** auf GitHub und meldet nur neue oder geänderte Treffer. Eine verschobene Frist erscheint als geändert, mit alter und neuer Frist.
- **Alles ist gegengeprüft.** Eine zweite KI-Sitzung hat jede Zeile gegen ihre Quelle gehalten: 938 TED-Links aus 670 Bekanntmachungen, 197 Belege zu früheren Aufträgen, 157 Domains, 190 Personen, 131 Telefonnummern. Fehler gingen in den Code, nicht in die Tabelle.

## Was nicht funktioniert

- **TED zeigt nur den oberen Rand.** Firmen, die nur unterhalb der EU-Schwelle gewinnen oder noch nie gewonnen haben, fehlen. Gerade sie brauchen euch vermutlich am meisten.
- **Die Website liefert die Geschäftsführung, fast nie den Champion.** 190 Personen, davon 167 Geschäftsführung, 22 Vertriebsleitung, 1 Champion. Telefon ist fast immer die Zentrale.
- **Die automatische Domainprüfung ist streng.** Manche echte Systemhäuser fallen raus, weil ihr Impressum nicht lesbar ist. Sie liegen mit Grund in einer eigenen Datei.
- **Der CPV-Test beweist, was eine Firma verkauft hat, nicht was sie ist.** Ein Maschinenhändler, der einmal Peripherie geliefert hat, sieht aus wie ein Systemhaus. Nur die Website trennt die beiden.

## Mit zwei weiteren Wochen

1. **Unterhalb der Schwelle:** Firmen mit genau einem TED-Zuschlag, Referenzseiten und Vergabekammer-Entscheidungen als zweite Quelle für die unsichtbaren Bieter.
2. **Personen in Clay:** LinkedIn-Titelsuche für Champion und Vertriebsleitung, dann E-Mail-Finder und Verifizierung. Rund 3 $ Datenkosten je qualifiziertem Lead.
3. **Signal 5, Kunde geht zum Wettbewerber:** dieselben Daten, ein Auftraggeber vergibt erstmals an jemand anderen.
4. **Betrieb in eurem Stack:** Supabase als Gedächtnis, Clay für die Anreicherung, nach Attio nur, was belegt ist.

**Dateien:** `data/` für Listen und Kontakte, `src/` für den Code in Laufreihenfolge, `docs/methode.md` für die Details, `docs/ki-chat.md` für den genutzten KI-Chat.

---

Ausfuehrliche Fassung mit allen Trefferquoten, den gescheiterten Tests und der
Fehlerhistorie: **docs/details.md**
