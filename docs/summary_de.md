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
TV 6,0 Prozent (3,5 bis 10,0); Out-of-home 2,7 Prozent (0,3 bis 7,9); Print 1,8 Prozent (0,4 bis 5,5); Facebook 2,5 Prozent (0,6 bis 5,5); Search 3,2 Prozent (0,3 bis 10,5). Es handelt sich um öffentliche Demodaten (Robyn, fünf benannte
Kanäle, Geldeinheiten ohne Währungsangabe); ein Wechsel auf echte Kundendaten ist
vorgesehen. Es wurden keine österreichischen Kundendaten verwendet.

**Entscheidung (Layer D).** Bei gleichem Gesamtbudget: TV +50 Prozent; Out-of-home -20 Prozent; Print +0 Prozent (von der Regel gehalten); Facebook +50 Prozent; Search +0 Prozent (von der Regel gehalten). Erwarteter
Gewinn im Median 15,1 Prozent des heutigen Medienbeitrags, 10. Perzentil
8,8 Prozent, Wahrscheinlichkeit eines Verlusts 0,0 Prozent. Die Umschichtung
wird empfohlen. Mit 25 Prozent mehr Budget liegt der Median-Gewinn bei 24,0 Prozent. Mit 200000 Geldeinheiten mehr pro Jahr steigt der Medienbeitrag im Median um 17,4 Prozent.

**Regel.** Budget wird nur in einen Kanal verschoben, solange die untere Grenze des
90-Prozent-Intervalls seines Grenz-ROAS über dem Breakeven-ROAS von 2,50 liegt
(Deckungsbeitrag 40 Prozent, eine im Konfigurationsfile festgehaltene Annahme),
und nur, wenn das 10. Perzentil des Umschichtungsgewinns positiv ist.

**Grenzen.** Wöchentliche nationale Daten trennen Kanäle mit gleichlaufenden Ausgaben
nur unscharf; das Modell setzt eine feste Wirkungsform voraus; Kalibrierung gegen
Lift-Tests, Geo-Daten und Wettbewerberausgaben stehen für Produktionsdaten aus.
