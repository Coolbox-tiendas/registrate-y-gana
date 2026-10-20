"""Lista las tablas de PostgreSQL con sus columnas y filas aproximadas. No lee datos personales."""
import os
import psycopg2

conn = psycopg2.connect(os.environ['DATABASE_URL'], connect_timeout=30)
cur = conn.cursor()
cur.execute("""
    SELECT c.table_schema, c.table_name, t.table_type,
           string_agg(c.column_name, ', ' ORDER BY c.ordinal_position)
    FROM information_schema.columns c
    JOIN information_schema.tables t USING (table_schema, table_name)
    WHERE c.table_schema NOT IN ('pg_catalog', 'information_schema')
    GROUP BY 1, 2, 3 ORDER BY 1, 2
""")
filas = cur.fetchall()
cur.execute("SELECT schemaname, relname, n_live_tup FROM pg_stat_user_tables")
aprox = {(s, r): n for s, r, n in cur.fetchall()}
print('=== TABLAS Y VISTAS ===')
for s, t, tipo, cols in filas:
    print(f'{s}.{t} [{tipo}] ~{aprox.get((s, t), "?")} filas: {cols}')
print()
print('=== CANDIDATAS (tienen landing_source o createdIn) ===')
for s, t, tipo, cols in filas:
    low = cols.lower().replace('_', '')
    if 'landingsource' in low or 'createdin' in low:
        print(f'{s}.{t} [{tipo}]')
conn.close()
