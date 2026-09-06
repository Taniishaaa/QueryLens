# QueryLens --- SQL Query Cost Prediction and Optimization System

QueryLens is a web application that allows a user to connect a
PostgreSQL database, explore its schema, run read-only SQL queries,
estimate query cost and execution time using trained ML models, and
generate verified SQL optimizations using the Gemini-based optimizer.

------------------------------------------------------------------------

## Project Structure

``` text
QueryLens/
├── backend/
│   ├── main.py                 # FastAPI application and API endpoints
│   ├── database.py             # PostgreSQL connection, metadata and query execution
│   ├── features.py             # SQL, database metadata and EXPLAIN feature extraction
│   ├── ml_models.py            # Regression and classification model interface
│   ├── optimizer.py            # Query optimization pipeline
│   ├── llm_rewriter.py         # Gemini-based candidate SQL generation
│   ├── explain_analyzer.py     # PostgreSQL EXPLAIN cost analysis
│   ├── equivalence_checker.py  # Result-equivalence verification
│   ├── sql_validator.py        # Read-only SQL validation
│   ├── schema_reader.py        # Database schema information for optimization
│   ├── requirements.txt
│   ├── .env.example
│   ├── models/
│   │   ├── model_histogram_gradient_boosting.pkl
│   │   └── best_classification_model.pkl
│   ├── test_phase2.py          # /connect and /run tests
│   ├── test_phase3.py          # Feature extraction tests
│   └── test_phase5.py          # End-to-end tests
│
├── frontend/
│   ├── index.html
│   ├── package.json
│   ├── vite.config.js
│   └── src/
│       ├── App.jsx             # QueryLens application UI and frontend workflow
│       ├── api.js              # Frontend API calls
│       ├── main.jsx
│       └── styles.css          # QueryLens UI and layout
│
└── README.md
```

------------------------------------------------------------------------

## User Flow

The QueryLens frontend follows this workflow:

1.  Start the QueryLens backend.
2.  Start the React/Vite frontend.
3.  Open the QueryLens web application.
4.  QueryLens checks the backend health and database connection status.
5.  If no database is connected, the **Connect your database** dialog is
    displayed.
6.  Enter a PostgreSQL connection string.
7.  Click **Connect database**.
8.  QueryLens connects to the PostgreSQL database and displays the
    returned schema.
9.  Use the **Schema Explorer** to search for tables or columns and
    expand tables to view their columns, types and related metadata.
10. Write or edit SQL in the query editor.
11. Choose one of the available actions:
    -   **Run query** --- executes the read-only query and displays the
        result set and execution time.
    -   **Estimate** --- runs the ML prediction pipeline and displays
        the predicted execution time, cost category, confidence and
        PostgreSQL plan signals.
    -   **Optimize** --- sends the query through the Gemini-based
        optimization pipeline and displays the verified optimization
        result.
12. Use the result tabs to inspect:
    -   **Results**
    -   **Query plan**
    -   **Features**
    -   **Optimized SQL**
13. If an optimization is verified as an improvement, copy the optimized
    SQL or replace the query editor contents with it.

------------------------------------------------------------------------

# Setup

## 1. Backend Setup

Open PowerShell or a terminal and move into the backend directory:

``` bash
cd backend
```

Install the backend dependencies:

``` bash
pip install -r requirements.txt
```

### Configure environment variables

Copy the example environment file:

``` bash
cp .env.example .env
```

On Windows PowerShell, if `cp` is unavailable, use:

``` powershell
Copy-Item .env.example .env
```

Edit `.env` and configure the required values, for example:

``` text
DEFAULT_CONNECTION_STRING=postgresql://user:password@localhost:5432/dbname
QUERY_TIMEOUT_SECONDS=30
```

If the Gemini-based optimizer is enabled, configure the Gemini API key
expected by the backend as defined in `.env.example`.

### ML model files

Place the trained models in:

``` text
backend/models/
```

The current backend expects:

``` text
backend/models/model_histogram_gradient_boosting.pkl
backend/models/best_classification_model.pkl
```

The models should be loaded successfully when the backend starts.

> The classification model and its scikit-learn preprocessing objects
> must be compatible with the scikit-learn version used by the
> environment in which the model was serialized. The regression model
> also reports a version warning if its training and runtime
> scikit-learn versions differ.

------------------------------------------------------------------------

## 2. Start the Backend

