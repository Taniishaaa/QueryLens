from database import get_connection


def get_database_schema(conn=None):

    if conn is None:
        conn = get_connection()

    if conn is None:
        raise RuntimeError("Database is not connected.")

    cursor = conn.cursor()

    try:

        # Get tables, columns and data types
        cursor.execute("""
            SELECT
                table_name,
                column_name,
                data_type
            FROM information_schema.columns
            WHERE table_schema = 'public'
            ORDER BY table_name, ordinal_position;
        """)

        columns = cursor.fetchall()

        # Get primary and foreign key information
        cursor.execute("""
            SELECT
                tc.table_name AS table_name,
                kcu.column_name AS column_name,
                tc.constraint_type,
                ccu.table_name AS referenced_table,
                ccu.column_name AS referenced_column
            FROM information_schema.table_constraints AS tc
            JOIN information_schema.key_column_usage AS kcu
                ON tc.constraint_name = kcu.constraint_name
                AND tc.table_schema = kcu.table_schema
            LEFT JOIN information_schema.constraint_column_usage AS ccu
                ON tc.constraint_name = ccu.constraint_name
                AND tc.table_schema = ccu.table_schema
            WHERE tc.table_schema = 'public'
              AND tc.constraint_type IN ('PRIMARY KEY', 'FOREIGN KEY')
            ORDER BY tc.table_name, kcu.column_name;
        """)

        constraints = cursor.fetchall()

        schema_text = []

        current_table = None

        for table_name, column_name, data_type in columns:

            if table_name != current_table:

                schema_text.append(
                    f"\nTABLE: {table_name}"
                )

                current_table = table_name

            schema_text.append(
                f"  - {column_name}: {data_type}"
            )

        schema_text.append("\n\nCONSTRAINTS:")

        for (
            table_name,
            column_name,
            constraint_type,
            referenced_table,
            referenced_column
        ) in constraints:

            if constraint_type == "PRIMARY KEY":

                schema_text.append(
                    f"  - PRIMARY KEY: "
                    f"{table_name}.{column_name}"
                )

            elif constraint_type == "FOREIGN KEY":

                schema_text.append(
                    f"  - FOREIGN KEY: "
                    f"{table_name}.{column_name} "
                    f"-> {referenced_table}.{referenced_column}"
                )

        return "\n".join(schema_text)

    finally:

        cursor.close()