"""
features.py
-----------
Feature extraction for the SQL execution-time regression model.

The final regression model expects exactly 20 features:

1.  num_tables
2.  num_joins
3.  num_filters
4.  has_group_by
5.  has_order_by
6.  has_aggregation
7.  num_aggregations
8.  num_selected_columns
9.  num_subqueries
10. query_depth
11. total_rows
12. total_table_size
13. num_indexes
14. column_cardinality
15. estimated_rows
16. estimated_cost
17. plan_depth
18. num_sequential_scans
19. num_index_scans
20. num_plan_joins
"""

import re
import json
import psycopg2.extras
from typing import Optional


# ============================================================
# 1. SQL FEATURE EXTRACTION
# ============================================================

def remove_comments(sql):
    """Remove SQL comments."""
    sql = re.sub(r"/\*.*?\*/", " ", sql, flags=re.S)
    sql = re.sub(r"--.*?$", " ", sql, flags=re.M)
    return sql


def extract_sql_features(sql: str) -> dict:
    """
    Extract SQL structural features.

    This follows the feature extraction logic used while
    creating the training dataset.
    """

    sql_clean = remove_comments(sql)

    normalized = re.sub(r"\s+", " ", sql_clean).strip()

    # --------------------------------------------------------
    # TABLES
    # --------------------------------------------------------

    from_match = re.search(
        r"\bFROM\s+(.*?)(?=\bWHERE\b|\bGROUP\s+BY\b|\bORDER\s+BY\b|\bLIMIT\b|$)",
        normalized,
        flags=re.I
    )

    num_tables = 0

    if from_match:
        from_part = from_match.group(1)

        table_parts = [
            x.strip()
            for x in from_part.split(",")
            if x.strip()
        ]

        num_tables = len(table_parts)

    # Explicit JOIN syntax
    explicit_joins = len(
        re.findall(r"\bJOIN\b", normalized, flags=re.I)
    )

    if explicit_joins > 0:
        num_tables += explicit_joins

    # --------------------------------------------------------
    # JOINS
    # --------------------------------------------------------

    num_joins = 0

    where_match = re.search(
        r"\bWHERE\b(.*?)(?=\bGROUP\s+BY\b|\bORDER\s+BY\b|\bLIMIT\b|$)",
        normalized,
        flags=re.I
    )

    if where_match:

        where_part = where_match.group(1)

        join_conditions = re.findall(
            r"\b[A-Za-z_][A-Za-z0-9_]*\.[A-Za-z_][A-Za-z0-9_]*\s*=\s*"
            r"[A-Za-z_][A-Za-z0-9_]*\.[A-Za-z_][A-Za-z0-9_]*\b",
            where_part,
            flags=re.I
        )

        num_joins = len(join_conditions)

    # --------------------------------------------------------
    # FILTERS
    # --------------------------------------------------------

    num_filters = 0

    where_match = re.search(
        r"\bWHERE\b(.*?)(?=\bGROUP\s+BY\b|\bORDER\s+BY\b|\bLIMIT\b|$)",
        normalized,
        flags=re.I
    )

    if where_match:

        where_part = where_match.group(1)

        predicates = []
        current = []
        depth = 0

        tokens = re.split(
            r"(\(|\)|\bAND\b)",
            where_part,
            flags=re.I
        )

        for token in tokens:

            token = token.strip()

            if not token:
                continue

            if token == "(":
                depth += 1
                current.append(token)

            elif token == ")":
                depth -= 1
                current.append(token)

            elif (
                re.fullmatch(r"\bAND\b", token, flags=re.I)
                and depth == 0
            ):

                predicate = " ".join(current).strip()

                if predicate:
                    predicates.append(predicate)

                current = []

            else:
                current.append(token)

        predicate = " ".join(current).strip()

        if predicate:
            predicates.append(predicate)

        num_filters = max(
            0,
            len(predicates) - num_joins
        )

    # --------------------------------------------------------
    # GROUP BY / ORDER BY
    # --------------------------------------------------------

    has_group_by = int(
        bool(
            re.search(
                r"\bGROUP\s+BY\b",
                normalized,
                flags=re.I
            )
        )
    )

    has_order_by = int(
        bool(
            re.search(
                r"\bORDER\s+BY\b",
                normalized,
                flags=re.I
            )
        )
    )

    # --------------------------------------------------------
    # AGGREGATIONS
    # --------------------------------------------------------

    aggregate_functions = re.findall(
        r"\b(COUNT|SUM|AVG|MIN|MAX)\s*\(",
        normalized,
        flags=re.I
    )

    num_aggregations = len(aggregate_functions)

    has_aggregation = int(
        num_aggregations > 0
    )

    # --------------------------------------------------------
    # SELECTED COLUMNS
    # --------------------------------------------------------

    select_match = re.search(
        r"\bSELECT\b(.*?)(?=\bFROM\b)",
        normalized,
        flags=re.I
    )

    num_selected_columns = 0

    if select_match:

        select_part = select_match.group(1)

        expressions = [
            x.strip()
            for x in select_part.split(",")
            if x.strip()
        ]

        num_selected_columns = len(expressions)

    # --------------------------------------------------------
    # SUBQUERIES
    # --------------------------------------------------------

    num_subqueries = len(
        re.findall(
            r"\(\s*SELECT\b",
            normalized,
            flags=re.I
        )
    )

    # --------------------------------------------------------
    # QUERY DEPTH
    # --------------------------------------------------------

    if num_subqueries == 0:

        query_depth = 1

    else:

        depth = 0
        max_depth = 0

        for char in normalized:

            if char == "(":

                depth += 1
                max_depth = max(
                    max_depth,
                    depth
                )

            elif char == ")":

                depth -= 1

        query_depth = max_depth

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


