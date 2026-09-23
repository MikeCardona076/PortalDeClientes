"""Refinamiento de Calidad de Ruta con GPS (Traffilog).

Se usa para rutas donde el ETA sobrecuenta paradas (p.ej. exige que la unidad
realmente se haya detenido). Devuelve calidad por ruta a partir de los viajes
reales (rid=5) y los puntos GPS de cada unidad.
"""

import json
import math
import threading
import time
from datetime import date, timedelta, timezone
from zoneinfo import ZoneInfo

import requests
from django.conf import settings

from .weeks import week_window


class TraffilogError(Exception):
    pass


class TraffilogClient:
    def __init__(self):
        self.base_url = settings.TRAFFILOG_BASE
        self.username = settings.TRAFFILOG_USERNAME
        self.password = settings.TRAFFILOG_PASSWORD
        self.session_token = None
        self._ts = 0.0

    def _post(self, payload, timeout=60):
        last = None
        for attempt in range(3):
            try:
                resp = requests.post(self.base_url, json=payload, timeout=timeout)
                if resp.status_code in (429, 500, 502, 503, 504):
                    time.sleep(0.5 * (attempt + 1))
                    continue
                resp.raise_for_status()
                return resp.json()
            except requests.RequestException as exc:
                last = exc
                time.sleep(0.5 * (attempt + 1))
        raise TraffilogError(f"Error Traffilog: {last}")

    @staticmethod
    def _data(response):
        return (response or {}).get("response", {}).get("properties", {}).get("data") or []

    def login(self, force=False):
        now = time.time()
        if self.session_token and not force and now - self._ts < 55 * 60:
            return self.session_token
        payload = {
            "action": {
                "name": "user_login",
                "parameters": {"login_name": self.username, "password": self.password},
            }
        }
        data = self._data(self._post(payload, timeout=15))
        if not data or not data[0].get("session_token"):
            raise TraffilogError("Login Traffilog falló.")
        self.session_token = data[0]["session_token"]
        self._ts = now
        return self.session_token

    def trips_for_license(self, license_number, from_date, to_date):
        payload = {
            "action": {
                "name": "get_vehicle_trips_extended",
                "parameters": [
                    {
                        "license_number": str(license_number),
                        "from_date": from_date,
                        "to_date": to_date,
                        "vehicle_id": "",
                        "driver_id": "",
                    }
                ],
                "session_token": self.login(),
            }
        }
        return self._data(self._post(payload)) or []

    def trip_locations(self, drive_id):
        payload = {
            "action": {
                "name": "get_trip_locations",
                "parameters": [{"drive_id": drive_id}],
                "session_token": self.login(),
            }
        }
        return self._data(self._post(payload)) or []

    def day_points(self, license_number, day_iso):
        points = []
        for t in self.trips_for_license(license_number, day_iso, day_iso):
            drive_id = t.get("drive_id")
            if drive_id:
                points.extend(self.trip_locations(drive_id))
        return points


# --------------------------------------------------------------------- geo/tiempo

def haversine_m(lat1, lng1, lat2, lng2):
    r = 6371000.0
    p1, p2 = math.radians(float(lat1)), math.radians(float(lat2))
    dp = math.radians(float(lat2) - float(lat1))
    dl = math.radians(float(lng2) - float(lng1))
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def minutes_of(value):
    if value is None:
        return None
    try:
        p = str(value).strip().split(":")
        return int(p[0]) * 60 + int(p[1]) + (int(p[2]) / 60.0 if len(p) > 2 else 0)
    except (ValueError, IndexError):
        return None


def parse_loc_time(value):
    if not value:
        return None
    s = str(value).replace("%3A", ":").replace("%2B", "+").replace("%20", " ")
    for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S"):
        try:
            from datetime import datetime

            return datetime.strptime(s[:19], fmt)
        except ValueError:
            continue
    return None


def _js(value):
    if isinstance(value, str):
        try:
            return json.loads(value)
        except ValueError:
            return None
    return value


def services_from_trips(route, trips, year, week, start=None, end=None):
    """Servicios reales (fecha, auto, horario) desde los viajes rid=5."""
    stops = _js(route.get("stops")) or []
    if not stops:
        return []
    if start is None or end is None:
        monday, sunday = week_window(year, week)
        if monday is None:
            return []
        start = monday.isoformat()
        end = sunday.isoformat()
    s_start, s_end = start, end
    stop_list = [
        {"index": i, "id": s.get("id"), "des": s.get("des"), "lat": s.get("lat"),
         "lng": s.get("lng"), "sched_min": None}
        for i, s in enumerate(stops) if isinstance(s, dict)
    ]
    seq = str(route.get("sequential_id"))
    rdesc = (route.get("description") or "").strip()
    out = []
    for trip in trips or []:
        if str(trip.get("shift")) != "IN" or str(trip.get("Tipo de Viaje")) != "N":
            continue
        fecha = str(trip.get("start_date") or "")[:10]
        if not (s_start <= fecha <= s_end):
            continue
        tseq = str(trip.get("ID Ruta") or "").strip().lstrip("0")
        tdesc = str(trip.get("des") or "").strip()
        if tseq:
            # Prioridad al número de ruta (ID Ruta) — exacto
            match = bool(seq) and tseq == str(seq).lstrip("0")
        else:
            # Fallback por descripción sólo si no hay ID Ruta
            match = bool(
                rdesc and tdesc
                and (rdesc.upper() == tdesc.upper()
                     or rdesc.upper() in tdesc.upper()
                     or tdesc.upper() in rdesc.upper())
            )
        if not match:
            continue
        out.append({
            "date": fecha,
            "stime": trip.get("start_time"),
            "etime": trip.get("end_time"),
            "car": str(trip.get("car") or "").strip(),
            "stops": stop_list,
        })
    return out


