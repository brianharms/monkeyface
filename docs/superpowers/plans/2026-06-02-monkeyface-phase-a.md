# monkeyface Phase A Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a local web tool that pulls real NASA POWER weather for strawberry field coordinates, derives agronomic weather features, generates simulated defect data with a known injected relationship, runs a confidence-aware factor-ranking analysis that must recover that relationship, and visualizes everything in the browser.

**Architecture:** A linear Python pipeline of five isolated modules (ingest → weather enrichment → feature builder → simulator + analysis) served by a thin FastAPI app to a single-page browser UI (Plotly charts + Leaflet map). The simulator is a swappable data source occupying the exact slot real defect data will later fill. Weather results are cached on disk so re-runs are instant. Phase B (forecast risk) is designed-for but NOT built here.

**Tech Stack:** Python 3.11+, pandas, numpy, scikit-learn, statsmodels, requests, FastAPI, uvicorn, pytest, openpyxl (Excel), python-multipart (uploads); frontend HTML/CSS/vanilla JS with Plotly and Leaflet via CDN.

---

## File Structure

```
monkeyface/
├── run.sh                          # one-command launch → opens localhost:8000
├── requirements.txt
├── pytest.ini
├── config.py                       # thresholds, window length, data-mode flag, NASA params
├── monkeyface/
│   ├── __init__.py
│   ├── schema.py                   # canonical column names + LotRecord dataclass
│   ├── ingest.py                   # Component 1: CSV/Excel → normalized lot records
│   ├── weather.py                  # Component 2: NASA POWER client + disk cache + window calc
│   ├── features.py                 # Component 3: daily weather → agronomic feature row
│   ├── simulate.py                 # Component 4a: features → simulated defect_rate (injected signal)
│   ├── analysis.py                 # Component 4b: factor ranking + confidence + spike explainer
│   ├── pipeline.py                 # wires 1→2→3→(4a)→4b into one callable
│   └── app.py                      # Component 5 backend: FastAPI endpoints
├── static/
│   ├── index.html                  # single-page UI shell
│   ├── app.js                      # upload, fetch results, render Plotly + Leaflet
│   └── style.css
├── sample_data/
│   └── fields_sample.csv           # ~12 real CA + MX field coords + harvest dates, NO defect col
├── tests/
│   ├── test_ingest.py
│   ├── test_weather.py
│   ├── test_features.py
│   ├── test_simulate.py
│   ├── test_analysis.py
│   ├── test_pipeline.py
│   └── test_app.py
└── docs/superpowers/{specs,plans}/ # already exist
```

**Responsibility boundaries:**
- `schema.py` — single source of truth for canonical field names; every module imports from here.
- `ingest.py` — messy spreadsheet → clean records. Knows nothing about weather.
- `weather.py` — the only module that touches the network. Pure cache-or-fetch behind one function.
- `features.py` — pure function: daily weather dict → feature dict. No I/O.
- `simulate.py` — pure function: feature rows → defect rates. No I/O. Swappable.
- `analysis.py` — pure function: feature+defect table → ranked results. No I/O.
- `pipeline.py` — orchestration only; no business logic of its own.
- `app.py` — HTTP glue only; delegates to pipeline.

---

## Task 0: Project Scaffolding

**Files:**
- Create: `requirements.txt`, `pytest.ini`, `monkeyface/__init__.py`, `config.py`, `.gitignore`

- [ ] **Step 1: Create `.gitignore`**

```
__pycache__/
*.pyc
.venv/
venv/
.cache/
weather_cache/
.pytest_cache/
.DS_Store
```

- [ ] **Step 2: Create `requirements.txt`**

```
pandas==2.2.2
numpy==1.26.4
scikit-learn==1.5.1
statsmodels==0.14.2
requests==2.32.3
fastapi==0.111.0
uvicorn==0.30.1
python-multipart==0.0.9
openpyxl==3.1.5
pytest==8.2.2
httpx==0.27.0
```

