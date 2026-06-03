"""Component 2: NASA POWER weather, cached on disk.

The only module that touches the network. One public function `enrich` takes
LotRecords and attaches a daily weather time-series for each lot's bloom window.
"""
import hashlib
import json
import os
from datetime import date, timedelta
import requests
import config
from monkeyface.schema import LotRecord


def bloom_window(harvest: date) -> tuple[date, date]:
    """Return (start, end) of the bloom/fruit-set window before harvest."""
    start = harvest - timedelta(days=config.WINDOW_START_DAYS)
    end = harvest - timedelta(days=config.WINDOW_END_DAYS)
    return start, end


def _cache_key(lat: float, lon: float, start: date, end: date) -> str:
    raw = f"{lat:.4f}_{lon:.4f}_{start.isoformat()}_{end.isoformat()}"
    return hashlib.sha1(raw.encode()).hexdigest()


def _cache_path(key: str) -> str:
    os.makedirs(config.WEATHER_CACHE_DIR, exist_ok=True)
    return os.path.join(config.WEATHER_CACHE_DIR, f"{key}.json")


def _parse_power(payload: dict) -> list[dict]:
    param = payload["properties"]["parameter"]
    dates = sorted(param["T2M_MIN"].keys())
    out = []
    for d in dates:
        out.append({
            "date": date(int(d[:4]), int(d[4:6]), int(d[6:8])),
            "t2m_min": float(param["T2M_MIN"][d]),
            "t2m_max": float(param["T2M_MAX"][d]),
            "t2m": float(param["T2M"][d]),
            "precip_mm": float(param["PRECTOTCORR"][d]),
            "rh": float(param["RH2M"][d]),
            "wind": float(param["WS2M"][d]),
        })
    return out


def fetch_weather(lat: float, lon: float, start: date, end: date) -> list[dict]:
    """Cache-or-fetch daily weather for one point+window. Returns list of dicts."""
    key = _cache_key(lat, lon, start, end)
    path = _cache_path(key)
    if os.path.exists(path):
        with open(path) as f:
            raw = json.load(f)
        return [{**r, "date": date.fromisoformat(r["date"])} for r in raw]

    resp = requests.get(config.NASA_POWER_URL, params={
        "parameters": ",".join(config.NASA_PARAMS),
        "community": config.NASA_COMMUNITY,
        "longitude": lon, "latitude": lat,
        "start": start.strftime("%Y%m%d"), "end": end.strftime("%Y%m%d"),
        "format": "JSON",
    }, timeout=60)
    resp.raise_for_status()
    daily = _parse_power(resp.json())

    with open(path, "w") as f:
        json.dump([{**r, "date": r["date"].isoformat()} for r in daily], f)
    return daily


def enrich(records: list[LotRecord]) -> dict[str, list[dict]]:
    """Return {lot_id: daily_weather_list} for every record."""
    result = {}
    for r in records:
        start, end = bloom_window(r.harvest_date)
        result[r.lot_id] = fetch_weather(r.lat, r.lon, start, end)
    return result
