import os
from database.connection import get_connection

def export_backup(file_path):
    """Export all tables to a .sql file with INSERT statements."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            with open(file_path, 'w', encoding='utf-8') as f:
                # Get all tables (excluding system tables)
                cur.execute("""
                    SELECT table_name FROM information_schema.tables
                    WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
                    ORDER BY table_name
                """)
                tables = [row[0] for row in cur.fetchall()]
                for table in tables:
                    # Get column names
                    cur.execute("SELECT * FROM {} LIMIT 0".format(table))  # safe as table name from system
                    col_names = [desc[0] for desc in cur.description]
                    col_str = ', '.join(col_names)
                    f.write(f"-- Table: {table}\n")
                    cur.execute(f"SELECT * FROM {table}")
                    rows = cur.fetchall()
                    for row in rows:
                        # Convert None to NULL
                        values = []
                        for v in row:
                            if v is None:
                                values.append('NULL')
                            elif isinstance(v, str):
                                values.append(f"'{v.replace("'", "''")}'")
                            else:
                                values.append(str(v))
                        f.write(f"INSERT INTO {table} ({col_str}) VALUES ({', '.join(values)});\n")
                    f.write("\n")
    return True

def import_backup(file_path):
    """Execute a .sql backup file to restore data."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            with open(file_path, 'r', encoding='utf-8') as f:
                sql_script = f.read()
                # Execute script (split by ';' but careful with strings)
                # Simple split – works for generated scripts
                statements = sql_script.split(';')
                for stmt in statements:
                    if stmt.strip():
                        cur.execute(stmt)
            conn.commit()
    return True