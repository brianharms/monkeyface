from datetime import date
import json
from unittest.mock import patch, MagicMock
from monkeyface.weather import bloom_window, _cache_key, fetch_weather, enrich
from monkeyface.schema import LotRecord
import config


def test_bloom_window_works_back_from_harvest():
    start, end = bloom_window(date(2024, 6, 15))
    assert end == date(2024, 6, 5)    # 10 days before harvest
    assert start == date(2024, 5, 1)  # 45 days before harvest


def test_cache_key_is_stable_for_same_inputs():
    k1 = _cache_key(36.9, -121.7, date(2024, 5, 1), date(2024, 6, 5))
    k2 = _cache_key(36.9, -121.7, date(2024, 5, 1), date(2024, 6, 5))
    assert k1 == k2
    k3 = _cache_key(36.9, -121.7, date(2024, 5, 2), date(2024, 6, 5))
    assert k1 != k3


def _fake_power_response():
    days = {f"202405{d:02d}": 5.0 + d for d in range(1, 6)}
    return {
        "properties": {"parameter": {
            "T2M_MIN": days, "T2M_MAX": {k: v + 12 for k, v in days.items()},
            "T2M": {k: v + 6 for k, v in days.items()},
            "PRECTOTCORR": {k: 0.0 for k in days},
            "RH2M": {k: 70.0 for k in days}, "WS2M": {k: 2.0 for k in days},
        }}
    }


def test_fetch_weather_parses_power_json(tmp_path):
    config.WEATHER_CACHE_DIR = str(tmp_path)
    fake = MagicMock()
    fake.json.return_value = _fake_power_response()
    fake.raise_for_status.return_value = None
    with patch("monkeyface.weather.requests.get", return_value=fake) as g:
        daily = fetch_weather(36.9, -121.7, date(2024, 5, 1), date(2024, 5, 5))
    assert len(daily) == 5
    assert daily[0]["date"] == date(2024, 5, 1)
    assert daily[0]["t2m_min"] == 6.0
    assert daily[0]["t2m_max"] == 18.0
    g.assert_called_once()


def test_fetch_weather_uses_cache_second_call(tmp_path):
    config.WEATHER_CACHE_DIR = str(tmp_path)
    fake = MagicMock()
    fake.json.return_value = _fake_power_response()
    fake.raise_for_status.return_value = None
    with patch("monkeyface.weather.requests.get", return_value=fake) as g:
        fetch_weather(36.9, -121.7, date(2024, 5, 1), date(2024, 5, 5))
        fetch_weather(36.9, -121.7, date(2024, 5, 1), date(2024, 5, 5))
    assert g.call_count == 1  # second call served from disk cache