From the `backend` directory:

``` bash
python -m uvicorn main:app --reload --port 8000
```

The backend runs at:

``` text
http://localhost:8000
```

Interactive API documentation is available at:

``` text
http://localhost:8000/docs
```

Before using the frontend, make sure the backend is running.

------------------------------------------------------------------------

## 3. Frontend Setup

Open a **new terminal** while keeping the backend running.

Move into the frontend directory:

``` bash
cd frontend
```

Install the frontend dependencies:

``` bash
npm install
```

Start the Vite development server:

``` bash
npm run dev
```

Vite will display the local frontend URL in the terminal, normally:

``` text
http://localhost:5173
```

Open that address in your browser.

The frontend communicates with the backend through the Vite proxy
configured for the QueryLens application.

------------------------------------------------------------------------

# Frontend Features

## 1. Backend and Database Connection Status

When the frontend opens, it checks `/health`.

The top navigation displays the current connection state:

-   **Checking connection**
-   **Connected**
-   **Connect database**

A refresh control is available to reload the application and re-check
the connection.

If the backend cannot be reached, the frontend displays an error asking
the user to start the API server.

If no PostgreSQL database is connected, the application shows a
connection prompt.

------------------------------------------------------------------------

## 2. PostgreSQL Connection Dialog

Click **Connect database** to open the connection dialog.

Enter a PostgreSQL connection string in the format:

``` text
postgresql://user:password@host:5432/database
```

The connection string field is presented as a password-type field.

Click:

**Connect database**

After a successful connection:

-   The connection dialog closes.
-   The connection status changes to **Connected**.
-   The connected database name is displayed in the top bar.
-   Database metadata is loaded into the Schema Explorer.
-   Query execution and analysis actions become available.

The frontend does not store the connection string.

------------------------------------------------------------------------

## 3. Schema Explorer

After connecting, the left-side **Schema Explorer** displays the
database schema returned by the backend.

It provides:

-   Database name
-   Schema information
-   Table count
-   Search
-   Table expansion
-   Column names
-   Data types
-   Nullable information
-   Estimated row counts
-   Index information
-   Foreign-key information

### Searching the schema

Use the search box to search by:

-   Schema name
-   Table name
-   Column name

Only matching tables are displayed.

### Viewing table details

Click a table to expand it.

The expanded table displays its columns and associated metadata.

------------------------------------------------------------------------

## 4. Query Editor

The center of the application contains the SQL query editor.

The editor:

-   Supports multiline SQL.
-   Displays the current query as `query.sql`.
-   Indicates that the query is PostgreSQL.
-   Shows the number of lines in the query.
-   Displays whether the application is ready to analyze the query.
-   Prevents analysis actions until a database is connected.

The editor initially contains a sample PostgreSQL query using the
`bookings.flights` and `bookings.routes` tables.

The query can be completely replaced with a user's own SQL.

### Clear

Click **Clear** to remove the current query.

------------------------------------------------------------------------

## 5. Run Query

Click:

**Run query**

to execute the current SQL through the backend `/run` endpoint.

The frontend displays the returned data in the **Results** tab.

The results include:

-   Number of rows returned
-   Execution time in milliseconds
-   Result columns
-   Result rows

If the query completes without returning a result set, the frontend
displays a completion message instead.

Only read-only SQL accepted by the backend can be executed.

------------------------------------------------------------------------

## 6. Estimate

Click:

**Estimate**

to send the SQL to the backend `/estimate` endpoint.

The query is analyzed without executing it as a normal query.

The frontend displays the returned analysis through the result tabs.

### Query Plan tab

The **Query plan** tab displays:

-   PostgreSQL estimated cost
-   Estimated rows
-   Plan depth
-   Sequential scans
-   Index scans
-   Plan joins

### Features tab

The **Features** tab displays the complete feature set returned by the
backend.

For the current regression model, the expected feature set contains 20
features:

1.  `num_tables`
2.  `num_joins`
3.  `num_filters`
4.  `has_group_by`
5.  `has_order_by`
6.  `has_aggregation`
7.  `num_aggregations`
8.  `num_selected_columns`
9.  `num_subqueries`
10. `query_depth`
11. `total_rows`
12. `total_table_size`
13. `num_indexes`
14. `column_cardinality`
15. `estimated_rows`
16. `estimated_cost`
17. `plan_depth`
18. `num_sequential_scans`
19. `num_index_scans`
20. `num_plan_joins`

