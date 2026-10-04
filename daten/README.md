# Eingabe und Zwischenstände

Die zwei Ordner sind leicht zu verwechseln: **`daten/` ist Eingabe, [`data/`](../data) ist Ausgabe.**

Diese Dateien liegen im Repo, damit der Lauf reproduzierbar ist, ohne 13.066 Bekanntmachungen neu aus TED zu ziehen. Das dauert sonst Stunden, und TED antwortet ab einer gewissen Frequenz mit 429.

| Datei | Inhalt |
| --- | --- |
| `icp_systemhaeuser.json` | Die Firmen nach dem CPV-Test, also vor der Domainprüfung. Ausgabe von `03_icp_filter.py`. |
| `domains.json` | Die aufgelösten Domains je Firma, mit Belegtyp und Begründung. Ausgabe von `04` und `05`. |
| `firma_auftraggeber.json` | Welche Firma bei welchem Auftraggeber schon geliefert hat. Daraus entsteht der Satz "dort habt ihr 2024 schon geliefert", samt Link auf den damaligen Zuschlag. |
| `patterno_signals.json` | Die Signale aus dem letzten Lauf, Eingabe für Enrichment und Mailmuster. |

Die Rohdaten aus TED selbst liegen nicht im Repo, die sind zu groß. [`../src/01_ted_zuschlaege_ziehen.py`](../src/01_ted_zuschlaege_ziehen.py) holt sie neu.
