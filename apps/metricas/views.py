from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render

from apps.bustrax import ns
from apps.bustrax.weeks import current_week, weeks_of_year
from apps.core.models import (
    BusinessUnit,
    Cliente,
    CRClienteSemana,
    CRRutaSemana,
    RutaIndicadoresSemana,
    Semana,
    ServicioRutaSemana,
    ViajeSemana,
)
from apps.core.scoping import get_scope_for_user


def _int_arg(request, name, default):
    try:
        return int(request.GET.get(name, default))
    except (TypeError, ValueError):
        return default


def _udn_arg(request, business_units=None, es_admin=False):
    """Código de UDN solicitado dentro del scope del usuario."""
    code = (request.GET.get("udn") or "").strip()
    if es_admin:
        if code:
            return code
        bu = BusinessUnit.objects.filter(activa=True).order_by("code").first()
        return bu.code if bu else "set_tj2"
    if business_units is not None:
        if code and business_units.filter(code=code).exists():
            return code
        bu = (
            business_units.filter(activa=True).order_by("code").first()
            or business_units.order_by("code").first()
        )
        return bu.code if bu else None
    bu = BusinessUnit.objects.filter(activa=True).order_by("code").first()
    return bu.code if bu else "set_tj2"


def _get_udn_bu(code):
    return BusinessUnit.objects.filter(code=code).first()


@login_required
def index(request):
    clientes, business_units, es_admin = get_scope_for_user(request.user)
    if not es_admin:
        clientes = clientes.filter(
            activo=True, grupos__business_unit__in=business_units
        ).distinct()

    udn = _udn_arg(request, business_units, es_admin) or "set_tj2"
    anio_actual = current_week()[0]
    db_years = set(Semana.objects.values_list("year", flat=True).distinct())
    years = sorted(db_years | {anio_actual}, reverse=True)
    year = _int_arg(request, "anio", anio_actual)
    if year not in years:
        years = sorted(set(years) | {year}, reverse=True)

    window = request.GET.get("window", settings.CR_WINDOW_DEFAULT)
    if window not in ("14d", "7d"):
        window = "14d"

    # Todas las semanas del año (aunque no tengan datos aún)
    if year == anio_actual:
        max_week = current_week()[1]
    else:
        wl = weeks_of_year(year)
        max_week = max(wl) if wl else 52
    all_weeks = list(range(1, max_week + 1))

    # Filtros (solo admin)
    cliente_sel = request.GET.get("cliente", "") if es_admin else ""
    semana_sel = None
    if es_admin:
        if cliente_sel:
            try:
                clientes = clientes.filter(pk=int(cliente_sel))
            except (TypeError, ValueError):
                cliente_sel = ""
        try:
            semana_sel = int(request.GET.get("semana", "")) if request.GET.get("semana") else None
        except (TypeError, ValueError):
            semana_sel = None
        week_nums = [semana_sel] if semana_sel in all_weeks else all_weeks
        if semana_sel not in all_weeks:
            semana_sel = None
    else:
        week_nums = all_weeks

    semanas = {s.week: s for s in Semana.objects.filter(year=year)}

    # Datos por cliente/semana
    cr = {
        (r.cliente_id, r.semana_id): r
        for r in CRClienteSemana.objects.filter(
            semana__year=year, window_mode=window, cliente__in=clientes
        )
    }
    viajes = {
        (v.cliente_id, v.semana_id): v
        for v in ViajeSemana.objects.filter(semana__year=year, cliente__in=clientes)
    }

    rows = []
    for cliente in clientes:
        cells = []
        total = 0
        for w in week_nums:
            s = semanas.get(w)
            v = viajes.get((cliente.id, s.id)) if s else None
            c = cr.get((cliente.id, s.id)) if s else None
            cells.append(
                {
                    "week": w,
                    "viajes": v.total if v else 0,
                    "ns": v.ns if v else None,
                    "cr": c.calidad if c else None,
                }
            )
            total += (v.total if v else 0)
        if total == 0 and not any(c["cr"] for c in cells):
            continue
        rows.append({"cliente": cliente, "cells": cells, "total": total})

    rows.sort(key=lambda r: -r["total"])

    clientes_filtro = (
        Cliente.objects.filter(activo=True).order_by("nombre")
        if es_admin
        else Cliente.objects.none()
    )

    return render(
        request,
        "metricas/index.html",
        {
            "years": years or [year],
            "year": year,
            "window": window,
            "week_nums": week_nums,
            "all_weeks": all_weeks,
            "rows": rows,
            "sem_actual": current_week()[1],
            "udn": udn,
            "es_admin": es_admin,
            "clientes_filtro": clientes_filtro,
            "cliente_sel": cliente_sel,
            "semana_sel": semana_sel,
        },
    )