The frontend renders the feature names and values dynamically from the
backend response.

### Query Insights panel

After an estimate is available, the right-side **Query insights** panel
displays the prediction summary, including the predicted execution time
and PostgreSQL cost/plan information returned by the backend.

If an estimate has not yet been performed, the panel prompts the user to
run an estimate.

------------------------------------------------------------------------

## 7. Optimize

Click:

**Optimize**

to send the SQL to the backend `/optimize` endpoint.

The frontend then switches to the **Optimized SQL** tab.

The backend optimizer generates candidate rewrites using Gemini and
verifies candidates before accepting an optimization.

The frontend displays:

-   Optimization status
-   Estimated cost reduction
-   Optimization explanation
-   Original PostgreSQL estimated cost
-   Optimized PostgreSQL estimated cost
-   Original SQL
-   Optimized SQL

### Verified improvement

When the backend returns:

``` text
status = IMPROVED
```

the frontend displays the optimization as:

**Verified equivalent**

and shows the estimated cost reduction.

Two actions become available:

**Copy optimized SQL**

Copies the optimized SQL to the clipboard.

**Replace editor query**

Replaces the SQL currently in the editor with the optimized SQL.

### No verified improvement

When the backend returns:

``` text
status = NO_IMPROVEMENT
```

the frontend displays:

**No verified improvement**

The original query remains the best verified option and no replacement
action is shown.

------------------------------------------------------------------------

## 8. Result Tabs

The main results area contains four tabs:

``` text
Results
Query plan
Features
Optimized SQL
```

### Results

Shows the output of a successful **Run query** operation.

### Query plan

Shows PostgreSQL planner information returned during **Estimate**.

### Features

Shows all extracted SQL, database and EXPLAIN features returned during
**Estimate**.

### Optimized SQL

Shows the verified optimization result returned by **Optimize**.

If an operation has not been performed yet, the relevant tab displays an
instruction explaining what action is required.

------------------------------------------------------------------------

## 9. Loading and Error States

While an operation is running, its button displays a progress state:

-   **Running...**
-   **Estimating...**
-   **Optimizing...**

Other query actions are disabled while a request is active.

Frontend errors are displayed inside the workspace.

Examples include:

-   Empty query
-   Database not connected
-   Backend unavailable
-   Database connection failure
-   Query execution failure
-   ML estimation failure
-   Optimization failure

------------------------------------------------------------------------

# API Endpoints

## GET /health

Check whether the server is running and whether a database is connected.

**Response:**

``` json
{
  "status": "ok",
  "connected": false
}
```

------------------------------------------------------------------------

## POST /connect

Connect to a PostgreSQL database and extract metadata.

**Request:**

``` json
{
  "connection_string": "postgresql://user:password@host:5432/dbname"
}
```

**Response:**

``` json
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
        "columns": [
          {
            "column_name": "flight_id",
            "data_type": "integer",
            "is_nullable": "NO"
          }
        ],
        "indexes": [],
        "foreign_keys": []
      }
    ]
  }
}
```

> Passwords are never echoed in responses or logs.

------------------------------------------------------------------------

## POST /run

Execute a read-only SQL query.

**Request:**

``` json
{
  "query": "SELECT * FROM bookings.flights LIMIT 10"
}
```

**Response:**

``` json
{
  "success": true,
  "columns": ["flight_id", "flight_no", "status"],
  "rows": [],
  "execution_time_ms": 4.2,
  "row_count": 10
}
```

The frontend sends the query and renders this response in the
**Results** tab.

> Blocked statements include `DROP`, `DELETE`, `TRUNCATE`, `ALTER`,
> `UPDATE`, `INSERT`, `CREATE`, `GRANT`, `REVOKE`, `COPY`, `VACUUM`, and
> `REINDEX`.

------------------------------------------------------------------------

## POST /estimate

Run the ML prediction pipeline.

The endpoint accepts the SQL query as raw text.

**Request body:**

``` text
SELECT * FROM bookings.flights WHERE status = 'Arrived'
```

**Response:**

``` json
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
    "query_depth": 1,
    "total_rows": 100000,
    "total_table_size": 12345678,
    "num_indexes": 2,
    "column_cardinality": 10,
    "estimated_rows": 107433,
    "estimated_cost": 1250.4,
    "plan_depth": 1,
    "num_sequential_scans": 1,
    "num_index_scans": 0,
    "num_plan_joins": 0
  }
}
```

