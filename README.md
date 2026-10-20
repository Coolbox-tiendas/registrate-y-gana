# Regístrate y Gana – dashboard automático

Cada 10 minutos GitHub lee PostgreSQL, calcula el avance y republica la página (link único, sin login).
En el repositorio solo se guardan **conteos por tienda**; nunca DNI ni datos personales.

## Archivos
| Archivo | Para qué sirve |
|---|---|
| `index.html` | La página del dashboard (carga los CSV de `data/`) |
| `actualizar.py` | Lee PostgreSQL y escribe `data/registros.csv`, `matriz.csv`, `matriz25.csv` |
| `generar_metas.py` | Una vez al mes: genera `data/metas.csv` y `data/tiendas.csv` desde los Excel |
| `.github/workflows/actualizar.yml` | Programa la actualización cada 10 minutos |
| `data/` | Datos que lee la página |

## Puesta en marcha (una sola vez)
1. Crea un repositorio **público** en GitHub (por ejemplo `registrate-y-gana`) y sube todo el contenido de esta carpeta.
   La carpeta `.github` es oculta: si la subida por arrastre no la toma, entra a *Add file › Create new file*, escribe
   `.github/workflows/actualizar.yml` y pega el contenido del archivo.
2. En el repositorio: **Settings › Secrets and variables › Actions › New repository secret**.
   Nombre: `DATABASE_URL`. Valor:
   `postgresql://USUARIO:CLAVE@HOST:5432/BASE?sslmode=require`
   (con tus datos reales de Render; la clave solo se escribe aquí).
3. **Settings › Pages › Build and deployment › Source: GitHub Actions**.
4. Pestaña **Actions › Actualizar dashboard › Run workflow**. Al terminar, el link aparece en Settings › Pages
   (será `https://TU_USUARIO.github.io/registrate-y-gana/`). Ese es el link que compartes.

Para ver los nombres de columna de la tabla sin traer datos, en tu computador:
`DATABASE_URL="..." python actualizar.py --probar`.

## Cada mes (cambio de mes)
1. En tu computador, con los Excel de ventas y listado actualizados:
   `pip install -r requirements.txt`
   `python generar_metas.py --ventas VENTAS_TIENDAS.xlsx --tiendas LISTADO_TIENDAS.xlsx --mes 2026-11`
2. Sube `data/metas.csv` y `data/tiendas.csv` al repositorio (reemplazando los anteriores). La página se republica sola.
   Si cambia solo el listado de tiendas, repite lo mismo en el mes en curso.

## Reglas que aplica
- Solo `landing_source = registrate-y-gana`; origen de 3 caracteres, sin "web"; códigos en mayúscula.
- Hora de Lima (UTC−5).
- Un DNI cuenta una sola vez por tienda (se conserva el primero); en otra tienda vuelve a contar.
- Meta: 15% de la venta del mismo mes del año anterior; si no hubo, 15% del promedio de los meses con venta; si nunca vendió, 20.
  Tiendas cerradas o inactivas: sin meta.

## Notas
- GitHub ejecuta los programados "cuando puede": pueden demorar unos minutos.
- En repositorios públicos, GitHub desactiva los programados tras 60 días sin actividad. La actualización mensual de metas cuenta como actividad.
- Si Render restringe IPs de entrada, debe permitir conexiones externas (por defecto lo permite).