@login_required
def cliente(request):
    clientes, business_units, es_admin = get_scope_for_user(request.user)
    nombre = request.GET.get("cliente", "")
    cliente_obj = get_object_or_404(Cliente, nombre=nombre)
    if not es_admin and not clientes.filter(pk=cliente_obj.pk).exists():
        return redirect("metricas:index")

    udn = _udn_arg(request, business_units, es_admin)
    bu = _get_udn_bu(udn) if udn else None
    if bu is None or (not es_admin and not business_units.filter(pk=bu.pk).exists()):
        return redirect("metricas:index")

    year = _int_arg(request, "anio", current_week()[0])
    week = _int_arg(request, "semana", current_week()[1])
    window = request.GET.get("window", settings.CR_WINDOW_DEFAULT)
    if window not in ("14d", "7d"):
        window = "14d"

    semana = Semana.objects.filter(year=year, week=week).first()
    kpi_viajes = kpi_ns = kpi_entradas = kpi_ret = None
    cr_actual = None
    if semana:
        v = ViajeSemana.objects.filter(cliente=cliente_obj, semana=semana).first()
        if v:
            kpi_viajes, kpi_ns = v.total, v.ns
            kpi_entradas, kpi_ret = v.entradas, v.retrasos
        c = CRClienteSemana.objects.filter(
            cliente=cliente_obj, semana=semana, window_mode=window
        ).first()
        if c:
            cr_actual = c.calidad

    # Serie de las últimas 11 semanas por fecha (soporta el cruce ISO 52/1)
    serie = []
    if semana:
        semanas_prev = list(
            Semana.objects.filter(inicio__lte=semana.inicio).order_by("-inicio")[:11]
        )[::-1]
    else:
        semanas_prev = []
    for s in semanas_prev:
        v = ViajeSemana.objects.filter(cliente=cliente_obj, semana=s).first()
        c = CRClienteSemana.objects.filter(
            cliente=cliente_obj, semana=s, window_mode=window
        ).first()
        serie.append(
            {
                "label": f"S{s.week}",
                "viajes": v.total if v else 0,
                "ns": v.ns if v else None,
                "cr": c.calidad if c else None,
            }
        )

    detalle = []
    if semana:
        indicadores = list(
            RutaIndicadoresSemana.objects.filter(
                business_unit=bu, grupo__cliente=cliente_obj, semana=semana
            )
            .select_related("grupo")
            .order_by("ruta_seq")
        )
        cr_map = {
            (r.grupo_id, r.ruta_seq): r
            for r in CRRutaSemana.objects.filter(
                grupo__cliente=cliente_obj,
                semana=semana,
                window_mode=window,
                grupo__business_unit=bu,
            )
        }
        if indicadores:
            for ind in indicadores:
                c = cr_map.get((ind.grupo_id, ind.ruta_seq))
                detalle.append(
                    {
                        "grupo": ind.grupo,
                        "ruta_seq": ind.ruta_seq,
                        "descripcion": ind.descripcion or (c.descripcion if c else ""),
                        "servicios": ind.servicios,
                        "retrasos": ind.retrasos,
                        "ns": ind.ns,
                        "calidad": c.calidad if c else None,
                        "source": c.source if c else ind.source,
                    }
                )
        else:
            for r in CRRutaSemana.objects.filter(
                grupo__cliente=cliente_obj,
                semana=semana,
                window_mode=window,
                grupo__business_unit=bu,
            ).order_by("-calidad"):
                detalle.append(
                    {
                        "grupo": r.grupo,
                        "ruta_seq": r.ruta_seq,
                        "descripcion": r.descripcion,
                        "servicios": r.servicios,
                        "retrasos": 0,
                        "ns": None,
                        "calidad": r.calidad,
                        "source": r.source,
                    }
                )

    return render(
        request,
        "metricas/cliente.html",
        {
            "cliente": cliente_obj,
            "udn": udn,
            "bu": bu,
            "year": year,
            "week": week,
            "window": window,
            "kpi_viajes": kpi_viajes,
            "kpi_ns": kpi_ns,
            "kpi_entradas": kpi_entradas,
            "kpi_ret": kpi_ret,
            "cr_actual": cr_actual,
            "serie": serie,
            "detalle": detalle,
            "sem_actual": current_week()[1],
        },
    )


