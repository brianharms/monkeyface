"""Batch formatter: normalize raw field spreadsheets to the canonical schema.

This is the SEPARATE formatting step. Real-world exports arrive with messy,
inconsistent column names; the formatter guesses each column's canonical role,
renames it, validates the rows, and emits a clean canonical CSV. Once a file
has been through here, the analyze flow can consume it directly with no
column-matching step.

Used by the in-app "Format files" mode (one call per uploaded file).
"""
import io
import pandas as pd
from monkeyface import schema


# Canonical column order for emitted files.
CANONICAL_ORDER = [
    schema.LOT_ID, schema.FIELD_ID, schema.LAT, schema.LON,
    schema.HARVEST_DATE, schema.DEFECT_RATE, schema.GROWER, schema.VARIETY,
]


def guess_canonical(col: str) -> str | None:
    """Guess which canonical field a raw column name maps to (or None)."""
    c = str(col).strip().lower()
    # exact canonical name wins
    if c in (schema.REQUIRED_COLUMNS + schema.KNOWN_OPTIONAL):
        return c
    if c in ("longitude", "long", "lng"):
        return schema.LON
    if c in ("latitude",):
        return schema.LAT
    # fuzzy keyword match
    if "lot" in c:
        return schema.LOT_ID
    if "field" in c or "ranch" in c or "block" in c:
        return schema.FIELD_ID
    if c.startswith("lat"):
        return schema.LAT
    if c.startswith("lon") or "lng" in c or "long" in c:
        return schema.LON
    if "harv" in c or "date" in c or "pick" in c:
        return schema.HARVEST_DATE
    if "defect" in c or "catface" in c or "monkey" in c or ("cat" in c and "face" in c):
        return schema.DEFECT_RATE
    if "grow" in c or "supplier" in c or "vendor" in c:
        return schema.GROWER
    if "variet" in c or "cultivar" in c:
        return schema.VARIETY
    return None


class FormatError(Exception):
    pass


def build_mapping(columns) -> dict:
    """Return { source_column: canonical_field } for the guessable columns.

    If two source columns guess to the same canonical field, only the FIRST is
    kept (the later one is left unmapped) so a rename never silently drops data.
    """
    mapping, claimed = {}, set()
    for col in columns:
        cn = guess_canonical(col)
        if cn and cn not in claimed:
            mapping[col] = cn
            claimed.add(cn)
    return mapping


def format_dataframe(df: pd.DataFrame):
    """Normalize one raw DataFrame to the canonical schema.

    Returns (clean_df, report) where report describes what happened. Raises
    FormatError if a REQUIRED canonical column can't be located.
    """
    mapping = build_mapping(df.columns)
    renamed = df.rename(columns=mapping)

    missing = [c for c in schema.REQUIRED_COLUMNS if c not in renamed.columns]
    if missing:
        raise FormatError(
            "could not find required column(s): " + ", ".join(missing)
            + f". Columns seen: {list(df.columns)}")

    # Keep only canonical columns that are present, in canonical order.
    present = [c for c in CANONICAL_ORDER if c in renamed.columns]
    clean = renamed[present].copy()

    # Normalize harvest_date to ISO (YYYY-MM-DD); drop rows we cannot parse.
    parsed = pd.to_datetime(clean[schema.HARVEST_DATE], errors="coerce")
    bad_dates = int(parsed.isna().sum())
    clean = clean.loc[parsed.notna()].copy()
    clean[schema.HARVEST_DATE] = parsed.dropna().dt.strftime("%Y-%m-%d")

    # Coerce coordinates; drop rows with non-numeric / out-of-range coords.
    for coord, lo, hi in ((schema.LAT, -90, 90), (schema.LON, -180, 180)):
        clean[coord] = pd.to_numeric(clean[coord], errors="coerce")
    before = len(clean)
    clean = clean[
        clean[schema.LAT].between(-90, 90) & clean[schema.LON].between(-180, 180)
    ].copy()
    bad_coords = before - len(clean)

    # Drop duplicate lot_ids (keep first).
    before = len(clean)
    clean = clean.drop_duplicates(subset=[schema.LOT_ID], keep="first").copy()
    dup_dropped = before - len(clean)

    report = {
        "rows_in": len(df),
        "rows_out": len(clean),
        "columns_mapped": mapping,
        "dropped_bad_dates": bad_dates,
        "dropped_bad_coords": bad_coords,
        "dropped_duplicates": dup_dropped,
    }
    return clean, report


def format_bytes(data: bytes, filename: str):
    """Parse raw file bytes, format, and return (csv_bytes, report)."""
    name = filename.lower()
    if name.endswith((".xlsx", ".xls")):
        df = pd.read_excel(io.BytesIO(data))
    else:
        df = pd.read_csv(io.BytesIO(data))
    clean, report = format_dataframe(df)
    out = clean.to_csv(index=False).encode("utf-8")
    return out, report
