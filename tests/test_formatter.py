import pandas as pd
import pytest
from monkeyface import formatter
from monkeyface import schema


def test_guess_canonical_matches_messy_names():
    assert formatter.guess_canonical("Lot #") == schema.LOT_ID
    assert formatter.guess_canonical("Ranch") == schema.FIELD_ID
    assert formatter.guess_canonical("Latitude") == schema.LAT
    assert formatter.guess_canonical("Longitude") == schema.LON
    assert formatter.guess_canonical("Pick Date") == schema.HARVEST_DATE
    assert formatter.guess_canonical("Cat-face %") == schema.DEFECT_RATE
    assert formatter.guess_canonical("Supplier") == schema.GROWER
    assert formatter.guess_canonical("totally unrelated") is None


def test_build_mapping_avoids_duplicate_canonical():
    # Two columns both guess to harvest_date; only the first should be kept.
    m = formatter.build_mapping(["Harvest Date", "Pick Date", "Lot", "Field", "lat", "lon"])
    targets = list(m.values())
    assert targets.count(schema.HARVEST_DATE) == 1


def test_format_dataframe_normalizes_and_reports():
    df = pd.DataFrame([
        {"Lot #": "L1", "Ranch": "North", "Latitude": 36.9, "Longitude": -121.7,
         "Pick Date": "05/20/2024", "Supplier": "Acme"},
        {"Lot #": "L2", "Ranch": "South", "Latitude": 34.9, "Longitude": -120.4,
         "Pick Date": "06/03/2024", "Supplier": "Acme"},
    ])
    clean, report = formatter.format_dataframe(df)
    assert list(clean.columns)[:5] == [schema.LOT_ID, schema.FIELD_ID,
                                       schema.LAT, schema.LON, schema.HARVEST_DATE]
    assert clean[schema.HARVEST_DATE].iloc[0] == "2024-05-20"   # ISO normalized
    assert report["rows_out"] == 2


def test_format_dataframe_drops_bad_rows():
    df = pd.DataFrame([
        {"lot_id": "L1", "field_id": "F1", "lat": 36.9, "lon": -121.7, "harvest_date": "2024-05-20"},
        {"lot_id": "L2", "field_id": "F2", "lat": 999, "lon": -121.7, "harvest_date": "2024-05-21"},  # bad lat
        {"lot_id": "L3", "field_id": "F3", "lat": 35.0, "lon": -120.0, "harvest_date": ""},           # bad date
        {"lot_id": "L1", "field_id": "F9", "lat": 35.0, "lon": -120.0, "harvest_date": "2024-05-22"}, # dup lot
    ])
    clean, report = formatter.format_dataframe(df)
    assert report["rows_out"] == 1
    assert report["dropped_bad_coords"] == 1
    assert report["dropped_bad_dates"] == 1
    assert report["dropped_duplicates"] == 1


def test_format_dataframe_raises_when_required_missing():
    df = pd.DataFrame([{"colA": 1, "colB": 2}])
    with pytest.raises(formatter.FormatError):
        formatter.format_dataframe(df)
