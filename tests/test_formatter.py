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


# ---- consolidation (Step 1: normalize + unify many files) ----

def _csv(rows_header_and_lines: str) -> bytes:
    return rows_header_and_lines.encode("utf-8")


def test_consolidate_merges_multiple_files():
    a = _csv("lot_id,field_id,lat,lon,harvest_date\nL1,N,36.9,-121.7,2024-05-20\n")
    b = _csv("lot_id,field_id,lat,lon,harvest_date\nL2,S,34.9,-120.4,2024-06-03\n")
    res = formatter.consolidate([(a, "a.csv"), (b, "b.csv")])
    assert res["ok"] is True
    assert res["file_count"] == 2
    assert res["total_rows"] == 2
    out = res["csv_bytes"].decode()
    assert "L1" in out and "L2" in out


def test_consolidate_dedupes_identical_rows_silently():
    # Same lot_id, IDENTICAL data, in two files -> keep one, no conflict.
    row = "lot_id,field_id,lat,lon,harvest_date\nL1,N,36.9,-121.7,2024-05-20\n"
    res = formatter.consolidate([(_csv(row), "a.csv"), (_csv(row), "b.csv")])
    assert res["ok"] is True
    assert res["total_rows"] == 1
    assert res["conflicts"] == []


def test_consolidate_blocks_on_true_conflict():
    # Same lot_id, DIFFERENT data -> blocking conflict, no master produced.
    a = _csv("lot_id,field_id,lat,lon,harvest_date\nL1,North,36.9,-121.7,2024-05-20\n")
    b = _csv("lot_id,field_id,lat,lon,harvest_date\nL1,South,34.9,-120.4,2024-06-03\n")
    res = formatter.consolidate([(a, "a.csv"), (b, "b.csv")])
    assert res["ok"] is False
    assert "csv_bytes" not in res
    assert res["conflicts"][0]["lot_id"] == "L1"
    assert set(res["conflicts"][0]["files"]) == {"a.csv", "b.csv"}


def test_consolidate_reports_unformattable_but_uses_the_rest():
    good = _csv("lot_id,field_id,lat,lon,harvest_date\nL1,N,36.9,-121.7,2024-05-20\n")
    junk = _csv("colA,colB\n1,2\n")
    res = formatter.consolidate([(good, "good.csv"), (junk, "junk.csv")])
    assert res["ok"] is True
    assert res["total_rows"] == 1
    per = {f["name"]: f for f in res["per_file"]}
    assert per["good.csv"]["ok"] is True
    assert per["junk.csv"]["ok"] is False
