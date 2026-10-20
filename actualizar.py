"""
Actualiza los datos del dashboard "Regístrate y Gana" desde PostgreSQL.

Lee la tabla de registros, aplica las reglas del negocio y escribe en data/:
  registros.csv   (día, tienda, registros únicos por tienda, registros brutos)
  matriz.csv      (DNI distintos por tienda y mes, hora de Lima, año en curso)
  matriz25.csv    (lo mismo para el año anterior, para la comparación a/a)
  actualizado.txt (hora de la última actualización)
No guarda DNI ni datos personales: solo conteos.

Uso:
  DATABASE_URL="postgresql://usuario:clave@host:5432/base?sslmode=require" python actualizar.py
  python actualizar.py --probar     (solo muestra los nombres de las columnas de la tabla)
"""
import os, re, sys
from datetime import datetime, timezone
import pandas as pd

TABLA = os.environ.get('TABLA', 'campaigns')
CAMPANA = os.environ.get('CAMPANA', 'registrate-y-gana')
SALIDA = os.environ.get('SALIDA', 'data')
TZ = 'America/Lima'

# Nombres posibles de cada columna (se comparan sin mayúsculas ni guiones bajos)
ALIAS = {
    'document': ['document', 'documento', 'dni'],
    'origin': ['origin', 'origen'],
    'landing_source': ['landingsource', 'source'],
    'created': ['createdin', 'createdon', 'createdat', 'created', 'fecharegistro'],
}


def _norm(s):
    return re.sub(r'[^a-z0-9]', '', s.lower())


def _mapear(columnas):
    por_norm = {_norm(c): c for c in columnas}
    out = {}
    for k, opciones in ALIAS.items():
        for o in opciones:
            if o in por_norm:
                out[k] = por_norm[o]; break
        else:
            raise SystemExit(f'No encuentro la columna "{k}" en {TABLA}. Columnas: {list(columnas)}. '
                             f'Ajusta ALIAS en actualizar.py.')
    return out


def consulta(conn, sql, params=None):
    with conn.cursor() as cur:
        cur.execute(sql, params)
        cols = [d[0] for d in cur.description]
        return pd.DataFrame(cur.fetchall(), columns=cols)


def leer(conn):
    cols = consulta(conn, f'SELECT * FROM "{TABLA}" LIMIT 0').columns
    m = _mapear(cols)
    print('Columnas usadas:', m)
    # Diagnóstico sin datos personales: valores de la columna de campaña
    dx = consulta(conn, f'SELECT "{m["landing_source"]}" AS valor, count(*) AS n FROM "{TABLA}" '
                        f'GROUP BY 1 ORDER BY 2 DESC LIMIT 15')
    print('Valores de', m['landing_source'], ':', dx.to_dict('records'))
    q = (f'SELECT "{m["document"]}" AS document, "{m["origin"]}" AS origin, '
         f'"{m["created"]}" AS created FROM "{TABLA}" '
         f'WHERE "{m["landing_source"]}" = %(c)s')
    df = consulta(conn, q, {'c': CAMPANA})
    print('Filas de la campaña', CAMPANA, ':', len(df))
    if df.empty:
        raise SystemExit(f'No hay filas con {m["landing_source"]} = "{CAMPANA}". Revisa los valores impresos arriba.')
    return df


def procesar(df, ahora=None):
    """df con columnas document, origin, created. Devuelve (registros, matriz, matriz_prev)."""
    r = df[df['origin'].notna()].copy()
    r['origin'] = r['origin'].astype(str).str.strip()
    r = r[(r['origin'].str.len() == 3) & (r['origin'].str.lower() != 'web')]      # solo códigos de tienda
    r['cod'] = r['origin'].str.upper()                                             # minúsculas -> mayúsculas
    r['ts'] = pd.to_datetime(r['created'], utc=True).dt.tz_convert(TZ).dt.tz_localize(None)   # UTC -> Lima
    r['document'] = r['document'].astype('string').str.strip()
    r = r.sort_values('ts')
    dup = r.duplicated(['document', 'cod']) & r['document'].notna()                # mismo DNI en la misma tienda
    r['u'] = (~dup).astype(int)                                                    # se cuenta solo el primero
    r['day'] = r['ts'].dt.strftime('%Y-%m-%d')
    r['mes'] = r['ts'].dt.strftime('%Y-%m')

    reg = r.groupby(['day', 'cod']).agg(regs=('u', 'sum'), brutos=('u', 'size')).reset_index()
    reg = reg[reg['regs'] > 0]

    hoy = pd.Timestamp(ahora) if ahora is not None else pd.Timestamp.now(tz=TZ)
    hoy = hoy.tz_localize(None) if hoy.tzinfo is None else hoy.tz_convert(TZ).tz_localize(None)
    anio = hoy.year

    def distintos(d):
        filas = [(c, 'lima', m, n) for (c, m), n in d.groupby(['cod', 'mes'])['document'].nunique().items()]
        filas += [(c, 'lima', 'total', n) for c, n in d.groupby('cod')['document'].nunique().items()]
        filas += [('*', 'lima', m, n) for m, n in d.groupby('mes')['document'].nunique().items()]
        filas.append(('*', 'lima', 'total', d['document'].nunique()))
        out = pd.DataFrame(filas, columns=['cod', 'huso', 'mes', 'dni'])
        return out[out['dni'] > 0]

    mat = distintos(r[r['ts'].dt.year == anio])

    # Año anterior (comparación a/a): meses completos, más el mes en curso cortado al mismo día ("c")
    p = r[r['ts'].dt.year == anio - 1]
    filas = [(c, 'lima', m, n) for (c, m), n in p.groupby(['cod', 'mes'])['document'].nunique().items()]
    mes_cur = f'{anio - 1}-{hoy.month:02d}'
    corte = p[(p['ts'].dt.month == hoy.month) & (p['ts'].dt.day <= hoy.day)]
    filas += [(c, 'lima', mes_cur + 'c', n) for c, n in corte.groupby('cod')['document'].nunique().items()]
    mat_prev = pd.DataFrame(filas, columns=['cod', 'huso', 'mes', 'dni'])
    mat_prev = mat_prev[mat_prev['dni'] > 0]
    return reg, mat, mat_prev


def escribir(reg, mat, prev, carpeta=SALIDA):
    os.makedirs(carpeta, exist_ok=True)
    reg.to_csv(f'{carpeta}/registros.csv', index=False)
    mat.to_csv(f'{carpeta}/matriz.csv', index=False)
    prev.to_csv(f'{carpeta}/matriz25.csv', index=False)
    with open(f'{carpeta}/actualizado.txt', 'w') as f:
        f.write(datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'))


if __name__ == '__main__':
    import psycopg2
    url = os.environ.get('DATABASE_URL')
    if not url:
        raise SystemExit('Falta la variable DATABASE_URL (conexión a PostgreSQL).')
    conn = psycopg2.connect(url, connect_timeout=30)
    try:
        if '--probar' in sys.argv:
            cols = consulta(conn, f'SELECT * FROM "{TABLA}" LIMIT 0').columns.tolist()
            print('Columnas de', TABLA, ':', cols)
            print('Mapeo detectado:', _mapear(cols))
            sys.exit(0)
        df = leer(conn)
    finally:
        conn.close()
    reg, mat, prev = procesar(df)
    escribir(reg, mat, prev)
    print(f'OK: {int(reg["regs"].sum()):,} registros únicos; último día {reg["day"].max()}')
