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
        monday, sunday = week_window(year, week)
        start14 = (monday - timedelta(days=7)).isoformat()
        end = sunday.isoformat()

        rows = api.fetch_report(o["bunit"], monday.isoformat(), end)
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
            grupo = GrupoCliente.objects.filter(
                group=o["grupo"], business_unit__code=o["bunit"]
            ).first()
            if grupo is None:
                self.stderr.write(
                    f"Grupo '{o['grupo']}' no existe; créalo antes en el admin."
                )
                return
            semana_obj, _ = Semana.objects.get_or_create(
                year=year, week=week, defaults={"inicio": monday, "fin": sunday}
            )

        client = gps.TraffilogClient()
        ruta_seq = str(o["ruta"]).zfill(4)
        for mode, trips_src, ini in (
            ("7d", rows, monday.isoformat()),
            ("14d", rows14, start14),
        ):
            calidad, n = gps.refinar_ruta(
                route, trips_src, year, week, tol_m=o["tol"], client=client, start=ini, end=end
            )
            self.stdout.write(f"  {mode}: calidad={calidad}% (servicios={n})")
            if o["guardar"] and calidad is not None:
                # Fila completa: `_recompute_cliente_cr` ignora las GPS sin servicios.
                CRRutaSemana.objects.update_or_create(
                    grupo=grupo, semana=semana_obj, ruta_seq=ruta_seq,
                    window_mode=mode,
                    defaults={
                        "descripcion": (route.get("description") or "")[:200],
                        "shift": str(route.get("shift") or ""),
                        "route_type": str(route.get("route_type") or ""),
                        "criterio": "gps",
                        "calidad": calidad,
                        "servicios": n,
                        "source": "gps",
                    },
                )
        if o["guardar"]:
            _recompute_cliente_cr(semana_obj, "14d", grupo.business_unit)
            _recompute_cliente_cr(semana_obj, "7d", grupo.business_unit)
        self.stdout.write(self.style.SUCCESS("Listo."))
