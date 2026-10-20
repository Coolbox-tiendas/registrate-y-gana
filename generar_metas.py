"""
Genera data/metas.csv y data/tiendas.csv a partir de los archivos de ventas y de listado de tiendas.
Se corre UNA VEZ AL MES (o cuando cambie el listado).

Uso:
  python generar_metas.py --ventas VENTAS_TIENDAS.xlsx --tiendas LISTADO_TIENDAS.xlsx --mes 2026-11
Opcional: --pct 0.15 --default 20

Reglas de la meta (por tienda):
  - Cerrada o inactiva: sin meta.
  - Si vendió en el mismo mes del año anterior: 15% de esa venta.
  - Si no, pero vendió en meses anteriores: 15% del promedio de los meses con venta.
  - Si nunca vendió: meta predeterminada (20).
"""
import argparse, calendar
from datetime import datetime
import pandas as pd

ap = argparse.ArgumentParser()
ap.add_argument('--ventas', required=True)
ap.add_argument('--tiendas', required=True)
ap.add_argument('--mes', required=True, help='YYYY-MM')
ap.add_argument('--pct', type=float, default=0.15)
ap.add_argument('--default', type=float, default=20)
ap.add_argument('--salida', default='data')
a = ap.parse_args()

mes = pd.Timestamp(a.mes + '-01')
dias = calendar.monthrange(mes.year, mes.month)[1]

l = pd.read_excel(a.tiendas)
t = l[['COD', 'NOMBRE DE TIENDA', 'ZONA', 'Zonal', 'FORMATO', 'CATEGORIA', 'STATUS']].copy()
t.columns = ['cod', 'nombre', 'zona', 'zonal', 'formato', 'categoria', 'status']
t['cod'] = t['cod'].astype(str).str.upper().str.strip()
t['formato'] = t['formato'].str.title().replace({'Modulo': 'Módulo'})

v = pd.read_excel(a.ventas)
v = v[v['TIENDA.1'].notna()].set_index('TIENDA.1')
meses = [c for c in v.columns if isinstance(c, datetime)]
previos = [m for m in meses if m < mes]
mismo = pd.Timestamp(mes.year - 1, mes.month, 1)

filas = []
for _, s in t.iterrows():
    cod = s['cod']
    serie = v.loc[cod, previos].fillna(0).astype(float) if cod in v.index else pd.Series(dtype=float)
    ant = float(v.loc[cod, mismo]) if cod in v.index and mismo in v.columns else 0.0
    con = serie[serie > 0]
    if ant > 0:
        tipo, base, bm, meta = 'mismo mes año anterior', ant, mismo.strftime('%Y-%m'), ant * a.pct
    elif len(con) > 0:
        tipo, base, bm, meta = 'promedio meses con venta', float(con.mean()), str(len(con)), float(con.mean()) * a.pct
    else:
        tipo, base, bm, meta = 'predeterminada', 0.0, '', a.default
    filas.append((cod, a.mes, round(base, 2), bm, tipo, round(meta, 2), dias))
pd.DataFrame(filas, columns=['cod', 'mes', 'venta_base', 'base_mes', 'base_tipo', 'meta', 'dias']).to_csv(f'{a.salida}/metas.csv', index=False)
t.to_csv(f'{a.salida}/tiendas.csv', index=False)
print('Listo:', len(t), 'tiendas, meta del mes', a.mes)
