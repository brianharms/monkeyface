# Project Monkeyface

A tool that tests whether **field-level weather** lines up with the strawberry
**monkey-face / cat-face** defect, and ranks which conditions are associated with
it — built for a strawberry processor's QA team.

Given a spreadsheet of fields (location + harvest date), it pulls each field's
*actual* weather during its bloom/fruit-development window from
[NASA POWER](https://power.larc.nasa.gov/), derives agronomic features
(cold nights, bloom rain, growing-degree-days, etc.), and runs a
confidence-aware analysis of which conditions track the defect rate.

Live web version: **[ritual.industries/monkeyface](https://ritual.industries/monkeyface)**

## The workflow

1. **Normalize & unify** — drop in all your raw field exports at once (different
   growers, seasons, messy column names). Each is cleaned to one canonical schema
   and merged into a single master file. Lot IDs must be unique; a true conflict
   (same lot, different data) blocks the merge so you can resolve it.
2. **Analyze** — upload the master file. The tool fetches each field's weather and
   ranks the conditions associated with the defect, with honest confidence and a
   "could we have seen the spike coming?" view.

## Status

**Phase A.** Defect data is currently **simulated** (with a known injected
relationship that doubles as a pipeline correctness test — the analysis must
recover it), since real defect data isn't collected yet. Swapping to real data is
a config flip (`DATA_MODE = "real"` in `config.py` + a `defect_rate` column).

**Phase B (designed-for, not built):** forecast-based forward risk scoring per
supplier. The fitted relationship and feature pipeline are reused unchanged.

## Run locally (canonical Python version)

    ./run.sh        # creates .venv (Python 3.11), installs deps, opens localhost:8000

## Test

    pytest            # offline unit + pipeline tests
    pytest -m slow    # also hit the real NASA POWER API (needs internet)

## Architecture

- `monkeyface/formatter.py` — normalize + unify raw files into one canonical dataset
- `monkeyface/weather.py` — NASA POWER fetch (cached) + bloom-window calc
- `monkeyface/features.py` — agronomic feature math
- `monkeyface/simulate.py` — simulated defect data (injected relationship)
- `monkeyface/analysis.py` — ridge ranking + correlation CIs + spike explainer
- `monkeyface/pipeline.py` — orchestration
- `monkeyface/app.py` — FastAPI backend
- `static/` — browser UI (Leaflet map + Plotly charts)

The live site at ritual.industries/monkeyface is a JavaScript/Cloudflare-Worker
port of this pipeline; this Python repo is the canonical, tested implementation.

---

🍓 Built with [Claude Code](https://claude.com/claude-code) and Jennifer Urbina.
