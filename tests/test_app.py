import base64
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


def test_format_endpoint_normalizes_messy_file():
    # Messy headers that the formatter should map to canonical columns.
    csv = (b"Lot #,Ranch,Latitude,Longitude,Pick Date,Grower\n"
           b"L1,North,36.9,-121.7,05/20/2024,Acme\n"
           b"L2,South,34.9,-120.4,06/03/2024,Acme\n")
    resp = client.post("/api/format",
                       files={"files": ("raw.csv", csv, "text/csv")})
    assert resp.status_code == 200
    f = resp.json()["files"][0]
    assert f["ok"] is True
    assert f["report"]["rows_out"] == 2
    clean = base64.b64decode(f["csv_b64"]).decode()
    header = clean.splitlines()[0].split(",")
    assert "lot_id" in header and "harvest_date" in header and "lat" in header


def test_format_endpoint_reports_unformattable_file():
    csv = b"colA,colB\n1,2\n"  # no recognizable required columns
    resp = client.post("/api/format",
                       files={"files": ("junk.csv", csv, "text/csv")})
    assert resp.status_code == 200
    f = resp.json()["files"][0]
    assert f["ok"] is False
    assert "required" in f["error"].lower()


def test_analyze_accepts_canonical_file():
    rows = "lot_id,field_id,lat,lon,harvest_date,grower\n" + "\n".join(
        f"L{i},F{i},36.9,-121.7,2024-06-15,G{i%3}" for i in range(60))
    with patch("monkeyface.weather.fetch_weather", side_effect=_fake_daily):
        resp = client.post("/api/analyze",
            files={"file": ("clean.csv", rows.encode(), "text/csv")})
    assert resp.status_code == 200
    body = resp.json()
    assert body["data_mode"] == "simulated"
    assert len(body["lots"]) == 60
    assert len(body["analysis"]["factors"]) >= 5


def test_analyze_rejects_unformatted_file():
    # Missing required canonical columns -> clear 400, not a guess.
    csv = b"Lot #,Ranch,Latitude\nL1,North,36.9\n"
    resp = client.post("/api/analyze",
                       files={"file": ("raw.csv", csv, "text/csv")})
    assert resp.status_code == 400
    assert "not formatted" in resp.json()["detail"].lower()
