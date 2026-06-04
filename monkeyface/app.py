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
    """Normalize a batch of raw spreadsheets to the canonical schema.

    Each file is guessed, renamed, validated, and returned as clean CSV bytes
    (base64) plus a per-file report. Files that can't be formatted are reported
    with an error rather than failing the whole batch.
    """
    out = []
    for f in files:
        data = await f.read()
        try:
            csv_bytes, report = formatter.format_bytes(data, f.filename)
            out.append({
                "name": f.filename,
                "ok": True,
                "report": report,
                "csv_b64": base64.b64encode(csv_bytes).decode("ascii"),
            })
        except Exception as e:  # noqa: BLE001 - per-file, reported not raised
            out.append({"name": f.filename, "ok": False, "error": str(e)})
    return {"files": out}


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
