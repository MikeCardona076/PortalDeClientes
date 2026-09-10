# Portal de Clientes — SETTEPI Pacífico

Dashboard por **cliente/planta** y **semana** con:
- Total de viajes
- Nivel de Servicio (NS)
- Calidad de Ruta (CR): **14d** (criterio plataforma, default) y **7d** (semana exacta)

Cada usuario-cliente ve solo su(s) planta(s); el admin ve todo.

## Requisitos
- Python 3.12+
- (Prod) PostgreSQL, Redis y Docker

## Instalación local (dev)
```bash
python -m venv .venv
.venv\Scripts\activate            # Windows
pip install -r requirements.txt
copy .env.example .env            # edita credenciales y SECRET_KEY
python manage.py migrate
python manage.py createsuperuser
python manage.py seed_bustrax --bunit set_tj2
```

## Correr
```bash
python manage.py runserver
```
- Portal: http://localhost:8000
- Admin: http://localhost:8000/admin/

## Sincronizar datos
```bash
python manage.py sync_semana 2026 6 --bunit set_tj2
python manage.py backfill 2026 --desde 1 --hasta 36 --bunit set_tj2
```
> En producción esto corre con Celery: `worker` + `beat` (**diario 05:00**, America/Tijuana)
> sincroniza la semana en curso. El contenedor `web` corre `migrate` al arrancar.

## Refinamiento GPS (Calidad de Ruta)
Para rutas donde el ETA sobrecuenta, se refina con GPS (criterio oficial Bustrax **200 m**):
1. En el admin crea `Refinamiento GPS` (grupo + `ruta_seq`).
2. Prueba: `python manage.py refinar_gps 2026 6 --grupo SCN-SCHNEIDER --ruta 142`
3. `sync_semana` lo aplica automáticamente (14d y 7d) y marca el CR como `mixto`.

## Filtros del dashboard (admin)
- Año (por defecto el actual).
- **Cliente**: Todos / uno.
- **Semana**: Todas (default) / una → muestra solo esa columna.
Los usuarios-cliente no ven estos selects.

## Producción (Docker + Nginx Proxy Manager)
```bash
cp .env.example .env      # DJANGO_ENV=prod, DEBUG=False, dominio, SMTP, Postgres
docker compose up -d --build
docker compose exec web python manage.py migrate
docker compose exec web python manage.py createsuperuser
```
Ver `deploy/nginx-proxy-manager.md` para el dominio y HTTPS.

## Estructura
```
config/          settings (dev/prod), urls, wsgi/asgi, celery
apps/core/       modelos, admin, scope por usuario
apps/bustrax/    APIs Bustrax, calendario, CR, NS, GPS (Traffilog)
apps/metricas/   vistas heatmap + drill
apps/sync/       sync_semana/backfill + Celery
templates/       plantillas
```

## Seguridad
- Las credenciales viven en `.env` (ignorado). **No** commitear tokens.
- `.env.example` trae placeholders.

Contexto técnico detallado para agentes: **`Judgeman.md`**.