> The exact feature values depend on the connected database and SQL
> query.

------------------------------------------------------------------------

## POST /optimize

Generate and verify SQL optimization candidates.

The endpoint accepts the SQL query as raw text.

**Request body:**

``` text
SELECT * FROM bookings.flights WHERE status = 'Arrived'
```

**Response:**

``` json
{
  "success": true,
  "optimization": {
    "original_sql": "SELECT * FROM bookings.flights WHERE status = 'Arrived'",
    "optimized_sql": "SELECT * FROM bookings.flights WHERE status = 'Arrived'",
    "original_cost": 1250.4,
    "optimized_cost": 1250.4,
    "improvement_percent": 0.0,
    "status": "NO_IMPROVEMENT",
    "optimization_explanation": "No generated candidate produced a lower PostgreSQL estimated cost while also passing SQL validation and result-equivalence verification."
  }
}
```

When a valid lower-cost equivalent candidate is found, the status is:

``` text
IMPROVED
```

The frontend displays the verified optimized SQL and provides
copy/replace actions.

------------------------------------------------------------------------

# ML Pipeline

## Cost Category Classification

The classification model predicts the SQL cost category.

The backend currently calls the classification model with the connected
query's extracted features and:

``` text
source_dataset = JOB
```

The model bundle is loaded from:

``` text
backend/models/best_classification_model.pkl
```

The bundle contains:

-   Classification model
-   Preprocessor
-   Label encoder
-   Classification feature columns

------------------------------------------------------------------------

## Execution-Time Regression

The regression model is:

``` text
HistGradientBoostingRegressor
```

The model is loaded from:

``` text
backend/models/model_histogram_gradient_boosting.pkl
```

The regression model predicts:

``` text
log1p(actual_execution_time)
```

The backend converts the prediction back to milliseconds using:

``` text
expm1(prediction)
```

The regression model expects exactly 20 features.

------------------------------------------------------------------------

# PostgreSQL Cost

PostgreSQL estimated cost is the database planner's internal cost unit.

It is **not equivalent to milliseconds**.

QueryLens therefore presents PostgreSQL estimated cost separately from
the ML-predicted execution time.

------------------------------------------------------------------------

# Query Optimization Pipeline

The current optimizer follows this process:

``` text
Original SQL
     │
     ▼
Analyze original PostgreSQL plan
     │
     ▼
Get original estimated cost
     │
     ▼
Generate candidate rewrites using Gemini
     │
     ▼
Validate each candidate
     │
     ▼
EXPLAIN each valid candidate
     │
     ▼
Compare estimated cost
     │
     ▼
Keep only lower-cost candidates
     │
     ▼
Check result equivalence
     │
     ▼
Select lowest-cost verified candidate
     │
     ├── IMPROVED
     │
     └── NO_IMPROVEMENT
```

A candidate is accepted only when it:

1.  Passes SQL validation.
2.  Has a lower PostgreSQL estimated cost than the original.
3.  Produces an equivalent result to the original query.

------------------------------------------------------------------------

# Running Tests

Update the database connection string at the top of the test files with
valid PostgreSQL credentials.

From the backend directory:

``` bash
cd backend
```

### Phase 2 --- connection and query execution

``` bash
python test_phase2.py
```

Tests:

-   `/connect`
-   `/run`

### Phase 3 --- feature extraction

``` bash
python test_phase3.py
```

Tests SQL and EXPLAIN feature extraction.

### Phase 5 --- end-to-end tests

``` bash
python test_phase5.py
```

Runs the available full end-to-end checks.

------------------------------------------------------------------------

# Security Notes

-   Passwords are not returned in API responses.
-   The frontend does not store the PostgreSQL connection string.
-   The connection string is sent to the configured QueryLens backend.
-   `/run` is restricted to read-only SQL through backend validation.
-   `/estimate` analyzes the query through feature extraction and
    PostgreSQL EXPLAIN.
-   Query execution uses the configured timeout.
-   Database credentials are kept in backend runtime state rather than
    persisted by the frontend.
-   The application does not currently provide a separate persistent
    user-account database.

> QueryLens connects to the user's PostgreSQL database for analysis.
> That database is separate from the QueryLens application itself; the
> current project does not implement a persistent application database
> for user accounts or query history.

