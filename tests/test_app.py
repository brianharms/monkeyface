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
