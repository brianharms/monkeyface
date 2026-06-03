# monkeyface — Design Spec

**Date:** 2026-06-02
**Status:** Approved design, pre-implementation
**Origin:** Voice memo with Jennifer (QA manager, strawberry processing plant), brainstormed via superpowers.

---

## 1. Problem

A strawberry deformity defect — **"monkey face / cat face"** — had higher prevalence this year at Jennifer's processing plant. She wants to know:

1. **Could this have been predicted** from publicly available data (weather, climate zones of the source fields)?
2. **Which factors most contribute** to the defect?
3. Can that data be accessed **automatically / on an ongoing basis** so risk can be forecast or flagged going forward?

Cat-face is a real, partly weather-driven defect. Its established causes cluster around the **bloom and fruit-set period**: cold nights and temperature swings that disrupt pollination, poor pollination weather (rain/wind/cold suppressing pollinator activity), and insect feeding (lygus bug, thrips) whose pressure is itself partly weather-driven. This gives the project a genuine causal hypothesis rather than a blind correlation hunt.

## 2. Goals & Non-Goals

**Goals**
- **Phase A (validate):** Determine whether weather/climate measured at each field during its bloom/fruit-development window correlates with that lot's defect rate, and rank the contributing factors with honest confidence. Answer "could we have seen the spike coming?"
- **Phase B (forecast, designed-for not built now):** Turn the validated relationship into a forward-looking, tiered **supplier/field risk flag** using forecast weather.
- Deliver a **local web tool**: drop in spreadsheets, get a clear visual representation out.
- Pull **real weather data** from day one, even while defect data is simulated.

**Non-Goals (YAGNI)**
- No hosted/multi-user web service, no accounts, no deployment. Local tool only.
- No precise numeric defect forecaster ("expect 7.3%"). The realistic Phase-B output is a directional risk indicator, not a point prediction.
- No attempt to model every cause. Weather is the core hypothesis; non-weather causes are handled as optional covariates, not first-class models.

## 3. Data Reality (from Jennifer, via brainstorm)

| Aspect | Reality |
| --- | --- |
| Defect data | Defect **rate per lot**, manually traceable to grower. Could be automated later. **<10 years** of history. |
| Volume | **~200+ lots** total across that period. Modest sample. |
| Location | **Field-level coordinates** available (lat/long per field). |
| Timing | Harvest dates known; bloom/fruit-set window derived by working backward from harvest. |
| Geography | **California AND Mexico/Baja** (year-round sourcing). |
| Non-weather data | Possible future grower-practice columns; granularity/detail **unknown** — must not be designed out. |

**Critical near-term constraint:** real defect data is **not yet collected**. The build starts with **simulated defect data** (real weather, fake defect rates) so the entire pipeline — ingest, weather pull, features, analysis, visuals — runs and is validated before real numbers exist.

## 4. Honest Expectations (recorded deliberately)

- **Explanation (Phase A): likely to succeed.** Field-level coords + dates + a known causal mechanism + a spike year (a natural experiment) make it plausible we identify 2–4 weather factors that meaningfully associate with defect rate, with defensible confidence.
- **Prediction (Phase B): a risk flag, not a crystal ball.** ~200 lots supports detecting strong effects and ranking factors, not a precise predictor. The realistic, useful win is a **tiered early-warning** Jennifer uses to decide where to inspect harder or which suppliers to watch.
- **Confounders are real and capped by data:** variety, grower practices, pest management, soil, field age are not in weather data. Lygus/thrips feeding causes cat-face directly and is only partly weather-driven, capping how much variance weather alone can explain.
- **A "weather explains less than hoped" result is still a valuable finding** — it redirects QA attention to non-weather causes. The framework is worth building either way.
- **The simulated-data start is also a correctness test:** the simulator injects a *known* weather→defect relationship; the analysis must recover it. If it can't recover an injected signal, the analysis is broken — caught before trusting real data.

## 5. Architecture

