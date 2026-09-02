"""
database.py
-----------
Handles PostgreSQL connection and metadata extraction.

Session state is stored in a simple module-level dict.
This is intentionally lightweight for a university project.
No authentication, no connection pooling — just a single active connection.
"""

import re
import psycopg2
import psycopg2.extras
from typing import Optional

# ---------------------------------------------------------------------------
# In-memory session — holds the active connection and extracted metadata.
# Only one connection is active at a time. Replace with a proper session store
# if multi-user support is ever needed.
# ---------------------------------------------------------------------------
_session: dict = {
    "connection": None,   # psycopg2 connection object
    "metadata": None,     # dict returned by extract_metadata()
    "db_name": None,      # plain database name (no credentials)
}


def get_session() -> dict:
    """Return the current session dict."""
    return _session


def is_connected() -> bool:
    conn = _session.get("connection")
    if conn is None:
        return False
    try:
        # A closed connection has a non-zero closed attribute.
        return conn.closed == 0
    except Exception:
        return False


def connect(connection_string: str) -> dict:
    """
    Validate, connect to the PostgreSQL database, and extract metadata.

    Returns a dict with keys: success, message, metadata (or error).
    Never includes the raw connection string / password in the return value.
    """
    # Basic format validation before attempting a real connection.
    if not _is_valid_connection_string(connection_string):
        return {
            "success": False,
            "error": "Invalid connection string format. Expected: postgresql://user:password@host:port/dbname",
        }

    try:
        conn = psycopg2.connect(connection_string, connect_timeout=10)
        conn.autocommit = True  # metadata queries don't need transactions

        # Discover all user schemas, then set search_path at session level.
        # This ensures schema-qualified queries like bookings.flights resolve
        # correctly for the lifetime of this connection.
        with conn.cursor() as cur:
            cur.execute("""
                SELECT schema_name
                FROM information_schema.schemata
                WHERE schema_name NOT IN ('pg_catalog','information_schema','pg_toast')
                  AND schema_name NOT LIKE 'pg_temp%'
                ORDER BY schema_name;
            """)
            schemas = [r[0] for r in cur.fetchall()] or ["public"]
            # Use SET LOCAL is session-level with autocommit — just SET is fine.
            search_path = ", ".join(schemas) + ", public"
            cur.execute("SELECT set_config('search_path', %s, false);", (search_path,))

        metadata = _extract_metadata(conn)

        # Only close the old connection AFTER the new one succeeds.
        _close_existing()

        # Persist in session
        _session["connection"] = conn
        _session["metadata"] = metadata
        _session["db_name"] = metadata.get("database_name", "unknown")

        return {
            "success": True,
            "message": "Database connected successfully",
            "metadata": metadata,
        }

    except psycopg2.OperationalError as e:
        # Sanitize: strip the connection string from psycopg2 error messages.
        error_msg = _sanitize_error(str(e))
        return {"success": False, "error": f"Connection failed: {error_msg}"}
    except Exception as e:
        return {"success": False, "error": "Unexpected error during connection."}


def get_connection() -> Optional[psycopg2.extensions.connection]:
    """Return the active psycopg2 connection, or None if not connected."""
    if is_connected():
        return _session["connection"]
    return None


