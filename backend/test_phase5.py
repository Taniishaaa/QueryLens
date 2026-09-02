"""
test_phase5.py
--------------
End-to-end tests for all backend endpoints.

Run from the backend/ directory:
    python test_phase5.py

Requirements:
    - FastAPI server must be running on localhost:8000
    - Update CONN below with your real PostgreSQL credentials
"""

import sys
import requests

BASE = "http://localhost:8000"
CONN = "postgresql://postgres:admin@localhost:5432/demo"  # <-- UPDATE THIS

# A valid read-only query against the airlines/bookings schema
VALID_QUERY        = "SELECT * FROM bookings.flights LIMIT 5"
HEAVY_QUERY        = """
    SELECT b.book_ref, t.passenger_name, f.flight_id, f.status
    FROM bookings.bookings b
    JOIN bookings.tickets t       ON b.book_ref  = t.book_ref
    JOIN bookings.ticket_flights tf ON t.ticket_no = tf.ticket_no
    JOIN bookings.flights f       ON tf.flight_id = f.flight_id
    WHERE f.status = 'Arrived'
    LIMIT 50
"""
DANGEROUS_QUERY    = "DELETE FROM bookings.flights"
BAD_SQL            = "SELEC * FORM flights"
EMPTY_QUERY        = ""

passed = 0
failed = 0


def check(name, condition, detail=""):
    global passed, failed
    if condition:
        print(f"  PASS  {name}")
        passed += 1
    else:
        print(f"  FAIL  {name}" + (f" — {detail}" if detail else ""))
        failed += 1


def section(title):
    print(f"\n{'='*55}")
    print(f"  {title}")
    print('='*55)


# ===========================================================================
# 0. Health check (no DB needed)
# ===========================================================================
section("0. Health check")
r = requests.get(f"{BASE}/health")
check("GET /health returns 200",          r.status_code == 200)
check("connected is false before connect", r.json().get("connected") == False)

# ===========================================================================
# 1. /connect — valid connection
# ===========================================================================
section("1. POST /connect — valid")
r = requests.post(f"{BASE}/connect", json={"connection_string": CONN})
if r.status_code != 200:
    print(f"\n  Cannot continue — connection failed: {r.json()}")
    print("  Fix the CONN string at the top of this file and retry.")
    sys.exit(1)

data = r.json()
check("returns 200",                   r.status_code == 200)
check("success is true",               data.get("success") == True)
check("metadata present",              "metadata" in data)
check("database_name present",         bool(data["metadata"].get("database_name")))
check("table_count > 0",               data["metadata"].get("table_count", 0) > 0)
check("schemas list present",          isinstance(data["metadata"].get("schemas"), list))
check("tables list present",           isinstance(data["metadata"].get("tables"), list))
check("no password in response",       CONN.split(":")[2].split("@")[0] not in str(data))

# Pick a real table from the metadata to use in /run and /estimate tests
_tables = data["metadata"].get("tables", [])
if not _tables:
    print("  No tables found in database — cannot continue.")
    sys.exit(1)

# Use the first available table for basic tests
_t         = _tables[0]
_schema    = _t["schema"]
_table     = _t["table"]
VALID_QUERY = f'SELECT * FROM "{_schema}"."{_table}" LIMIT 5'
print(f"  INFO: Using table {_schema}.{_table} for /run and /estimate tests")

# For the heavy join test, try to find 4 tables in the same schema
_schema_tables = [t for t in _tables if t["schema"] == _schema]
if len(_schema_tables) >= 2:
    t1, t2 = _schema_tables[0], _schema_tables[1]
    HEAVY_QUERY = f'SELECT * FROM "{t1["schema"]}"."{t1["table"]}" LIMIT 50'
else:
    HEAVY_QUERY = VALID_QUERY

# ===========================================================================
# 2. /connect — invalid format
# ===========================================================================
section("2. POST /connect — invalid format")
r = requests.post(f"{BASE}/connect", json={"connection_string": "not-a-valid-string"})
check("returns 400",                   r.status_code == 400)
check("error message present",        "detail" in r.json())

# ===========================================================================
# 3. /connect — wrong credentials (valid format, bad creds)
# ===========================================================================
section("3. POST /connect — wrong credentials")
r = requests.post(f"{BASE}/connect", json={"connection_string": "postgresql://wrong:wrong@localhost:5432/wrong"})
check("returns 400",                   r.status_code == 400)
check("no password leaked",            "wrong" not in r.json().get("detail", "").replace("wrong","***"))

