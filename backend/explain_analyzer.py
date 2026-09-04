from database import get_connection


def get_query_cost(sql, conn=None):

    if conn is None:
        conn = get_connection()

    if conn is None:
        raise RuntimeError("Database is not connected.")

    cursor = conn.cursor()

    try:

        explain_sql = f"""
        EXPLAIN (FORMAT JSON)
        {sql}
        """

        cursor.execute(explain_sql)

        result = cursor.fetchone()[0]

        plan = result[0]["Plan"]

        return {
            "startup_cost": plan.get("Startup Cost"),
            "total_cost": plan.get("Total Cost"),
            "estimated_rows": plan.get("Plan Rows"),
            "plan_width": plan.get("Plan Width"),
            "node_type": plan.get("Node Type"),
        }

    finally:

        cursor.close()