"""Viajes y Nivel de Servicio (NS Llegada) desde el reporte rid=5.

Fórmulas (validadas contra el Excel del cliente):
  entrada   = Tipo de Viaje == "N", shift == "IN", Estado != "Cancelado", grupo no excluido
  DIF_LLEG  = (end_eta - end_time) en minutos
  VAL_RET   = entrada y record_quality == 1 y 4 < DIF_LLEG < 1300
  %NS       = (entradas - retrasos) / entradas * 100
"""

from collections import defaultdict

from .cr import client_base

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