# ============================================================
# 2. TABLE EXTRACTION
# ============================================================

def extract_table_names(sql: str):
    """
    Extract table names from the FROM clause.

    Matches the reference dataset-generation implementation.
    """

    normalized = re.sub(
        r"\s+",
        " ",
        remove_comments(sql)
    ).strip()

    match = re.search(
        r"\bFROM\s+(.*?)(?=\bWHERE\b|\bGROUP\s+BY\b|\bORDER\s+BY\b|\bLIMIT\b|$)",
        normalized,
        flags=re.I
    )

    if not match:
        return []

    from_part = match.group(1)

    tables = []

    for item in from_part.split(","):

        item = item.strip()

        if not item:
            continue

        pieces = re.split(
            r"\s+",
            item
        )

        if pieces:

            table_name = pieces[0]

            table_name = table_name.strip("()")

            if table_name:
                tables.append(table_name)

    return list(
        dict.fromkeys(tables)
    )


# ============================================================
# 3. DATABASE METADATA
# ============================================================

def get_table_metadata(cursor, tables):
    """
    Get total estimated rows and total physical table size
    for referenced tables.
    """

    total_rows = 0
    total_size = 0

    for table in tables:

        cursor.execute(
            """
            SELECT
                COALESCE(reltuples, 0),
                pg_total_relation_size(oid)
            FROM pg_class
            WHERE relname = %s
              AND relkind = 'r'
            """,
            (table,)
        )

        result = cursor.fetchone()

        if result:

            rows, size = result

            total_rows += int(rows)
            total_size += int(size)

    return total_rows, total_size


def get_num_indexes(cursor, tables):
    """
    Count indexes on all referenced tables.
    """

    total_indexes = 0

    for table in tables:

        cursor.execute(
            """
            SELECT COUNT(*)
            FROM pg_indexes
            WHERE schemaname = 'public'
              AND tablename = %s
            """,
            (table,)
        )

        total_indexes += cursor.fetchone()[0]

    return total_indexes


# ============================================================
# 4. COLUMN CARDINALITY
# ============================================================

def get_column_cardinality(cursor, sql):
    """
    Calculate average COUNT(DISTINCT column) for columns
    appearing in non-join WHERE predicates.
    """

    normalized = re.sub(
        r"\s+",
        " ",
        remove_comments(sql)
    ).strip()

    where_match = re.search(
        r"\bWHERE\b(.*?)(?=\bGROUP\s+BY\b|\bORDER\s+BY\b|\bLIMIT\b|$)",
        normalized,
        flags=re.I
    )

    if not where_match:
        return 0

    where_part = where_match.group(1)

    columns = re.findall(
        r"\b([A-Za-z_][A-Za-z0-9_]*)\.([A-Za-z_][A-Za-z0-9_]*)\b",
        where_part
    )

    selected_columns = []

    for table, column in columns:

        # Ignore join columns.
        pattern = (
            rf"\b{re.escape(table)}\.{re.escape(column)}\s*=\s*[\w]+\.[\w]+"
        )

        if re.search(
            pattern,
            where_part,
            flags=re.I
        ):
            continue

        pattern_reverse = (
            rf"[\w]+\.[\w]+\s*=\s*"
            rf"{re.escape(table)}\.{re.escape(column)}\b"
        )

        if re.search(
            pattern_reverse,
            where_part,
            flags=re.I
        ):
            continue

        selected_columns.append(
            (table, column)
        )

    selected_columns = list(
        dict.fromkeys(selected_columns)
    )

    cardinalities = []

    for table_alias, column in selected_columns:

        alias_match = re.search(
            rf"\b(\w+)\s+(?:AS\s+)?{re.escape(table_alias)}\b",
            normalized,
            flags=re.I
        )

        if alias_match:

            table_name = alias_match.group(1)

        else:

            table_name = table_alias

        cursor.execute(
            """
            SELECT EXISTS (
                SELECT 1
                FROM information_schema.columns
                WHERE table_schema = 'public'
                  AND table_name = %s
                  AND column_name = %s
            )
            """,
            (table_name, column)
        )

        exists = cursor.fetchone()[0]

        if not exists:
            continue

        query = f'''
            SELECT COUNT(DISTINCT "{column}")
            FROM "{table_name}"
        '''

        cursor.execute(query)

        value = cursor.fetchone()[0]

        if value is not None:
            cardinalities.append(
                int(value)
            )

    if not cardinalities:
        return 0

    return round(
        sum(cardinalities) /
        len(cardinalities)
    )


