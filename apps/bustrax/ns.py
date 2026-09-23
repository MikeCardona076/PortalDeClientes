"""Viajes y Nivel de Servicio (NS Llegada) desde el reporte rid=5.

Fórmulas (validadas contra el Excel del cliente):
  entrada   = Tipo de Viaje == "N", shift == "IN", Estado != "Cancelado", grupo no excluido
  DIF_LLEG  = (end_eta - end_time) en minutos
  VAL_RET   = entrada y record_quality == 1 y 4 < DIF_LLEG < 1300
  %NS       = (entradas - retrasos) / entradas * 100
"""

from collections import defaultdict
from datetime import date, time

from .cr import client_base, route_seq_from_service_id

EXCLUIDOS_EXACTOS = {
    "GRUPO VIAJES ESPECIALES - set_tj2",
    "GRUPO VIAJES ESPECIALES - set_tj1",
    "GRUPO VIAJES ESPECIALES - set_mxl",
    "GRUPO VIAJES ESPECIALES - set_cab",
    "GRUPO VIAJES ESPECIALES - set_qui",
    "TVM-TELVISTA MEXICALI",
}
EXCLUIDOS_PREFIJO = ("GRUPO VIAJES ESPECIALES",)
RETRASO_MIN = 4
RETRASO_MAX = 1300


def _time_minutes(value):
    if not value:
        return None
    s = str(value).strip()
    if s in ("00:00:00", "00:00"):
        return 0
    try:
        parts = s.split(":")
        return int(parts[0]) * 60 + int(parts[1]) + (int(parts[2]) / 60.0 if len(parts) > 2 else 0)
    except (ValueError, IndexError):
        return None


def dif_llegada(row):
    eta = row.get("end_eta")
    tme = row.get("end_time")
    m_eta = _time_minutes(eta)
    m_tme = _time_minutes(tme)
    if m_eta is None or m_tme is None:
        return 0
    if eta and str(eta).strip() == "00:00:00":
        return 0
    return m_eta - m_tme


def _parse_date(value):
    s = str(value or "").strip()[:10]
    if not s:
        return None
    try:
        return date.fromisoformat(s)
    except ValueError:
        return None


def _parse_time(value):
    s = str(value or "").strip()
    if not s:
        return None
    parts = s.split(":")
    try:
        return time(
            int(parts[0]),
            int(parts[1]),
            int(parts[2]) if len(parts) > 2 else 0,
        )
    except (ValueError, TypeError, IndexError):
        return None


def minutes_diff(real_value, prog_value):
    """Minutos de diferencia (real - programado), con ajuste de medianoche."""
    real = _parse_time(real_value)
    prog = _parse_time(prog_value)
    if real is None or prog is None:
        return None
    d = (real.hour * 60 + real.minute) - (prog.hour * 60 + prog.minute)
    if d > 720:
        d -= 1440
    elif d < -720:
        d += 1440
    return int(d)


def normalize_service(row):
    """Normaliza una fila de rid=5 para guardarla como detalle.

    En la API, `time` es el programado y `eta` el real.
    """
    tipo = str(row.get("Tipo de Viaje") or "").strip()
    shift = str(row.get("shift") or "").strip().upper()
    status = str(row.get("status") or "").strip()
    estado = str(row.get("Estado de Viaje") or "").strip()
    group = str(row.get("group") or "").strip()
    recq = row.get("record_quality")
    cancelado = (estado == "Cancelado") or (status == "9")

    _, entrada, retraso = trip_flags(row)
    dif_ini = minutes_diff(row.get("start_eta"), row.get("start_time"))
    dif_fin = minutes_diff(row.get("end_eta"), row.get("end_time"))
    if dif_ini is None:
        diag_ini = ""
    elif RETRASO_MIN < dif_ini < RETRASO_MAX:
        diag_ini = "Retrasado"
    else:
        diag_ini = "A tiempo"

    ruta_seq = str(row.get("ID Ruta") or "").strip()
    if not ruta_seq:
        ruta_seq = route_seq_from_service_id(row.get("id_servicio") or "") or ""

    return {
        "grupo": group,
        "external_id": str(row.get("id") or "").strip(),
        "service_id": str(row.get("id_servicio") or "").strip(),
        "ruta_seq": ruta_seq,
        "descripcion": str(row.get("des") or "")[:200],
        "fecha_inicio": _parse_date(row.get("start_date")),
        "fecha_fin": _parse_date(row.get("end_date")),
        "car": str(row.get("car") or "").strip(),
        "operador": str(row.get("operador") or "").strip()[:120],
        "nomina": str(row.get("no. de nomina") or "").strip()[:40],
        "prog_ini": _parse_time(row.get("start_time")),
        "real_ini": _parse_time(row.get("start_eta")),
        "dif_ini": dif_ini,
        "prog_fin": _parse_time(row.get("end_time")),
        "real_fin": _parse_time(row.get("end_eta")),
        "dif_fin": dif_fin,
        "diagnostico_inicio": diag_ini,
        "diagnostico_viaje": str(row.get("Diagnostico Viaje") or "")[:80],
        "estado_viaje": estado[:60],
        "status": status[:5],
        "tipo_viaje": tipo[:5],
        "shift": shift[:5],
        "record_quality": "" if recq is None else str(recq).strip()[:5],
        "es_entrada": bool(entrada),
        "es_retraso": bool(retraso),
        "servicio": 1 if (tipo == "N" and shift == "IN" and not cancelado and not _excluido(group)) else 0,
    }


