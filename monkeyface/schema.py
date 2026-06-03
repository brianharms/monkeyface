"""Canonical column names and the normalized record type.

Every module imports names from here so a rename happens in one place.
"""
from dataclasses import dataclass, field
from datetime import date

# Canonical column names produced by ingest and consumed downstream.
LOT_ID = "lot_id"
FIELD_ID = "field_id"
LAT = "lat"
LON = "lon"
HARVEST_DATE = "harvest_date"
DEFECT_RATE = "defect_rate"
GROWER = "grower"
VARIETY = "variety"

REQUIRED_COLUMNS = [LOT_ID, FIELD_ID, LAT, LON, HARVEST_DATE]
KNOWN_OPTIONAL = [DEFECT_RATE, GROWER, VARIETY]


@dataclass
class LotRecord:
    lot_id: str
    field_id: str
    lat: float
    lon: float
    harvest_date: date
    defect_rate: float | None = None
    grower: str | None = None
    variety: str | None = None
    # Arbitrary extra columns (future grower-practice data) carried through.
    extra: dict = field(default_factory=dict)
