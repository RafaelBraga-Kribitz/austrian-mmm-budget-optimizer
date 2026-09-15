# Zusammenfassung für Entscheider

Stand: 2026-09-15. Alle Zahlen stammen aus den Artefakten unter reports/ und werden von
scripts/render_summary_de.py eingesetzt.

**Frage.** Welche Kanäle haben für einen Werbetreibenden tatsächlich zusätzlichen Umsatz
gebracht, wie weit lagen die von den Plattformen gemeldeten Zahlen daneben, und was
bringt eine Umschichtung des Budgets?

**Methode.** Ein bayesianisches Marketing-Mix-Modell (Adstock, Sättigung, Trend,
Saisonalität, ein Kontrollfaktor) wird zuerst auf einem synthetischen Werbetreibenden
mit bekannter Wahrheit geprüft und erst dann auf Daten angewendet. Jede Aussage trägt
ein 90-Prozent-Intervall.

**Nachweis (Layer P).** Auf synthetischen Daten liegen 26 von 28 wahren
Parametern innerhalb ihrer 90-Prozent-Intervalle. Der von der Plattform gemeldete Anteil
von Paid Search liegt 24,8 Prozentpunkte über dem tatsächlichen inkrementellen
Anteil; Offline-Medien bekommen von der Plattform gar nichts zugeschrieben.

**Beiträge (Layer R, öffentliche Demodaten).** Inkrementeller Umsatzanteil:
Media channel 1 22,1 Prozent (18,1 bis 28,1); Media channel 2 7,1 Prozent (6,6 bis 7,7). Es handelt sich um öffentliche Demodaten mit indexierten
Ausgaben; ein Wechsel auf echte Kundendaten ist vorgesehen. Es wurden keine
österreichischen Kundendaten verwendet.

**Entscheidung (Layer D).** Bei gleichem Gesamtbudget: Media channel 1 +23 Prozent; Media channel 2 -45 Prozent. Erwarteter
Gewinn im Median 2,5 Prozent des heutigen Medienbeitrags, 10. Perzentil
-0,8 Prozent, Wahrscheinlichkeit eines Verlusts 14,6 Prozent. Die Umschichtung
wird nach der Entscheidungsregel nicht empfohlen. Mit 25 Prozent mehr Budget liegt der Median-Gewinn bei 23,3 Prozent.

**Regel.** Budget wird nur in einen Kanal verschoben, solange die untere Grenze des
90-Prozent-Intervalls seines Grenz-ROAS über dem Breakeven-ROAS von 2,50 liegt
(Deckungsbeitrag 40 Prozent, eine im Konfigurationsfile festgehaltene Annahme),
und nur, wenn das 10. Perzentil des Umschichtungsgewinns positiv ist.

**Grenzen.** Wöchentliche nationale Daten trennen Kanäle mit gleichlaufenden Ausgaben
nur unscharf; das Modell setzt eine feste Wirkungsform voraus; Kalibrierung gegen
Lift-Tests, Geo-Daten und Wettbewerberausgaben stehen für Produktionsdaten aus.
