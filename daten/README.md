# Eingabe und Zwischenstaende

Die zwei Ordner sind leicht zu verwechseln: **`daten/` ist Eingabe, [`data/`](../data) ist Ausgabe.**

Diese Dateien liegen im Repo, damit der Lauf reproduzierbar ist, ohne 13.066 Bekanntmachungen neu aus TED zu ziehen. Das dauert sonst Stunden, und TED antwortet ab einer gewissen Frequenz mit 429.

| Datei | Inhalt |
| --- | --- |
| `icp_systemhaeuser.json` | Die Firmen nach dem CPV-Test, also vor der Domainpruefung. Ausgabe von `03_icp_filter.py`. |
| `domains.json` | Die aufgeloesten Domains je Firma, mit Belegtyp und Begruendung. Ausgabe von `04` und `05`. |
| `firma_auftraggeber.json` | Welche Firma bei welchem Auftraggeber schon geliefert hat. Daraus entsteht der Satz "dort habt ihr 2024 schon geliefert", samt Link auf den damaligen Zuschlag. |
| `patterno_signals.json` | Die Signale aus dem letzten Lauf, Eingabe fuer Enrichment und Mailmuster. |

Die Rohdaten aus TED selbst liegen nicht im Repo, die sind zu gross. [`../src/01_ted_zuschlaege_ziehen.py`](../src/01_ted_zuschlaege_ziehen.py) holt sie neu.
