import sqlglot


FORBIDDEN_KEYWORDS = {
    "INSERT",
    "UPDATE",
    "DELETE",
    "DROP",
    "ALTER",
    "CREATE",
    "TRUNCATE",
    "GRANT",
    "REVOKE",
}


def validate_sql(sql):

    if not sql or not sql.strip():
        return False, "Empty SQL query"

    sql = sql.strip()

    upper_sql = sql.upper()

    for keyword in FORBIDDEN_KEYWORDS:

        if keyword in upper_sql:

            return False, f"Forbidden keyword: {keyword}"

    try:

        parsed = sqlglot.parse_one(
            sql,
            dialect="postgres"
        )

        if parsed is None:

            return False, "Could not parse SQL"

        if parsed.key.upper() not in {"SELECT", "WITH"}:

            return False, "Only SELECT/WITH queries are allowed"

        return True, "Valid SQL"

    except Exception as e:

        return False, f"SQL parsing error: {e}"