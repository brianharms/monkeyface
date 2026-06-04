# Session Log

This file tracks session handoffs so the next Claude Code instance can quickly get up to speed.

---

## Session — 2026-06-03 22:47

### Goal
Multi-part session that built Project Monkeyface from a brainstorm into a live,
branded, deployed tool — then stress-tested it against Jennifer's real QA data.
Span: brainstorm → spec → plan → TDD implementation → Titan-brand redesign →
UX/comprehension passes → two audits → batch formatter/unify → public GitHub repo
→ live web port at ritual.industries/monkeyface → real-data test.

### Accomplished
- **Full Phase A tool built** (Python/FastAPI + Leaflet/Plotly UI), TDD, 46 tests passing.
- **Titan Frozen Fruit rebrand**: real logo (cropped tagline, links to titanfrozen.com),
  navy #062a46 / strawberry-red #bc2133 palette, 1200px centered layout, footer credit.
- **Guided UX**: stepped flow, plain-language factor table (Driver/Pushes/Strength/How sure
  with hover-for-stats), panel subtitles, honest copy ("line up with" not "cause").
- **Two audits run** (code-correctness + data-honesty). Fixed: C1 empty-window 500→400,
  C2 blank harvest_date crash→per-row flag, C3 single-year spike fabrication→honest message.
- **Batch formatter + UNIFY** (`monkeyface/formatter.py` `consolidate()`): Step 1 = drop many
  messy files → clean + merge into one master.csv. lot_id is primary key; identical re-exports
  dedupe silently, TRUE conflicts (same lot, different data) BLOCK the merge with a clear list.
  Removed the old per-file column-matching Step 2 entirely.
- **Public GitHub repo**: https://github.com/brianharms/monkeyface (Python = canonical).
- **Live web port deployed**: ritual.industries/monkeyface — JS port of the whole pipeline in a
  Cloudflare Worker (engine.js), verified to reproduce Python numbers exactly. Tested live
  end-to-end with real NASA weather on 5 CA/Baja fields.
- **Tested Jennifer's REAL data** (`PSAB_Field_Notes_Master.xlsx`, shared via Drive) — see
  Known Issues; this is the most important finding of the session.

### In Progress / Incomplete
- **THE BIG FINDING (real data gap):** Jennifer's real file is 46,708 QA inspection rows,
  2023–2026, columns: Date, Facility, Inspector, Commodity, Cert, Grower, Crates, Variety,
  Ozs, Defects(Oz), Rot(Oz), Insect%, ..., **Catfaced %**, ... Total%, Comments.
  It has the defect signal (`Catfaced %`) AND 4 years of data — BUT **NO lat/lon, NO field_id,
  no field location at all.** It's keyed by **Grower**, not field. "Facility" = cooling/processing
  plant (not where grown). The tool's entire premise (pull weather from each field's coords)
  cannot run on this. The formatter correctly REJECTS it: "missing required column(s): lot_id,
  field_id, lat, lon". This is a premise the synthetic sample satisfied but reality doesn't.
- **Proposed path forward (awaiting user decision):** build a **grower → coordinates lookup**
  (representative lat/lon per grower or grower+region; Jennifer likely knows roughly where each
  grows). Weather pulled per grower-region instead of per field. Unlocks all 46K rows + 4 years
  (would finally light up the spike explainer with real multi-year signal). User has NOT yet
  approved this direction — do not build without confirmation.
- **Two honesty TODOs unaddressed** (in `TODO.md`): (1) no multiple-comparisons correction
  (~30% false "Strong" at n=12 across 7 factors); (2) map color scale is per-dataset-relative,
  not absolute (not comparable across runs — needs fixed scale + legend).

### Key Decisions
- Python repo = canonical/tested; JS Worker = faithful web port (two codebases, kept in sync).
- GitHub repo PUBLIC (so the site's "View source" link works for visitors).
- Merge rule: block ONLY true conflicts (same lot_id + different data); dedupe identical silently.
- Consolidation produces a downloadable master.csv (human checkpoint), then re-upload to Analyze
  (chose NOT to auto-flow, to keep a review gate on the unified data).
- Hosting: chose to PORT backend to a Cloudflare Worker (vs. landing page or separate Python host).

### Files Changed
- monkeyface (this repo): `monkeyface/formatter.py` (new consolidate), `ingest.py` (_parse_date
  NaT fix, normalize_canonical), `analysis.py` (single-year spike→None), `pipeline.py` (empty→400),
  `app.py` (/api/format consolidate, /api/analyze canonical-only), `static/{index.html,app.js,style.css}`,
  `tests/{test_formatter.py,test_app.py,test_ingest.py}`, `README.md`, `TODO.md`, this file.
- ritual-industries-site (SEPARATE repo): `monkeyface/{engine.js,index.html,app.js,style.css,assets/}`,
  `worker.js` (added /api/monkeyface/format + /analyze routes + json() helper). Already committed
  there as e1be6e6 and deployed.

### Known Issues
- **Real data has no coordinates** (see In Progress) — the #1 blocker for using real data.
- **Defect-column ambiguity:** formatter's `guess_canonical` maps BOTH `Defects (Oz)` and
  `Catfaced %` to `defect_rate`; build_mapping keeps the FIRST seen, which for her file would be
  `Defects (Oz)` (wrong — we want cat-face specifically). Needs a preference for the cat-face
  column. Minor but would silently pick the wrong metric.
- Map color scale relative-not-absolute; no multiple-comparisons correction (TODO.md).

### Running Services
- **STALE uvicorn dev server on port 8000** (PIDs 50739/50742) — `./.venv/bin/uvicorn
  monkeyface.app:app --port 8000 --reload`. Left over from local testing. Safe to kill:
  `lsof -ti:8000 | xargs kill`. The shutdown step will attempt to stop it.
- The LIVE site (ritual.industries/monkeyface) runs on Cloudflare, nothing local needed.

### Next Steps
1. **Decide the grower→location strategy** with the user (path #1 above). If approved: build a
   grower→lat/lon lookup table + adapt formatter/pipeline to accept a grower-keyed file + location
   table, aggregate crate rows to grower×date defect rates, pull regional weather.
2. Fix the defect-column preference (prefer `Catfaced %` over `Defects (Oz)`).
3. Address the two TODO.md honesty items before any real sourcing use.
4. Real data is 4 years — once locations exist, the spike explainer becomes genuinely useful.

### Raw data location
Jennifer's file decoded to `/tmp/PSAB_Field_Notes_Master.xlsx` (5.8 MB, will not persist).
Source: Google Drive file id `1cZXFUi8hQQ3G_xhoUxUqYCv1g3A_2OcU`, shared with
brianthomasharms@gmail.com. Sheet "Field Notes" = 46708×24; "Sheet1" = a pivot summary.
