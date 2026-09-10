from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from apps.bustrax.weeks import current_week, sunday_of_week, weeks_of_year
from apps.core.models import (
    Cliente,
    CRClienteSemana,
    CRRutaSemana,
    Semana,
    ViajeSemana,
)
from apps.core.scoping import get_clientes_for_user


def _int_arg(request, name, default):
    try:
        return int(request.GET.get(name, default))
    except (TypeError, ValueError):
        return default


@login_required
def index(request):
    clientes, es_admin = get_clientes_for_user(request.user)
    if not es_admin:
        clientes = clientes.filter(activo=True)

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
            "es_admin": es_admin,
            "clientes_filtro": clientes_filtro,
            "cliente_sel": cliente_sel,
            "semana_sel": semana_sel,
        },
    )


@login_required
def cliente(request):
    clientes, es_admin = get_clientes_for_user(request.user)
    nombre = request.GET.get("cliente", "")
    cliente_obj = get_object_or_404(Cliente, nombre=nombre)
    if not es_admin and not clientes.filter(pk=cliente_obj.pk).exists():
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

    # Serie de las últimas 11 semanas (según DB)
    serie = []
    semanas_prev = list(
        Semana.objects.filter(year=year, week__lte=week).order_by("-week")[:11]
    )[::-1]
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
        detalle = list(
            CRRutaSemana.objects.filter(
                grupo__cliente=cliente_obj, semana=semana, window_mode=window
            ).order_by("-calidad")
        )

    return render(
        request,
        "metricas/cliente.html",
        {
            "cliente": cliente_obj,
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
