from google import genai

from config import GEMINI_API_KEY, GEMINI_MODEL
from schema_reader import get_database_schema


# ============================================================
# GEMINI CLIENT
# ============================================================

client = genai.Client(
    api_key=GEMINI_API_KEY
)


# ============================================================
# GENERATE OPTIMIZATION CANDIDATES
# ============================================================

def generate_candidates(
    original_sql,
    conn,
    original_plan,
    number_of_candidates=5
):

    schema = get_database_schema(conn)

    prompt = f"""
You are an expert PostgreSQL query optimizer.

Your task is to generate alternative SQL queries that are
semantically equivalent to the original query while attempting
to reduce PostgreSQL EXPLAIN estimated execution cost.

============================================================
DATABASE SCHEMA
============================================================

{schema}

============================================================
ORIGINAL SQL QUERY
============================================================

{original_sql}

============================================================
ORIGINAL POSTGRESQL QUERY PLAN INFORMATION
============================================================

{original_plan}

============================================================
OPTIMIZATION OBJECTIVE
============================================================

The original query has already been analyzed by PostgreSQL.

Use the available query-plan information together with the
SQL structure and database schema to identify likely expensive
operations.

Generate alternative formulations that have a realistic chance
of producing a lower PostgreSQL EXPLAIN estimated cost.

Do NOT perform cosmetic rewrites simply to make the SQL look
different.

Prioritize transformations that can actually affect the
execution plan.

============================================================
POSSIBLE OPTIMIZATION STRATEGIES
============================================================

Consider the following when appropriate:

1. Reorganizing JOIN structure.

2. Converting implicit comma joins into explicit JOIN syntax.

3. Removing genuinely redundant join predicates.

4. Rewriting suitable IN / EXISTS conditions.

5. Rewriting suitable EXISTS / IN conditions.

6. Pushing selective predicates earlier when semantically safe.

7. Reducing unnecessary intermediate rows.

8. Simplifying boolean predicates without changing semantics.

9. Eliminating genuinely redundant operations.

10. Restructuring subqueries when this can reduce work.

11. Taking advantage of existing indexes visible in the schema.

12. Reducing unnecessary scans or joins.

13. Restructuring aggregation when it can reduce the number
    of rows reaching the aggregation stage.

14. Using a different but equivalent relational formulation
    when it is likely to produce a cheaper execution plan.

Only use a transformation when it is semantically safe.

============================================================
IMPORTANT OPTIMIZATION PRINCIPLE
============================================================

Do NOT assume that a rewrite is an optimization merely because
it is cleaner, shorter, or uses explicit JOIN syntax.

The actual PostgreSQL EXPLAIN estimated cost is the authority.

Every candidate generated here will be independently:

1. SQL validated
2. EXPLAIN analyzed
3. compared against the original cost
4. checked for result equivalence

The final optimizer will only accept a candidate if it is both
semantically equivalent and lower cost.

============================================================
SEMANTIC REQUIREMENTS
============================================================

Every candidate MUST:

- return exactly the same result
- preserve duplicate behavior
- preserve NULL behavior
- preserve filtering semantics
- preserve JOIN cardinality
- preserve aggregation semantics
- preserve selected columns
- preserve aliases where required
- use only existing tables
- use only existing columns
- use valid PostgreSQL syntax

Never change the requested result simply to reduce cost.

============================================================
SAFETY REQUIREMENTS
============================================================

Only SELECT or WITH queries are allowed.

Never generate:

INSERT
UPDATE
DELETE
DROP
ALTER
CREATE
TRUNCATE

Do not modify database data or schema.

============================================================
CANDIDATE DIVERSITY
============================================================

Generate exactly {number_of_candidates} candidates.

The candidates should explore DIFFERENT optimization ideas.

Do NOT generate five nearly identical queries with only
formatting or whitespace differences.

For example, if appropriate, candidates could explore:

- JOIN restructuring
- predicate restructuring
- EXISTS transformation
- subquery restructuring
- redundant-condition elimination

Use only strategies that are actually applicable to the query.

============================================================
EXPLANATION REQUIREMENT
============================================================

For every candidate, provide a SHORT explanation describing
the intended optimization.

The explanation must answer:

"What was changed and why might this reduce PostgreSQL cost?"

Keep the explanation to 1-2 concise sentences.

Do not claim that the candidate is actually faster.

The candidate will only be considered successful after PostgreSQL
EXPLAIN and equivalence verification.

============================================================
OUTPUT FORMAT
============================================================

Return ONLY this exact structure:

---CANDIDATE---

---QUERY---
<complete PostgreSQL SQL query>

---REASON---
<1-2 sentence explanation of the intended optimization>

---CANDIDATE---

---QUERY---
<complete PostgreSQL SQL query>

---REASON---
<1-2 sentence explanation of the intended optimization>

Continue until exactly {number_of_candidates} candidates
have been generated.

Do not include any additional commentary.
"""

    print(
        f"[llm_rewriter] Requesting "
        f"{number_of_candidates} candidates from Gemini..."
    )

    response = client.models.generate_content(
        model=GEMINI_MODEL,
        contents=prompt
    )

    text = response.text.strip()

    print(
        "[llm_rewriter] Gemini response received."
    )

    return parse_candidates(
        text,
        number_of_candidates
    )


# ============================================================
# PARSE GEMINI RESPONSE
# ============================================================

def parse_candidates(
    text,
    number_of_candidates
):

    candidates = []

    blocks = text.split(
        "---CANDIDATE---"
    )

    for block in blocks:

        block = block.strip()

        if not block:
            continue

        # ----------------------------------------------------
        # Extract QUERY
        # ----------------------------------------------------

        if "---QUERY---" not in block:
            continue

        query_part = block.split(
            "---QUERY---",
            1
        )[1]

        if "---REASON---" in query_part:

            query_text, reason = query_part.split(
                "---REASON---",
                1
            )

        else:

            query_text = query_part
            reason = (
                "Gemini did not provide a specific "
                "optimization explanation."
            )

        query = query_text.strip()
        reason = reason.strip()

        # ----------------------------------------------------
        # Remove markdown code fences
        # ----------------------------------------------------

        query = query.replace(
            "```sql",
            ""
        ).replace(
            "```SQL",
            ""
        ).replace(
            "```",
            ""
        ).strip()

        # ----------------------------------------------------
        # Basic validation
        # ----------------------------------------------------

        if not query:
            continue

        if not (
            query.upper().startswith("SELECT")
            or
            query.upper().startswith("WITH")
        ):
            continue

        candidates.append({
            "sql": query,
            "reason": reason
        })

    print(
        f"[llm_rewriter] Parsed "
        f"{len(candidates)} valid candidates."
    )

    return candidates[:number_of_candidates]