from datetime import date
from monkeyface.weather import _parse_power


def test_parse_power_drops_fill_value_days():
    days = {"20240501": 5.0, "20240502": -999.0, "20240503": 7.0}
    payload = {"properties": {"parameter": {
        "T2M_MIN": days,
        "T2M_MAX": {"20240501": 18.0, "20240502": 19.0, "20240503": 20.0},
        "T2M": {"20240501": 11.0, "20240502": 11.0, "20240503": 13.0},
        "PRECTOTCORR": {"20240501": 0.0, "20240502": 0.0, "20240503": 0.0},
        "RH2M": {"20240501": 70.0, "20240502": 70.0, "20240503": 70.0},
        "WS2M": {"20240501": 2.0, "20240502": 2.0, "20240503": 2.0},
    }}}
    daily = _parse_power(payload)
    dates = [d["date"] for d in daily]
    assert date(2024, 5, 2) not in dates   # the -999 day is dropped
    assert len(daily) == 2
    assert all(d["t2m_min"] > -998 for d in daily)


def test_parse_power_drops_day_when_any_param_is_fill():
    days = {"20240501": 5.0, "20240502": 6.0}
    payload = {"properties": {"parameter": {
        "T2M_MIN": days,
        "T2M_MAX": {"20240501": 18.0, "20240502": 19.0},
        "T2M": {"20240501": 11.0, "20240502": 11.0},
        "PRECTOTCORR": {"20240501": 0.0, "20240502": -999.0},  # fill in precip only
        "RH2M": {"20240501": 70.0, "20240502": 70.0},
        "WS2M": {"20240501": 2.0, "20240502": 2.0},
    }}}
    daily = _parse_power(payload)
    assert len(daily) == 1
    assert daily[0]["date"] == date(2024, 5, 1)
