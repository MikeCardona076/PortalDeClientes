"""Backfill de Calidad de Ruta por GPS (Traffilog) para un rango de semanas.

Dos fases:
  A) Descarga PARALELA de puntos GPS por (auto, día UTC) hacia GpsPunto.
  B) Cálculo SERIAL de CR/paradas por ruta-semana desde el caché.

Reanudable: si un car-día ya está en GpsPunto, no se vuelve a pedir.

Ejemplo:
  python manage.py backfill_gps 2026 --desde 25 --hasta 41 --bunit set_tj2 --workers 6
"""

import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.db import close_old_connections

from apps.bustrax import client as api
from apps.bustrax import gps
from apps.bustrax.weeks import week_window
from apps.core.models import (
    BusinessUnit,
    GpsPunto,
    RefinamientoRuta,
    ServicioRutaSemana,
)
from apps.sync.services import _aplicar_refinamientos, _recompute_cliente_cr, _semana


class Command(BaseCommand):
    help = "Backfill de CR por GPS (descarga paralela + cálculo)."

    def add_arguments(self, parser):
        parser.add_argument("year", type=int)
        parser.add_argument("--desde", type=int, default=1)
        parser.add_argument("--hasta", type=int, default=None)
        parser.add_argument("--bunit", default="set_tj2")
        parser.add_argument("--workers", type=int, default=6)
        parser.add_argument("--grupo", default=None, help="Restringe a un group exacto.")
        parser.add_argument("--solo-descarga", action="store_true")
        parser.add_argument("--solo-calculo", action="store_true")
        parser.add_argument("--limite", type=int, default=0, help="Máx. car-días (pruebas).")

    # ------------------------------------------------------------------ Fase A
    def _car_dias(self, bu, year, desde, hasta, grupo):
        monday0, _ = week_window(year, desde)
        _, sunday_n = week_window(year, hasta)
        start = (monday0 - timedelta(days=7)).isoformat()
        end = sunday_n.isoformat()

        refs = set(
            RefinamientoRuta.objects.filter(
                grupo__business_unit__code=bu
            ).values_list("grupo_id", "ruta_seq")
        )
        qs = (
            ServicioRutaSemana.objects.filter(
                business_unit__code=bu,
                shift="IN",
                tipo_viaje="N",
                fecha_inicio__gte=start,
                fecha_inicio__lte=end,
            )
            .exclude(car="")
            .values_list("grupo_id", "ruta_seq", "car", "fecha_inicio")
            .distinct()
        )
        needed = set()
        for grupo_id, ruta_seq, car, fecha in qs:
            if refs and (grupo_id, ruta_seq) not in refs:
                continue
            needed.add((str(car), fecha.isoformat()))
            needed.add((str(car), (fecha + timedelta(days=1)).isoformat()))
        return needed

    def _descargar(self, needed, workers, limite=0):
        cached = set(
            GpsPunto.objects.filter(car__in={c for c, _ in needed}).values_list(
                "car", "dia_utc"
            )
        )
        cached = {(c, d.isoformat()) for c, d in cached}
        items = sorted(needed - cached)
        if limite:
            items = items[:limite]
        self.stdout.write(
            f"Fase A: {len(items)} car-días por descargar, "
            f"{len(needed) - len(items)} ya en caché."
        )
        if not items:
            return

        local = threading.local()
        contador = {"ok": 0, "err": 0}
        lock = threading.Lock()

        def _client():
            c = getattr(local, "c", None)
            if c is None:
                c = gps.TraffilogClient()
                c.login()
                local.c = c
            return c

        def work(item):
            car, dia = item
            try:
                gps._db_day_points(_client(), car, dia)
                key = "ok"
            except Exception:
                key = "err"
            finally:
                close_old_connections()
            with lock:
                contador[key] += 1
                n = contador["ok"] + contador["err"]
                if n % 100 == 0:
                    self.stdout.write(
                        f"  ... {n}/{len(items)} "
                        f"(ok={contador['ok']} err={contador['err']})"
                    )

        with ThreadPoolExecutor(max_workers=workers) as ex:
            for _ in ex.map(work, items):
                pass
        self.stdout.write(
            self.style.WARNING(
                f"Fase A lista: ok={contador['ok']} err={contador['err']}"
            )
        )

    # ------------------------------------------------------------------ Fase B
    def _calcular(self, bu, year, desde, hasta, grupo=None):
        for week in range(desde, hasta + 1):
            try:
                semana_obj, monday, sunday = _semana(year, week)
            except ValueError:
                continue
            start14 = (monday - timedelta(days=7)).isoformat()
            end = sunday.isoformat()
            try:
                rows = api.fetch_report(bu, monday.isoformat(), end)
            except api.BustraxError as exc:
                self.stderr.write(f"S{week}: rid=5 no disponible ({exc})")
                continue
            bu_obj, _ = BusinessUnit.objects.get_or_create(
                code=bu, defaults={"nombre": bu}
            )
            try:
                n = _aplicar_refinamientos(
                    semana_obj, bu, [], rows, year, week, monday, start14, end,
                    grupo=grupo,
                )
            except Exception as exc:  # noqa: BLE001 (resiliencia ante Traffilog)
                self.stderr.write(f"S{week}: refinamiento GPS falló ({exc})")
                continue
            _recompute_cliente_cr(semana_obj, "7d", bu_obj)
            _recompute_cliente_cr(semana_obj, "14d", bu_obj)
            self.stdout.write(f"S{week}: {n} rutas refinadas (gps).")

    def handle(self, *args, **o):
        year, bu = o["year"], o["bunit"]
        desde = o["desde"]
        hasta = o["hasta"] or desde
        if o["solo_descarga"] and o["solo_calculo"]:
            self.stderr.write("No combines --solo-descarga y --solo-calculo.")
            return
        self.stdout.write(f"Backfill GPS {year} S{desde}-S{hasta} · {bu}")

        if not o["solo_calculo"]:
            needed = self._car_dias(bu, year, desde, hasta, o["grupo"])
            self._descargar(needed, o["workers"], o["limite"])

        if not o["solo_descarga"]:
            self._calcular(bu, year, desde, hasta, o["grupo"])

        self.stdout.write(self.style.SUCCESS("Backfill GPS terminado."))
