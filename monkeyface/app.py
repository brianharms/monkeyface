"""Component 5 backend: thin FastAPI glue. Delegates to pipeline."""
import base64
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
import os
from monkeyface import ingest, pipeline, formatter

app = FastAPI(title="monkeyface")

STATIC_DIR = os.path.join(os.path.dirname(__file__), "..", "static")


@app.get("/")
def index():
    return FileResponse(os.path.join(STATIC_DIR, "index.html"))


@app.post("/api/format")
async def format_files(files: list[UploadFile] = File(...)):
    """Step 1: normalize a batch of raw spreadsheets AND merge into one file.

    Each file is matched to the canonical schema and cleaned, then all rows are
    consolidated into a single unified `master.csv`. lot_id is the primary key:
    identical re-exports de-dupe silently; a true conflict (same lot_id, different
    data) blocks the merge and is reported for the user to resolve.
    """
    raw = [(await f.read(), f.filename) for f in files]
    result = formatter.consolidate(raw)
    if result.get("ok"):
        result["csv_b64"] = base64.b64encode(result.pop("csv_bytes")).decode("ascii")
    return result


@app.post("/api/analyze")
async def analyze(file: UploadFile = File(...)):
    """Run the full pipeline on an ALREADY-FORMATTED (canonical) file.

    Files must have been through the formatter first; otherwise we reject with
    a clear message naming the missing columns.
    """
    data = await file.read()
    try:
        df = ingest.load_table(data, file.filename)
    except Exception as e:  # noqa: BLE001
        raise HTTPException(400, f"could not read file: {e}")
    try:
        records, errors = ingest.normalize_canonical(df, return_errors=True)
    except ingest.IngestError as e:
        raise HTTPException(400, str(e))
    if not records:
        raise HTTPException(400, f"no valid rows. errors: {errors[:5]}")

    try:
        result = pipeline.run_pipeline(records)
    except ValueError as e:
        raise HTTPException(400, str(e))
    result["row_errors"] = errors
    return result


# Static assets (app.js, style.css) under /static
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
