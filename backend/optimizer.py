"""
optimizer.py
------------
Query optimization and recommendation module.

CURRENT STATE: Dummy implementation.
Returns a placeholder recommendation so the /estimate pipeline
works end-to-end while the real optimizer is being developed.

FUTURE: Replace get_optimization_recommendation() body with:
  1. Query analysis
  2. Candidate SQL generation
  3. Equivalence verification via EXPLAIN cost comparison
  4. Return the best verified candidate

IMPORTANT: This module must NEVER claim a rewritten query is
equivalent without verification. The dummy below is clearly marked.
"""


def get_optimization_recommendation(query: str, features: dict) -> dict:
    """
    Return an optimization recommendation for the given query.

    Parameters
    ----------
    query    : str  — the original SQL query
    features : dict — combined feature dict from features.extract_all_features()

    Returns
    -------
    dict with keys:
        available       : bool — whether a recommendation is available
        reason          : str  — human-readable explanation
        optimized_query : str  — suggested rewrite (or original if none)
    """
    # -- DUMMY implementation ----------------------------------------------
    # Generates a simple rule-based hint based on feature values.
    # Does NOT produce a verified equivalent query.
    # Replace this entire block with the real optimizer later.

    reason = _dummy_reason(features)

    return {
        "available": True,          # DUMMY — always claims available
        "reason": reason,
        "optimized_query": query,   # DUMMY — returns original query unchanged
    }


# ---------------------------------------------------------------------------
# Dummy helper — produce a readable hint from features
# ---------------------------------------------------------------------------

def _dummy_reason(features: dict) -> str:
    hints = []

    if features.get("num_seq_scans", 0) > 0:
        hints.append("Sequential scan detected — consider adding an index on the filtered column.")

    if features.get("num_joins", 0) >= 3:
        hints.append("Multiple joins detected — verify that join columns are indexed.")

    if features.get("estimated_cost", 0) >= 1000:
        hints.append("High estimated cost — consider breaking the query into smaller steps or using a CTE.")

    if features.get("has_aggregation") and not features.get("has_group_by"):
        hints.append("Aggregation without GROUP BY — confirm this is intentional.")

    if features.get("num_subqueries", 0) > 0:
        hints.append("Subquery detected — consider rewriting as a JOIN for better performance.")

    if not hints:
        hints.append("No obvious optimization opportunities detected for this query.")

    return " ".join(hints)