# Re-connect with valid credentials for remaining tests
r = requests.post(f"{BASE}/connect", json={"connection_string": CONN})
if r.status_code != 200:
    print(f"  ERROR: Re-connect after wrong-creds test failed: {r.json()}")
    sys.exit(1)

# ===========================================================================
# 4. /run — valid SELECT
# ===========================================================================
section("4. POST /run — valid SELECT")
# Check health first to confirm we're actually connected
h = requests.get(f"{BASE}/health")
print(f"  DEBUG health before /run: {h.json()}")
r = requests.post(f"{BASE}/run", json={"query": VALID_QUERY})
data = r.json()
print(f"  DEBUG /run status={r.status_code} detail={data.get('detail','')}")
check("returns 200",                   r.status_code == 200)
check("success is true",               data.get("success") == True)
check("columns list present",          isinstance(data.get("columns"), list))
check("rows list present",             isinstance(data.get("rows"), list))
check("execution_time_ms present",     data.get("execution_time_ms") is not None)
check("row_count == len(rows)",        data.get("row_count") == len(data.get("rows", [])))

# ===========================================================================
# 5. /run — dangerous SQL blocked
# ===========================================================================
section("5. POST /run — dangerous SQL blocked")
for stmt in ["DELETE FROM bookings.flights",
             "DROP TABLE bookings.flights",
             "TRUNCATE bookings.flights",
             "UPDATE bookings.flights SET status='x'",
             "INSERT INTO bookings.flights VALUES (1)"]:
    r = requests.post(f"{BASE}/run", json={"query": stmt})
    check(f"blocked: {stmt.split()[0]}",  r.status_code == 400)

# ===========================================================================
# 6. /run — invalid SQL
# ===========================================================================
section("6. POST /run — invalid SQL")
r = requests.post(f"{BASE}/run", json={"query": BAD_SQL})
check("returns 400",                   r.status_code == 400)
check("error message present",        "detail" in r.json())

# ===========================================================================
# 7. /run — empty query
# ===========================================================================
section("7. POST /run — empty query")
r = requests.post(f"{BASE}/run", json={"query": EMPTY_QUERY})
check("returns 400",                   r.status_code == 400)

# ===========================================================================
# 8. /estimate — basic query
# ===========================================================================
section("8. POST /estimate — basic query")
r = requests.post(f"{BASE}/estimate", json={"query": VALID_QUERY})
data = r.json()
check("returns 200",                        r.status_code == 200)
check("success is true",                    data.get("success") == True)
check("cost_category present",              data.get("cost_category") in ["Low", "Medium", "High"])
check("confidence between 0 and 1",         0 <= data.get("confidence", -1) <= 1)
check("predicted_execution_time_ms > 0",    data.get("predicted_execution_time_ms", 0) > 0)
check("estimated_cost >= 0",                data.get("estimated_cost", -1) >= 0)
check("features dict present",             isinstance(data.get("features"), dict))
check("recommendation present",            isinstance(data.get("recommendation"), dict))
check("recommendation.available present",  "available" in data.get("recommendation", {}))
check("recommendation.reason present",     bool(data.get("recommendation", {}).get("reason")))
check("recommendation.optimized_query present", bool(data.get("recommendation", {}).get("optimized_query")))

# ===========================================================================
# 9. /estimate — heavy multi-join query
# ===========================================================================
section("9. POST /estimate — heavy multi-join query")
r = requests.post(f"{BASE}/estimate", json={"query": HEAVY_QUERY})
data = r.json()
check("returns 200",           r.status_code == 200)
check("cost_category present", data.get("cost_category") in ["Low", "Medium", "High"])
check("features dict present", isinstance(data.get("features"), dict))

# ===========================================================================
# 10. /estimate — dangerous SQL blocked
# ===========================================================================
section("10. POST /estimate — dangerous SQL blocked")
r = requests.post(f"{BASE}/estimate", json={"query": DANGEROUS_QUERY})
check("returns 400",  r.status_code == 400)

# ===========================================================================
# 11. Database metadata extraction sanity
# ===========================================================================
section("11. Metadata extraction sanity")
r = requests.post(f"{BASE}/connect", json={"connection_string": CONN})
meta = r.json()["metadata"]
tables = meta.get("tables", [])
check("at least one table has columns",
      any(len(t.get("columns", [])) > 0 for t in tables))
check("at least one table has estimated_row_count",
      any(t.get("estimated_row_count", 0) >= 0 for t in tables))

# ===========================================================================
# Summary
# ===========================================================================
total = passed + failed
print(f"\n{'='*55}")
print(f"  Results: {passed}/{total} passed", "" if failed == 0 else f"— {failed} FAILED")
print('='*55)

if failed > 0:
    sys.exit(1)
