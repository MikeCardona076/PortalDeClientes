# Judgeman — Contexto para agentes

Documento de contexto para cualquier agente/LLM que trabaje en **PortalDeClientes**
(dashboard de Clientes de SETTEPI Pacífico). Léelo antes de tocar código.

---

## 1. ¿Qué es?

Portal web (Django 6) que muestra KPIs operativos por **cliente/planta** y **semana**:
- **Total de viajes**
- **Nivel de Servicio (NS Llegada)**
- **Calidad de Ruta (CR)** en dos ventanas: **14d** (criterio de la plataforma Bustrax, default) y **7d** (semana exacta)
- (Pendiente) Score de Seguridad, que vendrá de otra API.

Se comparte con clientes: cada usuario-cliente ve **solo su(s) planta(s)**; el admin ve todo.

Dominio previsto: `portalclientes.pacifico.mikecardona076.com` (aún local).

---

## 2. Stack y estructura

- **Django 6** + `python-decouple`, `requests`, `whitenoise`.
- **Dev**: SQLite, email en consola, sin Celery. **Prod**: PostgreSQL, SMTP, Celery/Redis (Docker + Nginx Proxy Manager).

```
config/            settings.py (dev/prod por DJANGO_ENV), urls.py, wsgi/asgi, celery.py
apps/core/         modelos, admin, scoping, middleware
apps/bustrax/      cliente de APIs, calendario (weeks), CR (cr.py), NS (ns.py), GPS (gps.py)
apps/metricas/     vistas heatmap + drill, urls, templates
apps/sync/         servicio sync_semana/backfill, management commands, tasks (Celery)
templates/         base, metricas/, registration/ (login, reset)
deploy/            nginx-proxy-manager.md
```

Apps registradas como `apps.core`, `apps.bustrax`, `apps.metricas`, `apps.sync`.

---

## 3. Fuentes de datos (APIs Bustrax)

Endpoint base: `https://api.bustrax.io/engine/get_json.php` y `.../get_reports.php`.
Credenciales por `.env` (ver §8). Formato de payload: `data[...]` form-urlencoded.

### 3.1 `get_trips_eta` — **histórico de viajes/paradas por rango de fechas** (clave)
```
type=get_trips_eta
data[bunit]=set_tj2            # o data[gcode]=<gcode> de un grupo
data[start_date]=YYYY-MM-DD
data[end_date]=YYYY-MM-DD
data[iuser], data[ver]=1.0.1, data[bttkn]
```
Devuelve lista de viajes con: `id, service_id, shift, route_type, car, status, group,
stops, stops_eta, start_date/time/eta, end_date/time/eta, start_status, end_status, driver`.
- `stops` = definición de paradas (id, des, lat, lng, times).
- `stops_eta` = por parada: `etaTS` (hora real detectada), `status`
  (`done`, `no_data`, `no_det`, `almost`, `proc`, `start`), `drsp`, `trsp`, `etaKM`.
- **No trae un flag `f`/`found` explícito**; el "found" se **deriva** (`status=="done"` + `etaTS`).
- Es la **única** vía para CR histórico (la API MAE no acepta fechas; ver §7).

### 3.2 `get_routes_full_with_stops_history` — MAE (snapshot reciente)
```
type=get_routes_full_with_stops_history
data[bunit]=set_tj2
data[with_stops]=true
data[with_daytimes_data]=true
```
- `stops`, `daytimes`, `stops_history` vienen como **string JSON**.
- `stops_history` = últimos **14 días** de viajes con `status IN (5,6,7,8)` y `found=1`
  (confirmado en el backend PHP de Bustrax `RouteController.php`).
- **No acepta fechas** → no sirve para histórico. Solo snapshot vigente.

### 3.3 `get_report_result` (rid=5) — viajes listado (NS/viajes)
```
type=get_report_result
data[rid]=5
data[inputs][]=<bunit>&data[inputs][]=<sdate>&data[inputs][]=<edate>
```
Campos: `Tipo de Viaje`, `shift`, `status`, `record_quality`, `group`, `Estado de Viaje`,
`start_date/time`, `end_date/time`, `end_eta`, etc. Es la fuente de NS y total de viajes.

### 3.4 `get_groups`
`type=get_groups`, `data[bunit]` → grupos (`id`, `description`, `gcode`, `bunit`).

### 3.5 Endpoints que **NO** sirven (probados en vivo)
- `get_trips_eta_report` / `tripsETAReport` / `multipleTripsETAReport`: HTTP 200 vacío.
- `get_trip_audit`: vacío con nuestro token.
- `history_wheres` en MAE: solo acepta condiciones sobre `r.` y el `stops_history` está fijo a 14 días.
- Acceso directo a BD `tracker`: ya no disponible.

---

