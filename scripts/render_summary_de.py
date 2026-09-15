"""Write docs/summary_de.md, a half-page German executive summary, from reports/.

Only runs when Layer D has produced reports/layer_d/decision.json; every number is
read from the artifacts. Values are recorded in reports/summary_de_values.json.

    uv run python scripts/render_summary_de.py --date 2026-09-15
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
REPORTS = ROOT / "reports"
VALUES: dict[str, str] = {}


def v(key: str, value) -> str:
    text = str(value)
    VALUES[key] = text
    return text


def pct(x: float, digits: int = 1) -> str:
    return f"{100 * float(x):.{digits}f}".replace(".", ",")


def num(x: float, digits: int = 2) -> str:
    return f"{float(x):.{digits}f}".replace(".", ",")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", default=date.today().isoformat())
    args = parser.parse_args()
    decision_path = REPORTS / "layer_d" / "decision.json"
    if not decision_path.exists():
        print("Layer D has not run; docs/summary_de.md is left for a later stage")
        return 0
    with open(decision_path, encoding="utf-8") as fh:
        dec = json.load(fh)
    with open(REPORTS / "layer_p" / "run_info.json", encoding="utf-8") as fh:
        p_info = json.load(fh)
    gap = pd.read_csv(REPORTS / "layer_p" / "attribution_gap.csv")
    search = gap[gap["channel"] == "Paid Search"].iloc[0]
    channels = pd.read_csv(REPORTS / "layer_r" / "channel_contributions.csv")
    table = pd.read_csv(REPORTS / "layer_d" / "reallocation_table.csv")
    same = dec["same_total"]
    plus = dec["plus_25_percent"]

    covered = v("p_covered", p_info["parameters_covered"])
    total = v("p_total", p_info["parameters_total"])
    search_gap = v("p_search_gap", num(search["gap_pp"], 1))
    shares = []
    for _, row in channels.iterrows():
        shares.append(
            f"{row['channel']} {v('r_share_' + row['channel'], pct(row['share_median']))} Prozent "
            f"({v('r_lo_' + row['channel'], pct(row['share_lo']))} bis "
            f"{v('r_hi_' + row['channel'], pct(row['share_hi']))})"
        )
    moves = []
    for _, r in table[table["scenario"] == "same_total"].iterrows():
        delta = v("d_delta_" + r["channel"], f"{r['delta_pct']:+.0f}")
        moves.append(f"{r['channel']} {delta} Prozent")
    gain_med = v("d_gain_median", num(same["gain_pct_of_current_contribution_median"], 1))
    gain_p10 = v("d_gain_p10", num(same["gain_pct_of_current_contribution_p10"], 1))
    p_neg = v("d_p_neg", pct(same["probability_gain_negative"]))
    breakeven = v("d_breakeven", num(dec["breakeven_roas"]))
    margin = v("d_margin", pct(dec["contribution_margin"], 0))
    p25 = v("d_p25_gain", num(plus["gain_pct_of_current_contribution_median"], 1))
    verdict = (
        "wird empfohlen" if same["recommend"]
        else "wird nach der Entscheidungsregel nicht empfohlen"
    )
    when = v("date", args.date)

    text = f"""# Zusammenfassung für Entscheider

Stand: {when}. Alle Zahlen stammen aus den Artefakten unter reports/ und werden von
scripts/render_summary_de.py eingesetzt.

**Frage.** Welche Kanäle haben für einen Werbetreibenden tatsächlich zusätzlichen Umsatz
gebracht, wie weit lagen die von den Plattformen gemeldeten Zahlen daneben, und was
bringt eine Umschichtung des Budgets?

**Methode.** Ein bayesianisches Marketing-Mix-Modell (Adstock, Sättigung, Trend,
Saisonalität, ein Kontrollfaktor) wird zuerst auf einem synthetischen Werbetreibenden
mit bekannter Wahrheit geprüft und erst dann auf Daten angewendet. Jede Aussage trägt
ein 90-Prozent-Intervall.

**Nachweis (Layer P).** Auf synthetischen Daten liegen {covered} von {total} wahren
Parametern innerhalb ihrer 90-Prozent-Intervalle. Der von der Plattform gemeldete Anteil
von Paid Search liegt {search_gap} Prozentpunkte über dem tatsächlichen inkrementellen
Anteil; Offline-Medien bekommen von der Plattform gar nichts zugeschrieben.

**Beiträge (Layer R, öffentliche Demodaten).** Inkrementeller Umsatzanteil:
{"; ".join(shares)}. Es handelt sich um öffentliche Demodaten mit indexierten
Ausgaben; ein Wechsel auf echte Kundendaten ist vorgesehen. Es wurden keine
österreichischen Kundendaten verwendet.

**Entscheidung (Layer D).** Bei gleichem Gesamtbudget: {"; ".join(moves)}. Erwarteter
Gewinn im Median {gain_med} Prozent des heutigen Medienbeitrags, 10. Perzentil
{gain_p10} Prozent, Wahrscheinlichkeit eines Verlusts {p_neg} Prozent. Die Umschichtung
{verdict}. Mit 25 Prozent mehr Budget liegt der Median-Gewinn bei {p25} Prozent.

**Regel.** Budget wird nur in einen Kanal verschoben, solange die untere Grenze des
90-Prozent-Intervalls seines Grenz-ROAS über dem Breakeven-ROAS von {breakeven} liegt
(Deckungsbeitrag {margin} Prozent, eine im Konfigurationsfile festgehaltene Annahme),
und nur, wenn das 10. Perzentil des Umschichtungsgewinns positiv ist.

**Grenzen.** Wöchentliche nationale Daten trennen Kanäle mit gleichlaufenden Ausgaben
nur unscharf; das Modell setzt eine feste Wirkungsform voraus; Kalibrierung gegen
Lift-Tests, Geo-Daten und Wettbewerberausgaben stehen für Produktionsdaten aus.
"""
    (ROOT / "docs" / "summary_de.md").write_text(text, encoding="utf-8")
    with open(REPORTS / "summary_de_values.json", "w", encoding="utf-8") as fh:
        json.dump(VALUES, fh, indent=2, sort_keys=True, ensure_ascii=False)
        fh.write("\n")
    print(f"docs/summary_de.md written with {len(VALUES)} values")
    return 0


if __name__ == "__main__":
    sys.exit(main())
