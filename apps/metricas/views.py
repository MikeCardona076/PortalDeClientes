from urllib.parse import quote

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.mail import EmailMultiAlternatives
from django.core.validators import validate_email
from django.http import HttpResponseForbidden, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils import timezone
from django.utils.formats import date_format

from apps.bustrax import ns
from apps.bustrax.weeks import current_week, prev_week, weeks_of_year
from apps.core.models import (
    BusinessUnit,
    Cliente,
    ComentarioSemana,
    CRClienteSemana,
    CRRutaSemana,
    ParadaRutaSemana,
    PerfilUsuario,
    RutaIndicadoresSemana,
    Semana,
    ServicioRutaSemana,
    ViajeSemana,
)
from apps.core.scoping import get_scope_for_user


CR_WINDOWS = ("7d", "14d")


def _window_arg(request, source=None):
    """Ventana CR solicitada, validada y con el default del proyecto."""
    source = request.GET if source is None else source
    default = settings.CR_WINDOW_DEFAULT
    if default not in CR_WINDOWS:
        default = "14d"
    window = source.get("window") or default
    return window if window in CR_WINDOWS else default


def _int_arg(request, name, default):
    try:
        return int(request.GET.get(name, default))
    except (TypeError, ValueError):
        return default


def _int_post(request, name, default):
    try:
        return int(request.POST.get(name, default))
    except (TypeError, ValueError):
        return default


def _stop_key(value):
    """Orden natural por Stop: 2 antes que 10, sin fallar con no numéricos."""
    s = str(value or "").strip()
    if s.isdigit():
        return (0, int(s), "")
    return (1, 0, s)


def _udn_default(qs):
    """Prefiere la UDN por defecto de settings; si no está, la primera."""
    return qs.filter(code=settings.DEFAULT_UDN).first() or qs.first()


def _udns_disponibles(business_units, udn=None):
    """UDN visibles para el selector (activas) más la seleccionada si falta."""
    udns = list(business_units.filter(activa=True).order_by("nombre"))
    if udn and not any(b.code == udn for b in udns):
        actual = (
            business_units.filter(code=udn).first()
            or BusinessUnit.objects.filter(code=udn).first()
        )
        if actual is not None:
            udns.append(actual)
    return udns


def _udn_arg(request, business_units=None, es_admin=False):
    """Código de UDN solicitado dentro del scope del usuario."""
    code = (request.GET.get("udn") or "").strip()
    if es_admin:
        if code and BusinessUnit.objects.filter(code=code).exists():
            return code
        bu = _udn_default(BusinessUnit.objects.filter(activa=True).order_by("code"))
        return bu.code if bu else settings.DEFAULT_UDN
    if business_units is not None:
        if code and business_units.filter(code=code).exists():
            return code
        bu = _udn_default(
            business_units.filter(activa=True).order_by("code")
        ) or _udn_default(business_units.order_by("code"))
        return bu.code if bu else None
    bu = _udn_default(BusinessUnit.objects.filter(activa=True).order_by("code"))
    return bu.code if bu else settings.DEFAULT_UDN


def _get_udn_bu(code):
    return BusinessUnit.objects.filter(code=code).first()


def _comentario_json(comentario, user, es_admin):
    """Representación del comentario para la API/JS."""
    return {
        "id": comentario.id,
        "texto": comentario.texto,
        "autor": comentario.autor_nombre(),
        "creado": date_format(
            timezone.localtime(comentario.creado), "d M Y H:i"
        ),
        "puede_borrar": bool(
            es_admin
            or (comentario.autor_id and comentario.autor_id == user.id)
        ),
    }


def _resumen_comentario(comentarios):
    """Resumen corto del último comentario para tooltips de la matriz."""
    if not comentarios:
        return ""
    c = comentarios[-1]
    texto = (c.texto or "").strip().replace("\n", " ")
    if len(texto) > 80:
        texto = texto[:79] + "…"
    return f"{c.autor_nombre()}: {texto}"


