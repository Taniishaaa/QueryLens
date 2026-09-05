# SQL Query Cost Prediction and Optimization System

A web application where a user connects their own database and analyzes SQL queries using ML-based cost prediction and optimization recommendations.

---

## Project Structure

```
QueryLens/
├── backend/
│   ├── main.py            # FastAPI app — all endpoints
│   ├── database.py        # PostgreSQL connection + metadata extraction
│   ├── features.py        # SQL + EXPLAIN feature extraction
│   ├── ml_models.py       # ML prediction interface (dummy → real)
│   ├── optimizer.py       # Query optimization recommendations (dummy → real)
│   ├── requirements.txt
│   ├── .env.example
│   ├── models/            # Drop trained .joblib model files here (Phase 6)
│   ├── test_phase2.py     # /connect and /run tests
│   ├── test_phase3.py     # Feature extraction tests
│   └── test_phase5.py     # Full end-to-end tests (45 checks)
├── frontend/               # React + plain CSS workspace UI
│   ├── src/App.jsx         # Phase 1 application shell
│   └── src/styles.css      # QueryLens design system and layout
└── README.md
```

---

## User Flow

1. User visits the website
2. User enters a db connection string
3. Backend connects and extracts database metadata
4. User writes a SQL query in the editor
5. User clicks one of two buttons:
   - **RUN** — executes the query, returns results and execution time
   - **ESTIMATE** — runs the ML pipeline, returns cost category, predicted time, and optimization recommendation

---

## Setup

### 1. Install dependencies

```bash
cd backend
pip install -r requirements.txt
```

### 2. Configure environment

```bash
cp .env.example .env
```

Edit `.env` if needed:

```
DEFAULT_CONNECTION_STRING=postgresql://user:password@localhost:5432/dbname
QUERY_TIMEOUT_SECONDS=30
```

### 3. Start the server

```bash
cd backend
uvicorn main:app --reload --port 8000
python -m uvicorn main:app --reload --port 8000
```

Server runs at `http://localhost:8000`
Interactive API docs at `http://localhost:8000/docs`

### 4. Start the frontend (Phase 1)

```bash
cd frontend
npm install
npm run dev
```

The Vite development server proxies `/api/*` requests to the backend at
`http://localhost:8000`. The current frontend supports the Phase 2 PostgreSQL
connection flow: it checks backend health, submits connection strings to
`/connect`, and renders the returned database schema. It also supports query
execution through `/run` and ML cost estimation through `/estimate`, including
result rows, planner signals, model confidence, and the full feature set.
Query optimization integration will be added in a subsequent phase.

---

## API Endpoints

### GET /health
Check if the server is running and whether a database is connected.

**Response:**
```json
{ "status": "ok", "connected": false }
```

---

### POST /connect
Connect to a PostgreSQL database and extract metadata.

**Request:**
```json
{
  "connection_string": "postgresql://user:password@host:5432/dbname"
}
```

**Response:**
```json
{
  "success": true,
  "message": "Database connected successfully",
  "metadata": {
    "database_name": "demo",
    "schemas": ["bookings", "public"],
    "table_count": 10,
    "tables": [
      {
        "schema": "bookings",
        "table": "flights",
        "estimated_row_count": 214867,
        "columns": [{ "column_name": "flight_id", "data_type": "integer", "is_nullable": "NO" }],
        "indexes": [...],
        "foreign_keys": [...]
      }
    ]
  }
}
```

> Passwords are never echoed in responses or logs.

---

### POST /run
Execute a read-only SQL query. Does not use ML models.

**Request:**
```json
{ "query": "SELECT * FROM bookings.flights LIMIT 10" }
```

**Response:**
```json
{
  "success": true,
  "columns": ["flight_id", "flight_no", "status"],
  "rows": [...],
  "execution_time_ms": 4.2,
  "row_count": 10
}
```

> Blocked statements: `DROP`, `DELETE`, `TRUNCATE`, `ALTER`, `UPDATE`, `INSERT`, `CREATE`, `GRANT`, `REVOKE`, `COPY`, `VACUUM`, `REINDEX`

---

### POST /estimate
Run the full ML prediction pipeline without executing the query.

**Request:**
```json
{ "query": "SELECT * FROM bookings.flights WHERE status = 'Arrived'" }
```

