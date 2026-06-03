from datetime import date
from monkeyface.features import build_features, FEATURE_NAMES


def _day(d, tmin, tmax, precip=0.0, rh=70.0, wind=2.0):
    return {"date": date(2024, 5, d), "t2m_min": tmin, "t2m_max": tmax,
            "t2m": (tmin + tmax) / 2, "precip_mm": precip, "rh": rh, "wind": wind}


def test_cold_nights_counts_below_threshold():
    daily = [_day(1, 4.0, 20), _day(2, 6.9, 20), _day(3, 8.0, 20)]
    f = build_features(daily)
    assert f["cold_nights"] == 2  # 4.0 and 6.9 are below 7.0


def test_heat_spike_days_counts_above_threshold():
    daily = [_day(1, 10, 31), _day(2, 10, 29), _day(3, 10, 35)]
    f = build_features(daily)
    assert f["heat_spike_days"] == 2  # 31 and 35 above 30.0


def test_bloom_rain_days_counts_wet_days():
    daily = [_day(1, 10, 20, precip=5.0), _day(2, 10, 20, precip=0.5),
             _day(3, 10, 20, precip=3.0)]
    f = build_features(daily)
    assert f["bloom_rain_days"] == 2  # 5.0 and 3.0 above 2.0


def test_gdd_accumulates_above_base():
    daily = [_day(1, 8, 12), _day(2, 12, 16)]  # means 10 and 14; base 10
    f = build_features(daily)
    assert f["gdd"] == 4.0  # (10-10) + (14-10)


def test_all_feature_names_present():
    daily = [_day(1, 10, 20)]
    f = build_features(daily)
    assert set(f.keys()) == set(FEATURE_NAMES)


def test_empty_daily_returns_zeros():
    f = build_features([])
    assert all(v == 0 for v in f.values())