def evaluate_service(service, point_tuples, tol_m, window_min):
    if not point_tuples:
        return [0] * len(service["stops"])
    s_min = minutes_of(service["stime"]) or 0
    e_min = minutes_of(service["etime"]) or s_min + 120
    if e_min < s_min:
        e_min += 24 * 60
    pts = [(m, lat, lng) for (m, lat, lng) in point_tuples if s_min - 10 <= m <= e_min + 10]
    found = [0] * len(service["stops"])
    for i, stop in enumerate(service["stops"]):
        sched = stop["sched_min"] if stop["sched_min"] is not None else (s_min + e_min) / 2
        lo = sched - window_min if window_min is not None else s_min
        hi = sched + window_min if window_min is not None else e_min
        for (m, lat, lng) in pts:
            if lo <= m <= hi and haversine_m(lat, lng, stop["lat"], stop["lng"]) <= tol_m:
                found[i] = 1
                break
    return found


def route_quality_services(services, day_points_fn, tol_m=150, window_min=None):
    total_found = total_stops = 0
    for svc in services:
        points = day_points_fn(svc["car"], svc["date"]) or []
        found = evaluate_service(svc, points, tol_m, window_min)
        total_found += sum(found)
        total_stops += len(found)
    if total_stops == 0:
        return None
    return round(total_found / total_stops * 100, 2)


def local_day_points(client, car, local_date, cache):
    """Puntos GPS de un día local (Traffilog UTC -> America/Tijuana)."""
    tz = ZoneInfo(settings.TRAFFILOG_TZ)
    d = date.fromisoformat(local_date)
    out = []
    for utc_day in (d.isoformat(), (d + timedelta(days=1)).isoformat()):
        key = (car, utc_day)
        if key not in cache:
            cache[key] = client.day_points(car, utc_day) or []
        for loc in cache[key]:
            t = parse_loc_time(loc.get("time"))
            if t is None:
                continue
            try:
                lat = float(loc.get("latitude"))
                lng = float(loc.get("longitude"))
            except (TypeError, ValueError):
                continue
            local = t.replace(tzinfo=timezone.utc).astimezone(tz).replace(tzinfo=None)
            if local.date().isoformat() == local_date:
                out.append((local.hour * 60 + local.minute + local.second / 60.0, lat, lng))
    return out


# --------------------------------------------------------------------- caché BD

def _db_day_points(client, car, utc_day):
    """Puntos crudos de (auto, día UTC), cacheados en la BD (GpsPunto)."""
    from apps.core.models import GpsPunto

    car = str(car)
    obj = GpsPunto.objects.filter(car=car, dia_utc=utc_day).first()
    if obj:
        return obj.puntos or []
    pts = client.day_points(car, utc_day) or []
    GpsPunto.objects.update_or_create(car=car, dia_utc=utc_day, defaults={"puntos": pts})
    return pts


def local_day_points_db(client, car, local_date):
    """Puntos de un día local usando la caché en BD."""
    tz = ZoneInfo(settings.TRAFFILOG_TZ)
    d = date.fromisoformat(local_date)
    out = []
    for utc_day in (d.isoformat(), (d + timedelta(days=1)).isoformat()):
        for loc in _db_day_points(client, car, utc_day):
            t = parse_loc_time(loc.get("time"))
            if t is None:
                continue
            try:
                lat = float(loc.get("latitude"))
                lng = float(loc.get("longitude"))
            except (TypeError, ValueError):
                continue
            local = t.replace(tzinfo=timezone.utc).astimezone(tz).replace(tzinfo=None)
            if local.date().isoformat() == local_date:
                out.append((local.hour * 60 + local.minute + local.second / 60.0, lat, lng))
    return out


def refinar_ruta(route, trips, year, week, tol_m=200, ventana_min=None,
                 client=None, start=None, end=None):
    """Calidad de ruta reconstruida por GPS (criterio plataforma: 200 m).

    route: objeto MAE crudo (con stops).
    trips: filas rid=5 de la semana (o rango).
    Devuelve (calidad | None, n_servicios).
    """
    client = client or TraffilogClient()
    client.login()
    services = services_from_trips(route, trips, year, week, start=start, end=end)
    if not services:
        return None, 0
    quality = route_quality_services(
        services,
        lambda car, d: local_day_points_db(client, car, d),
        tol_m=tol_m,
        window_min=ventana_min,
    )
    return quality, len(services)
