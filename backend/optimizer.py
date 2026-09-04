from llm_rewriter import generate_candidates
from sql_validator import validate_sql
from equivalence_checker import equivalent_queries
from explain_analyzer import get_query_cost


# ============================================================
# SQL QUERY OPTIMIZER
# ============================================================

def optimize_query(
    original_sql,
    conn
):

    print("\n" + "=" * 70)
    print("SQL QUERY COST OPTIMIZER")
    print("=" * 70)

    print("\nORIGINAL QUERY")
    print("-" * 70)
    print(original_sql)

    # ========================================================
    # STEP 1: ANALYZE ORIGINAL QUERY
    # ========================================================

    print(
        "\n[1] Analyzing original query..."
    )

    original_plan = get_query_cost(
        original_sql,
        conn
    )

    original_cost = original_plan[
        "total_cost"
    ]

    print(
        f"Original estimated cost: "
        f"{original_cost}"
    )

    print(
        f"Estimated rows: "
        f"{original_plan['estimated_rows']}"
    )

    print(
        f"Plan node: "
        f"{original_plan.get('node_type')}"
    )

    # ========================================================
    # STEP 2: GENERATE CANDIDATES
    # ========================================================

    print(
        "\n[2] Generating candidate "
        "queries using Gemini..."
    )

    candidates = generate_candidates(
        original_sql,
        conn,
        original_plan,
        number_of_candidates=5
    )

    print(
        f"Generated {len(candidates)} candidates."
    )

    valid_candidates = []

    # ========================================================
    # STEP 3: VALIDATE + EXPLAIN + EQUIVALENCE
    # ========================================================

    for i, candidate in enumerate(
        candidates,
        start=1
    ):

        candidate_sql = candidate["sql"]
        candidate_reason = candidate["reason"]

        print("\n" + "-" * 70)
        print(f"CANDIDATE {i}")
        print("-" * 70)

        print(candidate_sql)

        print(
            "\nIntended optimization:"
        )

        print(
            candidate_reason
        )

        # ----------------------------------------------------
        # SQL VALIDATION
        # ----------------------------------------------------

        valid, message = validate_sql(
            candidate_sql
        )

        print(
            f"\nValidation: {message}"
        )

        if not valid:

            print(
                "Candidate rejected."
            )

            continue

        # ----------------------------------------------------
        # EXPLAIN CANDIDATE
        # ----------------------------------------------------

        try:

            candidate_plan = get_query_cost(
                candidate_sql,
                conn
            )

            candidate_cost = candidate_plan[
                "total_cost"
            ]

            print(
                f"Estimated cost: "
                f"{candidate_cost}"
            )

        except Exception as e:

            print(
                f"EXPLAIN failed: {e}"
            )

            continue

        # ----------------------------------------------------
        # COST COMPARISON
        # ----------------------------------------------------

        if candidate_cost >= original_cost:

            print(
                "Candidate is not cheaper."
            )

            continue

        print(
            "Candidate is cheaper."
        )

        # ----------------------------------------------------
        # EQUIVALENCE CHECK
        # ----------------------------------------------------

        print(
            "Checking result equivalence..."
        )

        equivalent, equivalence_message = \
            equivalent_queries(
                original_sql,
                candidate_sql,
                conn
            )

        print(
            f"Equivalence: "
            f"{equivalence_message}"
        )

        if not equivalent:

            print(
                "Candidate rejected because "
                "results are not equivalent."
            )

            continue

        # ----------------------------------------------------
        # ACCEPT CANDIDATE
        # ----------------------------------------------------

        print(
            "Candidate accepted."
        )

        valid_candidates.append({

            "candidate_id":
                i,

            "sql":
                candidate_sql,

            "reason":
                candidate_reason,

            "estimated_cost":
                candidate_cost,

            "estimated_rows":
                candidate_plan[
                    "estimated_rows"
                ]

        })

    # ========================================================
    # STEP 4: SELECT BEST CANDIDATE
    # ========================================================

    print("\n" + "=" * 70)
    print("OPTIMIZATION RESULT")
    print("=" * 70)

    # --------------------------------------------------------
    # No improvement
    # --------------------------------------------------------

    if not valid_candidates:

        print(
            "\nNo valid lower-cost "
            "candidate found."
        )

        print(
            "Original query will be retained."
        )

        return {

            "original_sql":
                original_sql,

            "optimized_sql":
                original_sql,

            "original_cost":
                original_cost,

            "optimized_cost":
                original_cost,

            "improvement_percent":
                0.0,

            "status":
                "NO_IMPROVEMENT",

            "optimization_explanation":
                (
                    "No generated candidate produced a "
                    "lower PostgreSQL estimated cost while "
                    "also passing SQL validation and "
                    "result-equivalence verification."
                )

        }

    # --------------------------------------------------------
    # Find lowest-cost candidate
    # --------------------------------------------------------

    best = min(
        valid_candidates,
        key=lambda x:
            x["estimated_cost"]
    )

    optimized_cost = best[
        "estimated_cost"
    ]

    improvement = (

        (
            original_cost -
            optimized_cost
        )
        / original_cost

    ) * 100

    # --------------------------------------------------------
    # Build explanation
    # --------------------------------------------------------

    optimization_explanation = (
        f"{best['reason']} "
        f"PostgreSQL estimated the rewritten query at "
        f"{optimized_cost:.2f} cost units compared with "
        f"{original_cost:.2f} for the original query, "
        f"and the result was verified as equivalent."
    )

    # --------------------------------------------------------
    # Print result
    # --------------------------------------------------------

    print(
        f"\nOriginal cost: "
        f"{original_cost}"
    )

    print(
        f"Optimized cost: "
        f"{optimized_cost}"
    )

    print(
        f"Cost reduction: "
        f"{improvement:.2f}%"
    )

    print(
        "\nOptimization explanation:"
    )

    print(
        optimization_explanation
    )

    print(
        "\nOPTIMIZED SQL"
    )

    print(
        "-" * 70
    )

    print(
        best["sql"]
    )

    # ========================================================
    # RETURN RESULT
    # ========================================================

    return {

        "original_sql":
            original_sql,

        "optimized_sql":
            best["sql"],

        "original_cost":
            original_cost,

        "optimized_cost":
            optimized_cost,

        "improvement_percent":
            round(
                improvement,
                4
            ),

        "status":
            "IMPROVED",

        "optimization_explanation":
            optimization_explanation,

        "candidate_id":
            best["candidate_id"]

    }