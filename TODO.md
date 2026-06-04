# Project Monkeyface — TODO

## Statistical / data-honesty (flagged by the data-accuracy audit, 2026-06-03)

These are about whether the numbers and charts are *right and not misleading* —
important before the tool informs real sourcing decisions.

- [ ] **Multiple-comparisons correction.** The analysis tests 7 weather factors
      independently with no Bonferroni/FDR adjustment. Empirically, at n=12 there's
      a ~30% chance of at least one factor being falsely flagged "Strong" on pure
      noise. The "How sure" tooltip currently claims "Strong = confident."
      *Fix options:* correct the significance threshold for the number of factors
      tested, OR downgrade the "Strong" copy and surface a multiplicity caveat.
      Location: `monkeyface/analysis.py` `_confidence()` (thresholds) +
      `static/app.js` confidence tooltip copy. Small change.

- [ ] **Map color scale is relative, not absolute.** `static/app.js` `renderMap()`
      normalizes defect color to *this dataset's* max, so the reddest dot is always
      the local worst even if absolute defect is low — colors aren't comparable
      across runs/seasons, which is misleading for a sourcing tool. *Fix:* use a
      fixed absolute scale (e.g. 0 → a defect ceiling) with a visible legend, or
      clearly label the scale as relative-to-this-batch. Needs a small legend UI.

## Already addressed (2026-06-03, for reference)
- C1 all-future/empty bloom windows → clear 400 (was raw 500)
- C2 blank harvest_date → per-row flag (was crash / silent NaT)
- C3 spike explainer single-year → honest "only one year" message (was fabricated comparison)
- Causal copy softened to associational ("line up with" / "associated with")