def aggregate_servicios(servicios):
    """Resumen de servicios, entradas, retrasos y NS por (grupo, ruta)."""
    acc = {}
    for s in servicios:
        key = (s["grupo"], s["ruta_seq"])
        b = acc.setdefault(
            key,
            {
                "grupo": s["grupo"],
                "ruta_seq": s["ruta_seq"],
                "descripcion": "",
                "servicios": 0,
                "entradas": 0,
                "retrasos": 0,
            },
        )
        b["servicios"] += s["servicio"]
        b["entradas"] += 1 if s["es_entrada"] else 0
        b["retrasos"] += 1 if s["es_retraso"] else 0
        if not b["descripcion"] and s["descripcion"]:
            b["descripcion"] = s["descripcion"]

    for b in acc.values():
        b["ns"] = (
            round((b["entradas"] - b["retrasos"]) / b["entradas"] * 100, 1)
            if b["entradas"]
            else None
        )
    return acc


def _excluido(group):
    g = str(group or "").strip()
    if not g:
        return True
    if g in EXCLUIDOS_EXACTOS:
        return True
    return any(g.upper().startswith(x.upper()) for x in EXCLUIDOS_PREFIJO)


def trip_flags(row):
    tipo = str(row.get("Tipo de Viaje") or "").strip()
    shift = str(row.get("shift") or "").strip().upper()
    status = str(row.get("status") or "").strip()
    estado = str(row.get("Estado de Viaje") or "").strip()
    group = str(row.get("group") or "").strip()
    recq = row.get("record_quality")

    rq_ok = False
    if recq is not None:
        if isinstance(recq, (int, float)):
            rq_ok = int(recq) == 1
        else:
            rq_ok = str(recq).strip() == "1"

    cancelado = (estado == "Cancelado") or (status == "9")
    completado = status in ("5", "6", "7", "8")
    tipo_estado = 1 if ((status in ("6", "7", "8") and tipo != "VA") or tipo in ("N", "V")) else 0
    retraso_valido = 1 if (shift == "IN" and rq_ok and tipo_estado == 1) else 0
    entrada = 1 if (
        tipo == "N" and shift == "IN" and completado and not cancelado and not _excluido(group)
    ) else 0

    val_ret = 0
    if entrada and retraso_valido:
        d = dif_llegada(row)
        val_ret = 1 if RETRASO_MIN < d < RETRASO_MAX else 0
    total = 1 if (completado and not cancelado) else 0
    return total, entrada, val_ret


def aggregate_rows(rows):
    """Agrega filas rid=5 por cliente base.

    Devuelve dict[cliente] = {total, entradas, retrasos, ns}
    """
    acc = defaultdict(lambda: {"total": 0, "entradas": 0, "retrasos": 0})
    for row in rows or []:
        if not isinstance(row, dict):
            continue
        cliente = client_base(str(row.get("group") or ""))
        if not cliente:
            continue
        t, v, r = trip_flags(row)
        acc[cliente]["total"] += t
        acc[cliente]["entradas"] += v
        acc[cliente]["retrasos"] += r
    out = {}
    for cliente, a in acc.items():
        ns = round((a["entradas"] - a["retrasos"]) / a["entradas"] * 100, 1) if a["entradas"] else None
        out[cliente] = {**a, "ns": ns}
    return out