## 4. Calendario operativo (¡importante!)

La semana corre **domingo–sábado**. El número de semana = **semana ISO del domingo** que la inicia
(validado contra el campo `Sem Via` del reporte). Ej.: dom 2026-08-23 = "Semana 34".

Implementado en `apps/bustrax/weeks.py`: `start_sunday`, `semvia`, `sunday_of_week`,
`week_window`, `weeks_of_year`, `current_week`.

---

## 5. Cálculo de métricas

### 5.1 Calidad de Ruta (CR) — `apps/bustrax/cr.py`
- Se toman viajes de `get_trips_eta` con `shift=="IN"`, `route_type=="N"`, `status in (5,6,7,8)`.
- Filtro de viaje (`trip_filter="bothdone"`): `start_status=="done"` y `end_status=="done"`.
- `found` por parada (criterio default `"done+etaTS"`): `status=="done"` y `etaTS` presente.
- Por ruta: `stopquality`/`routequality = found / total * 100` (promedio de paradas).
- CR del cliente = **promedio simple** sobre sus rutas IN/N con datos.
- **Dos ventanas** (`window_mode`): `14d` = `[domingo-7d, sábado]` (replica la ventana de 14 días
  de la plataforma, default) y `7d` = `[domingo, sábado]`.
- Calibración conocida (SCHNEIDER S6 2026): CR 14d ≈ 97.14, 7d ≈ 97.17 vs histórico 97.44.
- **Caveat**: hay rutas donde el ETA sobrecuenta (ej. seq 142 real 91 vs API ~99). Para eso
  existe el **refinamiento GPS** (`apps/bustrax/gps.py`), **cableado** en `sync_semana`:
  - Se configura en el admin con `RefinamientoRuta` (grupo + `ruta_seq`).
  - Criterio por defecto **200 m** (oficial de Bustrax: `tracker/eta/eta.php:780`, `$md = 200`,
    `found = smin < md`), parametrizable por ruta.
  - Calcula ambas ventanas (`14d` y `7d`) y guarda `CRRutaSemana.source="gps"`.
  - `CRClienteSemana` se recalcula mezclando API+GPS (`source="mixto"`).
  - Puntos GPS cacheados en BD (`GpsPunto`). Prueba: `manage.py refinar_gps 2026 6 --grupo SCN-SCHNEIDER --ruta 142`.
  - Resultado observado 142: `7d=98.99`, `14d=85.35` (real 91) — Traffilog difiere del `his` interno de Bustrax.

### 5.2 Nivel de Servicio (NS) y Viajes — `apps/bustrax/ns.py`
Fórmulas (validadas contra Excel del cliente):
```
entrada  = Tipo de Viaje=="N" y shift=="IN" y Estado!="Cancelado" y grupo no excluido
DIF_LLEG = (end_eta - end_time) en minutos
VAL_RET  = entrada y record_quality==1 y 4 < DIF_LLEG < 1300
%NS      = (entradas - retrasos) / entradas * 100
total    = nº de filas del cliente en la semana
```
Exclusiones de denominador: grupos `GRUPO VIAJES ESPECIALES*` y `TVM-TELVISTA MEXICALI`.

---

## 6. Modelos y auth (`apps/core`)

- `BusinessUnit` (code, nombre), `Cliente` (nombre base), `GrupoCliente` (group exacto→cliente/bunit).
- `Semana` (year, week, inicio, fin), `ViajeSemana` (total, entradas, retrasos, ns).
- `CRRutaSemana` (grupo, ruta_seq, shift, route_type, window_mode, calidad, servicios, source).
- `CRClienteSemana` (cliente, semana, window_mode, calidad, rutas, source).
- `MaeRuta`, `GpsPunto`, `SyncLog`.
- **Scope**: `PerfilUsuario` (OneToOne User) con M2M `clientes` y `es_admin`.
  `apps/core/scoping.get_clientes_for_user()`; middleware `ScopeMiddleware` pone
  `request.scope_clientes`/`request.scope_es_admin`.

Regla de **nombre base de cliente** (`cr.client_base`): `"SCN-SCHNEIDER"` → `"SCHNEIDER"`;
`"STG-STRYKER GF"`/`"STP-STRYKER P1"` → `"STRYKER"`.

---

## 7. Sincronización

- Servicio: `apps/sync/services.py::sync_semana(year, week, bunits, force)`.
  Descarga `get_trips_eta` (14d) + `rid5`, calcula y guarda CR 14d/7d y viajes/NS.
- Comandos:
  ```
  python manage.py sync_semana 2026 6 --bunit set_tj2
  python manage.py backfill 2026 [--desde 1 --hasta 36] [--bunit set_tj2]
  python manage.py seed_bustrax --bunit set_tj2
  ```
