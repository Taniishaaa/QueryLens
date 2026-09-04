from llm_rewriter import generate_candidates
from sql_validator import validate_sql
from equivalence_checker import equivalent_queries
from explain_analyzer import get_query_cost


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

    # =========================================================
    # STEP 1: Original EXPLAIN
    # =========================================================

    print("\n[1] Analyzing original query...")

    original_plan = get_query_cost(
        original_sql,
        conn
    )

    original_cost = \
        original_plan["total_cost"]

    print(
        f"Original estimated cost: "
        f"{original_cost}"
    )

    print(
        f"Estimated rows: "
        f"{original_plan['estimated_rows']}"
    )

    # =========================================================
    # STEP 2: Gemini candidates
    # =========================================================

    print(
        "\n[2] Generating candidate "
        "queries using Gemini..."
    )

    candidates = generate_candidates(
        original_sql,
        conn,
        number_of_candidates=3
    )

    print(
        f"Generated {len(candidates)} candidates."
    )

    valid_candidates = []

    # =========================================================
    # STEP 3: Validate + EXPLAIN + Equivalence
    # =========================================================

    for i, candidate in enumerate(
        candidates,
        start=1
    ):

        print("\n" + "-" * 70)
        print(f"CANDIDATE {i}")
        print("-" * 70)

        print(candidate)

        # -----------------------------------------------------
        # SQL validation
        # -----------------------------------------------------

        valid, message = \
            validate_sql(candidate)

        print(
            f"\nValidation: {message}"
        )

        if not valid:

            print("Rejected.")

            continue

        # -----------------------------------------------------
        # EXPLAIN candidate
        # -----------------------------------------------------

        try:

            candidate_plan = \
                get_query_cost(
                    candidate,
                    conn
                )

            candidate_cost = \
                candidate_plan["total_cost"]

            print(
                f"Estimated cost: "
                f"{candidate_cost}"
            )

        except Exception as e:

            print(
                f"EXPLAIN failed: {e}"
            )

            continue

        # -----------------------------------------------------
        # Only test equivalence if candidate
        # looks potentially better
        # -----------------------------------------------------

        if candidate_cost >= original_cost:

            print(
                "Candidate is not cheaper."
            )

            continue

        print(
            "Candidate is cheaper. "
            "Checking equivalence..."
        )

        equivalent, message = \
            equivalent_queries(
                original_sql,
                candidate,
                conn
            )

        print(
            f"Equivalence: {message}"
        )

        if not equivalent:

            print("Rejected.")

            continue

        valid_candidates.append({

            "candidate_id":
                i,

            "sql":
                candidate,

            "estimated_cost":
                candidate_cost,

            "estimated_rows":
                candidate_plan[
                    "estimated_rows"
                ]

        })

    # =========================================================
    # STEP 4: Select best candidate
    # =========================================================

    print("\n" + "=" * 70)
    print("OPTIMIZATION RESULT")
    print("=" * 70)

    if not valid_candidates:

        print(
            "\nNo valid lower-cost "
            "candidate found."
        )

        print(
            "\nOriginal query will be retained."
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
                0,

            "status":
                "NO_IMPROVEMENT"

        }

    best = min(
        valid_candidates,
        key=lambda x:
            x["estimated_cost"]
    )

    optimized_cost = \
        best["estimated_cost"]

    improvement = (

        (
            original_cost -
            optimized_cost
        )
        / original_cost

    ) * 100

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

    print("\nOPTIMIZED SQL")
    print("-" * 70)

    print(
        best["sql"]
    )

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
            improvement,

        "status":
            "IMPROVED"

    }