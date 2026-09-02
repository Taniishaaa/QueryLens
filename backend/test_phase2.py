# test_phase2.py
import requests

BASE = "http://localhost:8000"
CONN = "postgresql://postgres:admin@localhost:5432/demo"
  # <-- UPDATE THIS

# Step 1: Connect
r = requests.post(f"{BASE}/connect", json={"connection_string": CONN})
print("Connect status:", r.status_code)
print("Connect response:", r.json())
if r.status_code != 200:
    print("Connection failed — fix CONN string above and retry.")
    exit(1)
print("Connect success:", r.json()["success"])

# Step 2: Valid SELECT
r = requests.post(f"{BASE}/run", json={"query": "SELECT * FROM bookings.flights LIMIT 3"})
print("Valid query:", r.status_code)
data = r.json()
print("  Columns:", data.get("columns"))
print("  Row count:", data.get("row_count"))
print("  Time (ms):", data.get("execution_time_ms"))

# Step 3: Dangerous query — should be blocked
r = requests.post(f"{BASE}/run", json={"query": "DELETE FROM bookings.flights"})
print("Dangerous query blocked:", r.status_code == 400, r.json().get("detail"))

# Step 4: Bad SQL — should return syntax error
r = requests.post(f"{BASE}/run", json={"query": "SELEC * FORM flights"})
print("Bad SQL caught:", r.status_code == 400, r.json().get("detail"))

# Step 5: Empty query
r = requests.post(f"{BASE}/run", json={"query": ""})
print("Empty query blocked:", r.status_code == 400)