def _cliente_bu_scope(request, cliente_nombre, udn):
    """Valida cliente y UDN contra el scope del usuario.

    Devuelve (cliente, bu, es_admin, error_response). error_response es None
    cuando la validación pasa.
    """
    clientes, business_units, es_admin = get_scope_for_user(request.user)
    cliente_obj = Cliente.objects.filter(nombre=cliente_nombre).first()
    if cliente_obj is None:
        return None, None, es_admin, JsonResponse(
            {"error": "Cliente no encontrado"}, status=404
        )
    if not es_admin and not clientes.filter(pk=cliente_obj.pk).exists():
        return None, None, es_admin, JsonResponse(
            {"error": "No autorizado"}, status=403
        )
    bu = _get_udn_bu(udn) if udn else None
    if bu is None or (not es_admin and not business_units.filter(pk=bu.pk).exists()):
        return None, None, es_admin, JsonResponse(
            {"error": "UDN no encontrada"}, status=404
        )
    return cliente_obj, bu, es_admin, None


@login_required
def index(request):
    clientes, business_units, es_admin = get_scope_for_user(request.user)
    if not es_admin:
        clientes = clientes.filter(
            activo=True, grupos__business_unit__in=business_units
        ).distinct()

    udn = _udn_arg(request, business_units, es_admin) or "set_tj2"
    bu = _get_udn_bu(udn)
    anio_actual = current_week()[0]
    db_years = set(Semana.objects.values_list("year", flat=True).distinct())
    years = sorted(db_years | {anio_actual}, reverse=True)
    year = _int_arg(request, "anio", anio_actual)
    if year not in years:
        years = sorted(set(years) | {year}, reverse=True)

    window = _window_arg(request)

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
            semana__year=year, window_mode=window, cliente__in=clientes,
            business_unit=bu,
        )
    }
    viajes = {
        (v.cliente_id, v.semana_id): v
        for v in ViajeSemana.objects.filter(
            semana__year=year, cliente__in=clientes, business_unit=bu
        )
    }

    # Comentarios del año por cliente/semana (para la insignia de la matriz)
    comentarios = {}
    if bu is not None:
        for comentario in (
            ComentarioSemana.objects.filter(
                business_unit=bu, semana__year=year, cliente__in=clientes
            )
            .select_related("autor")
            .order_by("creado")
        ):
            comentarios.setdefault(
                (comentario.cliente_id, comentario.semana_id), []
            ).append(comentario)

    rows = []
    for cliente in clientes:
        cells = []
        total = 0
        for w in week_nums:
            s = semanas.get(w)
            v = viajes.get((cliente.id, s.id)) if s else None
            c = cr.get((cliente.id, s.id)) if s else None
            cs = comentarios.get((cliente.id, s.id), []) if s else []
            cells.append(
                {
                    "week": w,
                    "viajes": v.total if v else 0,
                    "ns": v.ns if v else None,
                    "cr": c.calidad if c else None,
                    "n_comentarios": len(cs),
                    "comentario_resumen": _resumen_comentario(cs),
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
            "udns": _udns_disponibles(business_units, udn),
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
    window = _window_arg(request)

    semana = Semana.objects.filter(year=year, week=week).first()
    kpi_viajes = kpi_ns = kpi_entradas = kpi_ret = None
    cr_actual = None
    if semana:
        v = ViajeSemana.objects.filter(
            cliente=cliente_obj, semana=semana, business_unit=bu
        ).first()
        if v:
            kpi_viajes, kpi_ns = v.total, v.ns
            kpi_entradas, kpi_ret = v.entradas, v.retrasos
        c = CRClienteSemana.objects.filter(
            cliente=cliente_obj, semana=semana, window_mode=window, business_unit=bu
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
        v = ViajeSemana.objects.filter(
            cliente=cliente_obj, semana=s, business_unit=bu
        ).first()
        c = CRClienteSemana.objects.filter(
            cliente=cliente_obj, semana=s, window_mode=window, business_unit=bu
        ).first()
        serie.append(
            {
                "label": f"S{s.week}",
                "year": s.year,
                "week": s.week,
                "semana_id": s.id,
                "inicio": s.inicio,
                "fin": s.fin,
                "viajes": v.total if v else 0,
                "ns": v.ns if v else None,
                "cr": c.calidad if c else None,
            }
        )

    # Comentarios (hilo) del cliente + UDN: mapa completo e historial
    comentarios_map = {}
    for comentario in (
        ComentarioSemana.objects.filter(cliente=cliente_obj, business_unit=bu)
        .select_related("autor", "semana")
        .order_by("creado")
    ):
        comentarios_map.setdefault(comentario.semana_id, []).append(comentario)

    comentarios_json = {}
    for lista in comentarios_map.values():
        s = lista[0].semana
        comentarios_json[f"{s.year}-{s.week}"] = {
            "year": s.year,
            "week": s.week,
            "semana_id": s.id,
            "inicio": s.inicio,
            "fin": s.fin,
            "comentarios": [
                _comentario_json(c, request.user, es_admin) for c in lista
            ],
        }

    for item in serie:
        info = comentarios_json.get(f"{item['year']}-{item['week']}")
        item["comentarios"] = info["comentarios"] if info else []
        item["ultimo"] = item["comentarios"][-1] if item["comentarios"] else None

    historial = []
    for lista in comentarios_map.values():
        s = lista[0].semana
        serializados = comentarios_json[f"{s.year}-{s.week}"]["comentarios"]
        historial.append(
            {
                "year": s.year,
                "week": s.week,
                "semana_id": s.id,
                "inicio": s.inicio,
                "fin": s.fin,
                "comentarios": serializados,
                "ultimo": serializados[-1],
            }
        )
    historial.sort(key=lambda h: (h["year"], h["week"]), reverse=True)

    historial_meses = []
    for h in historial:
        clave = h["inicio"].strftime("%Y-%m")
        if not historial_meses or historial_meses[-1]["clave"] != clave:
            historial_meses.append(
                {
                    "clave": clave,
                    "nombre": date_format(h["inicio"], "F Y").capitalize(),
                    "semanas": [],
                }
            )
        historial_meses[-1]["semanas"].append(h)

    detalle = []
    if semana:
        indicadores = list(
            RutaIndicadoresSemana.objects.filter(
                business_unit=bu,
                grupo__cliente=cliente_obj,
                semana=semana,
                window_mode=window,
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
            "udns": _udns_disponibles(business_units, udn),
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
            "historial_meses": historial_meses,
            "comentarios_json": comentarios_json,
            "detalle": detalle,
            "correos_cliente": _correos_cliente(
                cliente_obj, bu, excluir=request.user.email
            ),
            "es_admin": es_admin,
            "sem_actual": current_week()[1],
        },
    )


def _correos_cliente(cliente_obj, bu, excluir=None):
    """Correos de superusuarios y de perfiles ligados a cliente/planta."""
    correos = set()

    for user in User.objects.filter(is_superuser=True, is_active=True).select_related(
        "perfil"
    ):
        if user.email:
            correos.add(user.email.strip().lower())
        perfil = getattr(user, "perfil", None)
        if perfil:
            for correo in perfil.correos or []:
                if correo:
                    correos.add(correo.strip().lower())

    perfiles = PerfilUsuario.objects.filter(
        clientes=cliente_obj, business_units=bu
    ).select_related("user")
    for perfil in perfiles:
        for correo in perfil.correos or []:
            if correo:
                correos.add(correo.strip().lower())
        if perfil.user.email:
            correos.add(perfil.user.email.strip().lower())

    if excluir:
        correos.discard(excluir.strip().lower())
    return sorted(correos)


def _parse_correos(texto):
    correos = []
    for parte in (texto or "").replace(";", ",").replace("\n", ",").split(","):
        correo = parte.strip()
        if not correo:
            continue
        try:
            validate_email(correo)
        except ValidationError:
            continue
        if correo not in correos:
            correos.append(correo)
    return correos


def _detalle_email(cliente_obj, bu, year, week, window):
    """Datos del correo: KPIs, tabla por ruta y retrasos de la semana."""
    semana = Semana.objects.filter(year=year, week=week).first()
    kpi_viajes = kpi_ns = kpi_entradas = kpi_ret = None
    cr_actual = None
    if semana:
        v = ViajeSemana.objects.filter(
            cliente=cliente_obj, semana=semana, business_unit=bu
        ).first()
        if v:
            kpi_viajes, kpi_ns = v.total, v.ns
            kpi_entradas, kpi_ret = v.entradas, v.retrasos
        c = CRClienteSemana.objects.filter(
            cliente=cliente_obj, semana=semana, window_mode=window, business_unit=bu
        ).first()
        if c:
            cr_actual = c.calidad

    detalle = []
    if semana:
        indicadores = list(
            RutaIndicadoresSemana.objects.filter(
                business_unit=bu,
                grupo__cliente=cliente_obj,
                semana=semana,
                window_mode=window,
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
                        "ruta_seq": ind.ruta_seq,
                        "descripcion": ind.descripcion or (c.descripcion if c else ""),
                        "servicios": ind.servicios,
                        "retrasos": ind.retrasos,
                        "ns": ind.ns,
                        "calidad": c.calidad if c else None,
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
                        "ruta_seq": r.ruta_seq,
                        "descripcion": r.descripcion,
                        "servicios": r.servicios,
                        "retrasos": 0,
                        "ns": None,
                        "calidad": r.calidad,
                    }
                )

    retrasos = []
    if semana:
        semanas = [semana]
        if window == "14d":
            pyear, pweek = prev_week(year, week)
            previa = Semana.objects.filter(year=pyear, week=pweek).first()
            if previa is not None:
                semanas.append(previa)
        retrasos = list(
            ServicioRutaSemana.objects.filter(
                business_unit=bu,
                semana__in=semanas,
                grupo__cliente=cliente_obj,
                dif_fin__gte=ns.RETRASO_MIN,
            )
            .select_related("grupo")
            .order_by("fecha_inicio", "ruta_seq", "real_fin")
        )

    return {
        "semana": semana,
        "kpi_viajes": kpi_viajes,
        "kpi_ns": kpi_ns,
        "kpi_entradas": kpi_entradas,
        "kpi_ret": kpi_ret,
        "cr_actual": cr_actual,
        "detalle": detalle,
        "retrasos": retrasos,
    }


@login_required
def enviar_detalle(request):
    """Envía por correo el detalle del cliente (solo admin)."""
    if request.method != "POST":
        return redirect("metricas:index")

    clientes, business_units, es_admin = get_scope_for_user(request.user)
    if not es_admin:
        return HttpResponseForbidden("Solo administradores.")

    cliente_obj = get_object_or_404(Cliente, nombre=request.POST.get("cliente", ""))
    udn = (request.POST.get("udn") or "").strip()
    bu = _get_udn_bu(udn)
    if bu is None:
        messages.error(request, "UDN no encontrada.")
        return redirect("metricas:index")

    year = _int_post(request, "anio", current_week()[0])
    week = _int_post(request, "semana", current_week()[1])
    window = _window_arg(request, source=request.POST)

    correos = _parse_correos(request.POST.get("destinatarios", ""))
    propio = (request.user.email or "").strip().lower()
    if propio:
        correos = [c for c in correos if c.lower() != propio]
    destino = (
        f"{reverse('metricas:cliente')}?cliente={quote(cliente_obj.nombre)}"
        f"&udn={quote(udn)}&anio={year}&semana={week}&window={window}"
    )
    if not correos:
        messages.error(request, "Agrega al menos un correo válido.")
        return redirect(destino)

    datos = _detalle_email(cliente_obj, bu, year, week, window)
    html = render_to_string(
        "emails/detalle_cliente.html",
        {
            "cliente": cliente_obj,
            "bu": bu,
            "udn": udn,
            "year": year,
            "week": week,
            "window": window,
            **datos,
        },
    )
    asunto = f"Detalle {cliente_obj.nombre} · Semana {week} {year} · {udn}"
    texto = (
        f"Detalle {cliente_obj.nombre} · Semana {week} {year} · {udn}\n"
        f"Total viajes: {datos['kpi_viajes']}\n"
        f"NS: {datos['kpi_ns']}\n"
        f"CR {window}: {datos['cr_actual']}\n"
    )
    msg = EmailMultiAlternatives(
        asunto, texto, settings.DEFAULT_FROM_EMAIL, correos
    )
    msg.attach_alternative(html, "text/html")
    try:
        msg.send(fail_silently=False)
        messages.success(request, f"Correo enviado a {', '.join(correos)}.")
    except Exception as exc:
        messages.error(request, f"No se pudo enviar el correo: {exc}")
    return redirect(destino)


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
    window = _window_arg(request)
    semana = Semana.objects.filter(year=year, week=week).first()
    if semana is None:
        return JsonResponse({"total": 0, "page": 1, "page_size": 100, "rows": []})

    semanas = [semana]
    if window == "14d":
        pyear, pweek = prev_week(year, week)
        previa = Semana.objects.filter(year=pyear, week=pweek).first()
        if previa is not None:
            semanas.append(previa)

    qs = ServicioRutaSemana.objects.filter(
        business_unit=bu, semana__in=semanas, grupo__cliente=cliente_obj
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


@login_required
def paradas(request):
    """Detalle JSON por parada de una ruta."""
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
    window = _window_arg(request)
    semana = Semana.objects.filter(year=year, week=week).first()
    if semana is None:
        return JsonResponse({"total": 0, "window": window, "rows": []})

    qs = ParadaRutaSemana.objects.filter(
        business_unit=bu,
        semana=semana,
        grupo__cliente=cliente_obj,
        window_mode=window,
    )
    ruta = (request.GET.get("ruta") or "").strip()
    grupo = (request.GET.get("grupo") or "").strip()
    if ruta:
        qs = qs.filter(ruta_seq=ruta)
    if grupo.isdigit():
        qs = qs.filter(grupo_id=int(grupo))

    rows = []
    for p in sorted(qs, key=lambda x: (x.ruta_seq, _stop_key(x.stop_id))):
        rows.append(
            {
                "stop_id": p.stop_id,
                "descripcion": p.descripcion,
                "lat": p.lat,
                "lng": p.lng,
                "servicios": p.servicios,
                "detectadas": p.detectadas,
                "detenidas": p.detenidas,
                "servicios_gps": p.servicios_gps,
                "vel_min": p.vel_min,
                "idle_seg": p.idle_seg,
                "calidad": p.calidad,
                "ultima_deteccion": p.ultima_deteccion.isoformat()
                if p.ultima_deteccion
                else "",
                "source": p.source,
            }
        )
    return JsonResponse({"total": len(rows), "window": window, "rows": rows})


@login_required
def comentario_crear(request):
    """Agrega un comentario al hilo de una semana (cliente + UDN)."""
    if request.method != "POST":
        return JsonResponse({"error": "Método no permitido"}, status=405)

    cliente_obj, bu, es_admin, error = _cliente_bu_scope(
        request, request.POST.get("cliente", ""), request.POST.get("udn", "")
    )
    if error is not None:
        return error

    texto = (request.POST.get("texto") or "").strip()
    if not texto:
        return JsonResponse({"error": "El comentario está vacío."}, status=400)
    if len(texto) > 2000:
        return JsonResponse(
            {"error": "El comentario es demasiado largo (máx. 2000 caracteres)."},
            status=400,
        )

    year = _int_post(request, "anio", current_week()[0])
    week = _int_post(request, "semana", current_week()[1])
    semana = Semana.objects.filter(year=year, week=week).first()
    if semana is None:
        return JsonResponse({"error": "Semana no encontrada"}, status=404)

    comentario = ComentarioSemana.objects.create(
        cliente=cliente_obj,
        business_unit=bu,
        semana=semana,
        autor=request.user,
        texto=texto,
    )
    return JsonResponse(
        {"ok": True, "comentario": _comentario_json(comentario, request.user, es_admin)}
    )


@login_required
def comentario_eliminar(request):
    """Elimina un comentario. Solo el autor o un administrador."""
    if request.method != "POST":
        return JsonResponse({"error": "Método no permitido"}, status=405)

    try:
        comentario_id = int(request.POST.get("id", ""))
    except (TypeError, ValueError):
        return JsonResponse({"error": "Comentario no encontrado"}, status=404)

    clientes, business_units, es_admin = get_scope_for_user(request.user)
    comentario = (
        ComentarioSemana.objects.filter(pk=comentario_id)
        .select_related("autor")
        .first()
    )
    if comentario is None:
        return JsonResponse({"error": "Comentario no encontrado"}, status=404)
    if not es_admin and (
        not clientes.filter(pk=comentario.cliente_id).exists()
        or not business_units.filter(pk=comentario.business_unit_id).exists()
    ):
        return JsonResponse({"error": "No autorizado"}, status=403)
    if not es_admin and comentario.autor_id != request.user.id:
        return JsonResponse(
            {"error": "Solo el autor puede eliminar su comentario."}, status=403
        )

    comentario.delete()
    return JsonResponse({"ok": True})
