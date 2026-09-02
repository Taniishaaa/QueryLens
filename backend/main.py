"""
main.py
-------
FastAPI application entry point.

Phase 1: /connect
Phase 2: /run
Phases 3-4 will add /estimate.
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv
import os

import database

load_dotenv()

QUERY_TIMEOUT_MS = int(os.getenv("QUERY_TIMEOUT_SECONDS", "30")) * 1000

app = FastAPI(
    title="SQL Query Cost Prediction and Optimization System",
    version="0.1.0",
)

# Allow all origins during development. Tighten this for production.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------

class ConnectRequest(BaseModel):
    connection_string: str


class RunRequest(BaseModel):
    query: str


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------

@app.get("/health")
def health():
    return {"status": "ok", "connected": database.is_connected()}


# ---------------------------------------------------------------------------
# POST /connect
# ---------------------------------------------------------------------------

@app.post("/connect")
def connect(req: ConnectRequest):
    """
    Accept a PostgreSQL connection string, connect to the database,
    extract metadata, and store the connection for this session.
    """
    result = database.connect(req.connection_string)

    if not result["success"]:
        # Return 400 with a clean error message — no stack traces.
        raise HTTPException(status_code=400, detail=result["error"])

    # Return success + metadata. Connection string / password never echoed.
    return {
        "success": True,
        "message": result["message"],
        "metadata": {
            "database_name": result["metadata"]["database_name"],
            "schemas": result["metadata"]["schemas"],
            "table_count": result["metadata"]["table_count"],
            # Full table detail (columns, indexes, FK) included for frontend use.
            "tables": result["metadata"]["tables"],
        },
    }


# ---------------------------------------------------------------------------
# POST /run
# ---------------------------------------------------------------------------

@app.post("/run")
def run(req: RunRequest):
    """
    Execute a read-only SQL query and return columns, rows, and execution time.
    Does NOT invoke ML models or the optimizer.
    """
    if not req.query or not req.query.strip():
        raise HTTPException(status_code=400, detail="Query must not be empty.")

    result = database.run_query(req.query.strip(), timeout_ms=QUERY_TIMEOUT_MS)

    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])

    return result
