"""
features.py
-----------
Reusable feature extraction functions for the ML pipeline.

Two types of features:
1. SQL features  — extracted by parsing the raw SQL string (no DB needed).
2. EXPLAIN features — extracted by running EXPLAIN (FORMAT JSON) on the DB.

The combined feature dict is what gets passed to ml_models.py.
These feature names must stay in sync with what the final trained model expects.
"""

import re
import json
import psycopg2
import psycopg2.extras
from typing import Optional


# ---------------------------------------------------------------------------
# 1. SQL FEATURES
# Extracted purely from the query text — no database connection required.
# ---------------------------------------------------------------------------

def extract_sql_features(query: str) -> dict:
    """
    Parse the SQL string and return a dict of structural features.

    All checks are case-insensitive and use word-boundary regex to avoid
    false matches inside column names or string literals.
    """
    q = query.upper()

    # Number of unique table references (FROM / JOIN clauses)
    # Counts occurrences of FROM and JOIN keywords as a proxy.
    num_tables = len(re.findall(r"\bFROM\b", q)) + len(re.findall(r"\bJOIN\b", q))

    # Number of JOIN keywords
    num_joins = len(re.findall(r"\bJOIN\b", q))

    # Number of filter conditions (WHERE / HAVING / ON clauses)
    num_filters = (
        len(re.findall(r"\bWHERE\b", q))
        + len(re.findall(r"\bHAVING\b", q))
        + len(re.findall(r"\bON\b", q))
    )

    has_group_by = 1 if re.search(r"\bGROUP\s+BY\b", q) else 0
    has_order_by = 1 if re.search(r"\bORDER\s+BY\b", q) else 0

    # Aggregation functions
    agg_functions = ["COUNT", "SUM", "AVG", "MIN", "MAX", "STDDEV", "VARIANCE"]
    num_aggregations = sum(
        len(re.findall(rf"\b{fn}\s*\(", q)) for fn in agg_functions
    )
    has_aggregation = 1 if num_aggregations > 0 else 0

    # Number of selected columns — count commas in SELECT clause + 1,
    # but treat SELECT * as 1.
    num_selected_columns = _count_selected_columns(q)

    # Subqueries — count nested SELECT keywords beyond the first
    all_selects = len(re.findall(r"\bSELECT\b", q))
    num_subqueries = max(0, all_selects - 1)

    # Query depth — rough measure via nesting of parentheses
    query_depth = _max_paren_depth(query)

    return {
        "num_tables": num_tables,
        "num_joins": num_joins,
        "num_filters": num_filters,
        "has_group_by": has_group_by,
        "has_order_by": has_order_by,
        "has_aggregation": has_aggregation,
        "num_aggregations": num_aggregations,
        "num_selected_columns": num_selected_columns,
        "num_subqueries": num_subqueries,
        "query_depth": query_depth,
    }


# ---------------------------------------------------------------------------
# 2. EXPLAIN FEATURES
# Extracted by running EXPLAIN (FORMAT JSON) — no ANALYZE, no execution.
# ---------------------------------------------------------------------------

def extract_explain_features(query: str, conn) -> dict:
    """
    Run EXPLAIN (FORMAT JSON) and extract plan-level features.

    Does NOT execute the query (no ANALYZE), so it is safe to call
    before the user explicitly runs the query.

    Returns a dict of plan features, or a dict with defaults + an error key
    if EXPLAIN fails for any reason.
    """
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(f"EXPLAIN (FORMAT JSON) {query}")
            plan_json = cur.fetchone()
            # psycopg2 returns the JSON column already parsed as a Python object.
            plan = plan_json[list(plan_json.keys())[0]]
            if isinstance(plan, str):
                plan = json.loads(plan)

        root = plan[0]["Plan"]
        features = _walk_plan(root)
        return features

    except Exception as e:
        # If EXPLAIN fails (e.g. invalid query), return safe defaults.
        return _default_explain_features(error=str(e))


def _walk_plan(node: dict, depth: int = 0) -> dict:
    """
    Recursively walk the EXPLAIN JSON plan tree and accumulate features.
    Called once on the root node; merges child results.
    """
    features = {
        "estimated_cost": node.get("Total Cost", 0.0),
        "estimated_rows": node.get("Plan Rows", 0),
        "plan_depth": depth,
        "num_seq_scans": 0,
        "num_index_scans": 0,
        "num_nested_loops": 0,
        "num_hash_joins": 0,
        "num_merge_joins": 0,
    }

    node_type = node.get("Node Type", "")
    if node_type == "Seq Scan":
        features["num_seq_scans"] = 1
    elif "Index" in node_type:
        features["num_index_scans"] = 1
    elif node_type == "Nested Loop":
        features["num_nested_loops"] = 1
    elif node_type == "Hash Join":
        features["num_hash_joins"] = 1
    elif node_type == "Merge Join":
        features["num_merge_joins"] = 1

    # Recurse into child plans
    for child in node.get("Plans", []):
        child_features = _walk_plan(child, depth + 1)
        # Keep the root's cost/rows but accumulate counts and max depth.
        features["plan_depth"] = max(features["plan_depth"], child_features["plan_depth"])
        features["num_seq_scans"]    += child_features["num_seq_scans"]
        features["num_index_scans"]  += child_features["num_index_scans"]
        features["num_nested_loops"] += child_features["num_nested_loops"]
        features["num_hash_joins"]   += child_features["num_hash_joins"]
        features["num_merge_joins"]  += child_features["num_merge_joins"]

    return features


def _default_explain_features(error: Optional[str] = None) -> dict:
    """Return zero-valued EXPLAIN features when EXPLAIN cannot be run."""
    result = {
        "estimated_cost": 0.0,
        "estimated_rows": 0,
        "plan_depth": 0,
        "num_seq_scans": 0,
        "num_index_scans": 0,
        "num_nested_loops": 0,
        "num_hash_joins": 0,
        "num_merge_joins": 0,
    }
    if error:
        result["explain_error"] = error
    return result


# ---------------------------------------------------------------------------
# 3. COMBINED FEATURES
# Single entry point used by /estimate.
# ---------------------------------------------------------------------------

def extract_all_features(query: str, conn=None) -> dict:
    """
    Return the full feature dict used by the ML pipeline.

    sql_features    — always extracted (no DB needed).
    explain_features — extracted if a connection is available.

    The combined dict is what gets passed to predict_cost_category()
    and predict_execution_time() in ml_models.py.
    """
    sql_feats = extract_sql_features(query)

    if conn is not None:
        explain_feats = extract_explain_features(query, conn)
    else:
        explain_feats = _default_explain_features(error="No connection available")

    return {**sql_feats, **explain_feats}


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _count_selected_columns(upper_query: str) -> int:
    """
    Estimate number of selected columns from the SELECT clause.
    Returns 1 for SELECT *, otherwise counts commas + 1.
    Handles cases where there is no SELECT (shouldn't happen for valid queries).
    """
    match = re.search(r"\bSELECT\b(.+?)\bFROM\b", upper_query, re.DOTALL)
    if not match:
        return 1
    select_clause = match.group(1).strip()
    if select_clause == "*":
        return 1
    # Count top-level commas (not inside parentheses)
    depth = 0
    commas = 0
    for ch in select_clause:
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
        elif ch == "," and depth == 0:
            commas += 1
    return commas + 1


def _max_paren_depth(query: str) -> int:
    """Return the maximum parenthesis nesting depth in the query."""
    depth = 0
    max_depth = 0
    for ch in query:
        if ch == "(":
            depth += 1
            max_depth = max(max_depth, depth)
        elif ch == ")":
            depth -= 1
    return max_depth
