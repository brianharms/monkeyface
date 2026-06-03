from datetime import date
from unittest.mock import patch
import pytest
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
