# Análisis: Calidad de Ruta (%CR) en CLIENTESD

_Estado al 2026-09-09 · Foco: Tijuana 2 (set_tj2), resto de UDN desactivadas a propósito._

---

## 1. Resumen ejecutivo

El dashboard CLIENTESD muestra 3 métricas por cliente y semana: **Total de Viajes**,
**Nivel de Servicio (NS)** y **Calidad de Ruta (CR)**. Las dos primeras salen bien de la
API de viajes (`rid=5`) y varían por semana. **La Calidad de Ruta es el punto débil**:

- Hoy la app usa un **CR "vigente" (snapshot)** calculado con la API MAE
  (`get_routes_full_with_stops_history`) + el algoritmo de la plataforma.
- Ese valor **no es por semana**: la API MAE no acepta filtros de fecha (probado en vivo)
  y su `stops_history` sólo refleja el historial **reciente/actual**.
- Tu histórico por semana (p. ej. SCHNEIDER S6 = **97.44%** y rutas 91/98/99/100%)
  sale de **exportar el MAE en esa semana**, no de una consulta histórica.
- Conclusión: para tener CR **por semana retroactivo** hay que **reconstruirlo con GPS
  (Traffilog)**, que sí guarda histórico por día. Validado: el método reproduce el CR en el
  rango correcto; falta **calibrar el umbral exacto** (distancia/ventana).

---

## 2. El origen de la confusión ("CR cambia por semana")

Viendo SCHNEIDER · Semana 6 se observaron 3 números distintos:

| Dónde | Valor | Qué es |
|---|---|---|
| Heatmap (modo CR) | 99 | CR snapshot redondeado a entero |
| Drill `/cliente` (KPI CR) | 98.8 | Mismo snapshot con 1 decimal |
| "Histórico" (export MAE S6) | 97.44 | CR real de esa semana (otra fuente) |

Los dos primeros son el **mismo dato** (snapshot = 98.8) mostrado con distinto redondeo.
El tercero es el CR **real de la semana**, que la app aún no puede producir sola.

---

## 3. Cómo funciona hoy la CR en la app

Flujo actual (módulos de CLIENTESD):

1. `bustrax.fetch_routes_cached("set_tj2")` → rutas MAE crudas (paradas + historial).
2. `calidad.process_mae()` → port Python del algoritmo JS de la plataforma:
   - se ignoran rutas `status == 9`;
   - `shift IN→E / OUT→S`, sólo importan `route_type == "N"` con shift `IN`;
   - `stops`, `daytimes` y `stops_history` se parsean como JSON;
   - por parada: `stopquality = foundInHistoryCount / historySize × 100`
     (found = nº de servicios del historial donde esa parada tiene `f != 0`);
   - por ruta: `routequality` = promedio de `stopquality` (tipo `V`: suma/2);
   - sin historial → "N/A".
3. `metrics.calidad_by_client()` → promedio de `routequality` sobre rutas IN/N del cliente.
   - Ej. SCHNEIDER = **98.8** (41 rutas IN/N con datos), STRYKER = **99.5** (25 rutas).
4. Ese valor es **único por cliente** y se pinta igual en todas las semanas del heatmap
   (con nota "CR vigente") y en el KPI/gauge del drill.

**Limitación**: no hay dimensión temporal. Probado en vivo que pasar fechas
(`start_date/end_date`, `sdate/edate`, `from/to`) al endpoint MAE **no cambia nada**:
la ruta 45 de STRYKER devolvió exactamente el mismo `stops_history` (24 servicios) incluso
pidiendo enero 2026. La API sólo da "lo reciente".

---

## 4. El camino GPS (Traffilog) para CR semanal real

Para recalcular una semana pasada hay que saber, para cada servicio de esa semana,
**con qué unidad y a qué hora** corrió la ruta y **si pasó por cada parada**. Eso se
reconstruye con Traffilog (`get_vehicle_trips_extended` + `get_trip_locations`).

### 4.1 Hallazgos técnicos clave (validados en vivo)

| Hallazgo | Detalle |
|---|---|
| **seq ↔ ID Ruta del export** | `sequential_id` del MAE = número del "ID Ruta" del export: `seq 143` ↔ `E-SCN-N0143`, `142`↔`N0142`, `145`↔`N0145`, etc. |
| **car ↔ license Traffilog** | El `car` del MAE es el `license_number` de Traffilog (`12439`, `13473`, …), con `vehicle_id` y grupo `SCN-SCHNEIDER`. |
| **Traffilog está en UTC** | La mañana local (05:10 Tijuana) aparece ~13:00 UTC y la tarde (16:50) ~00:50 UTC del día siguiente. |
| **Día local = UTC d + d+1** | Para cubrir un día local hay que unir los puntos de dos días UTC y convertir a `America/Tijuana`. |
| **La asignación de autos cambia** | El MAE describe la ruta **hoy**; en la semana 6 la ruta `0142` corrió con el auto **8815** (no el `13574` actual) y la `0147` con **13036** (no `11030`). |
| **Los viajes reales vienen del rid=5** | Por eso los servicios de la semana se toman del reporte `rid=5` (fecha, auto, `start_time`/`end_time` reales), no del calendario actual del MAE. |

