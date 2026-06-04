"""Orchestration: wire ingest output -> weather -> features -> (sim) -> analysis.

No business logic of its own. Switches defect source on config.DATA_MODE.
"""
import config
from monkeyface import weather, features, simulate, analysis
from monkeyface.schema import LotRecord


def run_pipeline(records: list[LotRecord]) -> dict:
    # real mode requires a defect_rate on every row; otherwise analysis dies
    # later with an opaque sklearn "Input y contains NaN" error. Guard early.
    if config.DATA_MODE != "simulated":
        if any(r.defect_rate is None for r in records):
            raise ValueError("real mode requires a defect_rate value for every row")

    # 2. weather (real)
    weather_by_lot = {}
    for r in records:
        start, end = weather.bloom_window(r.harvest_date)
        weather_by_lot[r.lot_id] = weather.fetch_weather(r.lat, r.lon, start, end)

    # lots whose bloom window returned no usable days (all future, or all
    # fill-filtered) would be analyzed as all-zero weather. Flag and exclude.
    weather_warnings = [r.lot_id for r in records if not weather_by_lot[r.lot_id]]
    if weather_warnings:
        dropped = set(weather_warnings)
        records = [r for r in records if r.lot_id not in dropped]

    # If every lot was dropped (e.g. all harvest dates in the future, so no
    # weather exists yet), there is nothing to analyze. Fail clearly instead of
    # crashing deep inside the analysis with an opaque error.
    if not records:
        raise ValueError(
            "no weather data available for any field — harvest dates may be in "
            "the future, or no field had usable weather in its bloom window")

    # 3. features
    feature_rows = []
    for r in records:
        feats = features.build_features(weather_by_lot[r.lot_id])
        feature_rows.append({"lot_id": r.lot_id, "grower": r.grower,
                             "features": feats})

    # 4a. defect source: simulated or real
    if config.DATA_MODE == "simulated":
        rates = simulate.simulate_defect_rates(feature_rows)
    else:
        rates = {r.lot_id: r.defect_rate for r in records}

    # assemble analysis input rows
    by_id = {r.lot_id: r for r in records}
    analysis_rows = []
    for fr in feature_rows:
        rec = by_id[fr["lot_id"]]
        analysis_rows.append({
            "lot_id": fr["lot_id"], "grower": fr["grower"],
            "features": fr["features"],
            "defect_rate": rates[fr["lot_id"]],
            "harvest_date": rec.harvest_date.isoformat(),
        })

    # 4b. analysis
    result = analysis.analyze(analysis_rows)

    # assemble UI-facing lots payload
    lots = []
    for fr in feature_rows:
        rec = by_id[fr["lot_id"]]
        lots.append({
            "lot_id": fr["lot_id"], "field_id": rec.field_id,
            "lat": rec.lat, "lon": rec.lon,
            "harvest_date": rec.harvest_date.isoformat(),
            "grower": rec.grower, "defect_rate": rates[fr["lot_id"]],
            "features": fr["features"],
            "weather": [{**d, "date": d["date"].isoformat()}
                        for d in weather_by_lot[fr["lot_id"]]],
        })

    return {
        "data_mode": config.DATA_MODE,
        "lots": lots,
        "weather_warnings": weather_warnings,
        "analysis": {
            "n": result.n,
            "factors": [vars(f) for f in result.factors],
            "spike": result.spike,
            "notes": result.notes,
        },
    }