```
Spreadsheet(s)            ┌─────────────────────────────┐
(fields + coords +  ───▶  │  1. INGEST / column-mapping │
 harvest dates;           └──────────────┬──────────────┘
 defect rate = real                      │  normalized lot records
 OR simulated)                           ▼
                          ┌─────────────────────────────┐
                          │  2. WEATHER ENRICHMENT      │  ◀── NASA POWER API
                          │  per field+window, cached   │      (real, CA + MX)
                          └──────────────┬──────────────┘
                                         ▼
                          ┌─────────────────────────────┐
                          │  3. FEATURE BUILDER         │  bloom cold-stress,
                          │  agronomic weather features │  GDD, bloom rain, heat…
                          └──────────────┬──────────────┘
                                         ▼
            ┌────────────────────────────┴───────────────────────┐
            ▼                                                     ▼
 ┌─────────────────────┐                          ┌──────────────────────────┐
 │  4a. SIMULATOR      │  injects known            │  4b. ANALYSIS            │
 │  (defect rate from  │  weather→defect ──▶       │  rank factors, effect    │
 │   weather + noise)  │  relationship             │  sizes, confidence       │
 └─────────────────────┘                          └──────────────┬───────────┘
   (swappable for real defect data later)                        ▼
                                                  ┌──────────────────────────┐
                                                  │  5. WEB UI / VISUALS     │
                                                  │  weather maps & charts,  │
                                                  │  defect-vs-factor plots  │
                                                  └──────────────────────────┘
```

Five units, one job each, clean handoffs. The **simulator (4a) is a pluggable data source** occupying exactly the slot real defect data will later fill — same output schema, so swapping it is a config change, not a rewrite.

## 6. Components

### 1. Ingest / column-mapping
- **Does:** Accepts CSV/Excel. Lets the user map messy columns to canonical fields: `lot_id`, `field_id`, `lat`, `lon`, `harvest_date`, `defect_rate` (optional when simulating), plus optional `grower`, `variety`, and **arbitrary extra columns** (future practice data) carried through untouched. Validates coordinates and dates, flags bad rows.
- **Depends on:** a spreadsheet parser (pandas).
- **Output:** normalized list of lot records (clean, typed).
- **Why isolated:** messy real-world spreadsheets are their own problem; quarantining ingest means the rest of the pipeline only sees clean records.

### 2. Weather enrichment
- **Does:** For each field, derives the **bloom/fruit-development window** by working backward from `harvest_date` (strawberry fruit develops ~25–35 days from bloom; window length configurable). Pulls daily weather for that lat/long/date-range from **NASA POWER** (free, global, no API key, identical coverage for CA and Mexico). Caches every result keyed by `(lat, lon, date_range)`.
- **Depends on:** NASA POWER API.
- **Output:** daily weather time-series per lot.
- **Why isolated:** the core automation and the only external dependency. A clean interface lets the source be swapped or augmented later (e.g., add CIMIS for CA precision) without touching analysis.

### 3. Feature builder
- **Does:** Collapses each lot's daily weather into **agronomically meaningful features**, each encoding a known cat-face mechanism: bloom-window cold-night count (nights below a pollination-disruption threshold), heat-spike days, growing-degree-days, rain-during-bloom, mean/diurnal humidity, diurnal temperature swing, etc. Feature definitions are explicit and reviewable (an agronomist can sanity-check them).
- **Depends on:** unit 2 output.
- **Output:** one feature row per lot.
- **Why isolated:** the agronomy lives here, explicitly — not buried inside a model.

### 4a. Simulator (swappable defect-data source)
- **Does:** Generates a plausible `defect_rate` per lot from the **real** weather features, with a **known, configurable injected relationship** (e.g., cold bloom nights + bloom rain raise defects), realistic noise, and a baseline rate. Optionally adds a faint grower effect to exercise confounder handling.
- **Depends on:** unit 3 real features.
- **Output:** identical record schema to real defect data.
- **Why it matters:** drop-in placeholder **and** ground-truth correctness test for 4b. Swapping to real data is a config flip.