------------------------------------------------------------------------

# Development Status

  -------------------------------------------------------------------------------
  Component               Status                  Description
  ----------------------- ----------------------- -------------------------------
  FastAPI backend         Done                    API server and database
                                                  workflow

  PostgreSQL connection   Done                    Connect and retrieve database
                                                  metadata

  SQL execution           Done                    Read-only `/run` endpoint

  SQL safety validation   Done                    Blocks non-read-only statements

  Feature extraction      Done                    SQL + database metadata +
                                                  PostgreSQL EXPLAIN features

  Regression model        Done                    HistGradientBoostingRegressor
                                                  integration

  Classification model    Done                    Trained classifier bundle
                                                  integration

  ML estimation           Done                    Cost category, confidence and
                                                  predicted execution time

  Gemini candidate        Done                    Generates optimization
  generation                                      candidates

  Query validation        Done                    Candidate SQL validation

  Cost comparison         Done                    PostgreSQL estimated-cost
                                                  comparison

  Equivalence             Done                    Original vs candidate result
  verification                                    verification

  Query optimization      Done                    Selects the best verified
                                                  lower-cost candidate

  React frontend          Done                    Complete QueryLens workspace

  Database connection UI  Done                    Connection modal and status
                                                  indicators

  Schema Explorer         Done                    Searchable tables and columns

  Query editor            Done                    SQL editing and clear
                                                  functionality

  Query results UI        Done                    Results table and execution
                                                  time

  Query plan UI           Done                    PostgreSQL planner metrics

  Features UI             Done                    Complete returned feature
                                                  display

  Optimization UI         Done                    Verified result, cost
                                                  comparison and SQL comparison

  Copy optimized SQL      Done                    Clipboard action

  Replace editor query    Done                    Applies verified optimized SQL
                                                  to editor
  -------------------------------------------------------------------------------

------------------------------------------------------------------------

# Troubleshooting

## Backend starts but `/estimate` returns 500

Check that both model files exist:

``` text
backend/models/model_histogram_gradient_boosting.pkl
backend/models/best_classification_model.pkl
```

The backend startup logs should report that the regression and
classification models loaded successfully.

If a classification model was serialized using a different scikit-learn
version, model loading may fail because of serialization
incompatibility. Use the compatible scikit-learn version used when the
model was trained/serialized.

------------------------------------------------------------------------

## `/estimate` shows an EXPLAIN syntax error

Check the SQL entered in the query editor.

For example, this is invalid:

``` sql
SELECT * FROM employees:
```

Use:

``` sql
SELECT * FROM employees;
```

------------------------------------------------------------------------

## `/optimize` fails while generating Gemini candidates

Check that:

-   The Gemini API configuration is present in the backend environment.
-   The Gemini SDK installed in the backend matches the API usage in
    `llm_rewriter.py`.
-   The connected database is available.
-   The submitted SQL is valid PostgreSQL.

------------------------------------------------------------------------

## Frontend says the backend is unavailable

Make sure the backend is running:

``` bash
python -m uvicorn main:app --reload --port 8000
```

Then refresh the frontend.

------------------------------------------------------------------------

## Frontend shows "Connect database"

This means the backend is reachable but no PostgreSQL database is
currently connected.

Click **Connect database**, enter a valid PostgreSQL connection string,
and connect again.

------------------------------------------------------------------------

## Query actions are disabled

The **Run query**, **Estimate**, and **Optimize** buttons require:

1.  A reachable backend.
2.  A connected PostgreSQL database.
3.  A non-running request.

Enter a query and connect the database before using these actions.

------------------------------------------------------------------------

# Typical Local Development Workflow

Use two terminals.

### Terminal 1 --- Backend

``` bash
cd backend
python -m uvicorn main:app --reload --port 8000
```

### Terminal 2 --- Frontend

``` bash
cd frontend
npm install
npm run dev
```

Then open the Vite URL shown in the frontend terminal.

The normal application workflow is:

``` text
Start backend
     ↓
Start frontend
     ↓
Open QueryLens
     ↓
Connect PostgreSQL
     ↓
Explore schema
     ↓
Write SQL
     ↓
Run / Estimate / Optimize
     ↓
Inspect Results / Query plan / Features / Optimized SQL
     ↓
Copy or replace with verified optimized SQL
```
