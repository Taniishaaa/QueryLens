"""
test_phase3.py
--------------
Quick sanity checks for features.py.
Run from the backend/ directory:  python test_phase3.py
"""

import requests
import json

BASE = "http://localhost:8000"
CONN = "postgresql://neondb_owner:npg_8QexLJbkcqp5@ep-falling-flower-a1nsa3qv-pooler.ap-southeast-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require"

# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def section(title):
    print(f"\n{'='*50}")
    print(f"  {title}")
    print('='*50)

# ---------------------------------------------------------------------------
# Connect first
# ---------------------------------------------------------------------------

section("0. Connect")
r = requests.post(f"{BASE}/connect", json={"connection_string": CONN})
if r.status_code != 200:
    print("Connection failed:", r.json())
    exit(1)
print("Connected:", r.json()["success"])

# ---------------------------------------------------------------------------
# Test /estimate (Phase 4 endpoint — not added yet).
# For now we test features.py directly via a small inline import.
# ---------------------------------------------------------------------------

section("1. SQL Feature Extraction (direct import)")

import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from features import extract_sql_features, extract_all_features
import database

# Connect database session directly for EXPLAIN test
database.connect(CONN)
conn = database.get_connection()

# Simple query
q1 = "SELECT * FROM bookings.flights LIMIT 10"
feats = extract_sql_features(q1)
print("Simple SELECT *:")
print(json.dumps(feats, indent=2))

# Aggregation + GROUP BY
q2 = """
SELECT route_no, COUNT(*) as cnt, AVG(actual_departure - scheduled_departure) as avg_delay
FROM bookings.flights
WHERE status = 'Arrived'
GROUP BY route_no
ORDER BY cnt DESC
"""
feats2 = extract_sql_features(q2)
print("\nAggregation + GROUP BY + ORDER BY:")
print(json.dumps(feats2, indent=2))
assert feats2["has_group_by"] == 1
assert feats2["has_order_by"] == 1
assert feats2["has_aggregation"] == 1
print("  -> Assertions passed")

# JOIN query
q3 = """
SELECT f.flight_id, r.departure_airport, r.arrival_airport
FROM bookings.flights f
JOIN bookings.routes r ON f.route_no = r.route_no
WHERE f.status = 'Scheduled'
"""
feats3 = extract_sql_features(q3)
print("\nJOIN query:")
print(json.dumps(feats3, indent=2))
assert feats3["num_joins"] >= 1
print("  -> Assertions passed")

# ---------------------------------------------------------------------------
section("2. EXPLAIN Feature Extraction")

all_feats = extract_all_features(q3, conn)
print("Combined features for JOIN query:")
print(json.dumps(all_feats, indent=2))
assert all_feats["estimated_cost"] > 0, "Expected non-zero estimated cost from EXPLAIN"
print("  -> estimated_cost > 0: passed")

# ---------------------------------------------------------------------------
section("3. EXPLAIN on a heavier query")

q4 = """
SELECT b.book_ref, t.passenger_name, f.flight_id, f.status
FROM bookings.bookings b
JOIN bookings.tickets t ON b.book_ref = t.book_ref
JOIN bookings.ticket_flights tf ON t.ticket_no = tf.ticket_no
JOIN bookings.flights f ON tf.flight_id = f.flight_id
WHERE f.status = 'Arrived'
ORDER BY b.book_ref
LIMIT 100
"""
all_feats4 = extract_all_features(q4, conn)
print("Multi-join query features:")
print(json.dumps(all_feats4, indent=2))

print("\nAll Phase 3 tests passed.")
