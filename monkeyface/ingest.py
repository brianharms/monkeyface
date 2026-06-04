"""Component 1: messy spreadsheet -> clean LotRecord list.

Knows nothing about weather. Tolerant of arbitrary extra columns, which are
carried through into LotRecord.extra so future grower-practice data flows on.
"""
import io
from datetime import date, datetime
import pandas as pd
from monkeyface import schema
from monkeyface.schema import LotRecord


class IngestError(Exception):
    pass


def load_table(data: bytes, filename: str) -> pd.DataFrame:
    """Parse uploaded bytes (CSV or Excel) into a DataFrame."""
    name = filename.lower()
    if name.endswith((".xlsx", ".xls")):
        return pd.read_excel(io.BytesIO(data))
    return pd.read_csv(io.BytesIO(data))


def _parse_date(value) -> date:
    if value is None or (not isinstance(value, (datetime, date)) and pd.isna(value)):
        raise ValueError("missing harvest_date")
    if isinstance(value, (datetime, pd.Timestamp)):
        if pd.isna(value):
            raise ValueError("missing harvest_date")
        return value.date()
    if isinstance(value, date):
        return value
    parsed = pd.to_datetime(str(value), errors="coerce")
    if pd.isna(parsed):
        raise ValueError(f"unparseable harvest_date: {value!r}")
    return parsed.date()


def _opt(v):
    return None if v is None else str(v)


def _coerce_row(row: dict) -> LotRecord:
    lat = float(row[schema.LAT])
    lon = float(row[schema.LON])
    if not (-90 <= lat <= 90):
        raise ValueError(f"lat out of range: {lat}")
    if not (-180 <= lon <= 180):
        raise ValueError(f"lon out of range: {lon}")

    canonical = set(schema.REQUIRED_COLUMNS + schema.KNOWN_OPTIONAL)
    extra = {k: v for k, v in row.items()
             if k not in canonical and pd.notna(v)}

    defect = row.get(schema.DEFECT_RATE)
    return LotRecord(
        lot_id=str(row[schema.LOT_ID]),
        field_id=str(row[schema.FIELD_ID]),
        lat=lat,
        lon=lon,
        harvest_date=_parse_date(row[schema.HARVEST_DATE]),
        defect_rate=None if defect is None or pd.isna(defect) else float(defect),
        grower=None if pd.isna(row.get(schema.GROWER)) else _opt(row.get(schema.GROWER)),
        variety=None if pd.isna(row.get(schema.VARIETY)) else _opt(row.get(schema.VARIETY)),
        extra=extra,
    )


def normalize_canonical(df: pd.DataFrame, return_errors: bool = False):
    """Validate an already-canonical DataFrame (no column matching).

    Used by the analyze flow, which only accepts files that have been through
    the formatter. Raises IngestError listing any missing required columns so
    the UI can tell the user to format the file first.
    """
    missing = [c for c in schema.REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        raise IngestError(
            "not formatted — missing required column(s): " + ", ".join(missing))
    return normalize(df, {c: c for c in df.columns}, return_errors=return_errors)


def normalize(df: pd.DataFrame, mapping: dict, return_errors: bool = False):
    """Rename columns per `mapping` (source_col -> canonical) and validate.

    Returns list[LotRecord]. If return_errors=True, returns (records, errors).
    Raises IngestError if a REQUIRED canonical column is absent after mapping.
    """
    renamed = df.rename(columns=mapping)
    missing = [c for c in schema.REQUIRED_COLUMNS if c not in renamed.columns]
    if missing:
        raise IngestError(f"missing required columns after mapping: {missing}")

    records, errors = [], []
    for i, row in enumerate(renamed.to_dict(orient="records")):
        try:
            records.append(_coerce_row(row))
        except Exception as e:  # noqa: BLE001 - row-level, reported not raised
            errors.append(f"row {i}: {e}")

    # duplicate lot_ids collapse silently downstream (pipeline keys by lot_id).
    # This is a structural problem, not a per-row one: raise in both modes.
    seen, dupes = set(), []
    for r in records:
        if r.lot_id in seen and r.lot_id not in dupes:
            dupes.append(r.lot_id)
        seen.add(r.lot_id)
    if dupes:
        raise IngestError(f"duplicate lot_id(s): {dupes}")

    if return_errors:
        return records, errors
    return records