# ============================================================
# 5. EXPLAIN PLAN FEATURES
# ============================================================

def extract_explain_features(query: str, conn) -> dict:

    try:

        with conn.cursor(
            cursor_factory=psycopg2.extras.RealDictCursor
        ) as cur:

            cur.execute(
                f"EXPLAIN (FORMAT JSON) {query}"
            )

            plan_json = cur.fetchone()

            plan = plan_json[
                list(plan_json.keys())[0]
            ]

            if isinstance(plan, str):
                plan = json.loads(plan)

        root = plan[0]["Plan"]

        features = _walk_plan(root)

        return features

    except Exception as e:

        return _default_explain_features(
            error=str(e)
        )


def _walk_plan(
    node: dict,
    depth: int = 0
) -> dict:

    features = {
        "estimated_cost": node.get(
            "Total Cost",
            0.0
        ),

        "estimated_rows": node.get(
            "Plan Rows",
            0
        ),

        "plan_depth": depth,

        "num_sequential_scans": 0,

        "num_index_scans": 0,

        "num_plan_joins": 0,
    }

    node_type = node.get(
        "Node Type",
        ""
    )

    if node_type in {
        "Seq Scan",
        "Parallel Seq Scan"
    }:

        features[
            "num_sequential_scans"
        ] = 1

    elif node_type in {
        "Index Scan",
        "Index Only Scan",
        "Bitmap Index Scan"
    }:

        features[
            "num_index_scans"
        ] = 1

    elif node_type in {
        "Nested Loop",
        "Hash Join",
        "Merge Join"
    }:

        features[
            "num_plan_joins"
        ] = 1

    for child in node.get(
        "Plans",
        []
    ):

        child_features = _walk_plan(
            child,
            depth + 1
        )

        features["plan_depth"] = max(
            features["plan_depth"],
            child_features["plan_depth"]
        )

        features[
            "num_sequential_scans"
        ] += child_features[
            "num_sequential_scans"
        ]

        features[
            "num_index_scans"
        ] += child_features[
            "num_index_scans"
        ]

        features[
            "num_plan_joins"
        ] += child_features[
            "num_plan_joins"
        ]

    return features


def _default_explain_features(
    error: Optional[str] = None
):

    result = {
        "estimated_cost": 0.0,
        "estimated_rows": 0,
        "plan_depth": 0,
        "num_sequential_scans": 0,
        "num_index_scans": 0,
        "num_plan_joins": 0,
    }

    if error:
        result["explain_error"] = error

    return result


# ============================================================
# 6. COMPLETE FEATURE EXTRACTION
# ============================================================

def extract_all_features(
    query: str,
    conn=None
) -> dict:

    sql_features = extract_sql_features(
        query
    )

    if conn is None:

        return {
            **sql_features,
            "total_rows": 0,
            "total_table_size": 0,
            "num_indexes": 0,
            "column_cardinality": 0,
            **_default_explain_features(
                error="No connection available"
            )
        }

    # --------------------------------------------------------
    # Database metadata
    # --------------------------------------------------------

    tables = extract_table_names(
        query
    )

    with conn.cursor() as cursor:

        total_rows, total_table_size = \
            get_table_metadata(
                cursor,
                tables
            )

        num_indexes = get_num_indexes(
            cursor,
            tables
        )

        column_cardinality = \
            get_column_cardinality(
                cursor,
                query
            )

    # --------------------------------------------------------
    # EXPLAIN
    # --------------------------------------------------------

    explain_features = extract_explain_features(
        query,
        conn
    )

    return {
        **sql_features,

        "total_rows": total_rows,

        "total_table_size": total_table_size,

        "num_indexes": num_indexes,

        "column_cardinality": column_cardinality,

        **explain_features
    }