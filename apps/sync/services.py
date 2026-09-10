"""Servicio de sincronización semanal (viajes, NS y CR 14d/7d)."""

from datetime import timedelta

from django.db import transaction

from apps.bustrax import client as api
from apps.bustrax import cr, ns
from apps.bustrax.weeks import week_window
from apps.core.models import (
    BusinessUnit,
    Cliente,
    CRClienteSemana,
    CRRutaSemana,
    GrupoCliente,
    Semana,
    SyncLog,
    ViajeSemana,
)

# UDN por defecto si aún no hay ninguna registrada en el admin.
DEFAULT_BUNITS = ["set_tj2"]


def _bunits(bunits):
    if bunits:
        return bunits
    activas = list(BusinessUnit.objects.filter(activa=True).values_list("code", flat=True))
    return activas or DEFAULT_BUNITS


def _semana(year, week):
    sunday, saturday = week_window(year, week)
    if sunday is None:
        raise ValueError(f"Semana inválida: {year}-W{week}")
    obj, _ = Semana.objects.get_or_create(
        year=year, week=week, defaults={"inicio": sunday, "fin": saturday}
    )
    return obj, sunday, saturday


def _cliente(nombre):
    obj, _ = Cliente.objects.get_or_create(nombre=nombre)
    return obj


def _grupo(group, gcode="", bunit_code=""):
    base = cr.client_base(group)
    cliente = _cliente(base)
    bu = None
    if bunit_code:
        bu, _ = BusinessUnit.objects.get_or_create(
            code=bunit_code, defaults={"nombre": bunit_code}
        )
    grupo, _ = GrupoCliente.objects.update_or_create(
        group=group,
        defaults={"cliente": cliente, "gcode": gcode, "business_unit": bu},
    )
    return grupo


def _store_cr(semana_obj, bunit_code, stats, window_mode):
    """Guarda CR por ruta y agrega por cliente."""
    aggs = cr.aggregate_clients(stats)
    for (group, ruta_seq), b in stats.items():
        if b["calidad"] is None:
            continue
        grupo = _grupo(group, bunit_code=bunit_code)
        CRRutaSemana.objects.update_or_create(
            grupo=grupo,
            semana=semana_obj,
            ruta_seq=ruta_seq,
            window_mode=window_mode,
            defaults={
                "descripcion": b["descripcion"],
                "shift": b["shift"],
                "route_type": b["route_type"],
                "calidad": b["calidad"],
                "servicios": b["servicios"],
                "source": "api",
            },
        )
    for cliente_base, data in aggs.items():
        cliente = _cliente(cliente_base)
        CRClienteSemana.objects.update_or_create(
            cliente=cliente,
            semana=semana_obj,
            window_mode=window_mode,
            defaults={
                "calidad": data["calidad"],
                "rutas": data["rutas"],
                "source": "api",
            },
        )
    return len(aggs)


@transaction.atomic
def sync_semana(year, week, bunits=None, force=False):
    """Sincroniza una semana operativa (domingo-sábado) para las UDN indicadas."""
    semana_obj, sunday, saturday = _semana(year, week)
    start14 = (sunday - timedelta(days=7)).isoformat()
    end = saturday.isoformat()

    resumen = {"year": year, "week": week, "bunits": [], "clientes_cr": 0, "clientes_ns": 0}

    for bu in _bunits(bunits):
        try:
            trips = api.get_trips_eta(start14, end, bunit=bu)
        except api.BustraxError as exc:
            SyncLog.objects.create(
                proceso="cr", year=year, week=week, estado="error", mensaje=f"{bu}: {exc}"
            )
            resumen["bunits"].append({"bunit": bu, "error": str(exc)})
            continue

        stats14 = cr.route_stats(trips)
        trips7 = [
            t for t in trips if sunday.isoformat() <= str(t.get("start_date") or "")[:10] <= end
        ]
        stats7 = cr.route_stats(trips7)

        n14 = _store_cr(semana_obj, bu, stats14, "14d")
        n7 = _store_cr(semana_obj, bu, stats7, "7d")
        resumen["clientes_cr"] = max(resumen["clientes_cr"], n14, n7)

        # Viajes / NS (rid=5) de la semana exacta
        try:
            rows = api.fetch_report(bu, sunday.isoformat(), end)
            agg = ns.aggregate_rows(rows)
            for cliente_base, data in agg.items():
                cliente = _cliente(cliente_base)
                ViajeSemana.objects.update_or_create(
                    cliente=cliente,
                    semana=semana_obj,
                    defaults={
                        "total": data["total"],
                        "entradas": data["entradas"],
                        "retrasos": data["retrasos"],
                        "ns": data["ns"],
                    },
                )
            resumen["clientes_ns"] = max(resumen["clientes_ns"], len(agg))
        except api.BustraxError as exc:
            SyncLog.objects.create(
                proceso="ns", year=year, week=week, estado="parcial", mensaje=f"{bu}: {exc}"
            )

        resumen["bunits"].append(
            {"bunit": bu, "trips": len(trips), "rutas14": len(stats14), "rutas7": len(stats7)}
        )

    SyncLog.objects.create(
        proceso="sync_semana",
        year=year,
        week=week,
        estado="ok",
        mensaje=str(resumen["bunits"]),
    )
    return resumen


def backfill(year, week_from=1, week_to=None, bunits=None):
    from apps.bustrax.weeks import current_week, weeks_of_year

    if week_to is None:
        week_to = current_week()[1] if year == current_week()[0] else max(weeks_of_year(year))
    results = []
    for week in range(week_from, week_to + 1):
        results.append(sync_semana(year, week, bunits=bunits))
    return results
