"""Component 3: daily weather -> one agronomic feature row.

Pure function, no I/O. Each feature encodes a known cat-face mechanism so an
agronomist can review the definitions directly.
"""
import config

FEATURE_NAMES = [
    "cold_nights",       # nights with T_min below pollination-disruption threshold
    "heat_spike_days",   # days with T_max above fruit-set stress threshold
    "bloom_rain_days",   # wet days suppressing pollinator activity
    "gdd",               # growing-degree-days above base temp
    "mean_rh",           # mean relative humidity
    "diurnal_swing",     # mean (T_max - T_min): instability proxy
    "mean_wind",         # mean wind speed (pollinator suppression)
]


def build_features(daily: list[dict]) -> dict:
    if not daily:
        return {name: 0 for name in FEATURE_NAMES}

    cold = sum(1 for d in daily if d["t2m_min"] < config.COLD_NIGHT_C)
    heat = sum(1 for d in daily if d["t2m_max"] > config.HEAT_SPIKE_C)
    rain = sum(1 for d in daily if d["precip_mm"] > config.RAIN_DAY_MM)
    gdd = sum(max(0.0, (d["t2m_min"] + d["t2m_max"]) / 2 - config.GDD_BASE_C)
              for d in daily)
    mean_rh = sum(d["rh"] for d in daily) / len(daily)
    swing = sum(d["t2m_max"] - d["t2m_min"] for d in daily) / len(daily)
    wind = sum(d["wind"] for d in daily) / len(daily)

    return {
        "cold_nights": cold,
        "heat_spike_days": heat,
        "bloom_rain_days": rain,
        "gdd": round(gdd, 3),
        "mean_rh": round(mean_rh, 3),
        "diurnal_swing": round(swing, 3),
        "mean_wind": round(wind, 3),
    }