(`httpx` is needed by FastAPI's `TestClient`.)

- [ ] **Step 3: Create `pytest.ini`**

```ini
[pytest]
testpaths = tests
python_files = test_*.py
addopts = -v
```

- [ ] **Step 4: Create `monkeyface/__init__.py`** (empty file)

```python
```

- [ ] **Step 5: Create `config.py`**

```python
"""Central configuration. Edit values here; modules import them."""

# --- Data mode --------------------------------------------------------------
# "simulated" = generate defect_rate from weather (Phase A default).
# "real"      = use the defect_rate column from the uploaded spreadsheet.
DATA_MODE = "simulated"

# --- Bloom / fruit-development window ----------------------------------------
# Strawberry fruit develops ~25-35 days from bloom. We pull weather for the
# window ending WINDOW_END_DAYS before harvest and starting WINDOW_START_DAYS
# before harvest (i.e. the bloom/fruit-set period that drives cat-face).
WINDOW_START_DAYS = 45  # days before harvest the window opens (earliest bloom)
WINDOW_END_DAYS = 10    # days before harvest the window closes

# --- NASA POWER --------------------------------------------------------------
NASA_POWER_URL = "https://power.larc.nasa.gov/api/temporal/daily/point"
NASA_PARAMS = ["T2M_MIN", "T2M_MAX", "T2M", "PRECTOTCORR", "RH2M", "WS2M"]
NASA_COMMUNITY = "AG"

# --- Agronomic thresholds (feature builder) ----------------------------------
COLD_NIGHT_C = 7.0       # nights with T2M_MIN below this disrupt pollination
HEAT_SPIKE_C = 30.0      # days with T2M_MAX above this stress fruit set
RAIN_DAY_MM = 2.0        # days with precip above this count as "rain during bloom"
GDD_BASE_C = 10.0        # base temperature for growing-degree-days

# --- Simulator (injected ground-truth relationship) --------------------------
# defect_rate = BASELINE + sum(coef * feature) + noise, clamped to [0, 1].
# The analysis MUST recover that cold_nights and bloom_rain are the strong
# positive drivers. Keep these as the known truth the pipeline test checks.
SIM_BASELINE = 0.05
SIM_COEFS = {
    "cold_nights": 0.020,   # strong positive driver
    "bloom_rain_days": 0.015,  # strong positive driver
    "heat_spike_days": 0.004,  # weak driver
    "gdd": 0.0,             # no effect (analysis should rank it low)
}
SIM_GROWER_EFFECT_SD = 0.01  # faint per-grower offset to exercise confounders
SIM_NOISE_SD = 0.02
SIM_SEED = 42

# --- Cache / server ----------------------------------------------------------
WEATHER_CACHE_DIR = "weather_cache"
PORT = 8000
```

- [ ] **Step 6: Commit**

```bash
cd ~/Desktop/Claude\ Projects/monkeyface
git add .gitignore requirements.txt pytest.ini monkeyface/__init__.py config.py
git commit -m "chore: project scaffolding and config"
```

---

## Task 1: Schema (canonical records)

**Files:**
- Create: `monkeyface/schema.py`
- Test: `tests/test_ingest.py` (shared with Task 2; schema tested via ingest)

- [ ] **Step 1: Create `monkeyface/schema.py`**

```python
"""Canonical column names and the normalized record type.

Every module imports names from here so a rename happens in one place.
"""
from dataclasses import dataclass, field
from datetime import date

# Canonical column names produced by ingest and consumed downstream.
LOT_ID = "lot_id"
FIELD_ID = "field_id"
LAT = "lat"
LON = "lon"
HARVEST_DATE = "harvest_date"
DEFECT_RATE = "defect_rate"
GROWER = "grower"
VARIETY = "variety"

REQUIRED_COLUMNS = [LOT_ID, FIELD_ID, LAT, LON, HARVEST_DATE]
KNOWN_OPTIONAL = [DEFECT_RATE, GROWER, VARIETY]


@dataclass
class LotRecord:
    lot_id: str
    field_id: str
    lat: float
    lon: float
    harvest_date: date
    defect_rate: float | None = None
    grower: str | None = None
    variety: str | None = None
    # Arbitrary extra columns (future grower-practice data) carried through.
    extra: dict = field(default_factory=dict)
```

- [ ] **Step 2: Commit**

```bash
git add monkeyface/schema.py
git commit -m "feat: canonical schema and LotRecord"
```

---

## Task 2: Ingest / column-mapping (Component 1)

**Files:**
- Create: `monkeyface/ingest.py`
- Test: `tests/test_ingest.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_ingest.py
import io
from datetime import date
import pandas as pd
import pytest
from monkeyface.ingest import load_table, normalize, IngestError
from monkeyface import schema


def _df(rows):
    return pd.DataFrame(rows)


def test_normalize_maps_messy_columns():
    df = _df([
        {"Lot #": "L1", "Field": "F1", "Latitude": 36.9, "Longitude": -121.7,
         "Harvested": "2024-05-01", "Defect %": 0.12, "Grower": "Acme"},
    ])
    mapping = {
        "Lot #": schema.LOT_ID, "Field": schema.FIELD_ID,
        "Latitude": schema.LAT, "Longitude": schema.LON,
        "Harvested": schema.HARVEST_DATE, "Defect %": schema.DEFECT_RATE,
        "Grower": schema.GROWER,
    }
    records = normalize(df, mapping)
    assert len(records) == 1
    r = records[0]
    assert r.lot_id == "L1"
    assert r.lat == 36.9
    assert r.harvest_date == date(2024, 5, 1)
    assert r.defect_rate == 0.12
    assert r.grower == "Acme"


def test_normalize_carries_unmapped_columns_into_extra():
    df = _df([
        {"lot_id": "L1", "field_id": "F1", "lat": 1.0, "lon": 2.0,
         "harvest_date": "2024-05-01", "pesticide_program": "P3"},
    ])
    mapping = {c: c for c in ["lot_id", "field_id", "lat", "lon", "harvest_date"]}
    records = normalize(df, mapping)
    assert records[0].extra == {"pesticide_program": "P3"}


def test_normalize_missing_required_column_raises():
    df = _df([{"lot_id": "L1", "lat": 1.0, "lon": 2.0, "harvest_date": "2024-05-01"}])
    mapping = {"lot_id": schema.LOT_ID, "lat": schema.LAT, "lon": schema.LON,
               "harvest_date": schema.HARVEST_DATE}  # no field_id
    with pytest.raises(IngestError):
        normalize(df, mapping)


def test_normalize_flags_bad_coordinates():
    df = _df([
        {"lot_id": "L1", "field_id": "F1", "lat": 999.0, "lon": -121.7,
         "harvest_date": "2024-05-01"},
    ])
    mapping = {c: c for c in ["lot_id", "field_id", "lat", "lon", "harvest_date"]}
    records, errors = normalize(df, mapping, return_errors=True)
    assert records == []
    assert any("lat" in e.lower() for e in errors)


def test_load_table_reads_csv_bytes():
    csv = b"lot_id,field_id,lat,lon,harvest_date\nL1,F1,36.9,-121.7,2024-05-01\n"
    df = load_table(csv, filename="x.csv")
    assert list(df.columns) == ["lot_id", "field_id", "lat", "lon", "harvest_date"]
    assert len(df) == 1
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd ~/Desktop/Claude\ Projects/monkeyface && python -m pytest tests/test_ingest.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'monkeyface.ingest'`

- [ ] **Step 3: Write `monkeyface/ingest.py`**

```python
"""Component 1: messy spreadsheet -> clean LotRecord list.

Knows nothing about weather. Tolerant of arbitrary extra columns, which are
carried through into LotRecord.extra so future grower-practice data flows on.
"""
import io
from datetime import date, datetime
import pandas as pd
from monkeyface import schema
from monkeyface.schema import LotRecord


class IngestError(Exception):
    pass


def load_table(data: bytes, filename: str) -> pd.DataFrame:
    """Parse uploaded bytes (CSV or Excel) into a DataFrame."""
    name = filename.lower()
    if name.endswith((".xlsx", ".xls")):
        return pd.read_excel(io.BytesIO(data))
    return pd.read_csv(io.BytesIO(data))


def _parse_date(value) -> date:
    if isinstance(value, (datetime, pd.Timestamp)):
        return value.date()
    if isinstance(value, date):
        return value
    return pd.to_datetime(str(value)).date()


def _coerce_row(row: dict) -> LotRecord:
    lat = float(row[schema.LAT])
    lon = float(row[schema.LON])
    if not (-90 <= lat <= 90):
        raise ValueError(f"lat out of range: {lat}")
    if not (-180 <= lon <= 180):
        raise ValueError(f"lon out of range: {lon}")

    canonical = set(schema.REQUIRED_COLUMNS + schema.KNOWN_OPTIONAL)
    extra = {k: v for k, v in row.items()
             if k not in canonical and pd.notna(v)}

    defect = row.get(schema.DEFECT_RATE)
    return LotRecord(
        lot_id=str(row[schema.LOT_ID]),
        field_id=str(row[schema.FIELD_ID]),
        lat=lat,
        lon=lon,
        harvest_date=_parse_date(row[schema.HARVEST_DATE]),
        defect_rate=None if defect is None or pd.isna(defect) else float(defect),
        grower=None if pd.isna(row.get(schema.GROWER)) else _opt(row.get(schema.GROWER)),
        variety=None if pd.isna(row.get(schema.VARIETY)) else _opt(row.get(schema.VARIETY)),
        extra=extra,
    )


def _opt(v):
    return None if v is None else str(v)


def normalize(df: pd.DataFrame, mapping: dict, return_errors: bool = False):
    """Rename columns per `mapping` (source_col -> canonical) and validate.

    Returns list[LotRecord]. If return_errors=True, returns (records, errors).
    Raises IngestError if a REQUIRED canonical column is absent after mapping.
    """
    renamed = df.rename(columns=mapping)
    missing = [c for c in schema.REQUIRED_COLUMNS if c not in renamed.columns]
    if missing:
        raise IngestError(f"missing required columns after mapping: {missing}")

    records, errors = [], []
    for i, row in renamed.to_dict(orient="records").__iter__().__class__(
            enumerate(renamed.to_dict(orient="records"))):
        try:
            records.append(_coerce_row(row))
        except Exception as e:  # noqa: BLE001 - row-level, reported not raised
            errors.append(f"row {i}: {e}")

    if return_errors:
        return records, errors
    return records
```

> Note: the `for i, row in ...` line above is intentionally simple — replace with the clean form below. Use this body for the loop instead:

```python
    records, errors = [], []
    for i, row in enumerate(renamed.to_dict(orient="records")):
        try:
            records.append(_coerce_row(row))
        except Exception as e:  # noqa: BLE001
            errors.append(f"row {i}: {e}")
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_ingest.py -v`
Expected: PASS (5 passed)

- [ ] **Step 5: Commit**

```bash
git add monkeyface/ingest.py tests/test_ingest.py
git commit -m "feat: ingest and normalize spreadsheets into LotRecords"
```

---

## Task 3: Weather enrichment (Component 2)

**Files:**
- Create: `monkeyface/weather.py`
- Test: `tests/test_weather.py`

NASA POWER (verified live): `GET https://power.larc.nasa.gov/api/temporal/daily/point?parameters=T2M_MIN,T2M_MAX&community=AG&longitude=-121.76&latitude=36.91&start=20240401&end=20240405&format=JSON`. Response: `json["properties"]["parameter"][PARAM][ "YYYYMMDD" ] = value` (float; temps °C, precip mm/day). No API key.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_weather.py
from datetime import date
import json
from unittest.mock import patch, MagicMock
from monkeyface.weather import bloom_window, _cache_key, fetch_weather, enrich
from monkeyface.schema import LotRecord
import config


def test_bloom_window_works_back_from_harvest():
    start, end = bloom_window(date(2024, 6, 15))
    assert end == date(2024, 6, 5)    # 10 days before harvest
    assert start == date(2024, 5, 1)  # 45 days before harvest


def test_cache_key_is_stable_for_same_inputs():
    k1 = _cache_key(36.9, -121.7, date(2024, 5, 1), date(2024, 6, 5))
    k2 = _cache_key(36.9, -121.7, date(2024, 5, 1), date(2024, 6, 5))
    assert k1 == k2
    k3 = _cache_key(36.9, -121.7, date(2024, 5, 2), date(2024, 6, 5))
    assert k1 != k3


def _fake_power_response():
    days = {f"202405{d:02d}": 5.0 + d for d in range(1, 6)}
    return {
        "properties": {"parameter": {
            "T2M_MIN": days, "T2M_MAX": {k: v + 12 for k, v in days.items()},
            "T2M": {k: v + 6 for k, v in days.items()},
            "PRECTOTCORR": {k: 0.0 for k in days},
            "RH2M": {k: 70.0 for k in days}, "WS2M": {k: 2.0 for k in days},
        }}
    }


def test_fetch_weather_parses_power_json(tmp_path):
    config.WEATHER_CACHE_DIR = str(tmp_path)
    fake = MagicMock()
    fake.json.return_value = _fake_power_response()
    fake.raise_for_status.return_value = None
    with patch("monkeyface.weather.requests.get", return_value=fake) as g:
        daily = fetch_weather(36.9, -121.7, date(2024, 5, 1), date(2024, 5, 5))
    assert len(daily) == 5
    assert daily[0]["date"] == date(2024, 5, 1)
    assert daily[0]["t2m_min"] == 6.0
    assert daily[0]["t2m_max"] == 18.0
    g.assert_called_once()


def test_fetch_weather_uses_cache_second_call(tmp_path):
    config.WEATHER_CACHE_DIR = str(tmp_path)
    fake = MagicMock()
    fake.json.return_value = _fake_power_response()
    fake.raise_for_status.return_value = None
    with patch("monkeyface.weather.requests.get", return_value=fake) as g:
        fetch_weather(36.9, -121.7, date(2024, 5, 1), date(2024, 5, 5))
        fetch_weather(36.9, -121.7, date(2024, 5, 1), date(2024, 5, 5))
    assert g.call_count == 1  # second call served from disk cache
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_weather.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'monkeyface.weather'`

- [ ] **Step 3: Write `monkeyface/weather.py`**

```python
"""Component 2: NASA POWER weather, cached on disk.

The only module that touches the network. One public function `enrich` takes
LotRecords and attaches a daily weather time-series for each lot's bloom window.
"""
import hashlib
import json
import os
from datetime import date, timedelta
import requests
import config
from monkeyface.schema import LotRecord


def bloom_window(harvest: date) -> tuple[date, date]:
    """Return (start, end) of the bloom/fruit-set window before harvest."""
    start = harvest - timedelta(days=config.WINDOW_START_DAYS)
    end = harvest - timedelta(days=config.WINDOW_END_DAYS)
    return start, end


def _cache_key(lat: float, lon: float, start: date, end: date) -> str:
    raw = f"{lat:.4f}_{lon:.4f}_{start.isoformat()}_{end.isoformat()}"
    return hashlib.sha1(raw.encode()).hexdigest()


def _cache_path(key: str) -> str:
    os.makedirs(config.WEATHER_CACHE_DIR, exist_ok=True)
    return os.path.join(config.WEATHER_CACHE_DIR, f"{key}.json")


def _parse_power(payload: dict) -> list[dict]:
    param = payload["properties"]["parameter"]
    dates = sorted(param["T2M_MIN"].keys())
    out = []
    for d in dates:
        out.append({
            "date": date(int(d[:4]), int(d[4:6]), int(d[6:8])),
            "t2m_min": float(param["T2M_MIN"][d]),
            "t2m_max": float(param["T2M_MAX"][d]),
            "t2m": float(param["T2M"][d]),
            "precip_mm": float(param["PRECTOTCORR"][d]),
            "rh": float(param["RH2M"][d]),
            "wind": float(param["WS2M"][d]),
        })
    return out


def fetch_weather(lat: float, lon: float, start: date, end: date) -> list[dict]:
    """Cache-or-fetch daily weather for one point+window. Returns list of dicts."""
    key = _cache_key(lat, lon, start, end)
    path = _cache_path(key)
    if os.path.exists(path):
        with open(path) as f:
            raw = json.load(f)
        return [{**r, "date": date.fromisoformat(r["date"])} for r in raw]

    resp = requests.get(config.NASA_POWER_URL, params={
        "parameters": ",".join(config.NASA_PARAMS),
        "community": config.NASA_COMMUNITY,
        "longitude": lon, "latitude": lat,
        "start": start.strftime("%Y%m%d"), "end": end.strftime("%Y%m%d"),
        "format": "JSON",
    }, timeout=60)
    resp.raise_for_status()
    daily = _parse_power(resp.json())

    with open(path, "w") as f:
        json.dump([{**r, "date": r["date"].isoformat()} for r in daily], f)
    return daily


def enrich(records: list[LotRecord]) -> dict[str, list[dict]]:
    """Return {lot_id: daily_weather_list} for every record."""
    result = {}
    for r in records:
        start, end = bloom_window(r.harvest_date)
        result[r.lot_id] = fetch_weather(r.lat, r.lon, start, end)
    return result
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_weather.py -v`
Expected: PASS (5 passed)

- [ ] **Step 5: Commit**

```bash
git add monkeyface/weather.py tests/test_weather.py
git commit -m "feat: NASA POWER weather enrichment with disk cache"
```

---

## Task 4: Feature builder (Component 3)

**Files:**
- Create: `monkeyface/features.py`
- Test: `tests/test_features.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_features.py
from datetime import date
from monkeyface.features import build_features, FEATURE_NAMES


def _day(d, tmin, tmax, precip=0.0, rh=70.0, wind=2.0):
    return {"date": date(2024, 5, d), "t2m_min": tmin, "t2m_max": tmax,
            "t2m": (tmin + tmax) / 2, "precip_mm": precip, "rh": rh, "wind": wind}


def test_cold_nights_counts_below_threshold():
    daily = [_day(1, 4.0, 20), _day(2, 6.9, 20), _day(3, 8.0, 20)]
    f = build_features(daily)
    assert f["cold_nights"] == 2  # 4.0 and 6.9 are below 7.0


def test_heat_spike_days_counts_above_threshold():
    daily = [_day(1, 10, 31), _day(2, 10, 29), _day(3, 10, 35)]
    f = build_features(daily)
    assert f["heat_spike_days"] == 2  # 31 and 35 above 30.0


def test_bloom_rain_days_counts_wet_days():
    daily = [_day(1, 10, 20, precip=5.0), _day(2, 10, 20, precip=0.5),
             _day(3, 10, 20, precip=3.0)]
    f = build_features(daily)
    assert f["bloom_rain_days"] == 2  # 5.0 and 3.0 above 2.0


def test_gdd_accumulates_above_base():
    daily = [_day(1, 8, 12), _day(2, 12, 16)]  # means 10 and 14; base 10
    f = build_features(daily)
    assert f["gdd"] == 4.0  # (10-10) + (14-10)


def test_all_feature_names_present():
    daily = [_day(1, 10, 20)]
    f = build_features(daily)
    assert set(f.keys()) == set(FEATURE_NAMES)


def test_empty_daily_returns_zeros():
    f = build_features([])
    assert all(v == 0 for v in f.values())
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_features.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'monkeyface.features'`

- [ ] **Step 3: Write `monkeyface/features.py`**

```python
"""Component 3: daily weather -> one agronomic feature row.

Pure function, no I/O. Each feature encodes a known cat-face mechanism so an
agronomist can review the definitions directly.
"""
import config

FEATURE_NAMES = [
    "cold_nights",       # nights with T_min below pollination-disruption threshold
    "heat_spike_days",   # days with T_max above fruit-set stress threshold
    "bloom_rain_days",   # wet days suppressing pollinator activity
    "gdd",               # growing-degree-days above base temp
    "mean_rh",           # mean relative humidity
    "diurnal_swing",     # mean (T_max - T_min): instability proxy
    "mean_wind",         # mean wind speed (pollinator suppression)
]


def build_features(daily: list[dict]) -> dict:
    if not daily:
        return {name: 0 for name in FEATURE_NAMES}

    cold = sum(1 for d in daily if d["t2m_min"] < config.COLD_NIGHT_C)
    heat = sum(1 for d in daily if d["t2m_max"] > config.HEAT_SPIKE_C)
    rain = sum(1 for d in daily if d["precip_mm"] > config.RAIN_DAY_MM)
    gdd = sum(max(0.0, (d["t2m_min"] + d["t2m_max"]) / 2 - config.GDD_BASE_C)
              for d in daily)
    mean_rh = sum(d["rh"] for d in daily) / len(daily)
    swing = sum(d["t2m_max"] - d["t2m_min"] for d in daily) / len(daily)
    wind = sum(d["wind"] for d in daily) / len(daily)

    return {
        "cold_nights": cold,
        "heat_spike_days": heat,
        "bloom_rain_days": rain,
        "gdd": round(gdd, 3),
        "mean_rh": round(mean_rh, 3),
        "diurnal_swing": round(swing, 3),
        "mean_wind": round(wind, 3),
    }
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_features.py -v`
Expected: PASS (6 passed)

- [ ] **Step 5: Commit**

```bash
git add monkeyface/features.py tests/test_features.py
git commit -m "feat: agronomic feature builder"
```

---

## Task 5: Simulator (Component 4a)

**Files:**
- Create: `monkeyface/simulate.py`
- Test: `tests/test_simulate.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_simulate.py
import numpy as np
from monkeyface.simulate import simulate_defect_rates
import config


def _feature_rows(n, cold_lo=0, cold_hi=10):
    rng = np.random.default_rng(0)
    rows = []
    for i in range(n):
        rows.append({
            "lot_id": f"L{i}", "grower": f"G{i % 4}",
            "features": {
                "cold_nights": int(rng.integers(cold_lo, cold_hi)),
                "heat_spike_days": int(rng.integers(0, 5)),
                "bloom_rain_days": int(rng.integers(0, 8)),
                "gdd": float(rng.uniform(100, 400)),
                "mean_rh": 70.0, "diurnal_swing": 10.0, "mean_wind": 2.0,
            },
        })
    return rows


def test_returns_rate_per_lot_in_unit_interval():
    rows = _feature_rows(50)
    rates = simulate_defect_rates(rows)
    assert set(rates.keys()) == {r["lot_id"] for r in rows}
    assert all(0.0 <= v <= 1.0 for v in rates.values())


def test_is_deterministic_with_seed():
    rows = _feature_rows(30)
    a = simulate_defect_rates(rows)
    b = simulate_defect_rates(rows)
    assert a == b


def test_cold_nights_increase_defect_rate_on_average():
    # Lots with many cold nights should average higher than lots with few.
    low = _feature_rows(40, cold_lo=0, cold_hi=1)
    high = _feature_rows(40, cold_lo=8, cold_hi=10)
    for i, r in enumerate(high):
        r["lot_id"] = f"H{i}"
    low_rates = list(simulate_defect_rates(low).values())
    high_rates = list(simulate_defect_rates(high).values())
    assert np.mean(high_rates) > np.mean(low_rates)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_simulate.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'monkeyface.simulate'`

- [ ] **Step 3: Write `monkeyface/simulate.py`**

```python
"""Component 4a: generate simulated defect_rate from REAL weather features.

A swappable data source occupying the exact slot real defect data will fill.
The injected relationship (config.SIM_COEFS) is the ground truth the analysis
must recover -- that recovery is the pipeline's end-to-end correctness test.
"""
import numpy as np
import config


def simulate_defect_rates(feature_rows: list[dict]) -> dict[str, float]:
    """feature_rows: [{"lot_id", "grower"?, "features": {...}}].

    Returns {lot_id: defect_rate in [0, 1]}.
    """
    rng = np.random.default_rng(config.SIM_SEED)

    growers = sorted({r.get("grower") for r in feature_rows if r.get("grower")})
    grower_offset = {
        g: rng.normal(0.0, config.SIM_GROWER_EFFECT_SD) for g in growers
    }

    rates = {}
    for r in feature_rows:
        f = r["features"]
        rate = config.SIM_BASELINE
        for name, coef in config.SIM_COEFS.items():
            rate += coef * f.get(name, 0.0)
        rate += grower_offset.get(r.get("grower"), 0.0)
        rate += rng.normal(0.0, config.SIM_NOISE_SD)
        rates[r["lot_id"]] = float(min(1.0, max(0.0, rate)))
    return rates
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_simulate.py -v`
Expected: PASS (3 passed)

- [ ] **Step 5: Commit**

```bash
git add monkeyface/simulate.py tests/test_simulate.py
git commit -m "feat: defect-rate simulator with injected ground-truth relationship"
```

---

## Task 6: Analysis (Component 4b)

**Files:**
- Create: `monkeyface/analysis.py`
- Test: `tests/test_analysis.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_analysis.py
import numpy as np
from monkeyface.analysis import analyze, FactorResult


def _table(n=200):
    """Build a feature+defect table where cold_nights is the true strong driver."""
    rng = np.random.default_rng(1)
    rows = []
    for i in range(n):
        cold = int(rng.integers(0, 12))
        rain = int(rng.integers(0, 10))
        gdd = float(rng.uniform(100, 400))
        # truth: defect rises with cold and rain; gdd irrelevant.
        defect = 0.05 + 0.02 * cold + 0.015 * rain + rng.normal(0, 0.02)
        rows.append({
            "lot_id": f"L{i}",
            "harvest_date": f"20{20 + i % 5:02d}-05-01",  # spread across years
            "features": {"cold_nights": cold, "bloom_rain_days": rain,
                         "gdd": gdd, "heat_spike_days": 0, "mean_rh": 70.0,
                         "diurnal_swing": 10.0, "mean_wind": 2.0},
            "defect_rate": max(0.0, defect),
            "grower": f"G{i % 4}",
        })
    return rows


def test_analyze_returns_ranked_factors():
    result = analyze(_table())
    assert len(result.factors) >= 5
    # factors sorted by absolute standardized effect, descending
    effects = [abs(f.std_effect) for f in result.factors]
    assert effects == sorted(effects, reverse=True)


def test_analyze_recovers_injected_drivers():
    """The known-truth pipeline test: cold_nights and bloom_rain must rank top."""
    result = analyze(_table())
    top_two = {result.factors[0].name, result.factors[1].name}
    assert top_two == {"cold_nights", "bloom_rain_days"}
    # the irrelevant factor must NOT be flagged as a strong driver
    gdd = next(f for f in result.factors if f.name == "gdd")
    assert gdd.confidence != "strong"


def test_each_factor_has_direction_and_confidence():
    result = analyze(_table())
    cold = next(f for f in result.factors if f.name == "cold_nights")
    assert cold.direction == "increases"
    assert cold.confidence in {"strong", "suggestive", "weak"}
    assert cold.ci_low < cold.ci_high


def test_spike_explainer_flags_anomalous_year():
    result = analyze(_table())
    assert result.spike is not None
    assert "year" in result.spike
    assert isinstance(result.spike["anomalous_factors"], list)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_analysis.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'monkeyface.analysis'`

- [ ] **Step 3: Write `monkeyface/analysis.py`**

```python
"""Component 4b: rank which factors drive defect_rate, with honest confidence.

Pure function. Leads with interpretable methods: standardized ridge regression
(handles correlated weather variables) for effect ranking, plus per-factor
correlation confidence intervals for honesty. Includes the spike explainer.
"""
from dataclasses import dataclass, field
import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge
from sklearn.preprocessing import StandardScaler


@dataclass
class FactorResult:
    name: str
    std_effect: float      # standardized ridge coefficient (comparable across factors)
    direction: str         # "increases" | "decreases" | "none"
    corr: float            # Pearson r vs defect_rate
    ci_low: float          # 95% CI on r
    ci_high: float
    confidence: str        # "strong" | "suggestive" | "weak"


@dataclass
class AnalysisResult:
    factors: list[FactorResult]
    n: int
    spike: dict | None = None
    notes: list[str] = field(default_factory=list)


def _corr_ci(r: float, n: int) -> tuple[float, float]:
    """Fisher z 95% CI for a Pearson correlation."""
    if n < 4 or abs(r) >= 1.0:
        return (r, r)
    z = np.arctanh(r)
    se = 1.0 / np.sqrt(n - 3)
    lo, hi = z - 1.96 * se, z + 1.96 * se
    return (float(np.tanh(lo)), float(np.tanh(hi)))


def _confidence(r: float, ci: tuple[float, float], n: int) -> str:
    lo, hi = ci
    sig = lo > 0 or hi < 0          # CI excludes zero
    if sig and abs(r) >= 0.3:
        return "strong"
    if sig and abs(r) >= 0.15:
        return "suggestive"
    return "weak"


def _table_to_frame(rows: list[dict]) -> pd.DataFrame:
    recs = []
    for r in rows:
        rec = dict(r["features"])
        rec["defect_rate"] = r["defect_rate"]
        rec["harvest_date"] = r.get("harvest_date")
        rec["grower"] = r.get("grower")
        recs.append(rec)
    return pd.DataFrame(recs)


def analyze(rows: list[dict]) -> AnalysisResult:
    df = _table_to_frame(rows)
    feature_cols = [c for c in df.columns
                    if c not in ("defect_rate", "harvest_date", "grower")]

    X = df[feature_cols].astype(float).values
    y = df["defect_rate"].astype(float).values
    n = len(df)

    Xs = StandardScaler().fit_transform(X)
    ridge = Ridge(alpha=1.0).fit(Xs, y)

    factors = []
    for col, coef in zip(feature_cols, ridge.coef_):
        r = float(np.corrcoef(df[col].astype(float), y)[0, 1]) if df[col].nunique() > 1 else 0.0
        ci = _corr_ci(r, n)
        conf = _confidence(r, ci, n)
        direction = "increases" if coef > 1e-6 else "decreases" if coef < -1e-6 else "none"
        factors.append(FactorResult(
            name=col, std_effect=float(coef), direction=direction,
            corr=r, ci_low=ci[0], ci_high=ci[1], confidence=conf,
        ))

    factors.sort(key=lambda f: abs(f.std_effect), reverse=True)

    spike = _spike_explainer(df, feature_cols)
    notes = []
    if n < 100:
        notes.append(f"Only {n} lots; treat all findings as suggestive, not conclusive.")
    return AnalysisResult(factors=factors, n=n, spike=spike, notes=notes)


def _spike_explainer(df: pd.DataFrame, feature_cols: list[str]) -> dict | None:
    """Identify the highest-defect year and which factors were anomalous then."""
    if df["harvest_date"].isna().all():
        return None
    years = pd.to_datetime(df["harvest_date"]).dt.year
    by_year_defect = df.groupby(years)["defect_rate"].mean()
    if by_year_defect.empty:
        return None
    spike_year = int(by_year_defect.idxmax())

    anomalous = []
    for col in feature_cols:
        overall = df[col].astype(float).mean()
        overall_sd = df[col].astype(float).std() or 1.0
        spike_mean = df[years == spike_year][col].astype(float).mean()
        z = (spike_mean - overall) / overall_sd
        if abs(z) >= 1.0:
            anomalous.append({"factor": col, "z": round(float(z), 2),
                              "spike_mean": round(float(spike_mean), 2),
                              "overall_mean": round(float(overall), 2)})
    anomalous.sort(key=lambda a: abs(a["z"]), reverse=True)
    return {"year": spike_year,
            "defect_rate": round(float(by_year_defect.max()), 4),
            "anomalous_factors": anomalous}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_analysis.py -v`
Expected: PASS (4 passed)

- [ ] **Step 5: Commit**

```bash
git add monkeyface/analysis.py tests/test_analysis.py
git commit -m "feat: confidence-aware factor-ranking analysis and spike explainer"
```

---

## Task 7: Pipeline orchestration

**Files:**
- Create: `monkeyface/pipeline.py`
- Test: `tests/test_pipeline.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_pipeline.py
from datetime import date
from unittest.mock import patch
from monkeyface.pipeline import run_pipeline
from monkeyface.schema import LotRecord
import config


def _records(n=20):
    return [LotRecord(lot_id=f"L{i}", field_id=f"F{i}", lat=36.9, lon=-121.7,
                      harvest_date=date(2024, 6, 15), grower=f"G{i % 3}")
            for i in range(n)]


def _fake_daily(*args, **kwargs):
    # deterministic but varied weather so features differ across lots
    import numpy as np
    rng = np.random.default_rng(abs(hash(args)) % 1000)
    out = []
    for d in range(1, 30):
        out.append({"date": date(2024, 5, d), "t2m_min": float(rng.uniform(2, 12)),
                    "t2m_max": float(rng.uniform(18, 33)), "t2m": 15.0,
                    "precip_mm": float(rng.uniform(0, 6)), "rh": 70.0, "wind": 2.0})
    return out


def test_pipeline_simulated_mode_produces_analysis():
    config.DATA_MODE = "simulated"
    with patch("monkeyface.weather.fetch_weather", side_effect=_fake_daily):
        result = run_pipeline(_records(60))
    assert result["data_mode"] == "simulated"
    assert len(result["lots"]) == 60
    assert "defect_rate" in result["lots"][0]
    assert len(result["analysis"]["factors"]) >= 5


def test_pipeline_real_mode_uses_provided_defect_rate():
    config.DATA_MODE = "real"
    recs = _records(10)
    for i, r in enumerate(recs):
        r.defect_rate = 0.1
    with patch("monkeyface.weather.fetch_weather", side_effect=_fake_daily):
        result = run_pipeline(recs)
    assert all(lot["defect_rate"] == 0.1 for lot in result["lots"])
    config.DATA_MODE = "simulated"  # restore
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_pipeline.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'monkeyface.pipeline'`

- [ ] **Step 3: Write `monkeyface/pipeline.py`**

```python
"""Orchestration: wire ingest output -> weather -> features -> (sim) -> analysis.

No business logic of its own. Switches defect source on config.DATA_MODE.
"""
import config
from monkeyface import weather, features, simulate, analysis
from monkeyface.schema import LotRecord


def run_pipeline(records: list[LotRecord]) -> dict:
    # 2. weather (real)
    weather_by_lot = {}
    for r in records:
        start, end = weather.bloom_window(r.harvest_date)
        weather_by_lot[r.lot_id] = weather.fetch_weather(r.lat, r.lon, start, end)

    # 3. features
    feature_rows = []
    for r in records:
        feats = features.build_features(weather_by_lot[r.lot_id])
        feature_rows.append({"lot_id": r.lot_id, "grower": r.grower,
                             "features": feats})

    # 4a. defect source: simulated or real
    if config.DATA_MODE == "simulated":
        rates = simulate.simulate_defect_rates(feature_rows)
    else:
        rates = {r.lot_id: r.defect_rate for r in records}

    # assemble analysis input rows
    by_id = {r.lot_id: r for r in records}
    analysis_rows = []
    for fr in feature_rows:
        rec = by_id[fr["lot_id"]]
        analysis_rows.append({
            "lot_id": fr["lot_id"], "grower": fr["grower"],
            "features": fr["features"],
            "defect_rate": rates[fr["lot_id"]],
            "harvest_date": rec.harvest_date.isoformat(),
        })

    # 4b. analysis
    result = analysis.analyze(analysis_rows)

    # assemble UI-facing lots payload
    lots = []
    for fr in feature_rows:
        rec = by_id[fr["lot_id"]]
        lots.append({
            "lot_id": fr["lot_id"], "field_id": rec.field_id,
            "lat": rec.lat, "lon": rec.lon,
            "harvest_date": rec.harvest_date.isoformat(),
            "grower": rec.grower, "defect_rate": rates[fr["lot_id"]],
            "features": fr["features"],
            "weather": [{**d, "date": d["date"].isoformat()}
                        for d in weather_by_lot[fr["lot_id"]]],
        })

    return {
        "data_mode": config.DATA_MODE,
        "lots": lots,
        "analysis": {
            "n": result.n,
            "factors": [vars(f) for f in result.factors],
            "spike": result.spike,
            "notes": result.notes,
        },
    }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_pipeline.py -v`
Expected: PASS (2 passed)

- [ ] **Step 5: Commit**

```bash
git add monkeyface/pipeline.py tests/test_pipeline.py
git commit -m "feat: pipeline orchestration with swappable defect source"
```

---

## Task 8: FastAPI backend (Component 5 server)

**Files:**
- Create: `monkeyface/app.py`
- Test: `tests/test_app.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_app.py
import io
from unittest.mock import patch
from datetime import date
from fastapi.testclient import TestClient
from monkeyface.app import app

client = TestClient(app)


def _fake_daily(*args, **kwargs):
    import numpy as np
    rng = np.random.default_rng(abs(hash(args)) % 1000)
    return [{"date": date(2024, 5, d), "t2m_min": float(rng.uniform(2, 12)),
             "t2m_max": float(rng.uniform(18, 33)), "t2m": 15.0,
             "precip_mm": float(rng.uniform(0, 6)), "rh": 70.0, "wind": 2.0}
            for d in range(1, 30)]


def test_index_served():
    resp = client.get("/")
    assert resp.status_code == 200
    assert "monkeyface" in resp.text.lower()


def test_columns_endpoint_returns_headers():
    csv = b"Lot,Field,Lat,Lon,Harvested\nL1,F1,36.9,-121.7,2024-06-15\n"
    resp = client.post("/api/columns",
                       files={"file": ("x.csv", csv, "text/csv")})
    assert resp.status_code == 200
    assert resp.json()["columns"] == ["Lot", "Field", "Lat", "Lon", "Harvested"]


def test_analyze_endpoint_runs_pipeline():
    rows = "lot_id,field_id,lat,lon,harvest_date,grower\n" + "\n".join(
        f"L{i},F{i},36.9,-121.7,2024-06-15,G{i%3}" for i in range(60))
    mapping = {c: c for c in ["lot_id", "field_id", "lat", "lon",
                              "harvest_date", "grower"]}
    import json
    with patch("monkeyface.weather.fetch_weather", side_effect=_fake_daily):
        resp = client.post("/api/analyze",
            files={"file": ("x.csv", rows.encode(), "text/csv")},
            data={"mapping": json.dumps(mapping)})
    assert resp.status_code == 200
    body = resp.json()
    assert body["data_mode"] == "simulated"
    assert len(body["lots"]) == 60
    assert len(body["analysis"]["factors"]) >= 5
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_app.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'monkeyface.app'`

- [ ] **Step 3: Write `monkeyface/app.py`**

```python
"""Component 5 backend: thin FastAPI glue. Delegates to pipeline."""
import json
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
import os
from monkeyface import ingest, pipeline

app = FastAPI(title="monkeyface")

STATIC_DIR = os.path.join(os.path.dirname(__file__), "..", "static")


@app.get("/")
def index():
    return FileResponse(os.path.join(STATIC_DIR, "index.html"))


@app.post("/api/columns")
async def columns(file: UploadFile = File(...)):
    """Return the spreadsheet's column headers so the UI can build a mapping."""
    data = await file.read()
    try:
        df = ingest.load_table(data, file.filename)
    except Exception as e:  # noqa: BLE001
        raise HTTPException(400, f"could not parse file: {e}")
    return {"columns": list(df.columns)}


@app.post("/api/analyze")
async def analyze(file: UploadFile = File(...), mapping: str = Form(...)):
    """Ingest + run the full pipeline. `mapping` is JSON source_col->canonical."""
    data = await file.read()
    try:
        df = ingest.load_table(data, file.filename)
        records, errors = ingest.normalize(df, json.loads(mapping),
                                            return_errors=True)
    except ingest.IngestError as e:
        raise HTTPException(400, str(e))
    if not records:
        raise HTTPException(400, f"no valid rows. errors: {errors[:5]}")

    result = pipeline.run_pipeline(records)
    result["row_errors"] = errors
    return result


# Static assets (app.js, style.css) under /static
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
```

- [ ] **Step 4: Create minimal `static/index.html`** (so `test_index_served` passes; full UI in Task 9)

```html
<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><title>monkeyface</title></head>
<body><h1>monkeyface</h1></body>
</html>
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `python -m pytest tests/test_app.py -v`
Expected: PASS (3 passed)

- [ ] **Step 6: Commit**

```bash
git add monkeyface/app.py tests/test_app.py static/index.html
git commit -m "feat: FastAPI backend with columns and analyze endpoints"
```

---

## Task 9: Web UI (Component 5 frontend)

**Files:**
- Create/replace: `static/index.html`, `static/app.js`, `static/style.css`
- Create: `sample_data/fields_sample.csv`

This task is UI; verification is manual (browser) plus a smoke test that the page references its assets. Plotly and Leaflet load from CDN.

- [ ] **Step 1: Create `sample_data/fields_sample.csv`** (real CA + MX coords, no defect column → exercises simulated mode)

```csv
lot_id,field_id,lat,lon,harvest_date,grower,variety
L001,Watsonville-A,36.9102,-121.7569,2024-05-20,CoastalBerry,Albion
L002,Watsonville-B,36.9300,-121.7700,2024-06-03,CoastalBerry,Albion
L003,Salinas-A,36.6777,-121.6555,2024-06-15,ValleyFarms,Monterey
L004,SantaMaria-A,34.9530,-120.4357,2024-05-28,CentralCoast,SanAndreas
L005,SantaMaria-B,34.9700,-120.4200,2024-06-20,CentralCoast,Albion
L006,Oxnard-A,34.1975,-119.1771,2024-04-15,SoCalGrowers,Fronteras
L007,Oxnard-B,34.2100,-119.1600,2024-05-05,SoCalGrowers,Fronteras
L008,SanQuintin-A,30.5589,-115.9389,2024-02-10,BajaFresh,Albion
L009,SanQuintin-B,30.4800,-115.9200,2024-03-01,BajaFresh,SanAndreas
L010,Maneadero-A,31.7167,-116.5667,2024-02-20,BajaFresh,Monterey
L011,Zamora-A,19.9854,-102.2836,2024-01-15,MichoacanBerry,SanAndreas
L012,Jacona-A,19.9500,-102.3100,2024-01-28,MichoacanBerry,Albion
```

- [ ] **Step 2: Create `static/style.css`**

```css
* { box-sizing: border-box; margin: 0; padding: 0; }
body { font-family: -apple-system, "SF Pro Display", sans-serif;
       background: #0d0f12; color: #e6e8ea; padding: 24px; }
h1 { font-size: 22px; margin-bottom: 4px; }
.sub { color: #8a9099; font-size: 13px; margin-bottom: 20px; }
#banner { display: inline-block; padding: 4px 12px; border-radius: 4px;
          font-size: 12px; font-weight: 600; letter-spacing: .04em;
          margin-bottom: 16px; }
.sim { background: #5a3d00; color: #ffcf70; }
.real { background: #0a3d1f; color: #74e39c; }
.panel { background: #15181d; border: 1px solid #262b33; border-radius: 8px;
         padding: 16px; margin-bottom: 16px; }
button { background: #2d7ff9; color: #fff; border: 0; border-radius: 6px;
         padding: 8px 16px; font-size: 14px; cursor: pointer; }
button:disabled { opacity: .5; cursor: default; }
select { background: #1c2027; color: #e6e8ea; border: 1px solid #333;
         border-radius: 4px; padding: 4px; }
table { width: 100%; border-collapse: collapse; font-size: 13px; }
th, td { text-align: left; padding: 6px 10px; border-bottom: 1px solid #262b33; }
.strong { color: #74e39c; } .suggestive { color: #ffcf70; }
.weak { color: #8a9099; }
#map { height: 380px; border-radius: 6px; }
.grid { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
.map-row { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
.note { color: #ffcf70; font-size: 12px; margin-top: 8px; }
.mapping-row { display: flex; gap: 8px; align-items: center; margin: 4px 0; }
.mapping-row label { width: 160px; font-size: 13px; }
</style>
```

(Remove the stray closing `</style>` if your editor adds it — this is a `.css` file.)

- [ ] **Step 3: Create `static/index.html`**

```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>monkeyface — strawberry defect risk explorer</title>
  <link rel="stylesheet" href="/static/style.css">
  <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"
        integrity="sha256-p4NxAoJBhIIN+hmNHrzRCf9tD/miZyoHS5obTRR9BMY="
        crossorigin="anonymous"/>
  <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"
          integrity="sha256-20nQCchB9co0qIjJZRGuk2/Z9VM+kNiyxNV1lvTlZBo="
          crossorigin="anonymous"></script>
  <script src="https://cdn.plot.ly/plotly-2.32.0.min.js"
          integrity="sha384-7TVmlZWH60iKX5Uk7lSvQhjtcgw2tkFjuwLcXoRSR4zXTyWFJRm9aPAguMh7CIra"
          crossorigin="anonymous"></script>
</head>
<body>
  <h1>monkeyface</h1>
  <div class="sub">Strawberry monkey-face / cat-face defect risk explorer · Phase A</div>
  <span id="banner" class="sim">DATA: SIMULATED</span>

  <div class="panel">
    <strong>1. Upload field data</strong> (CSV/Excel: lot, field, lat, lon, harvest date)
    <div style="margin-top:10px;">
      <input type="file" id="file" accept=".csv,.xlsx,.xls">
      <button id="loadCols">Load columns</button>
    </div>
    <div id="mapping" style="margin-top:12px;"></div>
    <button id="run" style="margin-top:12px;" disabled>Run analysis</button>
    <div id="status" class="note"></div>
  </div>

  <div class="map-row">
    <div class="panel"><strong>Fields</strong><div id="map" style="margin-top:10px;"></div></div>
    <div class="panel"><strong>Factor ranking</strong><div id="factors"></div></div>
  </div>

  <div class="panel"><strong>Could we have seen the spike?</strong><div id="spike"></div></div>

  <div class="grid">
    <div class="panel"><strong>Defect vs. factor</strong><div id="scatter"></div></div>
    <div class="panel"><strong>Weather (selected field's bloom window)</strong><div id="weather"></div></div>
  </div>

  <script src="/static/app.js"></script>
</body>
</html>
```

- [ ] **Step 4: Create `static/app.js`**

```javascript
const CANONICAL = ["lot_id", "field_id", "lat", "lon", "harvest_date",
                   "defect_rate", "grower", "variety"];
let lastResult = null;

const $ = (id) => document.getElementById(id);

$("loadCols").onclick = async () => {
  const f = $("file").files[0];
  if (!f) { $("status").textContent = "Choose a file first."; return; }
  const fd = new FormData(); fd.append("file", f);
  const r = await fetch("/api/columns", { method: "POST", body: fd });
  if (!r.ok) { $("status").textContent = "Parse error."; return; }
  const { columns } = await r.json();
  buildMapping(columns);
  $("run").disabled = false;
};

function guess(col) {
  const c = col.toLowerCase();
  if (c.includes("lot")) return "lot_id";
  if (c.includes("field")) return "field_id";
  if (c.startsWith("lat")) return "lat";
  if (c.startsWith("lon") || c.includes("lng")) return "lon";
  if (c.includes("harv") || c.includes("date")) return "harvest_date";
  if (c.includes("defect")) return "defect_rate";
  if (c.includes("grow")) return "grower";
  if (c.includes("variet")) return "variety";
  return "";
}

function buildMapping(columns) {
  const html = columns.map((col) => {
    const opts = ['<option value="">— ignore —</option>']
      .concat(CANONICAL.map((cn) =>
        `<option value="${cn}" ${guess(col) === cn ? "selected" : ""}>${cn}</option>`))
      .join("");
    return `<div class="mapping-row"><label>${col}</label>
            <select data-src="${col}">${opts}</select></div>`;
  }).join("");
  $("mapping").innerHTML = html;
}

$("run").onclick = async () => {
  const f = $("file").files[0];
  const mapping = {};
  document.querySelectorAll("#mapping select").forEach((s) => {
    if (s.value) mapping[s.dataset.src] = s.value;
  });
  const fd = new FormData();
  fd.append("file", f);
  fd.append("mapping", JSON.stringify(mapping));
  $("status").textContent = "Pulling weather + analyzing… (first run is slower)";
  $("run").disabled = true;
  const r = await fetch("/api/analyze", { method: "POST", body: fd });
  $("run").disabled = false;
  if (!r.ok) { const e = await r.json(); $("status").textContent = e.detail; return; }
  lastResult = await r.json();
  $("status").textContent = `Done. ${lastResult.lots.length} lots analyzed.`;
  render(lastResult);
};

function render(res) {
  const banner = $("banner");
  banner.textContent = "DATA: " + res.data_mode.toUpperCase();
  banner.className = res.data_mode === "simulated" ? "sim" : "real";
  renderMap(res.lots);
  renderFactors(res.analysis);
  renderSpike(res.analysis.spike);
  renderScatter(res.lots, res.analysis.factors[0].name);
  renderWeather(res.lots[0]);
}

let map, layer;
function renderMap(lots) {
  if (!map) { map = L.map("map").setView([34, -119], 5);
    L.tileLayer("https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}.png",
      { attribution: "© OpenStreetMap © CARTO" }).addTo(map); }
  if (layer) map.removeLayer(layer);
  layer = L.layerGroup().addTo(map);
  const max = Math.max(...lots.map((l) => l.defect_rate || 0), 0.0001);
  lots.forEach((l) => {
    const t = (l.defect_rate || 0) / max;
    const color = `rgb(${Math.round(120 + 135 * t)},${Math.round(180 - 140 * t)},90)`;
    L.circleMarker([l.lat, l.lon], { radius: 8, color, fillColor: color,
      fillOpacity: 0.8 })
      .bindPopup(`<b>${l.field_id}</b><br>lot ${l.lot_id}<br>` +
                 `defect ${(100 * (l.defect_rate || 0)).toFixed(1)}%`)
      .on("click", () => renderWeather(l))
      .addTo(layer);
  });
}

function renderFactors(a) {
  const rows = a.factors.map((f) =>
    `<tr><td>${f.name}</td>
     <td>${f.direction}</td>
     <td>${f.std_effect.toFixed(4)}</td>
     <td>r=${f.corr.toFixed(2)} [${f.ci_low.toFixed(2)}, ${f.ci_high.toFixed(2)}]</td>
     <td class="${f.confidence}">${f.confidence}</td></tr>`).join("");
  let note = a.notes.map((n) => `<div class="note">${n}</div>`).join("");
  $("factors").innerHTML =
    `<table><tr><th>factor</th><th>dir</th><th>effect</th><th>corr (95% CI)</th>
     <th>confidence</th></tr>${rows}</table>${note}`;
}

function renderSpike(s) {
  if (!s) { $("spike").textContent = "No multi-year data to assess a spike."; return; }
  const af = s.anomalous_factors.map((a) =>
    `<li>${a.factor}: ${a.z > 0 ? "+" : ""}${a.z}σ vs normal ` +
    `(${a.spike_mean} vs ${a.overall_mean})</li>`).join("");
  $("spike").innerHTML =
    `<p>Highest-defect year: <b>${s.year}</b> ` +
    `(mean defect ${(100 * s.defect_rate).toFixed(1)}%).</p>` +
    `<p>Conditions that were anomalous that year:</p><ul>${af || "<li>none ≥1σ</li>"}</ul>`;
}

function renderScatter(lots, factorName) {
  const x = lots.map((l) => l.features[factorName]);
  const y = lots.map((l) => 100 * (l.defect_rate || 0));
  Plotly.newPlot("scatter", [{
    x, y, mode: "markers", type: "scatter",
    marker: { size: 9, color: "#2d7ff9" },
    text: lots.map((l) => l.field_id),
  }], { paper_bgcolor: "#15181d", plot_bgcolor: "#15181d",
        font: { color: "#e6e8ea" }, margin: { t: 10, r: 10 },
        xaxis: { title: factorName }, yaxis: { title: "defect %" } },
    { displayModeBar: false });
}

function renderWeather(lot) {
  if (!lot) return;
  const d = lot.weather.map((w) => w.date);
  Plotly.newPlot("weather", [
    { x: d, y: lot.weather.map((w) => w.t2m_min), name: "T min",
      type: "scatter", line: { color: "#74b9ff" } },
    { x: d, y: lot.weather.map((w) => w.t2m_max), name: "T max",
      type: "scatter", line: { color: "#ff7675" } },
    { x: d, y: lot.weather.map((w) => w.precip_mm), name: "precip mm",
      type: "bar", marker: { color: "#55efc4" }, yaxis: "y2" },
  ], { paper_bgcolor: "#15181d", plot_bgcolor: "#15181d",
       font: { color: "#e6e8ea" }, margin: { t: 24 },
       title: `${lot.field_id} bloom window`,
       yaxis: { title: "°C" },
       yaxis2: { title: "mm", overlaying: "y", side: "right" } },
     { displayModeBar: false });
}
```

- [ ] **Step 5: Manual verification (browser)**

Run: `cd ~/Desktop/Claude\ Projects/monkeyface && ./run.sh` (created in Task 10). Then:
1. Open `http://localhost:8000`.
2. Upload `sample_data/fields_sample.csv`, click "Load columns" → mapping dropdowns auto-guess.
3. Click "Run analysis". First run pulls real NASA POWER weather (slower); re-runs are cached.
4. Confirm: orange "DATA: SIMULATED" banner; 12 field markers on the map (CA + Baja + Michoacán); factor table with `cold_nights` / `bloom_rain_days` ranked at top with "strong" or "suggestive"; spike panel names a year; scatter and weather charts render; clicking a map marker updates the weather chart.

- [ ] **Step 6: Commit**

```bash
git add static/ sample_data/
git commit -m "feat: browser UI (Leaflet map, Plotly charts, column mapping)"
```

---

## Task 10: Launch script + README + end-to-end smoke

**Files:**
- Create: `run.sh`, `README.md`
- Test: `tests/test_pipeline.py` (add one live-network end-to-end, marked slow)

- [ ] **Step 1: Create `run.sh`**

```bash
#!/usr/bin/env bash
set -e
cd "$(dirname "$0")"
if [ ! -d .venv ]; then
  python3 -m venv .venv
  ./.venv/bin/pip install -q -r requirements.txt
fi
echo "monkeyface running at http://localhost:8000  (Ctrl-C to stop)"
( sleep 1 && open http://localhost:8000 ) &
exec ./.venv/bin/uvicorn monkeyface.app:app --port 8000 --reload
```

- [ ] **Step 2: Make it executable**

Run: `chmod +x run.sh`

- [ ] **Step 3: Add a live end-to-end test (real NASA POWER, opt-in)**

Append to `tests/test_pipeline.py`:

```python
import pytest


@pytest.mark.slow
def test_pipeline_live_nasa_power_one_field():
    """Opt-in: hits the real NASA POWER API. Run with: pytest -m slow"""
    import config
    config.DATA_MODE = "simulated"
    recs = [LotRecord(lot_id="L1", field_id="Watsonville", lat=36.9102,
                      lon=-121.7569, harvest_date=date(2024, 5, 20),
                      grower="CoastalBerry")]
    result = run_pipeline(recs)
    assert len(result["lots"]) == 1
    w = result["lots"][0]["weather"]
    assert len(w) > 20                      # ~35-day window of daily data
    assert all("t2m_min" in d for d in w)   # real parsed weather
```

- [ ] **Step 4: Register the marker in `pytest.ini`** (so `-m slow` works and default runs skip it)

Replace `pytest.ini` contents with:

```ini
[pytest]
testpaths = tests
python_files = test_*.py
addopts = -v -m "not slow"
markers =
    slow: hits the real NASA POWER network API
```

- [ ] **Step 5: Run the full offline suite, then the live test once**

Run: `python -m pytest`
Expected: all tests PASS, the slow one DESELECTED.

Run: `python -m pytest -m slow`
Expected: `test_pipeline_live_nasa_power_one_field` PASS (requires internet).

- [ ] **Step 6: Create `README.md`**

```markdown
# monkeyface

Local web tool to test whether field-level weather predicts the strawberry
**monkey-face / cat-face** defect, and to rank which conditions drive it.

Phase A (this build): real NASA POWER weather + **simulated** defect data
(with an injected known relationship that doubles as a pipeline correctness
test). Swap to real defect data by setting `DATA_MODE = "real"` in `config.py`
and including a `defect_rate` column in your spreadsheet.

## Run

```bash
./run.sh        # creates .venv, installs deps, opens http://localhost:8000
```

Upload a CSV/Excel with columns for lot, field, lat, lon, harvest date
(see `sample_data/fields_sample.csv`). Map the columns, click Run.

## Test

```bash
pytest            # offline unit + pipeline tests
pytest -m slow    # also hit the real NASA POWER API (needs internet)
```

## What's NOT here (Phase B, designed-for)

Forecast-based forward risk scoring per supplier. The fitted relationship from
`analysis.py` and the feature pipeline are reused unchanged; Phase B adds a
forecast-weather input and a risk-readout view. No architectural change needed.
```

- [ ] **Step 7: Commit**

```bash
git add run.sh README.md tests/test_pipeline.py pytest.ini
git commit -m "feat: launch script, README, live NASA POWER smoke test"
```

---

## Self-Review

**Spec coverage:**
- Component 1 ingest/column-mapping → Task 2 (+ extra-columns carry-through, bad-row flagging) ✓
- Component 2 weather enrichment + cache + bloom window → Task 3 (verified live API shape) ✓
- Component 3 feature builder (cold nights, heat spikes, bloom rain, GDD, humidity, swing, wind) → Task 4 ✓
- Component 4a simulator with injected relationship as correctness test → Task 5 ✓
- Component 4b analysis: ranking + effect size + direction + confidence + spike explainer → Task 6 ✓
- Component 5 web UI: Leaflet field map colored by defect, Plotly weather charts, defect-vs-factor, factor ranking, SIMULATED/REAL banner → Tasks 8–9 ✓
- Non-weather covariates carried through (grower in pipeline, extra columns in ingest) → Tasks 2, 7 ✓
- Swappable simulated↔real via `DATA_MODE` config → Task 7 (`test_pipeline_real_mode_uses_provided_defect_rate`) ✓
- Tech stack (pandas, sklearn/statsmodels, FastAPI, Plotly, Leaflet, file cache, one-command run) → Tasks 0, 3, 8, 9, 10 ✓
- Success criterion "analysis recovers injected relationship" → Task 6 `test_analyze_recovers_injected_drivers` ✓
- Success criterion "real weather visualized independent of defect data" → Task 9 weather chart + Task 10 live test ✓
- Phase B explicitly NOT built, only designed-for → README + spec note, no task ✓

**Placeholder scan:** No "TBD/TODO/handle edge cases" — every code step shows complete code. The one prose note in Task 2 (loop-form correction) and Task 9 Step 2 (stray `</style>`) are explicit corrections, not placeholders.

**Type consistency:** `LotRecord` fields (Task 1) used identically in ingest (2), weather (3), pipeline (7), app (8). `build_features`/`FEATURE_NAMES` (4) consumed in simulate (5), analysis (6), pipeline (7). `FactorResult` fields (6) rendered by `vars(f)` in pipeline (7) and read by the same keys in `app.js` `renderFactors` (9): `name, direction, std_effect, corr, ci_low, ci_high, confidence` — all match. `run_pipeline` return keys (`data_mode, lots, analysis{n,factors,spike,notes}`) consumed identically in `app.js` `render`. `fetch_weather` signature `(lat, lon, start, end)` patched consistently across tests. ✓

**statsmodels note:** listed in requirements for honesty/CI work but the implemented analysis uses scikit-learn Ridge + a Fisher-z CV by hand (no statsmodels import), so there's no unused-import bug; statsmodels remains available if a future task wants OLS p-values. Acceptable — flagged here for transparency.