@login_required
def retrasos(request):
    """Detalle JSON de servicios retrasados para el modal."""
    clientes, business_units, es_admin = get_scope_for_user(request.user)
    nombre = request.GET.get("cliente", "")
    cliente_obj = get_object_or_404(Cliente, nombre=nombre)
    if not es_admin and not clientes.filter(pk=cliente_obj.pk).exists():
        return JsonResponse({"error": "No autorizado"}, status=403)

    udn = _udn_arg(request, business_units, es_admin)
    bu = _get_udn_bu(udn) if udn else None
    if bu is None or (not es_admin and not business_units.filter(pk=bu.pk).exists()):
        return JsonResponse({"error": "UDN no encontrada"}, status=404)

    year = _int_arg(request, "anio", current_week()[0])
    week = _int_arg(request, "semana", current_week()[1])
    semana = Semana.objects.filter(year=year, week=week).first()
    if semana is None:
        return JsonResponse({"total": 0, "page": 1, "page_size": 100, "rows": []})

    qs = ServicioRutaSemana.objects.filter(
        business_unit=bu, semana=semana, grupo__cliente=cliente_obj
    ).select_related("grupo__cliente")

    ruta = (request.GET.get("ruta") or "").strip()
    grupo = (request.GET.get("grupo") or "").strip()
    if ruta:
        qs = qs.filter(ruta_seq=ruta)
    if grupo.isdigit():
        qs = qs.filter(grupo_id=int(grupo))

    # El modal muestra todos los Δ>=4 min, aunque no tengan record_quality.
    qs = qs.filter(dif_fin__gte=ns.RETRASO_MIN).order_by("fecha_inicio", "real_fin", "id")
    total = qs.count()
    page = max(1, _int_arg(request, "page", 1))
    page_size = 100
    filas = qs[(page - 1) * page_size: page * page_size]

    def hora(value):
        return value.strftime("%H:%M:%S") if value else ""

    def diag_fin(valor):
        if valor is None:
            return ""
        if ns.RETRASO_MIN <= valor < ns.RETRASO_MAX:
            return "Retrasado"
        return "A tiempo"

    rows = []
    for s in filas:
        rows.append(
            {
                "id": s.external_id,
                "fecha_inicio": s.fecha_inicio.isoformat() if s.fecha_inicio else "",
                "fecha_fin": s.fecha_fin.isoformat() if s.fecha_fin else "",
                "ruta": s.ruta_seq,
                "cliente": s.grupo.cliente.nombre,
                "udn": bu.code,
                "veh": s.car,
                "operador": s.operador,
                "nomina": s.nomina,
                "prog_ini": hora(s.prog_ini),
                "real_ini": hora(s.real_ini),
                "dif_ini": s.dif_ini,
                "prog_fin": hora(s.prog_fin),
                "real_fin": hora(s.real_fin),
                "dif_fin": s.dif_fin,
                "diagnostico_inicio": s.diagnostico_inicio,
                "diagnostico_fin": diag_fin(s.dif_fin),
            }
        )
    return JsonResponse({"total": total, "page": page, "page_size": page_size, "rows": rows})