- En prod: tareas Celery (`apps/sync/tasks.py`) + **beat diario 05:00** (America/Tijuana) con
  `tarea_sync_semana_actual` (`CELERY_BEAT_SCHEDULE` en `config/settings.py`).
- El `web` corre `migrate` al arrancar (`deploy/entrypoint.sh` + `ENTRYPOINT` en `Dockerfile`).
- UDN por defecto si no hay ninguna en BD: `set_tj2`. (Actualmente **solo se sincroniza set_tj2**.)

---

## 8. Secretos y configuración

- **Nunca** subir credenciales. Se leen de `.env` (ignorado). Plantilla: `.env.example` (con placeholders).
- Variables: `SECRET_KEY`, `DEBUG`, `ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS`,
  `POSTGRES_*`, `EMAIL_*`, `BUSTRAX_*` (iuser/tokens/vers), `TRAFFILOG_*`, `CR_WINDOW_DEFAULT`.
- `DJANGO_ENV=dev|prod` decide SQLite/Postgres, email consola/SMTP, etc.

---

## 9. Legacy (no incluido en el repo)

El primer intento fue una app **Flask** (movida a `legacy_flask/`, **ignorada** por git porque
contenía tokens hardcodeados). Lo útil ya fue portado a `apps/bustrax/`:
- `gps.py` ← cliente Traffilog (`login`, `trips_for_license`, `trip_locations`, `day_points`) y
  reconstrucción de paradas por proximidad GPS (haversine, UTC→America/Tijuana, día local = UTC d y d+1).
- `cr.py` / `ns.py` ← lógica de CR y NS.
No reescribir desde cero: revisar `apps/bustrax/` primero.

---

## 10. Deploy

- `Dockerfile` + `docker-compose.yml` (web, db Postgres, redis, worker, beat).
- `deploy/nginx-proxy-manager.md` para el dominio en Nginx Proxy Manager (HTTPS).
- Prod: `DJANGO_ENV=prod`, `DEBUG=False`, `ALLOWED_HOSTS`/`CSRF_TRUSTED_ORIGINS` con el dominio.

---

## 11. Pendientes / caveats

1. **Calibrar GPS por ruta**: el criterio es 200 m; en la 142 el `14d` da 85.35 vs 91 real
   (Traffilog ≠ `his` interno de Bustrax). Ajustar `tol_m`/ventana por ruta si hace falta.
2. Asignar **scope** a usuarios-cliente en el admin.
3. Sincronizar **otras UDN** (hoy solo `set_tj2`).
4. Score de Seguridad (otra API) pendiente.
5. Rotar tokens (estuvieron en texto plano en el legacy local).

---

## 12. Seguridad / continuidad del token (2026-10)

Contexto operativo:
- **w2 = la plataforma web** de Bustrax para SETTEPI. Por un incidente de seguridad se
  dieron de baja permisos de w2; el **login web de la cuenta LOGMIKE quedó bloqueado** y
  sólo se restablecerán las cuentas MAE que Yasmín solicite. **No habrá cuenta nueva.**
- El portal **NO usa la web**: usa la **API** (`api.bustrax.io`) con el token `bttkn` de
  `LOGMIKE_TJ2`. Verificado en vivo (2026-10-09): `get_groups`, `get_trips_eta`, MAE
  (`get_routes_full_with_stops_history`) y `rid=5` responden **200** → **no afectados**.

Por qué seguimos dentro:
- El permiso de **web** es distinto del **token de API**. `validToken()`
  (`tracker/eta/updates/updates.php:1082`) valida sólo:
  `token['user'] == user` y `strtotime(token['date']) > token_datetime` (usuario con `status=1`).
  **No consulta permisos de w2.**
- Los tokens **no expiran por tiempo**; viven hasta que se **regeneran** o se **desactiva**
  el usuario. (Ojo: `validateToken()` con 60 s es OTRO flujo, no el de la API.)

Riesgo:
- Si **desactivan la cuenta** o **regeneran el token**, la API deja de responder y no habrá
  reemplazo. Los datos ya sincronizados quedan en la BD; se rompería sólo la actualización.

Mitigaciones (plan):
1. **Blindar el histórico mientras el token vive**: backfill de años previos + **export/backup**
   de la BD.
2. **Robustez**: detectar auth fallida en `sync` (respuesta vacía/denegada) → `SyncLog` +
   **banner** en el dashboard; comando `manage.py check_tokens` (pendiente).
3. **Fuente alterna**: **Traffilog (GPS) es independiente** de Bustrax → el CR por GPS
   seguiría funcionando; viajes/NS base sí dependen de Bustrax (plan B: aproximar desde GPS).
4. **Nunca** subir tokens al repo (`.env` está ignorado; `.env.example` con placeholders).
