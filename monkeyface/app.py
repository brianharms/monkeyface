"""Component 5 backend: thin FastAPI glue. Delegates to pipeline."""
import json
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
import os
from monkeyface import ingest, pipeline

app = FastAPI(title="monkeyface")

STATIC_DIR = os.path.join(os.path.dirname(__file__), "..", "static")


@app.get("/")
def index():
    return FileResponse(os.path.join(STATIC_DIR, "index.html"))


@app.post("/api/columns")
async def columns(file: UploadFile = File(...)):
    """Return the spreadsheet's column headers so the UI can build a mapping."""
    data = await file.read()
    try:
        df = ingest.load_table(data, file.filename)
    except Exception as e:  # noqa: BLE001
        raise HTTPException(400, f"could not parse file: {e}")
    return {"columns": list(df.columns)}


@app.post("/api/analyze")
async def analyze(file: UploadFile = File(...), mapping: str = Form(...)):
    """Ingest + run the full pipeline. `mapping` is JSON source_col->canonical."""
    data = await file.read()
    try:
        df = ingest.load_table(data, file.filename)
        records, errors = ingest.normalize(df, json.loads(mapping),
                                            return_errors=True)
    except ingest.IngestError as e:
        raise HTTPException(400, str(e))
    if not records:
        raise HTTPException(400, f"no valid rows. errors: {errors[:5]}")

    result = pipeline.run_pipeline(records)
    result["row_errors"] = errors
    return result


# Static assets (app.js, style.css) under /static
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