def run_query(query: str, timeout_ms: int = 30000) -> dict:
    """
    Validate and execute a read-only SQL query against the connected database.

    - Rejects dangerous statements (DROP, DELETE, TRUNCATE, ALTER, UPDATE, INSERT, etc.)
    - Enforces a query timeout via PostgreSQL statement_timeout.
    - Returns columns, rows, and actual execution time in milliseconds.
    """
    if not is_connected():
        return {"success": False, "error": "No database connected. Call /connect first."}

    # Safety check — block destructive SQL before sending to the database.
    rejection = _check_dangerous_query(query)
    if rejection:
        return {"success": False, "error": rejection}

    conn = _session["connection"]

    import time

    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            # Set statement timeout to prevent long-running queries.
            cur.execute(f"SET statement_timeout = {timeout_ms};")

            start = time.perf_counter()
            cur.execute(query)
            elapsed_ms = round((time.perf_counter() - start) * 1000, 3)

            columns = [desc.name for desc in cur.description] if cur.description else []
            # Convert RealDictRow objects to plain dicts for JSON serialisation.
            rows = [dict(row) for row in cur.fetchall()]

        return {
            "success": True,
            "columns": columns,
            "rows": rows,
            "execution_time_ms": elapsed_ms,
            "row_count": len(rows),
        }

    except psycopg2.errors.QueryCanceled:
        return {"success": False, "error": f"Query exceeded timeout of {timeout_ms}ms and was cancelled."}
    except psycopg2.errors.SyntaxError as e:
        return {"success": False, "error": f"SQL syntax error: {e.pgerror.strip()}"}
    except psycopg2.ProgrammingError as e:
        return {"success": False, "error": f"Query error: {e.pgerror.strip() if e.pgerror else str(e)}"}
    except psycopg2.Error as e:
        return {"success": False, "error": f"Database error: {e.pgerror.strip() if e.pgerror else str(e)}"}
    except Exception:
        return {"success": False, "error": "Unexpected error while executing query."}


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _is_valid_connection_string(cs: str) -> bool:
    """
    Lightweight format check.
    Accepts: postgresql://... or postgres://...
    """
    pattern = r"^postgres(?:ql)?://[^:]+:[^@]+@[^:/]+(?::\d+)?/\S+"
    return bool(re.match(pattern, cs))


def _close_existing():
    """Close and discard any currently open connection."""
    conn = _session.get("connection")
    if conn and conn.closed == 0:
        try:
            conn.close()
        except Exception:
            pass
    _session["connection"] = None
    _session["metadata"] = None
    _session["db_name"] = None


def _check_dangerous_query(query: str) -> Optional[str]:
    """
    Return an error string if the query contains a forbidden statement,
    or None if the query looks safe to execute.

    Matches whole keywords at word boundaries to avoid false positives
    (e.g. a column named 'updated_at' should not be blocked).
    """
    forbidden = [
        "DROP", "DELETE", "TRUNCATE", "ALTER", "UPDATE",
        "INSERT", "CREATE", "REPLACE", "GRANT", "REVOKE",
        "COPY", "VACUUM", "REINDEX",
    ]
    upper_query = query.upper()
    for keyword in forbidden:
        # Match as a whole word so 'UPDATES' or 'DELETES' in column names are safe.
        if re.search(rf"\b{keyword}\b", upper_query):
            return (
                f"Forbidden statement detected: {keyword}. "
                "Only read-only queries (SELECT) are allowed."
            )
    return None


def _sanitize_error(msg: str) -> str:
    """
    Remove credentials from psycopg2 error messages before returning to client.
    psycopg2 sometimes echoes connection params in the error string.
    """
    # Remove anything that looks like a password= or user= parameter.
    msg = re.sub(r"password=[^\s]+", "password=***", msg, flags=re.IGNORECASE)
    msg = re.sub(r"://[^@]+@", "://***:***@", msg)
    return msg.strip()


