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
