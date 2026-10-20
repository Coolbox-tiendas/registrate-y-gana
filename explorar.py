"""Diagnóstico de public.campaigns: solo conteos y valores de códigos de tienda. Sin datos personales."""
import os
import psycopg2

conn = psycopg2.connect(os.environ['DATABASE_URL'], connect_timeout=30)
cur = conn.cursor()


def q(sql, params=None):
    cur.execute(sql, params)
    return cur.fetchall()


print('=== TIPOS DE COLUMNA ===')
for c, t in q("SELECT column_name, data_type FROM information_schema.columns "
              "WHERE table_schema='public' AND table_name='campaigns' ORDER BY ordinal_position"):
    print(f'{c}: {t}')

total = q('SELECT count(*) FROM public.campaigns')[0][0]
print(f'\n=== TOTAL FILAS: {total} ===')

print('\n=== FILAS NO VACÍAS POR COLUMNA ===')
cols = [r[0] for r in q("SELECT column_name FROM information_schema.columns "
                        "WHERE table_schema='public' AND table_name='campaigns' ORDER BY ordinal_position")]
for c in cols:
    n = q(f'SELECT count("{c}") FROM public.campaigns')[0][0]
    print(f'{c}: {n}')

print('\n=== created_on: rango ===')
print(q('SELECT min(created_on), max(created_on) FROM public.campaigns'))

print('\n=== VALORES DE source (top 15) ===')
for v, n in q('SELECT source, count(*) FROM public.campaigns GROUP BY 1 ORDER BY 2 DESC LIMIT 15'):
    print(f'{v!r}: {n}')

print('\n=== origin: largo y valores más frecuentes ===')
for l, n in q('SELECT length(origin), count(*) FROM public.campaigns GROUP BY 1 ORDER BY 2 DESC LIMIT 10'):
    print(f'largo {l}: {n}')
for v, n in q('SELECT origin, count(*) FROM public.campaigns GROUP BY 1 ORDER BY 2 DESC LIMIT 15'):
    print(f'{v!r}: {n}')

print('\n=== source x registros con origin de 3 letras ===')
for v, n in q("SELECT source, count(*) FROM public.campaigns "
              "WHERE length(origin)=3 AND lower(origin)<>'web' GROUP BY 1 ORDER BY 2 DESC LIMIT 15"):
    print(f'{v!r}: {n}')

print('\n=== created_on por mes ===')
for m, n in q("SELECT to_char(created_on,'YYYY-MM'), count(*) FROM public.campaigns GROUP BY 1 ORDER BY 1"):
    print(f'{m}: {n}')
conn.close()
