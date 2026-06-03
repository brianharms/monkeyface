# monkeyface

Local web tool to test whether field-level weather predicts the strawberry
**monkey-face / cat-face** defect, and to rank which conditions drive it.

Phase A (this build): real NASA POWER weather + **simulated** defect data
(with an injected known relationship that doubles as a pipeline correctness
test). Swap to real defect data by setting `DATA_MODE = "real"` in `config.py`
and including a `defect_rate` column in your spreadsheet.

## Run

    ./run.sh        # creates .venv (Python 3.11), installs deps, opens http://localhost:8000

Upload a CSV/Excel with columns for lot, field, lat, lon, harvest date
(see `sample_data/fields_sample.csv`). Map the columns, click Run.

## Test

    pytest            # offline unit + pipeline tests
    pytest -m slow    # also hit the real NASA POWER API (needs internet)

## What's NOT here (Phase B, designed-for)

Forecast-based forward risk scoring per supplier. The fitted relationship from
`analysis.py` and the feature pipeline are reused unchanged; Phase B adds a
forecast-weather input and a risk-readout view. No architectural change needed.
