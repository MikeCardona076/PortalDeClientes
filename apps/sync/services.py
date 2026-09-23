"""Servicio de sincronización semanal (viajes, NS y CR 14d/7d)."""

from datetime import timedelta

from django.db import transaction

from apps.bustrax import client as api
from apps.bustrax import cr, gps, ns
from apps.bustrax.weeks import week_window
from apps.core.models import (
    BusinessUnit,
    Cliente,
    CRClienteSemana,
    CRRutaSemana,
    GrupoCliente,
    RefinamientoRuta,
    RutaIndicadoresSemana,
    Semana,
    ServicioRutaSemana,
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
    monday, sunday = week_window(year, week)
    if monday is None:
        raise ValueError(f"Semana inválida: {year}-W{week}")
    obj, _ = Semana.objects.update_or_create(
        year=year, week=week, defaults={"inicio": monday, "fin": sunday}
    )
    return obj, monday, sunday


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


def _recompute_cliente_cr(semana_obj, window_mode):
    """Recalcula CRClienteSemana promediando CRRutaSemana (API y/o GPS)."""
    from collections import defaultdict

    filas = CRRutaSemana.objects.filter(
        semana=semana_obj, window_mode=window_mode
    ).select_related("grupo")
    agg = defaultdict(list)
    hay_gps = False
    for f in filas:
        if f.calidad is None:
            continue
        agg[f.grupo.cliente_id].append(f.calidad)
        if f.source == "gps":
            hay_gps = True
    for cliente_id, vals in agg.items():
        source = "mixto" if hay_gps else "api"
        CRClienteSemana.objects.update_or_create(
            cliente_id=cliente_id,
            semana=semana_obj,
            window_mode=window_mode,
            defaults={
                "calidad": round(sum(vals) / len(vals), 2),
                "rutas": len(vals),
                "source": source,
            },
        )


def _aplicar_refinamientos(semana_obj, bu, trips, rows, year, week, monday, start14, end):
    """Aplica GPS a las rutas marcadas en RefinamientoRuta (14d y 7d)."""
    refs = list(
        RefinamientoRuta.objects.filter(
            activo=True, grupo__business_unit__code=bu
        ).select_related("grupo")
    )
    if not refs:
        return 0
    try:
        mae_routes = api.fetch_routes(bu)
    except api.BustraxError as exc:
        SyncLog.objects.create(
            proceso="gps", year=year, week=week, estado="parcial",
            mensaje=f"{bu}: MAE no disponible ({exc})",
        )
        return 0

    idx = {
        str(r.get("sequential_id")): r
        for r in mae_routes
        if str(r.get("shift")) == "IN" and str(r.get("route_type")) == "N"
    }

    # Viajes rid5 del rango de 14 días (para la ventana 14d)
    try:
        rows14 = api.fetch_report(bu, start14, end)
    except api.BustraxError:
        rows14 = rows

    client = gps.TraffilogClient()
    hechos = 0
    for ref in refs:
        route = idx.get(str(ref.ruta_seq))
        if not route:
            continue
        for mode, trips_src, ini in (
            ("7d", rows, monday.isoformat()),
            ("14d", rows14, start14),
        ):
            calidad, _ = gps.refinar_ruta(
                route, trips_src, year, week,
                tol_m=ref.tol_m, ventana_min=ref.ventana_min,
                client=client, start=ini, end=end,
            )
            if calidad is None:
                continue
            CRRutaSemana.objects.update_or_create(
                grupo=ref.grupo,
                semana=semana_obj,
                ruta_seq=ref.ruta_seq,
                window_mode=mode,
                defaults={"calidad": calidad, "source": "gps"},
            )
        hechos += 1
    return hechos


def _sync_servicios(semana_obj, bunit_code, rows):
    """Persiste los servicios de rid=5 y recalcula indicadores por ruta."""
    bu, _ = BusinessUnit.objects.get_or_create(
        code=bunit_code, defaults={"nombre": bunit_code}
    )
    servicios = [
        ns.normalize_service(r) for r in (rows or []) if isinstance(r, dict)
    ]
    servicios = [s for s in servicios if s["external_id"]]
    ids = {s["external_id"] for s in servicios}

    ServicioRutaSemana.objects.filter(
        business_unit=bu, semana=semana_obj
    ).exclude(external_id__in=ids).delete()

    group_cache = {}

    def get_grupo(group):
        if group not in group_cache:
            group_cache[group] = _grupo(group, bunit_code=bunit_code)
        return group_cache[group]

    for s in servicios:
        ServicioRutaSemana.objects.update_or_create(
            business_unit=bu,
            semana=semana_obj,
            external_id=s["external_id"],
            defaults={
                "grupo": get_grupo(s["grupo"]),
                "service_id": s["service_id"],
                "ruta_seq": s["ruta_seq"],
                "descripcion": s["descripcion"],
                "fecha_inicio": s["fecha_inicio"],
                "fecha_fin": s["fecha_fin"],
                "car": s["car"],
                "operador": s["operador"],
                "nomina": s["nomina"],
                "prog_ini": s["prog_ini"],
                "real_ini": s["real_ini"],
                "dif_ini": s["dif_ini"],
                "prog_fin": s["prog_fin"],
                "real_fin": s["real_fin"],
                "dif_fin": s["dif_fin"],
                "diagnostico_inicio": s["diagnostico_inicio"],
                "diagnostico_viaje": s["diagnostico_viaje"],
                "estado_viaje": s["estado_viaje"],
                "status": s["status"],
                "tipo_viaje": s["tipo_viaje"],
                "shift": s["shift"],
                "record_quality": s["record_quality"],
                "es_entrada": s["es_entrada"],
                "es_retraso": s["es_retraso"],
                "source": "api",
            },
        )

    RutaIndicadoresSemana.objects.filter(
        business_unit=bu, semana=semana_obj
    ).delete()
    for (group, ruta), data in ns.aggregate_servicios(servicios).items():
        RutaIndicadoresSemana.objects.update_or_create(
            business_unit=bu,
            semana=semana_obj,
            grupo=get_grupo(group),
            ruta_seq=ruta,
            defaults={
                "descripcion": data["descripcion"],
                "servicios": data["servicios"],
                "entradas": data["entradas"],
                "retrasos": data["retrasos"],
                "ns": data["ns"],
                "source": "api",
            },
        )
    return len(servicios)


@transaction.atomic
def sync_semana(year, week, bunits=None, force=False):
    """Sincroniza una semana operativa (lunes-domingo) para las UDN indicadas."""
    semana_obj, monday, sunday = _semana(year, week)
    start14 = (monday - timedelta(days=7)).isoformat()
    end = sunday.isoformat()

    resumen = {"year": year, "week": week, "bunits": [], "clientes_cr": 0, "clientes_ns": 0, "gps": 0}

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
            t for t in trips if monday.isoformat() <= str(t.get("start_date") or "")[:10] <= end
        ]
        stats7 = cr.route_stats(trips7)

        _store_cr(semana_obj, bu, stats14, "14d")
        _store_cr(semana_obj, bu, stats7, "7d")

        # Viajes / NS (rid=5) de la semana exacta
        rows = []
        try:
            rows = api.fetch_report(bu, monday.isoformat(), end)
            if rows:
                _sync_servicios(semana_obj, bu, rows)
            else:
                SyncLog.objects.create(
                    proceso="servicios",
                    year=year,
                    week=week,
                    estado="parcial",
                    mensaje=f"{bu}: rid=5 vacío; no se reemplazó el detalle existente",
                )
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

        # Refinamiento GPS de rutas marcadas (14d y 7d)
        gps_n = _aplicar_refinamientos(
            semana_obj, bu, trips, rows, year, week, monday, start14, end
        )
        resumen["gps"] += gps_n

        # Recalcular agregados por cliente (mezcla API + GPS)
        _recompute_cliente_cr(semana_obj, "14d")
        _recompute_cliente_cr(semana_obj, "7d")
        resumen["clientes_cr"] = max(resumen["clientes_cr"], len(stats14), len(stats7))

        resumen["bunits"].append(
            {
                "bunit": bu,
                "trips": len(trips),
                "rutas14": len(stats14),
                "rutas7": len(stats7),
                "gps": gps_n,
            }
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