### 4.2 Resultados de validación (SCHNEIDER · Semana 6)

| Ruta | %CR real (export) | GPS (método) | Comentario |
|---|---|---|---|
| 145 (4TA SECCIÓN-RES. DEL BOSQUE) | 100 | **100** | exacto con tol ≥100 m, ventana completa |
| 147 (ALTIPLANO1) | 100 | **100** | con viajes reales (auto 13036) |
| 146 (5 Y 10-MÓDULOS) | 99 | **100** | 1 punto de diferencia |
| 143 (10 DE MAYO-INSURGENTES) | 98 | **96.6** (tol 150 m, ventana completa) | margen ~1.4 pts |
| 142 (10 DE MAYO-TUNEL-GRANJAS) | 91 | **98.99** | con viajes reales (auto 8815); **+8 pts** → calibración pendiente |

El método **reproduce el orden de magnitud y acierta en la mayoría**; la diferencia
residual (p. ej. 142) indica que el umbral exacto de la plataforma (distancia/ventana y/o
segmentación de servicios) aún no está clavado.

### 4.3 Parámetros actuales (por calibrar)

- `TOL_M = 150` m
- `WINDOW_MIN = None` (usa todo el rango del viaje)

Barrido pendiente sobre tol (40–200 m) × ventana (ninguna/5/10/15/20 min) contra las rutas
oráculo `142:91, 143:98, 145:100, 146:99, 147:100, 148:100, 149:100`.

---

## 5. Módulos/scripts creados en CLIENTESD

| Archivo | Rol |
|---|---|
| `app.py`, `templates/` | Vista heatmap + drill (CR snapshot hoy) |
| `bustrax.py` | Cliente API Bustrax (viajes `rid=5`, rutas MAE) con caché a disco |
| `calidad.py` | Algoritmo `routequality/stopquality` (port del JS de la plataforma) |
| `metrics.py` | Semana domingo–sábado, NS Llegada, agregación por cliente, caché por semana |
| `traffilog.py` | Cliente Traffilog (login, viajes, `get_trip_locations`) |
| `gps_calidad.py` | Geo/hora, servicios de una ruta, detección de paradas por GPS |
| `cr_gps.py` | CR por ruta/cliente-semana desde GPS usando **viajes reales rid=5** (+ caché a disco de puntos GPS) |
| `cr_gps_validate.py` | Barrido simple de parámetros (una ruta) |
| `cr_calibrate.py` | Barrido tol × ventana contra las 7 rutas-oráculo (**pendiente de terminar**) |

---

## 6. Costo / performance (importante)

- Descargar los puntos GPS de **un día-unidad** cuesta ~8–20 s (varios viajes → ubicaciones).
- Una ruta/semana ≈ 7–8 días × 1 auto ≈ **1.5–2.5 min** (ya con caché a disco en `data_cache/gps_pts_*`).
- SCHNEIDER completo (≈41 rutas IN/N) ≈ **1 hora por semana** la primera vez; después usa caché.
- Para producción hace falta: **backfill por semana en segundo plano** (thread + caché) y
  exponer el CR-GPS calculado en matriz/drill por `(cliente, semana)`.

---

## 7. Qué falta / decisiones abiertas

1. **Terminar la calibración** (`cr_calibrate.py`): elegir `(tol_m, window_min)` que minimice
   el error frente a las 7 rutas-oráculo (y ampliar oráculo con más rutas si es posible).
2. **Mapeo ruta↔unidad por semana vía rid=5** ya resuelto; validar con más clientes/semanas.
3. **Integrar CR semanal en la UI**: matriz y drill usarían la tabla `(cliente, semana)`
   calculada por GPS; el snapshot MAE quedaría sólo como respaldo si no hay datos GPS de una
   semana. Decidir etiquetado ("CR GPS") y nota en la UI.
4. Definir **caché/backfill** (semana vigente se refresca, históricas se calculan una vez).
5. Confirmar definición exacta de negocio de "parada visitada" si la plataforma lo permite
   (distancia y ventana), o dejar la calibración empírica como autoridad.

---

## 8. Recomendación

Seguir el camino **GPS-Traffilog con servicios reales del rid=5**, porque es la única forma
de obtener CR **retroactivo por semana** (validado funcionalmente). El siguiente paso
concreto es terminar el barrido de calibración de `cr_calibrate.py` (la corrida anterior se
interrumpió) y, con el umbral fijado, construir la tabla semanal cacheada e integrarla a la
matriz/drill.
