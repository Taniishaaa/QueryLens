def execute_query(sql, conn):

    cursor = conn.cursor()

    try:

        cursor.execute(
            "SET statement_timeout = 60000"
        )

        cursor.execute(
            "SET default_transaction_read_only = on"
        )

        cursor.execute(sql)

        rows = cursor.fetchall()

        columns = [
            desc[0]
            for desc in cursor.description
        ]

        return columns, rows

    finally:

        cursor.close()


def equivalent_queries(
    original_sql,
    candidate_sql,
    conn
):

    try:

        original_columns, original_rows = \
            execute_query(
                original_sql,
                conn
            )

        candidate_columns, candidate_rows = \
            execute_query(
                candidate_sql,
                conn
            )

        if original_columns != candidate_columns:

            return False, "Different output columns"

        original_sorted = sorted(
            [tuple(row) for row in original_rows],
            key=lambda x: str(x)
        )

        candidate_sorted = sorted(
            [tuple(row) for row in candidate_rows],
            key=lambda x: str(x)
        )

        if original_sorted == candidate_sorted:

            return True, "Equivalent"

        return False, "Different result sets"

    except Exception as e:

        return False, f"Execution error: {str(e)}"