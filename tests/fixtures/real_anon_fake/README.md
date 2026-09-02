# `real_anon_fake` — a fabricated Layer R fixture

This directory's three CSV files are fabricated data, authored solely from the
SPEC-02 section 5.2 channel taxonomy and the BP-D-03 anonymized-output column names,
for the sole purpose of exercising the `layer_r_present` jinja branch (D-20) before
real anonymized data exists. Every number here is a round constant chosen to be
self-evidently synthetic — twelve identical weekly rows per channel, a flat revenue
figure, a two-week promo flag pattern — and none of it is derived from, shaped by,
or proportional to any real client figure. It contains no client identity, no real
magnitude, and no anonymization factor (AGENTS A-4), and it must never be treated as
a sample of real agency data. This directory is scanned by `scripts/leak_scan.py`
in CI along with the rest of the tree, exactly like every other tracked file.
