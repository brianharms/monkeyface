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
