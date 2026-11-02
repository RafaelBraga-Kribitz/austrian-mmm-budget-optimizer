# Österreichisches MMM und Budgetoptimierung

[🇧🇷 PT-BR](README.pt-BR.md) · [🇬🇧 EN-UK](README.md) · [🇦🇹 DE-AT](README.de-AT.md)

## Überblick

Dieses Repository zeigt ein bayesianisches Marketing-Mix-Modell (MMM) und eine Regel zur Umverteilung des Medienbudgets. Das Modell ist auf einen österreichischen Werbekontext ausgelegt, verwendet aber **keine österreichischen Kundendaten**. Es wird mit künstlichen Daten bekannter Wahrheit validiert und mit einem öffentlichen Beispieldatensatz demonstriert.

Für den öffentlichen Beispieldatensatz lautet die Empfehlung: Out-of-Home um 20 % reduzieren und TV sowie Facebook jeweils um 50 % erhöhen, bei gleichbleibendem Gesamtbudget. Der geschätzte Median des Zugewinns beträgt 15,1 % des aktuellen Medienbeitrags; das 10. Perzentil liegt bei 8,8 %. In keiner der 500 posterioren Ziehungen entsteht ein Verlust. Die Geldbeträge sind in den Einheiten des Beispieldatensatzes angegeben, **nicht in Euro**.

Das Modell schätzt den inkrementellen Beitrag je Kanal samt 90-%-Intervallen, vergleicht ihn mit Plattformmeldungen und wendet eine Break-even-Regel an. Budget wird einem Kanal nur zugeteilt, wenn die Untergrenze des marginalen Return on Ad Spend (ROAS) über dem Break-even-Wert liegt.

## Was das Projekt zeigt

- Bayesianisches MMM mit Wirkungskurven und ausgewiesener Unsicherheit.
- Validierung mit künstlichen Daten, deren wahre Werte bekannt sind.
- Budgetempfehlung mit einer Break-even-Regel statt einer Rangliste nach Medianwerten.
- Berücksichtigung des österreichischen Feiertagskalenders und wöchentlicher Daten.

## Wesentliche Grenzen

Die öffentliche Demonstration ist kein österreichischer Kundenfall und darf nicht als Euro-Ergebnis interpretiert werden. Die Empfehlung hängt von Annahmen zu Deckungsbeitrag und Verschiebungsgrenzen ab. Eine reale Anwendung benötigt Kundendaten und eine lokale Validierung.

## Weiterlesen

Das [vollständige README auf Englisch](README.md) enthält Ergebnisse, Tabellen, Dashboards, Methodik und Ausführungsanleitung. Siehe auch die [wirtschaftliche Bewertung](docs/economic-evaluation.md).

[Repository](https://github.com/RafaelBraga-Kribitz/austrian-mmm-budget-optimizer)