### 4b. Analysis
- **Does:** Ranks which factors — weather features **plus** any grower/practice covariates — associate with defect rate, reporting **effect size, direction, and confidence** for each. With ~200 rows, leads with interpretable methods: correlations and a **regularized regression** (handles correlated weather variables) with confidence intervals. Reports uncertainty honestly — flags weak/thin-sample factors as "suggestive, not conclusive." Includes the **"could we have seen the spike?"** view: was the high-defect year also anomalous in the factors that matter?
- **Depends on:** merged feature + defect table.
- **Output:** ranked factor table + a fitted relationship reusable for Phase-B risk scoring.
- **Why isolated:** separating analysis from simulator and UI lets it be validated against injected truth and reused for forecasting.

### 5. Web UI / visuals (local tool)
- **Does:** The local web tool. Upload spreadsheets → view: a **Leaflet map of fields** (real coordinates, colored by defect rate); **Plotly weather charts** for any field's bloom window (real data, valuable on its own); **defect-vs-factor plots**; the **factor ranking** with confidence; the **spike-year explainer**. A persistent **"DATA: SIMULATED / REAL"** banner so simulated defects are never mistaken for measured ones.
- **Depends on:** analysis + enrichment outputs.
- **Output:** the visual representation.
- **Why isolated:** pure presentation; swapping simulated→real or adding the Phase-B risk readout changes what it shows, not how it's built.

## 7. Non-Weather Variables (design commitment)

Weather is the core hypothesis. **Grower identity and any future practice columns are optional covariates** that (a) help control for confounding and (b) are ranked alongside weather so we can see whether practices or weather explain more. The ingest and analysis layers carry arbitrary extra columns through as candidate factors, so new practice data slots in as more factors to rank — never a redesign. Granularity of that data is currently unknown and the design does not depend on it.

## 8. Phase B (designed-for, not built now)

The fitted relationship from 4b + a field's **forecast** weather (NASA POWER short-range / forecast source, or seasonal outlook) → a **tiered risk flag** per upcoming lot/supplier. Same pipeline; one new input (forecast instead of historical weather) and one new UI view. No new architecture.

## 9. Tech Stack

- **Backend / analysis:** Python — `pandas` (wrangling), `scikit-learn` / `statsmodels` (regularized regression + confidence intervals), `requests` (NASA POWER).
- **Server:** **FastAPI** — minimal local server: upload endpoint, JSON API; trivially hosts the Phase-B risk endpoint later.
- **Frontend:** Browser single-page tool — HTML/CSS/JS, **Plotly** (interactive charts), **Leaflet** (field map). No heavy frontend framework.
- **Cache:** local file cache (SQLite or keyed JSON) for weather results → instant re-runs, polite to the API.
- **Run:** one command (`./run.sh` → opens `localhost:PORT`). No deployment, no accounts.

## 10. Success Criteria

1. Real NASA POWER weather is pulled and visualized for the actual field coordinates (CA + Mexico) — useful on its own, independent of defect data.
2. With simulated defect data, the analysis **recovers the injected relationship**, proving the pipeline is correct end-to-end.
3. The local web tool ingests spreadsheets and produces the field map, weather charts, defect-vs-factor plots, and a confidence-aware factor ranking.
4. Swapping simulated → real defect data is a config change, not a code rewrite.
5. The "could we have seen the spike?" view answers the original question honestly, with stated confidence.
6. The architecture supports adding Phase-B forecast risk scoring without structural change.

## 11. Open Questions (resolve as data arrives)

- Exact bloom-window length / offset from harvest per region/variety (start with a configurable default; refine with Jennifer/an agronomist).
- Which NASA POWER variables map best to the cat-face mechanisms (validate during feature-builder work).
- Real defect-data schema and collection cadence (currently manual; automation is a future step).
- Grower-practice data: availability, granularity, format (unknown; designed to absorb whatever arrives).
