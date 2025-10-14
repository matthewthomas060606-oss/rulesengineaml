import os
import time
from datetime import datetime, timezone
import sqlite3
from fastapi import FastAPI, File, UploadFile, Body, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from engine import screen_xml_bytes, refresh_lists, response_code_from_result
from database import warm_database
from config import get_config

try:
    from config import config
except Exception:
    config = get_config()

MAX_REQUEST_MB = int(os.getenv("AML_MAX_REQUEST_MB", 5))

app = FastAPI(title="AML Screening API", version="0.1.0")

@app.on_event("startup")
def startup_warm():
    warm_database()

class ScreenRequest(BaseModel):
    xml: str

def _enforce_size(n_bytes: int):
    limit = MAX_REQUEST_MB * 1048576
    if n_bytes > limit:
        raise HTTPException(status_code=413, detail="payload too large")

@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/ready")
def ready():
    try:
        if not config.DB_PATH or not os.path.exists(config.DB_PATH):
            return {"ready": False, "reason": "db-missing"}
        conn = sqlite3.connect(config.DB_PATH)
        cur = conn.cursor()
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='sanctionslist'")
        if not cur.fetchone():
            return {"ready": False, "reason": "table-missing"}
        cur.execute("SELECT COUNT(1) FROM sanctionslist")
        row_count = cur.fetchone()[0]
        if row_count <= 0:
            return {"ready": False, "reason": "empty-db"}
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='sanctions_fts'")
        if not cur.fetchone():
            return {"ready": False, "reason": "fts-missing"}
        return {"ready": True, "reason": None}
    except Exception as e:
        return {"ready": False, "reason": f"error: {e.__class__.__name__}"}

@app.get("/warm-status")
def warm_status():
    return warm_database()

@app.post("/screen")
def screen(req: ScreenRequest = Body(...)):
    try:
        data = req.xml.encode("utf-8")
        _enforce_size(len(data))
        result = screen_xml_bytes(data)
        code = response_code_from_result(result)
        result.setdefault("engine", {})["responseCode"] = code
        return JSONResponse(content=result, headers={"X-Response-Code": code})
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/screen/file")
async def screen_file(file: UploadFile = File(...)):
    try:
        xml_bytes = await file.read()
        _enforce_size(len(xml_bytes))
        result = screen_xml_bytes(xml_bytes)
        code = response_code_from_result(result)
        result.setdefault("engine", {})["responseCode"] = code
        return JSONResponse(content=result, headers={"X-Response-Code": code})
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/refresh-lists")
def refresh_lists_endpoint():
    n = refresh_lists()
    return {"status": "rebuilt", "rows": n}
