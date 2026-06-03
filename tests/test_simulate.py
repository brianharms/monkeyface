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
