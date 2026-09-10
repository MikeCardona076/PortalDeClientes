"""Cliente HTTP de las APIs Bustrax (solo lectura)."""

import requests
from django.conf import settings

HEADERS = {"Content-Type": "application/x-www-form-urlencoded; charset=UTF-8"}


class BustraxError(Exception):
    pass


def _post(url, data, timeout=None):
    last = None
    for _ in range(3):
        try:
            resp = requests.post(
                url, data=data, headers=HEADERS, timeout=timeout or settings.BUSTRAX_TIMEOUT
            )
            if resp.status_code != 200:
                raise BustraxError(f"HTTP {resp.status_code}")
            return resp
        except requests.RequestException as exc:
            last = exc
    raise BustraxError(f"Error de conexión: {last}")


def _unwrap(data):
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        for key in ("data", "routes", "results", "rows"):
            if isinstance(data.get(key), list):
                return data[key]
    raise BustraxError("Respuesta inesperada (sin lista).")


def _base_payload(**extra):
    payload = {
        "data[iuser]": settings.BUSTRAX_IUSER,
        "data[ver]": settings.BUSTRAX_VER_JSON,
        "data[bttkn]": settings.BUSTRAX_TOKEN_MAE,
    }
    for key, value in extra.items():
        payload[f"data[{key}]"] = value
    return payload


def get_groups(bunit):
    """Lista de grupos de una UDN (id, description, gcode, bunit...)."""
    payload = _base_payload(bunit=bunit)
    payload["type"] = "get_groups"
    return _unwrap(_post(settings.BUSTRAX_URL_JSON, payload).json())


def get_trips_eta(start_date, end_date, bunit=None, gcode=None):
    """Histórico de viajes con ETA y paradas por rango de fechas.

    Acepta `bunit` (toda la UDN) o `gcode` (un grupo/cliente).
    """
    payload = _base_payload(start_date=start_date, end_date=end_date)
    if bunit:
        payload["data[bunit]"] = bunit
    if gcode:
        payload["data[gcode]"] = gcode
    payload["type"] = "get_trips_eta"
    return _unwrap(_post(settings.BUSTRAX_URL_JSON, payload).json())


def fetch_routes(bunit):
    """Rutas maestras con paradas e historial (MAE)."""
    payload = _base_payload(
        bunit=bunit,
        with_stops="true",
        with_daytimes_data="true",
    )
    payload["type"] = "get_routes_full_with_stops_history"
    return _unwrap(_post(settings.BUSTRAX_URL_JSON, payload).json())


def fetch_report(bunit, start_date, end_date, rid="5"):
    """Reporte plano (rid=5 = viajes listado) para NS/viajes."""
    payload = [
        ("type", "get_report_result"),
        ("data[rid]", rid),
        ("data[inputs][]", bunit),
        ("data[inputs][]", start_date),
        ("data[inputs][]", end_date),
        ("data[iuser]", settings.BUSTRAX_IUSER),
        ("data[ver]", settings.BUSTRAX_VER_REPORTS),
        ("data[bttkn]", settings.BUSTRAX_TOKEN_TRIPS),
    ]
    return _unwrap(_post(settings.BUSTRAX_URL_REPORTS, payload).json())
