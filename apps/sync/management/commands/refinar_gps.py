"""Prueba/refina una ruta por GPS: `python manage.py refinar_gps 2026 6 --grupo SCN-SCHNEIDER --ruta 142`."""

from datetime import timedelta

from django.core.management.base import BaseCommand

from apps.bustrax import client as api
from apps.bustrax import gps
from apps.bustrax.weeks import week_window
from apps.core.models import CRRutaSemana, GrupoCliente, Semana
from apps.sync.services import _recompute_cliente_cr


class Command(BaseCommand):
    help = "Calcula la Calidad de Ruta por GPS para una ruta (14d y 7d)."

    def add_arguments(self, parser):
        parser.add_argument("year", type=int)
        parser.add_argument("week", type=int)
        parser.add_argument("--grupo", required=True, help="Group exacto, p.ej. SCN-SCHNEIDER")
        parser.add_argument("--ruta", required=True, help="sequential_id de la ruta, p.ej. 142")
        parser.add_argument("--bunit", default="set_tj2")
        parser.add_argument("--tol", type=int, default=200, help="Tolerancia en metros (plataforma=200)")
        parser.add_argument("--guardar", action="store_true", help="Guarda en CRRutaSemana/CRClienteSemana")

    def handle(self, *args, **o):
        year, week = o["year"], o["week"]
        sunday, saturday = week_window(year, week)
        start14 = (sunday - timedelta(days=7)).isoformat()
        end = saturday.isoformat()

        rows = api.fetch_report(o["bunit"], sunday.isoformat(), end)
        rows14 = api.fetch_report(o["bunit"], start14, end)
        mae = api.fetch_routes(o["bunit"])
        route = next(
            (r for r in mae
             if str(r.get("sequential_id")) == str(o["ruta"])
             and str(r.get("shift")) == "IN" and str(r.get("route_type")) == "N"),
            None,
        )
        if not route:
            self.stderr.write("Ruta no encontrada en el MAE.")
            return
        self.stdout.write(
            f"Ruta {o['ruta']} · {route.get('description')} · car {(route.get('car') or '')[:30]}"
        )

        grupo = None
        semana_obj = None
        if o["guardar"]:
            grupo, _ = GrupoCliente.objects.get_or_create(group=o["grupo"])
            semana_obj, _ = Semana.objects.get_or_create(
                year=year, week=week, defaults={"inicio": sunday, "fin": saturday}
            )

        client = gps.TraffilogClient()
        for mode, trips_src, ini in (
            ("7d", rows, sunday.isoformat()),
            ("14d", rows14, start14),
        ):
            calidad, n = gps.refinar_ruta(
                route, trips_src, year, week, tol_m=o["tol"], client=client, start=ini, end=end
            )
            self.stdout.write(f"  {mode}: calidad={calidad}% (servicios={n})")
            if o["guardar"] and calidad is not None:
                CRRutaSemana.objects.update_or_create(
                    grupo=grupo, semana=semana_obj, ruta_seq=o["ruta"], window_mode=mode,
                    defaults={"calidad": calidad, "source": "gps"},
                )
        if o["guardar"]:
            _recompute_cliente_cr(semana_obj, "14d")
            _recompute_cliente_cr(semana_obj, "7d")
        self.stdout.write(self.style.SUCCESS("Listo."))