**Response:**
```json
{
  "success": true,
  "cost_category": "High",
  "confidence": 0.91,
  "predicted_execution_time_ms": 245.6,
  "estimated_cost": 1250.4,
  "features": {
    "num_tables": 1,
    "num_joins": 0,
    "num_filters": 1,
    "has_group_by": 0,
    "has_order_by": 0,
    "has_aggregation": 0,
    "num_aggregations": 0,
    "num_selected_columns": 1,
    "num_subqueries": 0,
    "query_depth": 0,
    "estimated_cost": 1250.4,
    "estimated_rows": 107433,
    "plan_depth": 1,
    "num_seq_scans": 1,
    "num_index_scans": 0,
    "num_nested_loops": 0,
    "num_hash_joins": 0,
    "num_merge_joins": 0
  },
  "recommendation": {
    "available": true,
    "reason": "Sequential scan detected — consider adding an index on the filtered column.",
    "optimized_query": "SELECT * FROM bookings.flights WHERE status = 'Arrived'"
  }
}
```

---

## ML Pipeline (Current State)

### Cost Category Classification

| Estimated Cost (PostgreSQL) | Category |
|-----------------------------|----------|
| < 100                       | Low      |
| 100 – 999                   | Medium   |
| ≥ 1000                      | High     |

> Note: PostgreSQL estimated cost is **not** milliseconds. It is the planner's internal unit.

### Current Models (Dummy)
`ml_models.py` currently uses rule-based dummy functions derived from the EXPLAIN estimated cost. These are clearly marked in the code and must be replaced with real trained models.

### Integrating Real Models (Phase 6 — teammate task)

Drop these files into `backend/models/`:

| File | Purpose |
|------|---------|
| `classifier.joblib` | Trained cost category classifier |
| `preprocessor.joblib` | Feature preprocessing pipeline |
| `regression_model.joblib` | Execution time regressor |
| `label_encoder.joblib` | Label encoder (if needed) |

Then update `ml_models.py` — the `_real_classify()` and `_real_regress()` stubs are already in place. The model files are auto-detected at startup; no other changes needed.

**Expected feature input to the model** (18 features):

| Feature | Source |
|---------|--------|
| `num_tables` | SQL parse |
| `num_joins` | SQL parse |
| `num_filters` | SQL parse |
| `has_group_by` | SQL parse |
| `has_order_by` | SQL parse |
| `has_aggregation` | SQL parse |
| `num_aggregations` | SQL parse |
| `num_selected_columns` | SQL parse |
| `num_subqueries` | SQL parse |
| `query_depth` | SQL parse |
| `estimated_cost` | EXPLAIN |
| `estimated_rows` | EXPLAIN |
| `plan_depth` | EXPLAIN |
| `num_seq_scans` | EXPLAIN |
| `num_index_scans` | EXPLAIN |
| `num_nested_loops` | EXPLAIN |
| `num_hash_joins` | EXPLAIN |
| `num_merge_joins` | EXPLAIN |

> The feature names above must match exactly what the trained model expects. Do not rename them.

---

## Optimizer (Current State — teammate task)

`optimizer.py` currently returns rule-based hints (sequential scan warnings, join index suggestions, etc.) and returns the original query unchanged.

The real optimizer should eventually:
1. Analyse the query and plan
2. Generate candidate rewrites
3. Verify equivalence using EXPLAIN cost comparison
4. Return the best verified candidate

The function signature must stay the same:
```python
get_optimization_recommendation(query: str, features: dict) -> dict
# returns: { "available": bool, "reason": str, "optimized_query": str }
```

---

## Running Tests

Update the `CONN` string at the top of each test file with your PostgreSQL credentials, then:

```bash
cd backend

# Phase 2 — /connect and /run
python test_phase2.py

# Phase 3 — feature extraction
python test_phase3.py

# Phase 5 — full end-to-end (45 checks)
python test_phase5.py
```

---

## Security Notes

- Passwords are never logged or returned in API responses
- Only `SELECT` queries are allowed through `/run` and `/estimate`
- Query execution has a configurable timeout (default 30s)
- Database credentials are stored in memory only for the current session

---

## Development Phases

| Phase | Status | Description |
|-------|--------|-------------|
| 1 | Done | FastAPI setup, `/connect`, metadata extraction |
| 2 | Done | `/run` endpoint, SQL safety validation |
| 3 | Done | `features.py` — SQL + EXPLAIN feature extraction |
| 4 | Done | `ml_models.py`, `optimizer.py`, `/estimate` endpoint |
| 5 | Done | End-to-end tests (45/45 passing) |
| 6 | Pending | Integrate real trained ML models |
| 7 | Pending | Real query optimization engine |
