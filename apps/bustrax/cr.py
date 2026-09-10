"""Cálculo de Calidad de Ruta (%CR) a partir de get_trips_eta.

Reconstruye el MAE por rango de fechas (14d o 7d) usando las paradas y su
`stops_eta` (status + etaTS). El denominador son los viajes válidos IN/N.
"""

import json
import re
from collections import defaultdict

VARIANT_SUFFIX = {"GF", "P", "MXL", "TJ", "T1", "T2", "PL1", "PL2", "PL3", "PL4", "PL5"}


def P(value):
    """Parsea un campo que puede venir como string JSON."""
    if isinstance(value, str):
        try:
            return json.loads(value)
        except ValueError:
            return value
    return value


def client_base(group):
    """Nombre base del cliente: 'SCN-SCHNEIDER' -> 'SCHNEIDER'."""
    if not group:
        return ""
    s = str(group).strip()
    up = s.upper()
    if "GRUPO VIAJES ESPECIALES" in up or "VIAJES AUTORIZADOS" in up:
        return "VIAJES ESPECIALES"
    _, sep, name = s.partition("-")
    name = name.strip()
    if not sep:
        return s
    tokens = name.split()
    while tokens:
        t = tokens[-1].upper()
        if t in VARIANT_SUFFIX or re.fullmatch(r"P\d+", t):
            tokens.pop()
        else:
            break
    return " ".join(tokens) if tokens else name


def route_seq_from_service_id(service_id):
    """'E-SCN-T1-R0179' -> '0179' (sequential_id)."""
    m = re.search(r"[A-Z](\d+)$", service_id or "")
    return m.group(1) if m else None


def _is_found(entry, criterio):
    e = P(entry)
    if not isinstance(e, dict):
        return False
    status = str(e.get("status") or "")
    has_ts = bool(e.get("etaTS"))
    if criterio == "etaTS":
        return has_ts
    if criterio == "done":
        return status == "done"
    # default "done+etaTS"
    return status == "done" and has_ts


def route_stats(trips, criterio="done+etaTS", trip_filter="bothdone", solo_primera=False):
    """Agrupa viajes por (grupo, ruta) y calcula calidad por ruta.

    Devuelve dict[(group, ruta_seq)] = {
        group, ruta_seq, descripcion, shift, route_type,
        found, total, servicios, calidad
    }
    """
    stats = {}

    def bucket(group, ruta_seq):
        key = (group, ruta_seq)
        if key not in stats:
            stats[key] = {
                "group": group,
                "ruta_seq": ruta_seq,
                "descripcion": "",
                "shift": "IN",
                "route_type": "N",
                "found": 0,
                "total": 0,
                "servicios": 0,
            }
        return stats[key]

    for t in trips or []:
        if str(t.get("shift")) != "IN" or str(t.get("route_type")) != "N":
            continue
        if str(t.get("status")) not in ("5", "6", "7", "8"):
            continue
        if trip_filter == "bothdone" and not (
            str(t.get("start_status")) == "done" and str(t.get("end_status")) == "done"
        ):
            continue
        group = str(t.get("group") or "").strip()
        ruta = route_seq_from_service_id(t.get("service_id"))
        if not group or not ruta:
            continue
        stops = P(t.get("stops")) or []
        stops_eta = P(t.get("stops_eta")) or []
        if not isinstance(stops, list) or not isinstance(stops_eta, list):
            continue
        n = min(len(stops), len(stops_eta))
        if n == 0:
            continue
        b = bucket(group, ruta)
        b["descripcion"] = b["descripcion"] or str(t.get("des") or "")[:200]
        b["servicios"] += 1
        indices = [0] if solo_primera else range(n)
        for i in indices:
            b["total"] += 1
            if _is_found(stops_eta[i], criterio):
                b["found"] += 1

    for b in stats.values():
        b["calidad"] = round(b["found"] / b["total"] * 100, 2) if b["total"] else None
    return stats


def aggregate_clients(stats):
    """Agrega route_stats por cliente base.

    Devuelve dict[cliente] = {calidad, rutas, detalle: [route_stats...]}
    """
    by_client = defaultdict(list)
    for b in stats.values():
        by_client[client_base(b["group"])].append(b)
    out = {}
    for cliente, rutas in by_client.items():
        con_datos = [r for r in rutas if r["calidad"] is not None]
        if con_datos:
            calidad = round(sum(r["calidad"] for r in con_datos) / len(con_datos), 2)
        else:
            calidad = None
        out[cliente] = {
            "calidad": calidad,
            "rutas": len(con_datos),
            "detalle": sorted(con_datos, key=lambda r: r["ruta_seq"]),
        }
    return out
