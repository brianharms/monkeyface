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
