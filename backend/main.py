"""
main.py
-------
FastAPI application entry point.

"""

from fastapi import FastAPI, HTTPException, Body
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv
import os

import database
import features as feat
import ml_models
import optimizer

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


class EstimateRequest(BaseModel):
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


# ---------------------------------------------------------------------------
# POST /estimate
# ---------------------------------------------------------------------------


@app.post("/estimate")
def estimate_sql(query: str = Body(..., media_type="text/plain")):
    """
    Estimate SQL execution time from raw SQL text.

    Accepts multiline SQL directly instead of requiring
    the SQL to be embedded inside a JSON string.
    """

    conn = database.get_connection()

    if conn is None:
        raise HTTPException(
            status_code=400,
            detail="Database is not connected."
        )

    try:
        all_features = feat.extract_all_features(query, conn)

        print("\n========== REGRESSION FEATURES ==========")

        for name, value in all_features.items():
            print(f"{name}: {value}")

        print(f"Feature count: {len(all_features)}")
        print("==========================================\n")

        classification = ml_models.predict_cost_category(
            all_features,
            query_text=query,
            source_dataset="JOB"
        )

        predicted_time_ms = ml_models.predict_execution_time(
            all_features
        )

        
        return {
            "success": True,
            "cost_category": classification["category"],
            "confidence": classification["confidence"],
            "predicted_execution_time_ms": predicted_time_ms,
            "estimated_cost": all_features.get("estimated_cost"),
            "features": all_features
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )

@app.post("/optimize")
def optimize_sql(
    query: str = Body(..., media_type="text/plain")
):
    """
    Optimize a SQL query using the Gemini-based
    SQL optimizer.

    Accepts multiline SQL directly as raw text.
    """

    conn = database.get_connection()

    if conn is None:
        raise HTTPException(
            status_code=400,
            detail="Database is not connected."
        )

    try:

        optimization = optimizer.optimize_query(
            query,
            conn
        )

        return {
            "success": True,
            "optimization": optimization
        }

    except Exception as e:

        raise HTTPException(
            status_code=500,
            detail=str(e)
        )    