from google import genai
from config import GEMINI_API_KEY, GEMINI_MODEL
from schema_reader import get_database_schema


client = genai.Client(
    api_key=GEMINI_API_KEY
)


def generate_candidates(
    original_sql,
    conn,
    number_of_candidates=3
):

    schema = get_database_schema(conn)

    prompt = f"""
You are an expert PostgreSQL query optimizer.

Your task is to generate alternative SQL queries that are
semantically equivalent to the original query.

DATABASE SCHEMA
===============
{schema}

ORIGINAL SQL
============
{original_sql}

Generate exactly {number_of_candidates} alternative
PostgreSQL SQL queries.

OBJECTIVE
=========
Find alternative formulations that may have a lower
PostgreSQL EXPLAIN estimated cost.

POSSIBLE SAFE TRANSFORMATIONS
=============================
- JOIN restructuring
- converting implicit joins to explicit JOIN syntax
- predicate restructuring
- EXISTS / IN transformations where semantically safe
- subquery restructuring
- filtering earlier where safe
- removing genuinely redundant operations
- other semantics-preserving SQL transformations

STRICT RULES
============
1. PostgreSQL syntax only.
2. Preserve exactly the same result.
3. Do not change selected columns.
4. Do not change filtering semantics.
5. Do not invent tables.
6. Do not invent columns.
7. Use only tables and columns present in the schema.
8. Do not modify the database.
9. Only SELECT or WITH queries.
10. Never use INSERT, UPDATE, DELETE, DROP, ALTER,
    CREATE or TRUNCATE.
11. Do not optimize by changing the requested result.
12. Generate genuinely different alternatives when possible.

OUTPUT FORMAT
=============

Return ONLY:

---QUERY---
<complete SQL query>

---QUERY---
<complete SQL query>

---QUERY---
<complete SQL query>

Do not provide explanations.
"""

    response = client.interactions.create(
        model=GEMINI_MODEL,
        input=prompt
    )

    text = response.output_text.strip()

    return parse_candidates(
        text,
        number_of_candidates
    )


def parse_candidates(
    text,
    number_of_candidates
):

    candidates = []

    parts = text.split(
        "---QUERY---"
    )

    for part in parts:

        query = part.strip()

        if not query:
            continue

        query = query.replace(
            "```sql",
            ""
        ).replace(
            "```",
            ""
        ).strip()

        if query:
            candidates.append(query)

    return candidates[:number_of_candidates]