def _extract_metadata(conn) -> dict:
    """
    Extract schema/table/column metadata from PostgreSQL catalog tables.

    Uses pg_catalog and information_schema — no full table scans.
    Returns a plain dict that is safe to send to the frontend.
    """
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:

        # -- Database name --------------------------------------------------
        cur.execute("SELECT current_database() AS db_name;")
        db_name = cur.fetchone()["db_name"]

        # -- Schema names (exclude system schemas) --------------------------
        cur.execute("""
            SELECT schema_name
            FROM information_schema.schemata
            WHERE schema_name NOT IN ('pg_catalog', 'information_schema', 'pg_toast')
              AND schema_name NOT LIKE 'pg_temp%'
            ORDER BY schema_name;
        """)
        schemas = [row["schema_name"] for row in cur.fetchall()]

        # -- Tables per schema (name + estimated row count from pg_class) ---
        cur.execute("""
            SELECT
                n.nspname                        AS schema_name,
                c.relname                        AS table_name,
                c.reltuples::bigint              AS estimated_row_count
            FROM pg_class c
            JOIN pg_namespace n ON n.oid = c.relnamespace
            WHERE c.relkind = 'r'
              AND n.nspname NOT IN ('pg_catalog', 'information_schema', 'pg_toast')
              AND n.nspname NOT LIKE 'pg_temp%'
            ORDER BY n.nspname, c.relname;
        """)
        tables_raw = cur.fetchall()

        # Build schema -> [table, ...] structure
        tables_by_schema: dict = {}
        for row in tables_raw:
            s = row["schema_name"]
            tables_by_schema.setdefault(s, []).append({
                "table_name": row["table_name"],
                "estimated_row_count": row["estimated_row_count"],
            })

        # -- Columns --------------------------------------------------------
        cur.execute("""
            SELECT
                table_schema,
                table_name,
                column_name,
                data_type,
                is_nullable
            FROM information_schema.columns
            WHERE table_schema NOT IN ('pg_catalog', 'information_schema', 'pg_toast')
            ORDER BY table_schema, table_name, ordinal_position;
        """)
        columns_raw = cur.fetchall()

        columns_by_table: dict = {}
        for row in columns_raw:
            key = f"{row['table_schema']}.{row['table_name']}"
            columns_by_table.setdefault(key, []).append({
                "column_name": row["column_name"],
                "data_type": row["data_type"],
                "is_nullable": row["is_nullable"],
            })

        # -- Indexes --------------------------------------------------------
        cur.execute("""
            SELECT
                n.nspname                        AS schema_name,
                t.relname                        AS table_name,
                i.relname                        AS index_name,
                ix.indisunique                   AS is_unique,
                ix.indisprimary                  AS is_primary,
                array_agg(a.attname ORDER BY a.attnum) AS columns
            FROM pg_index ix
            JOIN pg_class t  ON t.oid  = ix.indrelid
            JOIN pg_class i  ON i.oid  = ix.indexrelid
            JOIN pg_namespace n ON n.oid = t.relnamespace
            JOIN pg_attribute a ON a.attrelid = t.oid
             AND a.attnum = ANY(ix.indkey)
            WHERE n.nspname NOT IN ('pg_catalog', 'information_schema', 'pg_toast')
            GROUP BY n.nspname, t.relname, i.relname, ix.indisunique, ix.indisprimary
            ORDER BY n.nspname, t.relname, i.relname;
        """)
        indexes_raw = cur.fetchall()

        indexes_by_table: dict = {}
        for row in indexes_raw:
            key = f"{row['schema_name']}.{row['table_name']}"
            indexes_by_table.setdefault(key, []).append({
                "index_name": row["index_name"],
                "is_unique": row["is_unique"],
                "is_primary": row["is_primary"],
                "columns": list(row["columns"]),
            })

        # -- Foreign keys ---------------------------------------------------
        cur.execute("""
            SELECT
                tc.table_schema,
                tc.table_name,
                kcu.column_name,
                ccu.table_schema  AS foreign_schema,
                ccu.table_name    AS foreign_table,
                ccu.column_name   AS foreign_column
            FROM information_schema.table_constraints  AS tc
            JOIN information_schema.key_column_usage   AS kcu
              ON tc.constraint_name = kcu.constraint_name
             AND tc.table_schema    = kcu.table_schema
            JOIN information_schema.constraint_column_usage AS ccu
              ON ccu.constraint_name = tc.constraint_name
            WHERE tc.constraint_type = 'FOREIGN KEY'
              AND tc.table_schema NOT IN ('pg_catalog', 'information_schema')
            ORDER BY tc.table_schema, tc.table_name;
        """)
        fk_raw = cur.fetchall()

        fk_by_table: dict = {}
        for row in fk_raw:
            key = f"{row['table_schema']}.{row['table_name']}"
            fk_by_table.setdefault(key, []).append({
                "column": row["column_name"],
                "references": f"{row['foreign_schema']}.{row['foreign_table']}.{row['foreign_column']}",
            })

    # -- Assemble final metadata dict --------------------------------------
    total_tables = sum(len(v) for v in tables_by_schema.values())

    tables_detail = []
    for t in tables_raw:
        key = f"{t['schema_name']}.{t['table_name']}"
        tables_detail.append({
            "schema": t["schema_name"],
            "table": t["table_name"],
            "estimated_row_count": t["estimated_row_count"],
            "columns": columns_by_table.get(key, []),
            "indexes": indexes_by_table.get(key, []),
            "foreign_keys": fk_by_table.get(key, []),
        })

    return {
        "database_name": db_name,
        "schemas": schemas,
        "table_count": total_tables,
        "tables": tables_detail,
    }
