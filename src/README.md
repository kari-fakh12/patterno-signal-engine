# Code, in Laufreihenfolge

Nur Standardbibliothek, keine Abhaengigkeiten. Jedes Skript liest aus `daten/` und schreibt nach `data/`.

Fuer einen einzelnen Lauf reicht `python3 src/07_signal_engine.py`. Genau das macht auch der Montagslauf in Actions.

| Skript | Was es tut | Aufgabe |
| --- | --- | --- |
| [`00_felder_pruefen.py`](00_felder_pruefen.py) | Probe gegen die TED-API: welches Feld traegt eigentlich den Zuschlagsempfaenger. Hier kam der Trick her, mit dem die API ihre eigenen 1.830 gueltigen Feldnamen preisgibt. | Vorarbeit |
| [`01_ted_zuschlaege_ziehen.py`](01_ted_zuschlaege_ziehen.py) | Zieht alle deutschen IT-Zuschlaege seit 2024 aus TED. 13.066 Bekanntmachungen. | 1a |
| [`02_gewinner_aggregieren.py`](02_gewinner_aggregieren.py) | Baut daraus die 5.386 Firmen, die wirklich gewonnen haben. Der Gewinner wird aus dem XML aufgeloest, nicht aus dem bequemen API-Feld, weil das Feld bei mehreren Losen den Falschen nennt. | 1a |
| [`03_icp_filter.py`](03_icp_filter.py) | Der Systemhaus-Test kommt aus den CPV-Codes, nicht aus dem Firmennamen: Hardware (30, 32, 516) **und** Software oder Dienstleistung (48, 72) muessen beide vorkommen. | 1a |
| [`04_domains_raten.py`](04_domains_raten.py) | Domain je Firma ohne Budget. Raet Kandidaten, liest den Rechtsnamen aus dem Impressum und vergleicht beide. Drei Anlaeufe haben es nicht geschafft, die Geschichte steht in [`../docs/methode.md`](../docs/methode.md). | 1c |
| [`05_domains_suche.py`](05_domains_suche.py) | Stufe 3 fuer die Faelle, die das Raten nicht geloest hat. | 1c |
| [`06_longlist1_export.py`](06_longlist1_export.py) | Longlist 1 als CSV, mit Tier und einer Confidence je Feld. | 1c |
| [`07_signal_engine.py`](07_signal_engine.py) | Die vier Signale, mit Gedaechtnis. Ein Fingerabdruck je Zeile entscheidet, ob ein Treffer neu, geaendert oder unveraendert ist. Das ist das Skript, das montags laeuft. | 2a, 2b |
| [`08_enrichment_waterfall.py`](08_enrichment_waterfall.py) | Kontakte aus Impressum und Teamseiten. Jede Person bekommt die Seite mit, auf der sie steht. Keine Zeile ohne Fundstelle. | 1d, 2d |
| [`09_enrichment_nachlauf.py`](09_enrichment_nachlauf.py) | Nachlauf fuer die Firmen, deren Impressum im ersten Durchgang nicht gefunden wurde. | 1d |
| [`10_mailmuster.py`](10_mailmuster.py) | Leitet das Mailmuster aus allen Adressen auf der Domain ab, nicht nur aus den Treffern. | 1d |
| [`11_icp_profil.py`](11_icp_profil.py) | Fakten ueber die gefilterte Firmenmenge, als Grundlage fuer das ICP-Profil. | 1a |
| [`12_signal_stellenanzeigen.py`](12_signal_stellenanzeigen.py) | Signal aus Stellenanzeigen ueber die API der Bundesagentur fuer Arbeit. | 2a |
| [`ausschluss.py`](ausschluss.py) | Wer kein Kunde ist, und warum. Hersteller, Konzerne, Reseller. Stand frueher in zwei von drei Skripten, deshalb enthielt Longlist 2 Firmen, die Longlist 1 korrekt ausgeschlossen hatte. Jetzt eine Stelle, drei Verwender. | alle |
