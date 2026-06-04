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

---

## 🚀 Setup on your laptop (for Jennifer + her Claude Code)

You can run the **full tool locally** on your own machine — completely separate
from the live website. Nothing you do locally touches ritual.industries. This is
the right way to experiment, try your own data, and change things.

**If you have Claude Code, just paste this to it:**

> Clone https://github.com/brianharms/monkeyface , set it up, and run it locally.
> It's a Python (FastAPI) web app. It needs **Python 3.11 or 3.12** (NOT 3.13+ —
> the pinned numpy/pandas don't build on newer versions yet). Use `./run.sh`,
> which creates a virtualenv and starts the server at http://localhost:8000.
> If `./run.sh` says it can't find a compatible Python, install one with
> `brew install python@3.12` and re-run it. No API keys or accounts are needed —
> it fetches public NASA weather data. To run the tests: `./.venv/bin/pytest`.

**If you'd rather do it by hand (macOS):**

    # 1. (once) install a compatible Python if you don't have one
    brew install python@3.12

    # 2. get the code
    git clone https://github.com/brianharms/monkeyface
    cd monkeyface

    # 3. run it — first run builds the environment, then opens your browser
    ./run.sh

That's it. The tool opens at **http://localhost:8000**. Press Ctrl-C to stop.

**Things to know:**
- **No accounts, no API keys, no payment** — weather comes from the free public
  NASA POWER API. You only need an internet connection.
- **Your data stays on your machine.** Files you upload are processed locally.
- There's a sample file at `sample_data/fields_sample.csv` to try it immediately.
- **Heads up — real data needs field coordinates.** The current tool needs each
  row to have a latitude/longitude and harvest date. The QA export
  (`PSAB_Field_Notes_Master.xlsx`) is organized by *grower* and has no field
  coordinates, so it can't be analyzed as-is yet — see `SESSION_LOG.md` and
  `TODO.md` for the plan to bridge grower → location.
- To edit and see changes: the server auto-reloads on save (`--reload`).

---

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

    ./run.sh        # creates .venv (Python 3.11/3.12), installs deps, opens localhost:8000

(See the **Setup on your laptop** section above for a full walkthrough.)

## Test

    ./.venv/bin/pytest          # offline unit + pipeline tests
    ./.venv/bin/pytest -m slow  # also hit the real NASA POWER API (needs internet)

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
