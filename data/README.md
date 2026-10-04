# Ausgabe: die Listen

Was die Pipeline schreibt. [`daten/`](../daten) daneben ist die Eingabe.

| Datei | Inhalt | Teil der Abgabe |
| --- | --- | --- |
| [`longlist1_markt.csv`](longlist1_markt.csv) | **157 Systemhäuser** mit belegtem Zuschlag und bestätigter Website. Tier, Begründung, Beleglink und eine Confidence je Feld. | 1c |
| [`enrichment_longlist1_alle.csv`](enrichment_longlist1_alle.csv) | Kontakte für **alle 157** Firmen. 237 Zeilen, weil eine Zeile je Person steht: **189 Personen** bei 109 Firmen, jede mit der Seite, auf der sie gefunden wurde. | 1d |
| [`enrichment_longlist1_top40.csv`](enrichment_longlist1_top40.csv) | Die **40 wichtigsten Accounts**. 60 Zeilen, weil mehrere Personen je Firma vorkommen, 47 davon mit Person. | 1d |
| [`longlist2_signale.csv`](longlist2_signale.csv) | **223 Signale bei 94 Firmen**. Je Zeile die Frist, der Link zur offenen Ausschreibung und der Link zum früheren Auftrag beim selben Auftraggeber. | 2c |
| [`enrichment_longlist2_top20.csv`](enrichment_longlist2_top20.csv) | Die **Top 20 nach Score**, mit fertigem Why-now-Satz. 31 Zeilen, 27 davon mit Person. | 2d |
| [`pruefen_domain_offen.csv`](pruefen_domain_offen.csv) | **Nicht Teil der Abgabe.** 166 aussortierte Firmen mit Grund. Liegt hier, damit nachvollziehbar ist, warum sie fehlen, statt dass sie einfach verschwinden. | nein |
| `longlist2_signale.json` | Dieselben Signale maschinenlesbar, Eingabe für das Enrichment. | Laufzeit |
| `signal_state.json` | Das Gedächtnis des Montagslaufs. Ein Fingerabdruck je Signal, daraus entsteht neu, geändert oder unverändert. Ohne diese Datei meldet die Pipeline jede Woche alles als neu. | Laufzeit |

**Zur Lesart:** eine leere Zelle heißt "nicht belegbar", nicht "gibt es nicht". Was sich nicht belegen ließ, ist leer geblieben statt geraten zu werden.
